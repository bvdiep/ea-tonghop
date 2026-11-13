// Generate a JWT token with the backend's secret and test /api/admin/usage
const jwt = require('jsonwebtoken');
const http = require('http');

const JWT_SECRET = process.env.JWT_SECRET;
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL;

// Get a super admin user first
const { Client } = require('pg');
const dbUrl = new URL(process.env.SUPABASE_DB_URL);

const c = new Client({
  host: dbUrl.hostname, port: +dbUrl.port,
  user: decodeURIComponent(dbUrl.username), password: decodeURIComponent(dbUrl.password),
  database: dbUrl.pathname.slice(1), ssl: false,
});

async function main() {
  await c.connect();

  // Find a super admin
  const admins = await c.query(`
    SELECT u.id, u.name, u.email, u.is_super_admin
    FROM ba.users u
    WHERE u.is_super_admin = true
    LIMIT 5
  `);
  console.log('Super admins:', admins.rows);

  if (admins.rows.length === 0) {
    // Fallback: any user
    const anyUser = await c.query('SELECT id, name, email FROM ba.users LIMIT 3');
    console.log('No super admin found. Users:', anyUser.rows);
    return;
  }

  // Create JWT token
  const user = admins.rows[0];
  const token = jwt.sign(
    { sub: user.id, email: user.email, is_super_admin: true },
    JWT_SECRET,
    { expiresIn: '1h' }
  );
  console.log('\nToken created for:', user.email);

  // Test API
  const req = http.request({
    host: 'localhost', port: 3001,
    path: '/api/admin/usage?tab=overview&since=2026-09-15&until=2026-09-23',
    headers: {
      'Accept': 'application/json',
      'Authorization': 'Bearer ' + token
    }
  }, res => {
    let body = '';
    res.on('data', chunk => body += chunk);
    res.on('end', () => {
      console.log('\n=== HTTP ' + res.statusCode + ' ===');
      try {
        const j = JSON.parse(body);
        if (j.kpis) {
          console.log('KPIs:', JSON.stringify(j.kpis, null, 2).slice(0, 1500));
        } else {
          console.log('Response:', JSON.stringify(j, null, 2).slice(0, 1500));
        }
      } catch(e) {
        console.log('Raw:', body.slice(0, 1000));
      }
      c.end();
      process.exit(0);
    });
  });
  req.on('error', e => { console.log('Error:', e.message); c.end(); process.exit(1); });
  req.end();
}

main().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
