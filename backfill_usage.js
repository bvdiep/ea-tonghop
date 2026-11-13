// Backfill usage data for /admin/usage dashboard (spp-dev, aios.bsmlabs.io)
//
// Usage: node backfill_usage.js preflight   (read-only checks)
//        node backfill_usage.js run         (derive events + rollup + verify)
//
// Safety: no DDL, no service restarts, no container changes. Only:
//   - INSERT ... ON CONFLICT DO NOTHING into ba.usage_events (currently empty),
//     rows marked payload.backfill = 'derived-from-ai_usage' (reversible)
//   - ba.fn_usage_daily_rollup(d) per day — the repo's own idempotent
//     function (DELETE + recompute per day) on the currently-empty summary.

const dbUrl = process.env.SUPABASE_DB_URL;
if (!dbUrl) {
  console.error('FATAL: SUPABASE_DB_URL not set');
  process.exit(1);
}
const url = new URL(dbUrl);
const { Client } = require('pg');

const UUID_RE =
  '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';

const client = new Client({
  host: url.hostname,
  port: parseInt(url.port),
  user: decodeURIComponent(url.username),
  password: decodeURIComponent(url.password),
  database: url.pathname.slice(1),
  ssl: false,
});

const phase = process.argv[2] ?? 'preflight';

async function rows(sql, params) {
  const r = await client.query(sql, params);
  return r.rows;
}

function log(label, data) {
  console.log(`\n=== ${label} ===`);
  console.log(JSON.stringify(data, null, 2));
}

async function preflight() {
  log('current_user / session TimeZone', await rows(
    "SELECT current_user, current_setting('TimeZone') AS tz"
  ));
  log('summary columns (cache_read_tokens present => 092 applied)', await rows(
    "SELECT column_name FROM information_schema.columns " +
    "WHERE table_schema='ba' AND table_name='usage_daily_summary' ORDER BY ordinal_position"
  ));
  log('rollup function exists', await rows(
    "SELECT p.proname, pg_get_function_identity_arguments(p.oid) AS args " +
    "FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace " +
    "WHERE n.nspname='ba' AND p.proname='fn_usage_daily_rollup'"
  ));
  log('privileges', await rows(
    "SELECT has_function_privilege(current_user, 'ba.fn_usage_daily_rollup(DATE)', 'EXECUTE') AS can_exec_rollup, " +
    "has_table_privilege(current_user, 'ba.usage_events', 'INSERT') AS can_insert_events, " +
    "has_table_privilege(current_user, 'ba.usage_daily_summary', 'INSERT') AS can_insert_summary"
  ));
  log('ai_usage UTC date range', await rows(
    "SELECT to_char(min(created_at AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD') AS dmin, " +
    "to_char(max(created_at AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD') AS dmax, " +
    "count(*) AS total FROM ba.ai_usage"
  ));
  log('distinct sessions (candidates for derived events)', await rows(
    'SELECT count(DISTINCT session_id) AS sessions FROM ba.ai_usage WHERE session_id IS NOT NULL'
  ));
  log('usage_events current count', await rows('SELECT count(*) AS n FROM ba.usage_events'));
  log('usage_daily_summary current count', await rows('SELECT count(*) AS n FROM ba.usage_daily_summary'));
  log('cron tables present (rollup joins them)', await rows(
    "SELECT table_name FROM information_schema.tables " +
    "WHERE table_schema='ba' AND table_name IN ('cron_job_runs','workspace_cron_jobs')"
  ));
}

