// Check if the backend has the /api/admin/usage endpoint code
const fs = require('fs');
const path = require('path');

function find(dir, depth = 0) {
  if (depth > 8) return;
  try {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory() && !['node_modules', '.next', '.git'].includes(e.name)) find(p, depth + 1);
      else if (e.name === 'route.ts' || e.name === 'page.tsx') {
        const c = fs.readFileSync(p, 'utf8');
        if (c.includes('admin/usage') || c.includes('usage-analytics') || c.includes('usage_daily_summary')) {
          console.log('\nFOUND:', p);
          console.log('--- first 30 lines ---');
          console.log(c.split('\n').slice(0, 30).join('\n'));
        }
      }
    }
  } catch(e) {}
}

console.log('Scanning /app/apps/backend...');
find('/app/apps/backend');
console.log('\nScanning /app/apps/frontend...');
find('/app/apps/frontend');
