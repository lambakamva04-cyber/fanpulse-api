/**
 * routes/chat.js
 * GET  /api/chat/rooms          — List all chat rooms
 * GET  /api/chat/:roomId        — Get messages for a room
 * POST /api/chat/:roomId        — Post a message (auth required)
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { authenticate } from '../middleware/auth.js';

const chat = new Hono();

// ── GET /api/chat/rooms ───────────────────────────────────────
chat.get('/rooms', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('chat_rooms')
      .select('id, name, type, is_active, message_count')
      .eq('is_active', true)
      .order('message_count', { ascending: false });
    if (error) throw error;
    return c.json({ rooms: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/chat/:roomId ─────────────────────────────────────
chat.get('/:roomId', async (c) => {
  try {
    const db    = getSupabase(c.env);
    const limit = Math.min(parseInt(c.req.query('limit') || '50'), 100);

    const { data, error } = await db
      .from('chat_messages')
      .select('id, content, created_at, user:users(id, username, display_name, avatar_url, country_code)')
      .eq('room_id', c.req.param('roomId'))
      .order('created_at', { ascending: false })
      .limit(limit);

    if (error) throw error;
    return c.json({ messages: (data || []).reverse() });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── POST /api/chat/:roomId ────────────────────────────────────
chat.post('/:roomId', authenticate, async (c) => {
  const { content } = await c.req.json();
  if (!content?.trim()) return c.json({ error: 'Message content required.' }, 400);
  if (content.length > 300) return c.json({ error: 'Message too long (max 300 chars).' }, 400);

  try {
    const db = getSupabase(c.env);

    const { data, error } = await db
      .from('chat_messages')
      .insert({
        room_id:    c.req.param('roomId'),
        user_id:    c.get('user').id,
        content:    content.trim(),
        created_at: new Date().toISOString(),
      })
      .select('id, content, created_at, user:users(id, username, display_name, country_code)')
      .single();

    if (error) throw error;

    // Increment room message count (fire-and-forget)
    db.from('chat_rooms').rpc('increment_message_count', { room_id: c.req.param('roomId') });

    return c.json({ message: data }, 201);
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default chat;
