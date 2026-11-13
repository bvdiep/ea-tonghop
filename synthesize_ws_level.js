// Final step: verify empty-day hypothesis, then synthesize the workspace-level
// rows the dashboard reads (stopgap until the rollup bug is fixed in-repo).
//
// Bug recap:
//  1. fn_usage_daily_rollup: platform INSERT ... SELECT SUM() FROM evts on a
//     day with ZERO events in all 3 sources produces one all-NULL row → NOT
//     NULL violation. Empty days crash — but they carry no data, so skipping
//     them loses nothing.
//  2. The rollup never writes workspace-level rows (user_id NULL, ws NOT NULL)
//     for user-attributed traffic, but /admin/usage reads exactly that level
//     for Overview / Finance-weekly / Performance-turns. All 239 rows are
//     user-attributed → dashboard main tabs empty despite data.
//
// This script:
//  A. Confirms every failed day is truly empty (no ai_usage, no events, no cron).
//  B. Folds user-level summary rows into workspace-level rows (pure aggregation,
//     replace-semantics upsert → idempotent). Reversible:
//     DELETE FROM ba.usage_daily_summary WHERE user_id IS NULL AND workspace_id IS NOT NULL;
//  C. Re-runs the dashboard simulation.

const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);
const { Client } = require('pg');
const client = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function main() {
  // ── A. Empty-day hypothesis ───────────────────────────────────────────────
  const empty = await client.query(`
    SELECT to_char(d, 'YYYY-MM-DD') AS day,
           (SELECT count(*) FROM ba.ai_usage u
             WHERE u.created_at >= d AND u.created_at < d + interval '1 day') AS usage_rows,
           (SELECT count(*) FROM ba.usage_events e
             WHERE e.created_at >= d AND e.created_at < d + interval '1 day') AS event_rows,
           (SELECT count(*) FROM ba.cron_job_runs r
             WHERE r.started_at >= d AND r.started_at < d + interval '1 day') AS cron_rows
    FROM generate_series('2026-06-30'::date, '2026-09-22'::date, '1 day') d
  `);
  const nonEmpty = empty.rows.filter(r => +r.usage_rows + +r.event_rows + +r.cron_rows > 0);
  const rolled = await client.query(
    'SELECT count(DISTINCT date) AS days FROM ba.usage_daily_summary'
  );
  console.log('=== A. days with ANY source data ===', nonEmpty.length,
    '| days rolled up ===', rolled.rows[0].days);
  const mismatch = nonEmpty.filter(r => {
    // a non-empty day must have a platform row
    return false; // presence checked via count below
  });
  // every non-empty day must appear in the summary
  const sumDays = new Set((await client.query('SELECT DISTINCT date FROM ba.usage_daily_summary')).rows.map(r => r.date.toISOString().slice(0, 10)));
  const missing = nonEmpty.filter(r => !sumDays.has(r.day));
  console.log('non-empty days missing from summary:', missing.length ? missing : 'NONE — no data lost');

  // ── B. Guard: no user-level rows with NULL workspace (would fold into platform) ──
  const stray = await client.query(
    'SELECT count(*) AS n FROM ba.usage_daily_summary WHERE user_id IS NOT NULL AND workspace_id IS NULL'
  );
  console.log('\n=== B. user-level rows with NULL workspace (must be 0) ===', stray.rows[0].n);
  if (+stray.rows[0].n > 0) {
    console.log('ABORT: unexpected rows — not folding.');
    return;
  }

  // Fold user-level → workspace-level (replace semantics, idempotent)
  const fold = await client.query(`
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
  console.log('workspace-level rows upserted:', fold.rowCount);

  // ── C. Dashboard simulation (default 30-day range + full range) ───────────
  const ws30 = await client.query(
    "SELECT count(*) AS n, sum(ai_calls) AS calls, sum(cost_usd) AS cost " +
    "FROM ba.usage_daily_summary WHERE date >= '2026-08-24' AND date < '2026-09-23' " +
    "AND user_id IS NULL AND workspace_id IS NOT NULL"
  );
  console.log('\n=== C. DASHBOARD workspace level, last 30d ===', JSON.stringify(ws30.rows[0]));

  const wsAll = await client.query(
    "SELECT count(*) AS n, sum(ai_calls) AS calls, sum(cost_usd) AS cost, sum(session_count) AS sessions " +
    "FROM ba.usage_daily_summary WHERE user_id IS NULL AND workspace_id IS NOT NULL"
  );
  console.log('=== DASHBOARD workspace level, all time ===', JSON.stringify(wsAll.rows[0]));

  // Cross-check: ws-level totals must equal platform totals
  const plat = await client.query(
    "SELECT sum(ai_calls) AS calls, sum(cost_usd) AS cost FROM ba.usage_daily_summary " +
    "WHERE workspace_id IS NULL AND user_id IS NULL"
  );
  console.log('=== platform level (must match ws-level) ===', JSON.stringify(plat.rows[0]));

  // Row counts by level
  const lv = await client.query(
    "SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, count(*) AS n " +
    "FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2"
  );
  console.log('=== rows by level ===', JSON.stringify(lv.rows));
}

client.connect().then(main).then(() => client.end()).catch(e => { console.error('FATAL:', e.message); process.exit(1); });
