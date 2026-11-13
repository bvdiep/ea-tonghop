// Survey usage data via SUPABASE_DB_URL (psql-style in Node)
// Parse the DB URL: postgresql://user:pass@host:port/db
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

const { Client } = (() => {
  try { return require('pg'); } catch(e) { return {}; }
})();

async function q(label, sql) {
  console.log(`\n=== ${label} ===`);
  if (!Client) { console.log('pg module not available'); return; }
  const c = new Client({
    host: url.hostname,
    port: parseInt(url.port),
    user: decodeURIComponent(url.username),
    password: decodeURIComponent(url.password),
    database: url.pathname.slice(1),
    ssl: false
  });
  try {
    await c.connect();
    const r = await c.query(sql);
    console.log(JSON.stringify(r.rows, null, 2));
  } catch (e) {
    console.log('ERROR:', e.message);
  } finally {
    await c.end();
  }
}

async function main() {
  await q('ai_usage count', 'SELECT count(*) FROM ba.ai_usage');
  await q('usage_daily_summary count', 'SELECT count(*) FROM ba.usage_daily_summary');
  await q('usage_events count', 'SELECT count(*) FROM ba.usage_events');
  await q('latest 3 ai_usage', 'SELECT * FROM ba.ai_usage ORDER BY created_at DESC LIMIT 3');
  await q('latest 3 usage_daily_summary', 'SELECT * FROM ba.usage_daily_summary ORDER BY date DESC LIMIT 3');
  await q('model_pricing', 'SELECT * FROM ba.model_pricing');
  await q('ai_usage source dist', 'SELECT source, count(*) FROM ba.ai_usage GROUP BY source');
  await q('ai_usage date range', 'SELECT min(created_at) earliest, max(created_at) latest FROM ba.ai_usage');
  await q('ai_usage table cols', "SELECT column_name FROM information_schema.columns WHERE table_schema='ba' AND table_name='ai_usage' ORDER BY ordinal_position");
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
