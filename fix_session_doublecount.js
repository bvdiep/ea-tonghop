// Fix the session_count double-count introduced by the ws-level fold.
//
// Contract (usage-analytics.ts): ws-level model-NULL rows carry ONLY sessions
// whose owner had NO resolvable user; user-level model-NULL rows carry
// user-attributed sessions. Overview sums BOTH levels → the fold must not copy
// user-attributed session_count into ws-level rows.
//
// Correct ws-level model-NULL session_count = session_create events for that
// (date, workspace) with user_id IS NULL. Verify that count first, then set it.

const dbUrl = process.env.SUPABASE_DB_URL;
const url = new URL(dbUrl);
const { Client } = require('pg');
const client = new Client({
  host: url.hostname, port: parseInt(url.port),
  user: decodeURIComponent(url.username), password: decodeURIComponent(url.password),
  database: url.pathname.slice(1), ssl: false,
});

async function main() {
  // 1. How many session_create events have user_id NULL? (expected 0 — all
  //    derived events carry the first turn's user, all UUIDs exist)
  const nullUser = await client.query(
    "SELECT count(*) AS n FROM ba.usage_events WHERE event_type = 'session_create' AND user_id IS NULL"
  );
  console.log('=== user-NULL session_create events (expected 0) ===', nullUser.rows[0].n);

  // 2. Current ws-level model-NULL session_count (the double-counted 70)
  const before = await client.query(
    "SELECT sum(session_count) AS s FROM ba.usage_daily_summary " +
    "WHERE user_id IS NULL AND workspace_id IS NOT NULL AND model IS NULL"
  );
  console.log('=== ws-level model-NULL session_count BEFORE ===', before.rows[0].s);

  // 3. Set ws-level model-NULL session_count to the true user-NULL session
  //    count per (date, workspace) — 0 here, but computed honestly.
  const upd = await client.query(`
    UPDATE ba.usage_daily_summary s
    SET session_count = COALESCE(e.cnt, 0), updated_at = now()
    FROM (
      SELECT (created_at AT TIME ZONE 'UTC')::date AS d, workspace_id, count(*) AS cnt
      FROM ba.usage_events
      WHERE event_type = 'session_create' AND user_id IS NULL
      GROUP BY 1, 2
    ) e
    WHERE s.user_id IS NULL AND s.workspace_id IS NOT NULL AND s.model IS NULL
      AND s.date = e.d AND s.workspace_id = e.workspace_id
  `);
  console.log('rows updated from event counts:', upd.rowCount);

  // zero out any ws-level model-NULL rows with no matching user-NULL events
  const zero = await client.query(`
    UPDATE ba.usage_daily_summary s
    SET session_count = 0, updated_at = now()
    WHERE s.user_id IS NULL AND s.workspace_id IS NOT NULL AND s.model IS NULL
      AND session_count > 0
      AND NOT EXISTS (
        SELECT 1 FROM ba.usage_events e
        WHERE e.event_type = 'session_create' AND e.user_id IS NULL
          AND (e.created_at AT TIME ZONE 'UTC')::date = s.date
          AND e.workspace_id = s.workspace_id
      )
  `);
  console.log('rows zeroed:', zero.rowCount);

  // 4. Verify the Overview session math: ws-level (0) + user-level (70) = 70
  const wsS = await client.query(
    "SELECT sum(session_count) AS s FROM ba.usage_daily_summary " +
    "WHERE user_id IS NULL AND workspace_id IS NOT NULL AND model IS NULL"
  );
  const usrS = await client.query(
    "SELECT sum(session_count) AS s FROM ba.usage_daily_summary " +
    "WHERE user_id IS NOT NULL AND model IS NULL"
  );
  const real = await client.query(
    "SELECT count(DISTINCT session_id) AS s FROM ba.ai_usage WHERE session_id IS NOT NULL"
  );
  console.log('\n=== VERIFY sessions ===');
  console.log('ws-level model-NULL:', wsS.rows[0].s,
    '| user-level model-NULL:', usrS.rows[0].s,
    '| real distinct sessions:', real.rows[0].s);
  console.log('Overview total =', (+wsS.rows[0].s) + (+usrS.rows[0].s), '(must equal real)');

  // 5. Cost integrity after all fixes
  const fin = await client.query(`
    SELECT
      (SELECT sum(cost_usd) FROM ba.ai_usage) AS raw_cost,
      (SELECT sum(cost_usd) FROM ba.usage_daily_summary
        WHERE user_id IS NULL AND workspace_id IS NOT NULL) AS ws_cost,
      (SELECT sum(cost_usd) FROM ba.usage_daily_summary
        WHERE workspace_id IS NULL AND user_id IS NULL) AS platform_cost
  `);
  console.log('\n=== VERIFY cost (raw == ws-level == platform) ===');
  console.log(JSON.stringify(fin.rows[0]));
}

client.connect().then(main).then(() => client.end()).catch(e => { console.error('FATAL:', e.message); process.exit(1); });
