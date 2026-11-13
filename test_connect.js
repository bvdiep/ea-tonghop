// Check if aios-frontend can reach the backend endpoint
const http = require('http');

const req = http.request({
  host: 'backend', port: 3001,
  path: '/api/admin/usage?tab=overview',
  headers: { 'Accept': 'application/json' }
}, res => {
  let body = '';
  res.on('data', c => body += c);
  res.on('end', () => {
    console.log('HTTP', res.statusCode);
    console.log('Body:', body.slice(0, 500));
  });
});
req.on('error', e => console.log('ERROR:', e.message));
req.setTimeout(5000, () => { console.log('TIMEOUT'); req.destroy(); });
req.end();
