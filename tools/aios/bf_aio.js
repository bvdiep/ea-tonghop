// Backfill aios-base-db — write result to file to avoid stdout truncation
const { Client } = require('pg');
const fs = require('fs');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);
const c = new Client({ host: url.hostname, port: +url.port, user: decodeURIComponent(url.username), password: decodeURIComponent(url.password), database: url.pathname.slice(1), ssl: false });

let OUT = [];
const out = (s) => { OUT.push(s); };

(async () => {
  await c.connect();
  out('CONNECT ' + url.hostname + ':' + url.port + '/' + url.pathname.slice(1));

  const st = await c.query("SELECT (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL) AS platform, (SELECT count(*) FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL) AS ws_level, (SELECT count(*) FROM ba.usage_daily_summary WHERE user_id IS NOT NULL) AS user_level");
  out('BEFORE ' + JSON.stringify(st.rows[0]));

  const days = await c.query(`WITH raw_days AS (SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS d FROM ba.ai_usage UNION SELECT DISTINCT (created_at AT TIME ZONE 'UTC')::date AS d FROM ba.usage_events UNION SELECT DISTINCT (started_at AT TIME ZONE 'UTC')::date AS d FROM ba.cron_job_runs) SELECT to_char(d, 'YYYY-MM-DD') AS dstr FROM raw_days ORDER BY d`);
  out('DAYS ' + days.rows.length);

  let ok = 0, failed = [];
  for (const { dstr } of days.rows) {
    try { await c.query('SELECT ba.fn_usage_daily_rollup($1::date)', [dstr]); ok++; }
    catch (e) { failed.push({ dstr, reason: e.message.includes('null value') ? 'empty' : e.message.slice(0, 80) }); }
  }
  out('ROLLUP ok=' + ok + ' failed=' + JSON.stringify(failed));

  const fold = await c.query(`INSERT INTO ba.usage_daily_summary (date, workspace_id, user_id, model, provider, ai_calls, ai_calls_failed, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, reasoning_tokens, cost_usd, session_count, cron_runs, cron_failed, error_count, updated_at) SELECT date, workspace_id, NULL, model, provider, SUM(ai_calls), SUM(ai_calls_failed), SUM(input_tokens), SUM(output_tokens), SUM(cache_read_tokens), SUM(cache_write_tokens), SUM(reasoning_tokens), SUM(cost_usd), SUM(session_count), SUM(cron_runs), SUM(cron_failed), SUM(error_count), now() FROM ba.usage_daily_summary WHERE user_id IS NOT NULL AND workspace_id IS NOT NULL GROUP BY date, workspace_id, model, provider ON CONFLICT ON CONSTRAINT usage_daily_summary_uq DO UPDATE SET ai_calls=EXCLUDED.ai_calls, ai_calls_failed=EXCLUDED.ai_calls_failed, input_tokens=EXCLUDED.input_tokens, output_tokens=EXCLUDED.output_tokens, cache_read_tokens=EXCLUDED.cache_read_tokens, cache_write_tokens=EXCLUDED.cache_write_tokens, reasoning_tokens=EXCLUDED.reasoning_tokens, cost_usd=EXCLUDED.cost_usd, session_count=EXCLUDED.session_count, cron_runs=EXCLUDED.cron_runs, cron_failed=EXCLUDED.cron_failed, error_count=EXCLUDED.error_count, updated_at=now()`);
  out('WS_FOLD ' + fold.rowCount);

  const fix = await c.query(`UPDATE ba.usage_daily_summary s SET session_count = COALESCE(e.cnt, 0), updated_at = now() FROM (SELECT (created_at AT TIME ZONE 'UTC')::date AS d, workspace_id, count(*) AS cnt FROM ba.usage_events WHERE event_type = 'session_create' AND user_id IS NULL GROUP BY 1, 2) e WHERE s.user_id IS NULL AND s.workspace_id IS NOT NULL AND s.model IS NULL AND s.date = e.d AND s.workspace_id = e.workspace_id`);
  out('SESS_FIX ' + fix.rowCount);

  const raw = await c.query('SELECT count(*) calls, sum(cost_usd) cost FROM ba.ai_usage');
  const plat = await c.query('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL');
  const ws = await c.query('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE workspace_id IS NOT NULL AND user_id IS NULL');
  const usr = await c.query('SELECT sum(ai_calls) calls, sum(cost_usd) cost FROM ba.usage_daily_summary WHERE user_id IS NOT NULL');
  out('RAW ' + JSON.stringify(raw.rows[0]));
  out('PLAT ' + JSON.stringify(plat.rows[0]));
  out('WS ' + JSON.stringify(ws.rows[0]));
  out('USR ' + JSON.stringify(usr.rows[0]));

  const lv = await c.query("SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, count(*) AS n FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2");
  out('LEVELS ' + JSON.stringify(lv.rows));

  const cross = await c.query(`SELECT to_char(raw.d, 'YYYY-MM-DD') AS dstr, raw.calls raw_c, raw.cost raw_cost, s.calls sum_c, s.cost sum_cost FROM (SELECT (created_at AT TIME ZONE 'UTC')::date AS d, count(*) AS calls, sum(cost_usd) AS cost FROM ba.ai_usage GROUP BY 1) raw LEFT JOIN (SELECT date, sum(ai_calls) AS calls, sum(cost_usd) AS cost FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL GROUP BY 1) s ON s.date = raw.d ORDER BY raw.d`);
  out('CROSS ' + JSON.stringify(cross.rows));

  await c.end();
  fs.writeFileSync('/tmp/bf_result.txt', OUT.join('\n'));
  // also print for good measure
  console.log('OK wrote /tmp/bf_result.txt');
})().catch(e => { console.error('FATAL', e.message); process.exit(1); });
