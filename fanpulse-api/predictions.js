/**
 * routes/predictions.js
 * POST /api/predictions              — Submit prediction (auth required)
 * GET  /api/predictions/me           — My predictions (auth required)
 * GET  /api/predictions/match/:id    — Score distribution for a match
 * GET  /api/predictions/ai/:matchId  — AI model prediction for a match
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { authenticate } from '../middleware/auth.js';
import { generateMatchPrediction } from '../services/predictions.js';

const predictions = new Hono();

// ── POST /api/predictions ─────────────────────────────────────
predictions.post('/', authenticate, async (c) => {
  const { match_id, predicted_home, predicted_away } = await c.req.json();

  if (!match_id) return c.json({ error: 'match_id required.' }, 400);
  if (predicted_home === undefined || predicted_away === undefined) {
    return c.json({ error: 'predicted_home and predicted_away required.' }, 400);
  }
  if (predicted_home < 0 || predicted_away < 0 || predicted_home > 20 || predicted_away > 20) {
    return c.json({ error: 'Scores must be between 0 and 20.' }, 400);
  }

  try {
    const db = getSupabase(c.env);

    const { data: match } = await db
      .from('matches')
      .select('id, status, kickoff_time')
      .eq('id', match_id)
      .single();

    if (!match) return c.json({ error: 'Match not found.' }, 404);
    if (match.status !== 'NS') return c.json({ error: 'Match has already started.' }, 400);
    if (new Date(match.kickoff_time) <= new Date()) {
      return c.json({ error: 'Prediction window has closed.' }, 400);
    }

    const { data, error } = await db
      .from('predictions')
      .upsert({
        user_id:        c.get('user').id,
        match_id,
        predicted_home: parseInt(predicted_home),
        predicted_away: parseInt(predicted_away),
        submitted_at:   new Date().toISOString(),
        is_scored:      false,
        points_awarded: 0,
      }, { onConflict: 'user_id,match_id' })
      .select()
      .single();

    if (error) throw error;
    return c.json({ prediction: data }, 201);
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/predictions/me ───────────────────────────────────
predictions.get('/me', authenticate, async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('predictions')
      .select(`
        id, predicted_home, predicted_away, points_awarded, is_scored, submitted_at,
        match:matches (
          id, status, home_score, away_score, kickoff_time,
          home_team:teams!matches_home_team_id_fkey (name, logo_url),
          away_team:teams!matches_away_team_id_fkey (name, logo_url)
        )
      `)
      .eq('user_id', c.get('user').id)
      .order('submitted_at', { ascending: false })
      .limit(50);
    if (error) throw error;
    return c.json({ predictions: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/predictions/match/:id ───────────────────────────
predictions.get('/match/:id', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('predictions')
      .select('predicted_home, predicted_away')
      .eq('match_id', c.req.param('id'))
      .limit(1000);
    if (error) throw error;

    const tally = {};
    (data || []).forEach(p => {
      const key = `${p.predicted_home}-${p.predicted_away}`;
      tally[key] = (tally[key] || 0) + 1;
    });

    const distribution = Object.entries(tally)
      .map(([score, count]) => {
        const [h, a] = score.split('-').map(Number);
        return { score, home: h, away: a, count };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);

    return c.json({ total: data?.length || 0, distribution });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/predictions/ai/:matchId ─────────────────────────
predictions.get('/ai/:matchId', async (c) => {
  try {
    const prediction = await generateMatchPrediction(c.env, c.req.param('matchId'));
    return c.json({ prediction });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default predictions;
