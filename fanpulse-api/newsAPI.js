/**
 * services/newsAPI.js
 * NewsAPI proxy — keeps the API key server-side only.
 * Free dev keys only work server-side (not from browsers).
 */

export async function fetchWCNews(env, q = 'FIFA World Cup 2026', pageSize = 12) {
  if (!env.NEWS_API_KEY) {
    console.warn('[newsAPI] NEWS_API_KEY not set');
    return { articles: [], source: 'no_key' };
  }

  try {
    const params = new URLSearchParams({
      q,
      sortBy:   'publishedAt',
      language: 'en',
      pageSize:  Math.min(pageSize, 20),
      apiKey:    env.NEWS_API_KEY,
    });

    const res  = await fetch(`https://newsapi.org/v2/everything?${params}`);
    const data = await res.json();

    if (data.status !== 'ok') {
      console.error('[newsAPI] Error:', data.message);
      return { articles: [], source: 'newsapi_error', message: data.message };
    }

    const articles = (data.articles || []).filter(
      a => a.title && a.title !== '[Removed]' && a.url
    );

    return { articles, source: 'newsapi', totalResults: data.totalResults };
  } catch (e) {
    console.error('[newsAPI] fetch failed:', e.message);
    return { articles: [], source: 'error' };
  }
}
