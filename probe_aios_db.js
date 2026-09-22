// Check aios-base-db (port 15432) via aios-backend container — the real DB for aios.bsmlabs.io
const { Client } = require('pg');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

const c = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function q(sql) {
  try {
    const r = await c.query(sql);
    return r.rows;
  } catch (e) {
    return [{ error: e.message }];
  }
}

async function main() {
  console.log('Connected to:', url.hostname + ':' + url.port + '/' + url.pathname.slice(1));

  console.log('\n=== ai_usage count ===', JSON.stringify(await q('SELECT count(*) FROM ba.ai_usage')));
  console.log('=== usage_daily_summary count ===', JSON.stringify(await q('SELECT count(*) FROM ba.usage_daily_summary')));
  console.log('=== usage_events count ===', JSON.stringify(await q('SELECT count(*) FROM ba.usage_events')));
  console.log('=== model_pricing count ===', JSON.stringify(await q('SELECT count(*) FROM ba.model_pricing')));

  console.log('\n=== ai_usage has dedup_key column? ===', JSON.stringify(await q(
    "SELECT 1 FROM information_schema.columns WHERE table_schema='ba' AND table_name='ai_usage' AND column_name='dedup_key'"
  )));
  console.log('=== ai_usage has source column? ===', JSON.stringify(await q(
    "SELECT 1 FROM information_schema.columns WHERE table_schema='ba' AND table_name='ai_usage' AND column_name='source'"
  )));
  console.log('=== usage_daily_summary has cache_read_tokens? ===', JSON.stringify(await q(
    "SELECT 1 FROM information_schema.columns WHERE table_schema='ba' AND table_name='usage_daily_summary' AND column_name='cache_read_tokens'"
  )));
  console.log('=== fn_usage_daily_rollup exists? ===', JSON.stringify(await q(
    "SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ba' AND p.proname='fn_usage_daily_rollup'"
  )));

  console.log('\n=== ai_usage sample ===', JSON.stringify(await q('SELECT * FROM ba.ai_usage ORDER BY created_at DESC LIMIT 3')));
  console.log('=== ai_usage date range ===', JSON.stringify(await q(
    "SELECT min(created_at) earliest, max(created_at) latest FROM ba.ai_usage"
  )));

  await c.end();
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
