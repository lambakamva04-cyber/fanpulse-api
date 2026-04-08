/**
 * routes/matches.js
 * GET /api/matches/live       — All currently live matches
 * GET /api/matches/today      — All matches today
 * GET /api/matches/wc2026     — WC 2026 fixtures direct from API-Football
 * GET /api/matches/fixtures   — Upcoming fixtures (?days=7&league_id=)
 * GET /api/matches/:id        — Match detail + events + AI prediction
 * GET /api/matches/:id/events — Goals, cards, subs for a match
 * GET /api/matches/:id/lineups
 * GET /api/matches/:id/highlights
 * GET /api/matches/:id/standings
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { fetchLiveMatches, fetchTodayFixtures, fetchWC2026, fetchLineups } from '../services/sportsAPI.js';
import { getMatchHighlights, getWCHighlights } from '../services/youtube.js';
import { generateMatchPrediction } from '../services/predictions.js';
import { optionalAuth } from '../middleware/auth.js';

const matches = new Hono();

const MATCH_SELECT = `
  id, api_id, status, elapsed_minutes,
  home_score, away_score, home_ht_score, away_ht_score,
  kickoff_time, venue, round, season,
  home_team:teams!matches_home_team_id_fkey (id, name, logo_url, short_name),
  away_team:teams!matches_away_team_id_fkey (id, name, logo_url, short_name),
  league:leagues (id, name, logo_url, country)
`;

// ── GET /api/matches/live ─────────────────────────────────────
matches.get('/live', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('matches')
      .select(MATCH_SELECT)
      .in('status', ['LIVE', 'HT', '1H', '2H', 'ET', 'P'])
      .order('kickoff_time', { ascending: true });
    if (error) throw error;
    return c.json({ matches: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/today ────────────────────────────────────
matches.get('/today', async (c) => {
  try {
    const db    = getSupabase(c.env);
    const start = new Date(); start.setHours(0, 0, 0, 0);
    const end   = new Date(); end.setHours(23, 59, 59, 999);
    const { data, error } = await db
      .from('matches')
      .select(MATCH_SELECT)
      .gte('kickoff_time', start.toISOString())
      .lte('kickoff_time', end.toISOString())
      .order('kickoff_time', { ascending: true });
    if (error) throw error;
    return c.json({ matches: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/wc2026 ───────────────────────────────────
// Fetches DIRECTLY from API-Football — no Supabase needed.
// Works before the tournament is seeded into the DB.
matches.get('/wc2026', async (c) => {
  try {
    const fixtures = await fetchWC2026(c.env);
    return c.json({
      matches: fixtures,
      source:  'api-football',
      league:  'FIFA World Cup 2026',
      count:   fixtures.length,
      note:    fixtures.length === 0
        ? 'No WC 2026 fixtures yet — API-Football publishes these closer to the tournament.'
        : null,
    });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/fixtures ─────────────────────────────────
matches.get('/fixtures', async (c) => {
  try {
    const db       = getSupabase(c.env);
    const days     = parseInt(c.req.query('days') || '7');
    const leagueId = c.req.query('league_id');
    const start    = new Date();
    const end      = new Date(Date.now() + days * 86_400_000);

    let q = db
      .from('matches')
      .select(MATCH_SELECT)
      .gte('kickoff_time', start.toISOString())
      .lte('kickoff_time', end.toISOString())
      .order('kickoff_time', { ascending: true });

    if (leagueId) q = q.eq('league_id', leagueId);

    const { data, error } = await q;
    if (error) throw error;
    return c.json({ matches: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/:id ──────────────────────────────────────
matches.get('/:id', optionalAuth, async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data: match, error } = await db
      .from('matches')
      .select(`
        ${MATCH_SELECT},
        events:match_events (
          id, event_type, player_name, assist_name, minute, extra_minute, detail,
          team:teams (id, name)
        )
      `)
      .eq('id', c.req.param('id'))
      .single();

    if (error) throw error;
    if (!match) return c.json({ error: 'Match not found.' }, 404);

    // AI prediction (upcoming/live matches only)
    let aiPrediction = null;
    if (['NS', 'LIVE', 'HT'].includes(match.status)) {
      try { aiPrediction = await generateMatchPrediction(c.env, match.id); } catch {}
    }

    // User's own prediction
    const user = c.get('user');
    let userPrediction = null;
    if (user) {
      const { data } = await db
        .from('predictions')
        .select('predicted_home, predicted_away, points_awarded, is_scored')
        .eq('match_id', match.id)
        .eq('user_id', user.id)
        .single();
      userPrediction = data || null;
    }

    const { count: predCount } = await db
      .from('predictions')
      .select('id', { count: 'exact', head: true })
      .eq('match_id', match.id);

    return c.json({ match, aiPrediction, userPrediction, predictionCount: predCount || 0 });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/:id/events ───────────────────────────────
matches.get('/:id/events', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('match_events')
      .select('id, event_type, player_name, assist_name, minute, extra_minute, detail, team:teams(id,name)')
      .eq('match_id', c.req.param('id'))
      .order('minute', { ascending: true });
    if (error) throw error;
    return c.json({ events: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/:id/lineups ──────────────────────────────
matches.get('/:id/lineups', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data: match } = await db
      .from('matches').select('api_id').eq('id', c.req.param('id')).single();
    if (!match) return c.json({ error: 'Match not found.' }, 404);
    const lineups = await fetchLineups(c.env, match.api_id);
    return c.json({ lineups });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/:id/highlights ──────────────────────────
matches.get('/:id/highlights', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data: match } = await db
      .from('matches')
      .select('kickoff_time, home_team:teams!matches_home_team_id_fkey(name), away_team:teams!matches_away_team_id_fkey(name)')
      .eq('id', c.req.param('id'))
      .single();
    if (!match) return c.json({ error: 'Match not found.' }, 404);
    const highlights = await getMatchHighlights(c.env, match.home_team.name, match.away_team.name, match.kickoff_time);
    return c.json({ highlights });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/highlights/wc ───────────────────────────
matches.get('/highlights/wc', async (c) => {
  try {
    const highlights = await getWCHighlights(c.env, 8);
    return c.json({ highlights });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/matches/:id/standings ────────────────────────────
matches.get('/:id/standings', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data: match } = await db
      .from('matches').select('league_id, season').eq('id', c.req.param('id')).single();
    if (!match) return c.json({ error: 'Match not found.' }, 404);

    const { data: standings, error } = await db
      .from('league_standings')
      .select('position, played, won, drawn, lost, goals_for, goals_against, goal_difference, points, form, team:teams(id, name, logo_url)')
      .eq('league_id', match.league_id)
      .eq('season', match.season)
      .order('position', { ascending: true });
    if (error) throw error;
    return c.json({ standings: standings || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default matches;
