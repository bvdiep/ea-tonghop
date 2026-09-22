// Check if the deployed usage-analytics code matches the repo
// by calling the API endpoint directly from the backend container
// with a fake auth token to see what error we get

const http = require('http');

// First, get a valid auth token from Supabase for a super admin
const { createClient } = (() => {
  try { return require('@supabase/supabase-js'); } catch(e) { return {}; }
})();

async function probe(path, token) {
  return new Promise((resolve, reject) => {
    const headers = { 'Accept': 'application/json' };
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    const req = http.request({
      host: 'localhost', port: 3001,
      path: path,
      headers
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        console.log('\n=== ' + path + ' === HTTP ' + res.statusCode);
        try {
          const j = JSON.parse(body);
          console.log(JSON.stringify(j, null, 2).slice(0, 2000));
        } catch(e) {
          console.log(body.slice(0, 1000));
        }
        resolve();
      });
    });
    req.on('error', e => { console.log('Error:', e.message); resolve(); });
    req.end();
  });
}

async function main() {
  // Test auth-less
  await probe('/api/admin/usage?tab=overview');
  await probe('/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23');

  // Test with supabase anon key
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  await probe('/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23', anonKey);

  // Test with service role key (should work as it bypasses RLS)
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (serviceKey) {
    await probe('/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23', serviceKey);
  }
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
