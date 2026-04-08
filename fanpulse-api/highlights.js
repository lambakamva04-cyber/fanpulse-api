/**
 * routes/highlights.js
 * GET /api/highlights/wc       — World Cup 2026 highlights
 * GET /api/highlights/league/:name — League highlights
 * GET /api/highlights/search   — Search ?q=Brazil+vs+Argentina
 */

import { Hono } from 'hono';
import { getWCHighlights, getLeagueHighlights, getMatchHighlights } from '../services/youtube.js';

const highlights = new Hono();

// ── GET /api/highlights/wc ────────────────────────────────────
highlights.get('/wc', async (c) => {
  try {
    const count = parseInt(c.req.query('count') || '8');
    const vids  = await getWCHighlights(c.env, Math.min(count, 10));
    return c.json({ highlights: vids, source: 'youtube' });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/highlights/league/:name ──────────────────────────
highlights.get('/league/:name', async (c) => {
  try {
    const league = decodeURIComponent(c.req.param('name'));
    const count  = parseInt(c.req.query('count') || '8');
    const vids   = await getLeagueHighlights(c.env, league, Math.min(count, 10));
    return c.json({ highlights: vids, league });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/highlights/search ────────────────────────────────
highlights.get('/search', async (c) => {
  const q = c.req.query('q');
  if (!q) return c.json({ error: 'q query param required.' }, 400);
  try {
    const [home, away] = q.split(' vs ');
    const vids = await getMatchHighlights(c.env, home?.trim() || q, away?.trim() || '', null);
    return c.json({ highlights: vids, query: q });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default highlights;
