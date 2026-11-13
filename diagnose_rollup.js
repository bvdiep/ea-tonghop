// Diagnose the rollup failure: compare deployed function vs repo, check cron data
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);
const { Client } = require('pg');
const client = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function main() {
  // 1. Deployed function definition — the cron/events UNION branches
  const r = await client.query(
    "SELECT pg_get_functiondef('ba.fn_usage_daily_rollup(DATE)'::regprocedure) AS def"
  );
  const def = r.rows[0].def;
  console.log('=== deployed function length ===', def.length);

  // Print just the UNION ALL branches (where NULL-count bugs live)
  const lines = def.split('\n');
  lines.forEach((l, i) => {
    if (/UNION ALL|SELECT j\.|SELECT e\.|SELECT 0, 0|NULL, NULL|GROUP BY/i.test(l)) {
      console.log(String(i).padStart(3), '|', l);
    }
  });

  // 2. Cron runs date range + count
  const cron = await client.query(
    "SELECT count(*) AS n, min(started_at) AS dmin, max(started_at) AS dmax FROM ba.cron_job_runs"
  );
  console.log('\n=== cron_job_runs ===', JSON.stringify(cron.rows[0]));

  // 3. Which failed days have cron runs? (2026-07-01 as sample)
  const sample = await client.query(
    "SELECT count(*) AS cron_rows FROM ba.cron_job_runs r JOIN ba.workspace_cron_jobs j ON j.id = r.job_id WHERE r.started_at >= '2026-07-01' AND r.started_at < '2026-07-02'"
  );
  console.log('\n=== 2026-07-01 cron rows ===', JSON.stringify(sample.rows[0]));

  // 4. A successful day (2026-09-22) — has ai_usage; does it also have cron runs?
  const sample2 = await client.query(
    "SELECT count(*) AS cron_rows FROM ba.cron_job_runs r JOIN ba.workspace_cron_jobs j ON j.id = r.job_id WHERE r.started_at >= '2026-09-22' AND r.started_at < '2026-09-23'"
  );
  console.log('\n=== 2026-09-22 cron rows ===', JSON.stringify(sample2.rows[0]));

  // 5. workspace_cron_jobs user_id nullability
  const cj = await client.query(
    "SELECT count(*) AS total, count(user_id) AS with_user FROM ba.workspace_cron_jobs"
  );
  console.log('\n=== workspace_cron_jobs users ===', JSON.stringify(cj.rows[0]));

  // 6. Simulate the workspace-level INSERT for 2026-07-01 to see which column goes NULL
  try {
    await client.query('BEGIN');
    await client.query("SELECT ba.fn_usage_daily_rollup('2026-07-01')");
    console.log('\n=== 2026-07-01 rollup: UNEXPECTED SUCCESS ===');
  } catch (e) {
    console.log('\n=== 2026-07-01 rollup error (as expected) ===');
    console.log(e.message);
    // where constraint: which insert? Get the detail
    if (e.detail) console.log('detail:', e.detail);
    if (e.where) console.log('where:', e.where);
    if (e.hint) console.log('hint:', e.hint);
  } finally {
    await client.query('ROLLBACK');
  }

  // 7. Reproduce the evts CTE for 2026-07-01 manually (workspace-level, first branch only)
  const sim = await client.query(`
    WITH evts AS (
      SELECT j.workspace_id, j.user_id, NULL::text AS model, NULL::text AS provider,
             NULL::bigint AS ai_calls, 0::bigint AS ai_calls_failed,
             NULL::bigint AS input_tokens, NULL::bigint AS output_tokens,
             NULL::bigint AS cache_read_tokens, NULL::bigint AS cache_write_tokens,
             NULL::bigint AS reasoning_tokens, NULL::numeric AS cost_usd,
             0::bigint AS session_count, 1::bigint AS cron_runs,
             CASE WHEN r.status = 'error' THEN 1 ELSE 0 END AS cron_failed,
             0::bigint AS error_count
      FROM ba.cron_job_runs r
      JOIN ba.workspace_cron_jobs j ON j.id = r.job_id
      WHERE r.started_at >= '2026-07-01' AND r.started_at < '2026-07-02'
    )
    SELECT workspace_id, user_id, model, provider,
           sum(ai_calls) AS sum_ai_calls, sum(cron_runs) AS sum_cron
    FROM evts GROUP BY workspace_id, user_id, model, provider
  `);
  console.log('\n=== simulated cron-only GROUP BY (ai_calls=NULL hypothesis) ===');
  console.log(JSON.stringify(sim.rows, null, 2));
}

client.connect().then(main).then(() => client.end()).catch(e => { console.error('FATAL:', e.message); process.exit(1); });