async function run() {
  // ── Step 1: derive session_create events from ai_usage ────────────────────
  // One event per distinct (session_id, workspace_id): first turn's timestamp
  // ≈ session start. Deterministic event_id (md5-uuid) + ON CONFLICT DO NOTHING
  // + NOT EXISTS guard => safe to re-run, never double-counts, never collides
  // with future real events (those use random UUIDs and cover new sessions).
  const derive = await client.query(
    `WITH sess AS (
       SELECT session_id, workspace_id,
              min(created_at) AS first_at,
              (array_agg(user_id ORDER BY created_at))[1] AS first_user_id
       FROM ba.ai_usage
       WHERE session_id IS NOT NULL
       GROUP BY session_id, workspace_id
     )
     INSERT INTO ba.usage_events
       (event_id, event_type, created_at, workspace_id, user_id, session_id, payload)
     SELECT
       (md5('spp-backfill:session:' || s.session_id || ':' ||
            coalesce(s.workspace_id::text, 'none')))::uuid,
       'session_create',
       s.first_at,
       s.workspace_id,
       CASE
         WHEN s.first_user_id ~ $1
              AND EXISTS (SELECT 1 FROM ba.users us WHERE us.id = s.first_user_id::uuid)
         THEN s.first_user_id::uuid
         ELSE NULL
       END,
       s.session_id,
       jsonb_build_object('backfill', 'derived-from-ai_usage', 'ran_at', now())
     FROM sess s
     WHERE NOT EXISTS (
       SELECT 1 FROM ba.usage_events e WHERE e.session_id = s.session_id
     )
     ON CONFLICT (event_id) DO NOTHING`,
    [UUID_RE]
  );
  log('Step 1: derived session_create events inserted', { inserted: derive.rowCount });

  // ── Step 2: roll up every day that has raw data (UTC days) ────────────────
  const { dmin, dmax } = (
    await rows(
      "SELECT to_char(min(created_at AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD') AS dmin, " +
      "to_char(max(created_at AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD') AS dmax FROM ba.ai_usage"
    )
  )[0];
  const days = (
    await rows('SELECT to_char(d, \'YYYY-MM-DD\') AS day FROM generate_series($1::date, $2::date, \'1 day\') AS d', [dmin, dmax])
  ).map((r) => r.day);

  let ok = 0;
  const failed = [];
  for (const day of days) {
    try {
      await client.query('SELECT ba.fn_usage_daily_rollup($1::date)', [day]);
      ok++;
    } catch (e) {
      failed.push({ day, error: e.message });
    }
  }
  log('Step 2: rollup', { from: dmin, to: dmax, days: days.length, ok, failed });
  if (failed.length > 0) process.exitCode = 1;

  // ── Step 3: verify raw vs summary ──────────────────────────────────────────
  log('VERIFY raw totals (ba.ai_usage)', await rows(
    'SELECT count(*) AS calls, sum(cost_usd) AS cost, ' +
    'sum(input_tokens) AS in_tok, sum(output_tokens) AS out_tok FROM ba.ai_usage'
  ));
  log('VERIFY platform-level summary totals', await rows(
    'SELECT sum(ai_calls) AS calls, sum(cost_usd) AS cost, ' +
    'sum(input_tokens) AS in_tok, sum(output_tokens) AS out_tok, ' +
    'sum(session_count) AS sessions ' +
    'FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL'
  ));
  log('VERIFY workspace-level totals (dashboard reads this level)', await rows(
    'SELECT sum(ai_calls) AS calls, sum(cost_usd) AS cost, sum(session_count) AS sessions ' +
    'FROM ba.usage_daily_summary WHERE user_id IS NULL AND workspace_id IS NOT NULL'
  ));
  log('VERIFY per-day raw vs summary (UTC)', await rows(
    `SELECT raw.d, raw.calls AS raw_calls, raw.cost AS raw_cost,
            s.calls AS sum_calls, s.cost AS sum_cost
     FROM (
       SELECT (created_at AT TIME ZONE 'UTC')::date AS d,
              count(*) AS calls, sum(cost_usd) AS cost
       FROM ba.ai_usage GROUP BY 1
     ) raw
     LEFT JOIN (
       SELECT date, sum(ai_calls) AS calls, sum(cost_usd) AS cost
       FROM ba.usage_daily_summary
       WHERE workspace_id IS NULL AND user_id IS NULL
       GROUP BY 1
     ) s ON s.date = raw.d
     ORDER BY raw.d`
  ));
  log('summary rows by level', await rows(
    'SELECT (workspace_id IS NULL) AS is_platform, (user_id IS NULL) AS user_null, count(*) AS n ' +
    'FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2'
  ));
}

(async () => {
  await client.connect();
  try {
    if (phase === 'run') await run();
    else await preflight();
  } finally {
    await client.end();
  }
})().catch((e) => {
  console.error('FATAL:', e.message);
  process.exit(1);
});
