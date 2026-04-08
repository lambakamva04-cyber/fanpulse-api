/**
 * routes/auth.js
 * POST /api/auth/register
 * POST /api/auth/login
 * GET  /api/auth/me
 * PATCH /api/auth/profile
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { authenticate, signToken, hashPassword, verifyPassword } from '../middleware/auth.js';

const auth = new Hono();

// ── POST /api/auth/register ───────────────────────────────────
auth.post('/register', async (c) => {
  const { username, email, password, display_name } = await c.req.json();

  if (!username || !email || !password) {
    return c.json({ error: 'username, email and password are required.' }, 400);
  }
  if (password.length < 8) {
    return c.json({ error: 'Password must be at least 8 characters.' }, 400);
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return c.json({ error: 'Username can only contain letters, numbers and underscores.' }, 400);
  }

  try {
    const db   = getSupabase(c.env);
    const hash = await hashPassword(password);

    const { data, error } = await db
      .from('users')
      .insert({
        username,
        email:        email.toLowerCase().trim(),
        password_hash: hash,
        display_name: display_name || username,
      })
      .select('id, username, email, display_name, role')
      .single();

    if (error) {
      if (error.code === '23505') {
        const field = error.message.includes('email') ? 'Email' : 'Username';
        return c.json({ error: `${field} already taken.` }, 409);
      }
      throw error;
    }

    const token = await signToken(c.env, data.id);
    return c.json({ user: data, token }, 201);
  } catch (e) {
    console.error('[auth] register:', e.message);
    return c.json({ error: 'Registration failed.' }, 500);
  }
});

// ── POST /api/auth/login ──────────────────────────────────────
auth.post('/login', async (c) => {
  const { email, password } = await c.req.json();
  if (!email || !password) return c.json({ error: 'Email and password required.' }, 400);

  try {
    const db = getSupabase(c.env);
    const { data: user } = await db
      .from('users')
      .select('id, username, email, display_name, role, password_hash, is_active, total_points')
      .eq('email', email.toLowerCase().trim())
      .single();

    if (!user) return c.json({ error: 'Invalid email or password.' }, 401);
    if (!user.is_active) return c.json({ error: 'Account suspended.' }, 403);

    const valid = await verifyPassword(password, user.password_hash);
    if (!valid) return c.json({ error: 'Invalid email or password.' }, 401);

    await db.from('users').update({ last_login: new Date().toISOString() }).eq('id', user.id);

    const { password_hash: _, ...safeUser } = user;
    const token = await signToken(c.env, user.id);
    return c.json({ user: safeUser, token });
  } catch (e) {
    console.error('[auth] login:', e.message);
    return c.json({ error: 'Login failed.' }, 500);
  }
});

// ── GET /api/auth/me ──────────────────────────────────────────
auth.get('/me', authenticate, async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('users')
      .select('id, username, email, display_name, avatar_url, role, total_points, predictions_made, correct_scores, correct_winners, country_code')
      .eq('id', c.get('user').id)
      .single();
    if (error) throw error;
    return c.json({ user: data });
  } catch (e) {
    return c.json({ error: 'Failed to fetch user.' }, 500);
  }
});

// ── PATCH /api/auth/profile ───────────────────────────────────
auth.patch('/profile', authenticate, async (c) => {
  const { display_name, avatar_url, country_code, favourite_team_id } = await c.req.json();
  const updates = {};
  if (display_name     !== undefined) updates.display_name      = display_name;
  if (avatar_url       !== undefined) updates.avatar_url        = avatar_url;
  if (country_code     !== undefined) updates.country_code      = country_code;
  if (favourite_team_id !== undefined) updates.favourite_team_id = favourite_team_id;

  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('users')
      .update(updates)
      .eq('id', c.get('user').id)
      .select('id, username, display_name, avatar_url, country_code, role')
      .single();
    if (error) throw error;
    return c.json({ user: data });
  } catch (e) {
    return c.json({ error: 'Profile update failed.' }, 500);
  }
});

export default auth;
