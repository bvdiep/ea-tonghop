// Test /api/admin/usage endpoint using internal fetch with auth
// Simulate what the frontend does when user is logged in as super admin

const http = require('http');

// We need a valid auth token. Check if there's a way to get one or test the endpoint differently.
// First, let's check if we can reach the endpoint at all and what error we get.

async function testEndpoint(path, token) {
  return new Promise((resolve, reject) => {
    const headers = { 'Accept': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;
    headers['Cookie'] = token ? `auth-token=${token}` : '';

    const req = http.request({
      host: 'localhost', port: 3001,
      path: path,
      headers
    }, res => {
      let body = '';
      res.on('data', c => body += c);
      res.on('end', () => {
        console.log('\n=== ' + path + ' === HTTP ' + res.statusCode);
        console.log('Headers:', JSON.stringify(res.headers));
        try {
          const j = JSON.parse(body);
          console.log('Body:', JSON.stringify(j, null, 2).slice(0, 2000));
        } catch(e) {
          console.log('Body (raw):', body.slice(0, 1000));
        }
        resolve();
      });
    });
    req.on('error', e => { console.log('Error:', e.message); resolve(); });
    req.end();
  });
}

async function main() {
  // Test without auth
  await testEndpoint('/api/admin/usage?tab=overview');
  await testEndpoint('/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23');

  // Check if the frontend container can reach backend
  const req = http.request({
    host: 'localhost', port: 3001,
    path: '/health'
  }, res => {
    let body = '';
    res.on('data', c => body += c);
    res.on('end', () => console.log('\n=== /health === HTTP ' + res.statusCode, body.slice(0, 200)));
  });
  req.on('error', e => console.log('\n=== /health === Error:', e.message));
  req.end();
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
