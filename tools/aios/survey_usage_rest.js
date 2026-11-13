// Survey usage data via Supabase REST API (no deps needed)
const https = require('https');
const url = require('url');

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;

function api(path, params = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(SUPABASE_URL + path);
    Object.entries(params).forEach(([k, v]) => u.searchParams.set(k, v));
    const req = https.request({
      hostname: u.hostname,
      path: u.pathname + u.search,
      headers: {
        'apikey': SERVICE_KEY,
        'Authorization': 'Bearer ' + SERVICE_KEY,
        'Prefer': 'count=exact'
      }
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        try { resolve(JSON.parse(body)); } catch(e) { resolve(body); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function q(label, fn) {
  try {
    const r = await fn();
    console.log(`\n=== ${label} ===`);
    console.log(JSON.stringify(r, null, 2));
  } catch (e) {
    console.log(`\n=== ${label} === THREW: ${e.message}`);
  }
}

async function main() {
  // Count ai_usage
  const usage = await api('/rest/v1/ai_usage', { select: '*', limit: '0' });
  console.log('\n=== ai_usage count ===', usage);

  // Latest 3 ai_usage
  await q('latest 3 ai_usage', () =>
    api('/rest/v1/ai_usage', { select: '*', order: 'created_at.desc', limit: '3' })
  );

  // Count usage_daily_summary
  const summary = await api('/rest/v1/usage_daily_summary', { select: '*', limit: '0' });
  console.log('\n=== usage_daily_summary count ===', summary);

  // Latest 3 summary
  await q('latest 3 usage_daily_summary', () =>
    api('/rest/v1/usage_daily_summary', { select: '*', order: 'date.desc', limit: '3' })
  );

  // Count usage_events
  const events = await api('/rest/v1/usage_events', { select: '*', limit: '0' });
  console.log('\n=== usage_events count ===', events);

  // Latest 3 events
  await q('latest 3 usage_events', () =>
    api('/rest/v1/usage_events', { select: '*', order: 'created_at.desc', limit: '3' })
  );

  // model_pricing
  await q('model_pricing', () =>
    api('/rest/v1/model_pricing', { select: '*' })
  );

  // ai_usage date range
  await q('ai_usage earliest', () =>
    api('/rest/v1/ai_usage', { select: 'created_at', order: 'created_at.asc', limit: '1' })
  );
  await q('ai_usage latest', () =>
    api('/rest/v1/ai_usage', { select: 'created_at', order: 'created_at.desc', limit: '1' })
  );

  // ai_usage source distribution
  await q('ai_usage sources (first 100)', () =>
    api('/rest/v1/ai_usage', { select: 'source', limit: '100' })
  );
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
