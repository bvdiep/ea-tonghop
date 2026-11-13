// Test /api/admin/usage endpoint + check summary rows on aios-base-db
const { Client } = require('pg');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

const c = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

(async () => {
  await c.connect();

  // Summary row breakdown
  const lv = await c.query(
    "SELECT (workspace_id IS NULL) AS platform, (user_id IS NULL) AS user_null, " +
    "count(*) AS n, min(date) AS dmin, max(date) AS dmax " +
    "FROM ba.usage_daily_summary GROUP BY 1, 2 ORDER BY 1, 2"
  );
  console.log('=== summary rows by level ===');
  lv.rows.forEach(r => console.log('  platform=' + r.platform, 'user_null=' + r.user_null, 'n=' + r.n, 'range=' + r.dmin + '→' + r.dmax));

  // Totals
  const tot = await c.query(
    "SELECT sum(ai_calls) AS calls, sum(cost_usd) AS cost FROM ba.usage_daily_summary WHERE workspace_id IS NULL AND user_id IS NULL"
  );
  console.log('\n=== platform total:', JSON.stringify(tot.rows[0]));

  const raw = await c.query("SELECT count(*) calls, sum(cost_usd) cost FROM ba.ai_usage");
  console.log('=== raw total:', JSON.stringify(raw.rows[0]));

  await c.end();
  process.exit(0);
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
