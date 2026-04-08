/**
 * routes/ai.js
 * POST /api/ai/chat       — AI assistant powered by Claude (Pro Plus only)
 * GET  /api/ai/preview/:matchId — AI match preview/analysis
 *
 * Requires ANTHROPIC_API_KEY secret set in Cloudflare dashboard.
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { authenticate } from '../middleware/auth.js';

const ai = new Hono();

const SYSTEM_PROMPT = `You are FanPulse AI, the official AI assistant for FanPulse World Cup 2026.
You are an expert in football/soccer, World Cup history, team statistics, player form, and match analysis.
You are friendly, enthusiastic, and knowledgeable.
Keep responses concise (under 200 words) and focused on football.
Format key stats and predictions clearly.
When discussing odds or predictions, note these are for entertainment only.
Do not discuss non-football topics.`;

// ── POST /api/ai/chat ─────────────────────────────────────────
// Pro Plus feature — requires authentication.
// In production, also check user.subscription_tier === 'pro_plus'.
ai.post('/chat', authenticate, async (c) => {
  if (!c.env.ANTHROPIC_API_KEY) {
    return c.json({ error: 'AI assistant not configured.' }, 503);
  }

  const { message, history = [] } = await c.req.json();
  if (!message?.trim()) return c.json({ error: 'Message required.' }, 400);

  // Build message array — include up to last 6 turns for context
  const messages = [
    ...history.slice(-6).map(h => ({ role: h.role, content: h.content })),
    { role: 'user', content: message.trim() },
  ];

  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method:  'POST',
      headers: {
        'Content-Type':      'application/json',
        'x-api-key':         c.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model:      'claude-haiku-4-5-20251001',
        max_tokens: 400,
        system:     SYSTEM_PROMPT,
        messages,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error?.message || `Anthropic API error ${res.status}`);
    }

    const data  = await res.json();
    const reply = data.content?.[0]?.text || 'Sorry, I could not generate a response.';
    return c.json({ reply, role: 'assistant' });
  } catch (e) {
    console.error('[ai] chat error:', e.message);
    return c.json({ error: 'AI response failed. Please try again.' }, 500);
  }
});

// ── GET /api/ai/preview/:matchId ──────────────────────────────
// Generates or returns a cached AI match preview.
// Available to all users (not Pro-gated — used as a hook to sell Pro Plus).
ai.get('/preview/:matchId', async (c) => {
  if (!c.env.ANTHROPIC_API_KEY) {
    return c.json({ error: 'AI previews not configured.' }, 503);
  }

  try {
    const db = getSupabase(c.env);

    // Return cached preview if available
    const { data: cached } = await db
      .from('ai_previews')
      .select('content, generated_at')
      .eq('match_id', c.req.param('matchId'))
      .single();

    if (cached && new Date(cached.generated_at) > new Date(Date.now() - 3_600_000)) {
      return c.json({ preview: cached.content, cached: true });
    }

    // Fetch match details for the prompt
    const { data: match } = await db
      .from('matches')
      .select(`
        kickoff_time, venue, round,
        home_team:teams!matches_home_team_id_fkey (name),
        away_team:teams!matches_away_team_id_fkey (name),
        league:leagues (name)
      `)
      .eq('id', c.req.param('matchId'))
      .single();

    if (!match) return c.json({ error: 'Match not found.' }, 404);

    const prompt = `Generate a concise match preview for: ${match.home_team.name} vs ${match.away_team.name}
Competition: ${match.league.name} — ${match.round || 'Group Stage'}
Venue: ${match.venue || 'TBD'}
Date: ${new Date(match.kickoff_time).toDateString()}

Include: key players to watch, recent form, head-to-head record if notable, and a predicted scoreline with brief reasoning. Keep it under 150 words.`;

    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method:  'POST',
      headers: {
        'Content-Type':      'application/json',
        'x-api-key':         c.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model:      'claude-haiku-4-5-20251001',
        max_tokens: 300,
        messages:   [{ role: 'user', content: prompt }],
      }),
    });

    const data    = await res.json();
    const preview = data.content?.[0]?.text || 'Preview unavailable.';

    // Cache the preview
    await db.from('ai_previews').upsert({
      match_id:     c.req.param('matchId'),
      content:      preview,
      generated_at: new Date().toISOString(),
    }, { onConflict: 'match_id' });

    return c.json({ preview, cached: false });
  } catch (e) {
    console.error('[ai] preview error:', e.message);
    return c.json({ error: 'Preview generation failed.' }, 500);
  }
});

export default ai;
