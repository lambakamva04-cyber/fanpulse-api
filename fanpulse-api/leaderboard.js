/**
 * routes/leaderboard.js
 * GET /api/leaderboard           — Top fans leaderboard
 * GET /api/leaderboard/countries — Country battle leaderboard
 * GET /api/leaderboard/user/:id  — Single user rank
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';

const leaderboard = new Hono();

// ── GET /api/leaderboard ──────────────────────────────────────
leaderboard.get('/', async (c) => {
  try {
    const db     = getSupabase(c.env);
    const limit  = Math.min(parseInt(c.req.query('limit') || '50'), 100);
    const offset = parseInt(c.req.query('offset') || '0');

    const { data, error } = await db
      .from('users')
      .select('id, username, display_name, avatar_url, country_code, total_points, predictions_made, correct_scores')
      .order('total_points', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;

    const ranked = (data || []).map((user, i) => ({
      ...user,
      rank: offset + i + 1,
    }));

    return c.json({ leaderboard: ranked, limit, offset });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/leaderboard/countries ───────────────────────────
// Aggregates fan points by country_code for the Country Battle.
leaderboard.get('/countries', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('users')
      .select('country_code, total_points')
      .not('country_code', 'is', null);

    if (error) throw error;

    // Aggregate in JS (no GROUP BY in Supabase JS client without RPC)
    const totals = {};
    const counts = {};
    (data || []).forEach(u => {
      const code = u.country_code;
      totals[code] = (totals[code] || 0) + (u.total_points || 0);
      counts[code] = (counts[code] || 0) + 1;
    });

    const countries = Object.entries(totals)
      .map(([code, pts]) => ({ code, totalPoints: pts, fanCount: counts[code] }))
      .sort((a, b) => b.totalPoints - a.totalPoints)
      .slice(0, 10)
      .map((c, i) => ({ ...c, rank: i + 1 }));

    return c.json({ countries });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/leaderboard/user/:id ────────────────────────────
leaderboard.get('/user/:id', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data: user, error } = await db
      .from('users')
      .select('id, username, display_name, avatar_url, country_code, total_points, predictions_made, correct_scores')
      .eq('id', c.req.param('id'))
      .single();

    if (error || !user) return c.json({ error: 'User not found.' }, 404);

    // Calculate rank by counting users with more points
    const { count } = await db
      .from('users')
      .select('id', { count: 'exact', head: true })
      .gt('total_points', user.total_points);

    return c.json({ user: { ...user, rank: (count || 0) + 1 } });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default leaderboard;
