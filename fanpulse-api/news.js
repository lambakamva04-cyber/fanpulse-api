/**
 * routes/news.js
 * GET  /api/news           — Published articles from Supabase
 * GET  /api/news/live      — Live WC news via NewsAPI proxy
 * GET  /api/news/:slug     — Single article
 * POST /api/news           — Create article (admin)
 * PATCH /api/news/:id      — Update article (admin)
 * DELETE /api/news/:id     — Delete article (admin)
 */

import { Hono } from 'hono';
import { getSupabase } from '../services/supabase.js';
import { fetchWCNews } from '../services/newsAPI.js';
import { authenticate, requireAdmin } from '../middleware/auth.js';

const news = new Hono();

function slugify(text) {
  return text.toLowerCase().trim()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    + '-' + Date.now();
}

// ── GET /api/news ─────────────────────────────────────────────
news.get('/', async (c) => {
  try {
    const db     = getSupabase(c.env);
    const limit  = Math.min(parseInt(c.req.query('limit') || '12'), 50);
    const offset = parseInt(c.req.query('offset') || '0');
    const tag    = c.req.query('tag');

    let q = db
      .from('news')
      .select('id, title, slug, excerpt, cover_image, tags, published_at, views, author:users!news_author_id_fkey(display_name)')
      .eq('is_published', true)
      .order('published_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (tag) q = q.contains('tags', [tag]);

    const { data, error } = await q;
    if (error) throw error;
    return c.json({ articles: data || [] });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/news/live ────────────────────────────────────────
// NewsAPI proxy — key never exposed to the browser.
// Falls back to Supabase articles if NewsAPI key is missing or fails.
news.get('/live', async (c) => {
  const query    = c.req.query('q') || 'FIFA World Cup 2026';
  const pageSize = parseInt(c.req.query('pageSize') || '12');

  const result = await fetchWCNews(c.env, query, pageSize);

  if (result.source === 'newsapi' && result.articles.length > 0) {
    return c.json(result);
  }

  // Fallback: return Supabase articles
  try {
    const db = getSupabase(c.env);
    const { data } = await db
      .from('news')
      .select('id, title, slug, excerpt, cover_image, tags, published_at')
      .eq('is_published', true)
      .order('published_at', { ascending: false })
      .limit(12);
    return c.json({ articles: data || [], source: 'supabase_fallback' });
  } catch (e) {
    return c.json({ articles: [], source: 'error' });
  }
});

// ── POST /api/news (admin) ────────────────────────────────────
news.post('/', authenticate, requireAdmin, async (c) => {
  const { title, excerpt, content, cover_image, tags, is_published, league_id, team_id } = await c.req.json();
  if (!title || !content) return c.json({ error: 'title and content required.' }, 400);

  try {
    const db  = getSupabase(c.env);
    const now = new Date().toISOString();
    const { data, error } = await db.from('news').insert({
      title,
      slug:         slugify(title),
      excerpt:      excerpt      || null,
      content,
      cover_image:  cover_image  || null,
      tags:         tags         || [],
      is_published: is_published || false,
      published_at: is_published ? now : null,
      author_id:    c.get('user').id,
      league_id:    league_id    || null,
      team_id:      team_id      || null,
    }).select().single();
    if (error) throw error;
    return c.json({ article: data }, 201);
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── PATCH /api/news/:id (admin) ───────────────────────────────
news.patch('/:id', authenticate, requireAdmin, async (c) => {
  const body    = await c.req.json();
  const updates = {};
  const fields  = ['title', 'excerpt', 'content', 'cover_image', 'tags', 'is_published', 'league_id', 'team_id'];
  fields.forEach(f => { if (body[f] !== undefined) updates[f] = body[f]; });
  if (updates.title) updates.slug = slugify(updates.title);
  if (updates.is_published) updates.published_at = new Date().toISOString();

  try {
    const db = getSupabase(c.env);
    const { data, error } = await db.from('news').update(updates).eq('id', c.req.param('id')).select().single();
    if (error) throw error;
    return c.json({ article: data });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── DELETE /api/news/:id (admin) ──────────────────────────────
news.delete('/:id', authenticate, requireAdmin, async (c) => {
  try {
    const db = getSupabase(c.env);
    const { error } = await db.from('news').delete().eq('id', c.req.param('id'));
    if (error) throw error;
    return c.json({ message: 'Article deleted.' });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

// ── GET /api/news/:slug ───────────────────────────────────────
// MUST stay last — catches anything not matched above.
news.get('/:slug', async (c) => {
  try {
    const db = getSupabase(c.env);
    const { data, error } = await db
      .from('news')
      .select('id, title, slug, excerpt, content, cover_image, tags, published_at, views, author:users!news_author_id_fkey(display_name, username, avatar_url)')
      .eq('slug', c.req.param('slug'))
      .eq('is_published', true)
      .single();

    if (error || !data) return c.json({ error: 'Article not found.' }, 404);

    // Increment view count — fire and forget
    getSupabase(c.env).from('news').update({ views: (data.views || 0) + 1 }).eq('id', data.id);

    return c.json({ article: data });
  } catch (e) {
    return c.json({ error: e.message }, 500);
  }
});

export default news;
