// Backfill aios-base-db (port 15432) — REAL DB for aios.bsmlabs.io
// Output goes to /app/backfill_result.json to avoid truncation.

const { Client } = require('pg');
const fs = require('fs');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

const log = [];
function L(label, data) {
  log.push({ label, data, ts: new Date().toISOString() });
  console.log(label + ': ' + JSON.stringify(data).slice(0, 300));
}

const c = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function q(sql, params) {
  try { const r = await c.query(sql, params); return r.rows; }
  catch (e) { return [{ error: e.message }]; }
}

async function main() {
  L('connect', url.hostname + ':' + url.port + '/' + url.pathname.slice(1));

  const state = await q("SELECT (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL) AS platform, (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL) AS ws_level, (SELECT count(*) FROM ba.usage_daily_summary WHERE user_id IS NOT NULL) AS user_level");
  L('before_summary_levels', state[0]);

  // Rollup days with raw data
  const days = await q(`
    WITH raw_days AS (
      SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS d FROM ba.ai_usage
      UNION
      SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS d FROM ba.usage_events
      UNION
      SELECT DISTINCT (started_at AT TIME ZONE 'UTC')::date AS d FROM ba.cron_job_runs
    )
    SELECT to_char(d, 'YYYY-MM-DD') AS day FROM raw_days ORDER BY d
  `);
  L('days_with_raw', days.length);

  let ok = 0, failed = [];
  for (const { day } of days) {
    try {
      await c.query('SELECT ba.fn_usage_daily_rollup($1::date)', [day]);
      ok++;
    } catch (e) {
      failed.push({ day, reason: e.message.includes('null value') ? 'empty_day' : e.message });
    }
  }
  L('rollup', { ok, failed });

  // Fold user-level to workspace-level
  const fold = await c.query(`
    INSERT INTO ba.usage_daily_summary
      (date, workspace_id, user_id, model, provider,
       ai_calls, ai_calls_failed, input_tokens, output_tokens,
       cache_read_tokens, cache_write_tokens, reasoning_tokens, cost_usd,
       session_count, cron_runs, cron_failed, error_count, updated_at)
    SELECT date, workspace_id, NULL, model, provider,
           SUM(ai_calls), SUM(ai_calls_failed), SUM(input_tokens), SUM(output_tokens),
           SUM(cache_read_tokens), SUM(cache_write_tokens), SUM(reasoning_tokens), SUM(cost_usd),
           SUM(session_count), SUM(cron_runs), SUM(cron_failed), SUM(error_count), now()
    FROM ba.usage_daily_summary
    WHERE user_id IS NOT NULL AND workspace_id IS NOT NULL
    GROUP BY date, workspace_id, model, provider
    ON CONFLICT ON CONSTRAINT usage_daily_summary_uq
    DO UPDATE SET
      ai_calls        = EXCLUDED.ai_calls,
      ai_calls_failed = EXCLUDED.ai_calls_failed,
      input_tokens    = EXCLUDED.input_tokens,
      output_tokens   = EXCLUDED.output_tokens,
      cache_read_tokens  = EXCLUDED.cache_read_tokens,
      cache_write_tokens = EXCLUDED.cache_write_tokens,
      reasoning_tokens   = EXCLUDED.reasoning_tokens,
      cost_usd        = EXCLUDED.cost_usd,
      session_count   = EXCLUDED.session_count,
      cron_runs       = EXCLUDED.cron_runs,
      cron_failed     = EXCLUDED.cron_failed,
      error_count     = EXCLUDED.error_count,
      updated_at      = now()
  `);
  L('ws_fold_upserted', fold.rowCount);

  // Fix session_count for ws-level model-NULL rows
  const fix = await c.query(`
    UPDATE ba.usage_daily_summary s
    SET session_count = COALESCE(e.cnt, 0), updated_at = now()
    FROM (
      SELECT (created_at AT TIME ZONE 'UTC')::date AS d, workspace_id, count(*) AS cnt
      FROM ba.usage_events WHERE event_type = 'session_create' AND user_id IS NULL
      GROUP BY 1, 2
    ) e
    WHERE s.user_id IS NULL AND s.workspace_id IS NOT NULL AND s.model IS NULL
      AND s.date = e.d AND s.workspace_id = e.workspace_id
  `);
  L('session_count_fixed', fix.rowCount);

  // Verify
  const raw = await q('SELECT count(*) calls, sum(cost_usd) cost FROM ba.ai_usage');
  const plat = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL');
  const ws = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL');
  const usr = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE user_id IS NOT NULL');

  L('verify', {
    raw: raw[0], platform: plat[0], ws_level: ws[0], user_level: usr[0],
  });

  const lv = await q("SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, count(*) AS n FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2");
  L('summary_levels_after', lv);

  const cross = await q(`
    SELECT to_char(raw.d, 'YYYY-MM-DD') day, raw.calls raw_c, raw.cost raw_cost,
           s.calls sum_c, s.cost sum_cost
    FROM (
      SELECT (created_at AT TIME ZONE 'UTC')::date d, count(*) calls, sum(cost_usd) cost
      FROM ba.ai_usage GROUP BY 1
    ) raw
    LEFT JOIN (
      SELECT date, sum(ai_calls) calls, sum(cost_usd) cost
      FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL GROUP BY 1
    ) s ON s.date = raw.d ORDER BY raw.d
  `);
  L('per_day_raw_vs_platform', cross);

  await c.end();
  fs.writeFileSync('/app/backfill_result.json', JSON.stringify(log, null, 2));
  console.log('\nDone. Full results in /app/backfill_result.json');
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
