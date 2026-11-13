// Check aios-base-db (port 15432)
const { Client } = require('pg');
const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);

console.log('Connecting to:', url.hostname + ':' + url.port, 'db:', url.pathname.slice(1));

const c = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

(async () => {
  try {
    await c.connect();
    console.log('Connected OK');

    const tables = await c.query("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema = 'ba' ORDER BY table_name");
    console.log('\n=== BA schema tables ===');
    tables.rows.forEach(r => console.log('  ', r.table_schema + '.' + r.table_name));

    if (tables.rows.some(r => r.table_name === 'ai_usage')) {
      const cnt = await c.query('SELECT count(*) FROM ba.ai_usage');
      console.log('\n=== ai_usage count:', cnt.rows[0].count);
      const range = await c.query('SELECT min(created_at) dmin, max(created_at) dmax FROM ba.ai_usage');
      console.log('=== ai_usage range:', JSON.stringify(range.rows[0]));
      const cols = await c.query("SELECT column_name FROM information_schema.columns WHERE table_schema='ba' AND table_name='ai_usage' ORDER BY ordinal_position");
      console.log('=== ai_usage columns:', cols.rows.map(r => r.column_name).join(', '));
    } else {
      console.log('\n=== ba.ai_usage: TABLE NOT FOUND ===');
    }

    if (tables.rows.some(r => r.table_name === 'usage_daily_summary')) {
      const cnt = await c.query('SELECT count(*) FROM ba.usage_daily_summary');
      console.log('\n=== usage_daily_summary count:', cnt.rows[0].count);
    } else {
      console.log('\n=== ba.usage_daily_summary: TABLE NOT FOUND ===');
    }

    if (tables.rows.some(r => r.table_name === 'usage_events')) {
      const cnt = await c.query('SELECT count(*) FROM ba.usage_events');
      console.log('\n=== usage_events count:', cnt.rows[0].count);
    } else {
      console.log('\n=== ba.usage_events: TABLE NOT FOUND ===');
    }

    const func = await c.query("SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ba' AND p.proname='fn_usage_daily_rollup'");
    console.log('\n=== fn_usage_daily_rollup:', func.rows.length > 0 ? 'EXISTS' : 'NOT FOUND');

  } catch (e) {
    console.error('ERROR:', e.message);
  } finally {
    await c.end();
    process.exit(0);
  }
})();
