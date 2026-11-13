// Backfill aios-base-db (port 15432) — REAL DB for aios.bsmlabs.io
// 1. Roll up days not yet rolled (catch-up using the repo's function)
// 2. Fold user-level → workspace-level rows (stopgap for the ws-level bug)
// 3. Verify raw == platform == ws-level totals

const { Client } = require('pg');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

const c = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function q(sql, params) {
  try {
    const r = await c.query(sql, params);
    return r.rows;
  } catch (e) {
    return [{ error: e.message }];
  }
}

async function main() {
  console.log('Connected to:', url.hostname + ':' + url.port + '/' + url.pathname.slice(1));

  // Current state
  const state = await q("SELECT (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL) AS platform, (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL) AS ws_level, (SELECT count(*) FROM ba.usage_daily_summary WHERE user_id IS NOT NULL) AS user_level");
  console.log('\n=== BEFORE: summary rows by level ===', JSON.stringify(state[0]));

  // ── Step 1: roll up all days not yet rolled ───────────────────────────────
  // Idempotent function — safe to re-run. The isDayRolledUp check in the
  // scheduler prevents re-rolling, but since cron may be disabled we iterate
  // explicitly and let the function's own DELETE+recompute handle it.
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
  console.log('\n=== days with raw data:', days.map(r => r.day).join(', '));

  let ok = 0, failed = [];
  for (const { day } of days) {
    try {
      await c.query('SELECT ba.fn_usage_daily_rollup($1::date)', [day]);
      ok++;
    } catch (e) {
      // Empty-day bug (no data at all in any source) — expected, no data lost
      if (e.message.includes('null value')) {
        failed.push({ day, reason: 'empty_day' });
      } else {
        failed.push({ day, reason: e.message });
      }
    }
  }
  console.log(`Step 1: rolled up ${ok}/${days.length} days, ${failed.length} empty-day skips`);

  // ── Step 2: fold user-level → workspace-level (replace semantics) ─────────
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
  console.log('Step 2: workspace-level rows upserted:', fold.rowCount);

  // Fix session_count: ws-level model-NULL should only count user-NULL events
  const fixSess = await c.query(`
    WITH ws_sums AS (
      SELECT s.date, s.workspace_id,
             COALESCE(e.cnt, 0) AS true_count
      FROM ba.usage_daily_summary s
      LEFT JOIN (
        SELECT (created_at AT TIME ZONE 'UTC')::date AS d, workspace_id, count(*) AS cnt
        FROM ba.usage_events WHERE event_type = 'session_create' AND user_id IS NULL
        GROUP BY 1, 2
      ) e ON e.d = s.date AND e.workspace_id = s.workspace_id
      WHERE s.user_id IS NULL AND s.workspace_id IS NOT NULL AND s.model IS NULL
    )
    UPDATE ba.usage_daily_summary s
    SET session_count = ws.true_count, updated_at = now()
    FROM ws_sums ws
    WHERE s.date = ws.date AND s.workspace_id = ws.workspace_id
      AND s.user_id IS NULL AND s.model IS NULL
  `);
  console.log('Step 3: session_count rows corrected:', fixSess.rowCount);

  // ── Step 4: verify ──────────────────────────────────────────────────────
  const raw = await q('SELECT count(*) calls, sum(cost_usd) cost FROM ba.ai_usage');
  const plat = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL');
  const ws = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL');
  const usr = await q('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE user_id IS NOT NULL');

  console.log('\n=== VERIFY (raw vs platform vs ws-level vs user-level) ===');
  console.log('  raw:      ', JSON.stringify(raw[0]));
  console.log('  platform: ', JSON.stringify(plat[0]));
  console.log('  ws-level: ', JSON.stringify(ws[0]));
  console.log('  user-level:', JSON.stringify(usr[0]));

  const lv2 = await q("SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, count(*) AS n, min(date) dmin, max(date) dmax FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2");
  console.log('\n=== summary rows by level AFTER ===');
  lv2.forEach(r => console.log('  platform=' + r.platform, 'user_null=' + r.user_null, 'n=' + r.n, 'range=' + r.dmin + '→' + r.dmax));

  // Raw vs platform per day
  const cross = await q(`
    SELECT to_char(raw.d, 'YYYY-MM-DD') AS day,
           raw.calls AS raw_calls, raw.cost AS raw_cost,
           s.calls AS sum_calls, s.cost AS sum_cost
    FROM (
      SELECT (created_at AT TIME ZONE 'UTC')::date AS d, count(*) calls, sum(cost_usd) cost
      FROM ba.ai_usage GROUP BY 1
    ) raw
    LEFT JOIN (
      SELECT date, sum(ai_calls) calls, sum(cost_usd) cost
      FROM ba.usage_daily_summary
      WHERE workspace_id IS NULL AND user_id IS NULL
      GROUP BY 1
    ) s ON s.date = raw.d
    ORDER BY raw.d
  `);
  console.log('\n=== per-day raw vs platform (must match) ===');
  cross.forEach(r => console.log('  ' + r.day + ' raw=' + r.raw_calls + ' $' + r.raw_cost + '  sum=' + r.sum_calls + ' $' + r.sum_cost));

  await c.end();
  process.exit(0);
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
