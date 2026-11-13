// Survey usage data on spp-dev (READ-ONLY)
const { createClient } = require('@supabase/supabase-js');
const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
const sb = createClient(url, key);

async function q(label, fn) {
  try {
    const r = await fn();
    console.log(`\n=== ${label} ===`);
    if (r.error) console.log('ERROR:', r.error.message);
    else console.log(JSON.stringify(r.data ?? r.count ?? r, null, 2));
  } catch (e) {
    console.log(`\n=== ${label} === THREW: ${e.message}`);
  }
}

async function main() {
  await q('ai_usage row count', async () => {
    const { count } = await sb.from('ai_usage').select('*', { count: 'exact', head: true });
    return count;
  });

  await q('usage_daily_summary row count', async () => {
    const { count } = await sb.from('usage_daily_summary').select('*', { count: 'exact', head: true });
    return count;
  });

  await q('usage_events row count', async () => {
    const { count } = await sb.from('usage_events').select('*', { count: 'exact', head: true });
    return count;
  });

  await q('model_pricing rows', async () => sb.from('model_pricing').select('*'));

  await q('latest 3 ai_usage rows', async () =>
    sb.from('ai_usage').select('*').order('created_at', { ascending: false }).limit(3)
  );

  await q('latest 3 usage_daily_summary rows', async () =>
    sb.from('usage_daily_summary').select('*').order('date', { ascending: false }).limit(3)
  );

  await q('latest 3 usage_events rows', async () =>
    sb.from('usage_events').select('*').order('created_at', { ascending: false }).limit(3)
  );

  await q('ai_usage source distribution (sample 500)', async () => {
    const { data } = await sb.from('ai_usage').select('source').limit(500);
    const c = {};
    (data || []).forEach(r => { c[r.source] = (c[r.source] || 0) + 1; });
    return c;
  });

  await q('ai_usage date range', async () => {
    const { data } = await sb.from('ai_usage').select('created_at').order('created_at').limit(1);
    const { data: d2 } = await sb.from('ai_usage').select('created_at').order('created_at', { ascending: false }).limit(1);
    return { earliest: data?.[0]?.created_at, latest: d2?.[0]?.created_at };
  });
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
