/**
 * src/index.js
 * FanPulse API — Cloudflare Worker Entry Point
 *
 * Routes:
 *   /api/auth/*         Auth (register, login, profile)
 *   /api/matches/*      Live scores, fixtures, WC 2026
 *   /api/news/*         News articles + NewsAPI proxy
 *   /api/predictions/*  Fan predictions + AI model
 *   /api/leaderboard/*  Fan + country leaderboards
 *   /api/highlights/*   YouTube highlights
 *   /api/chat/*         Chat rooms
 *   /api/ai/*           Claude AI assistant + match previews
 *   /health             Health check
 *
 * Cron triggers (defined in wrangler.toml):
 *   * * * * *    → live score sync (every minute)
 *   *\/2 * * * * → prediction scoring (every 2 min)
 *   0 *\/6 * * * → standings sync (every 6 hours)
 */

import { Hono }       from 'hono';
import { cors }       from 'hono/cors';
import { logger }     from 'hono/logger';

import authRoutes        from './routes/auth.js';
import matchRoutes       from './routes/matches.js';
import newsRoutes        from './routes/news.js';
import predictionRoutes  from './routes/predictions.js';
import leaderboardRoutes from './routes/leaderboard.js';
import highlightRoutes   from './routes/highlights.js';
import chatRoutes        from './routes/chat.js';
import aiRoutes          from './routes/ai.js';

import { fetchLiveMatches, fetchStandings } from './services/sportsAPI.js';
import { scoreFinishedMatches, generateMatchPrediction } from './services/predictions.js';
import { getSupabase } from './services/supabase.js';

const app = new Hono();

// ── CORS ──────────────────────────────────────────────────────
app.use('*', async (c, next) => {
  const origin = c.env.FRONTEND_URL || 'https://fanpulse.pages.dev';
  return cors({
    origin:         [origin, 'http://localhost:3000', 'http://localhost:5173'],
    allowHeaders:   ['Content-Type', 'Authorization'],
    allowMethods:   ['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'],
    credentials:    true,
    maxAge:         86400,
  })(c, next);
});

// ── Request logger (dev only) ──────────────────────────────────
app.use('*', logger());

// ── Health check ──────────────────────────────────────────────
app.get('/health', (c) => c.json({
  status:  'ok',
  service: 'FanPulse API',
  runtime: 'Cloudflare Workers',
  version: '3.0.0',
  time:    new Date().toISOString(),
}));

// ── API Routes ─────────────────────────────────────────────────
app.route('/api/auth',        authRoutes);
app.route('/api/matches',     matchRoutes);
app.route('/api/news',        newsRoutes);
app.route('/api/predictions', predictionRoutes);
app.route('/api/leaderboard', leaderboardRoutes);
app.route('/api/highlights',  highlightRoutes);
app.route('/api/chat',        chatRoutes);
app.route('/api/ai',          aiRoutes);

// ── 404 fallthrough ────────────────────────────────────────────
app.notFound((c) => c.json({ error: 'Route not found.' }, 404));

// ── Error handler ──────────────────────────────────────────────
app.onError((err, c) => {
  console.error('[worker] unhandled error:', err.message);
  return c.json({ error: err.message || 'Internal server error.' }, 500);
});

// ── Cron handler (replaces node-cron) ─────────────────────────
async function scheduled(event, env, ctx) {
  const cron = event.cron;
  console.log(`[cron] triggered: ${cron}`);

  // Every minute — sync live match scores + events
  if (cron === '* * * * *') {
    try {
      const live = await fetchLiveMatches(env);
      if (live.length > 0) {
        const db = getSupabase(env);
        for (const m of live) {
          await db.from('matches').upsert({
            api_id:          m.apiId,
            home_score:      m.homeScore,
            away_score:      m.awayScore,
            home_ht_score:   m.homeHalfScore,
            away_ht_score:   m.awayHalfScore,
            status:          m.status,
            elapsed_minutes: m.elapsed,
            updated_at:      new Date().toISOString(),
          }, { onConflict: 'api_id' });
        }
        console.log(`[cron] synced ${live.length} live matches`);
      }
    } catch (e) {
      console.error('[cron] live sync failed:', e.message);
    }
  }

  // Every 2 minutes — score finished match predictions
  if (cron === '*/2 * * * *') {
    try {
      await scoreFinishedMatches(env);
    } catch (e) {
      console.error('[cron] scoring failed:', e.message);
    }
  }

  // Every 6 hours — sync league standings
  if (cron === '0 */6 * * *') {
    try {
      const LEAGUES = [1, 39, 140, 135, 78, 61, 2, 288];
      const db      = getSupabase(env);
      for (const leagueId of LEAGUES) {
        const standings = await fetchStandings(env, leagueId);
        const { data: leagueRow } = await db.from('leagues').select('id').eq('api_id', leagueId).single();
        if (!leagueRow) continue;
        for (const s of standings) {
          const { data: teamRow } = await db.from('teams').select('id').eq('api_id', s.team.apiId).single();
          if (!teamRow) continue;
          await db.from('league_standings').upsert({
            league_id: leagueRow.id, team_id: teamRow.id,
            season: new Date().getFullYear(), position: s.rank,
            played: s.played, won: s.won, drawn: s.drawn, lost: s.lost,
            goals_for: s.goalsFor, goals_against: s.goalsAgainst,
            points: s.points, form: s.form,
            updated_at: new Date().toISOString(),
          }, { onConflict: 'league_id,team_id,season' });
        }
      }
      console.log('[cron] standings synced');
    } catch (e) {
      console.error('[cron] standings failed:', e.message);
    }
  }
}

// ── Export ─────────────────────────────────────────────────────
export default {
  fetch:     app.fetch,
  scheduled,
};
