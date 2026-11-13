// Test /api/admin/usage endpoint inside aios-backend container
const https = require('https');
const http = require('http');

const BASE = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3001';

async function call(path) {
  return new Promise((resolve, reject) => {
    const mod = BASE.startsWith('https') ? https : http;
    const url = new URL(BASE + path);
    const req = mod.request({
      hostname: url.hostname, port: url.port,
      path: url.pathname + url.search,
      headers: { 'Accept': 'application/json' }
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        console.log('\n=== ' + path + ' === HTTP ' + res.statusCode);
        try { resolve(JSON.parse(body)); } catch(e) { console.log(body.slice(0, 500)); resolve(null); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  // Test admin usage (default 30-day overview)
  const r = await call('/api/admin/usage?tab=overview');
  if (r && r.kpis) {
    console.log('KPIs:', JSON.stringify(r.kpis, null, 2));
  }

  // Test with specific date range
  const r2 = await call('/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23');
  if (r2 && r2.kpis) {
    console.log('\nKPIs (Sep 15-23):', JSON.stringify(r2.kpis, null, 2));
  }
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
