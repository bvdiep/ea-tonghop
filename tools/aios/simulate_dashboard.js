// Simulate the exact dashboard queries (usage-analytics.ts) against current data
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);
const { Client } = require('pg');
const client = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function main() {
  // Default dashboard range: last 30 days (2026-08-24 → 2026-09-23)
  // fetchSummaryRows level="workspace": user_id IS NULL AND workspace_id IS NOT NULL
  const ws = await client.query(
    "SELECT count(*) AS n, sum(ai_calls) AS calls, sum(cost_usd) AS cost " +
    "FROM ba.usage_daily_summary " +
    "WHERE date >= '2026-08-24' AND date < '2026-09-23' " +
    "AND user_id IS NULL AND workspace_id IS NOT NULL"
  );
  console.log('=== DASHBOARD "workspace" level (Overview/Finance-weekly/Performance-turns read this) ===');
  console.log(JSON.stringify(ws.rows[0]));

  // fetchSummaryRows level="user": user_id NOT NULL
  const usr = await client.query(
    "SELECT count(*) AS n, sum(ai_calls) AS calls, sum(cost_usd) AS cost " +
    "FROM ba.usage_daily_summary " +
    "WHERE date >= '2026-08-24' AND date < '2026-09-23' AND user_id IS NOT NULL"
  );
  console.log('\n=== DASHBOARD "user" level (per-user tables, DAU, drill) ===');
  console.log(JSON.stringify(usr.rows[0]));

  // fetchUserSessionCount: user-level, model NULL
  const sess = await client.query(
    "SELECT sum(session_count) AS sessions FROM ba.usage_daily_summary " +
    "WHERE date >= '2026-08-24' AND date < '2026-09-23' " +
    "AND user_id IS NOT NULL AND model IS NULL"
  );
  console.log('\n=== sessions (user-level model-NULL rows) ===');
  console.log(JSON.stringify(sess.rows[0]));

  // Breakdown of ALL summary rows by level
  const lv = await client.query(
    "SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, " +
    "count(*) AS n, sum(ai_calls) AS calls, sum(cost_usd) AS cost " +
    "FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2"
  );
  console.log('\n=== all summary rows by level ===');
  console.log(JSON.stringify(lv.rows, null, 2));
}

client.connect().then(main).then(() => client.end()).catch(e => { console.error('FATAL:', e.message); process.exit(1); });
