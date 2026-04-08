/**
 * services/youtube.js
 * YouTube Data API v3 — match highlight and reel search.
 * Quota: 10,000 units/day on free tier. Each search = 100 units.
 */

const BASE = 'https://www.googleapis.com/youtube/v3/search';

async function searchYouTube(env, query, maxResults = 5) {
  if (!env.YOUTUBE_API_KEY) {
    console.warn('[youtube] YOUTUBE_API_KEY not set');
    return [];
  }

  try {
    const params = new URLSearchParams({
      key:               env.YOUTUBE_API_KEY,
      q:                 `${query} highlights`,
      part:              'snippet',
      type:              'video',
      order:             'relevance',
      maxResults:        Math.min(maxResults, 10),
      videoDuration:     'medium',
      relevanceLanguage: 'en',
      safeSearch:        'none',
    });

    const res  = await fetch(`${BASE}?${params}`);
    const data = await res.json();

    return (data.items || []).map(item => ({
      videoId:     item.id.videoId,
      title:       item.snippet.title,
      description: item.snippet.description,
      thumbnail:   item.snippet.thumbnails?.high?.url || item.snippet.thumbnails?.default?.url,
      channel:     item.snippet.channelTitle,
      publishedAt: item.snippet.publishedAt,
      url:         `https://www.youtube.com/watch?v=${item.id.videoId}`,
      embedUrl:    `https://www.youtube.com/embed/${item.id.videoId}`,
    }));
  } catch (e) {
    console.error('[youtube] search failed:', e.message);
    return [];
  }
}

export async function getMatchHighlights(env, homeTeam, awayTeam, date) {
  const dateStr = date
    ? new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    : '';
  return searchYouTube(env, `${homeTeam} vs ${awayTeam} ${dateStr}`.trim(), 5);
}

export async function getLeagueHighlights(env, league, count = 8) {
  return searchYouTube(env, `${league} best goals`, count);
}

export async function getWCHighlights(env, count = 8) {
  return searchYouTube(env, 'FIFA World Cup 2026 goals highlights', count);
}
