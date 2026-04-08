/**
 * services/sportsAPI.js
 * API-Football v3 wrapper — uses native fetch (no axios needed in Workers).
 * All functions accept env so secrets stay scoped to the request context.
 *
 * Tracked leagues:
 *   1   = FIFA World Cup
 *   39  = English Premier League
 *   140 = La Liga
 *   135 = Serie A
 *   78  = Bundesliga
 *   61  = Ligue 1
 *   2   = UEFA Champions League
 *   288 = South African PSL
 */

const BASE    = 'https://v3.football.api-sports.io';
const LEAGUES = [1, 39, 140, 135, 78, 61, 2, 288];

function headers(env) {
  return {
    'x-rapidapi-host': 'v3.football.api-sports.io',
    'x-rapidapi-key':  env.RAPIDAPI_FOOTBALL_KEY,
  };
}

async function apiFetch(env, path) {
  const res = await fetch(`${BASE}${path}`, { headers: headers(env) });
  if (!res.ok) throw new Error(`API-Football ${res.status}: ${path}`);
  return res.json();
}

// ── Live matches ──────────────────────────────────────────────
export async function fetchLiveMatches(env) {
  try {
    const data = await apiFetch(env, '/fixtures?live=all');
    return (data.response || [])
      .filter(f => LEAGUES.includes(f.league?.id))
      .map(normaliseFixture);
  } catch (e) {
    console.error('[sportsAPI] fetchLiveMatches:', e.message);
    return [];
  }
}

// ── Today's fixtures ──────────────────────────────────────────
export async function fetchTodayFixtures(env) {
  const today = new Date().toISOString().split('T')[0];
  try {
    const data = await apiFetch(env, `/fixtures?date=${today}`);
    return (data.response || [])
      .filter(f => LEAGUES.includes(f.league?.id))
      .map(normaliseFixture);
  } catch (e) {
    console.error('[sportsAPI] fetchTodayFixtures:', e.message);
    return [];
  }
}

// ── WC 2026 fixtures (direct — bypasses Supabase) ─────────────
export async function fetchWC2026(env) {
  try {
    const season = env.WC_SEASON     || '2026';
    const league = env.WC_LEAGUE_ID  || '1';
    const data   = await apiFetch(env, `/fixtures?league=${league}&season=${season}`);
    return (data.response || []).map(normaliseFixture);
  } catch (e) {
    console.error('[sportsAPI] fetchWC2026:', e.message);
    return [];
  }
}

// ── Fixtures for a specific league ────────────────────────────
export async function fetchFixtures(env, leagueId, days = 7) {
  const from = new Date().toISOString().split('T')[0];
  const to   = new Date(Date.now() + days * 86400000).toISOString().split('T')[0];
  try {
    const data = await apiFetch(env, `/fixtures?league=${leagueId}&from=${from}&to=${to}`);
    return (data.response || []).map(normaliseFixture);
  } catch (e) {
    console.error('[sportsAPI] fetchFixtures:', e.message);
    return [];
  }
}

// ── Match events (goals, cards, subs) ─────────────────────────
export async function fetchMatchEvents(env, fixtureId) {
  try {
    const data = await apiFetch(env, `/fixtures/events?fixture=${fixtureId}`);
    return (data.response || []).map(normaliseEvent);
  } catch (e) {
    console.error('[sportsAPI] fetchMatchEvents:', e.message);
    return [];
  }
}

// ── Lineups ───────────────────────────────────────────────────
export async function fetchLineups(env, fixtureId) {
  try {
    const data = await apiFetch(env, `/fixtures/lineups?fixture=${fixtureId}`);
    return data.response || [];
  } catch (e) {
    console.error('[sportsAPI] fetchLineups:', e.message);
    return [];
  }
}

// ── Standings ─────────────────────────────────────────────────
export async function fetchStandings(env, leagueId) {
  const season = new Date().getFullYear();
  try {
    const data  = await apiFetch(env, `/standings?league=${leagueId}&season=${season}`);
    const groups = data.response?.[0]?.league?.standings || [];
    return groups.flat().map(normaliseStanding);
  } catch (e) {
    console.error('[sportsAPI] fetchStandings:', e.message);
    return [];
  }
}

// ── Normalisers ───────────────────────────────────────────────
function normaliseFixture(f) {
  return {
    apiId:         f.fixture.id,
    status:        mapStatus(f.fixture.status.short),
    elapsed:       f.fixture.status.elapsed,
    kickoffTime:   f.fixture.date,
    venue:         f.fixture.venue?.name || null,
    homeScore:     f.goals?.home  ?? null,
    awayScore:     f.goals?.away  ?? null,
    homeHalfScore: f.score?.halftime?.home ?? null,
    awayHalfScore: f.score?.halftime?.away ?? null,
    round:         f.league?.round || null,
    homeTeam: { apiId: f.teams.home.id, name: f.teams.home.name, logo: f.teams.home.logo },
    awayTeam: { apiId: f.teams.away.id, name: f.teams.away.name, logo: f.teams.away.logo },
    league:   { apiId: f.league.id, name: f.league.name, logo: f.league.logo },
  };
}

function normaliseEvent(e) {
  return {
    minute:      e.time.elapsed,
    extraMinute: e.time.extra || null,
    type:        mapEventType(e.type, e.detail),
    detail:      e.detail,
    player:      e.player?.name || null,
    assist:      e.assist?.name || null,
    teamApiId:   e.team?.id,
  };
}

function normaliseStanding(s) {
  return {
    rank:         s.rank,
    played:       s.all.played,
    won:          s.all.win,
    drawn:        s.all.draw,
    lost:         s.all.lose,
    goalsFor:     s.all.goals.for,
    goalsAgainst: s.all.goals.against,
    points:       s.points,
    form:         s.form,
    team:         { apiId: s.team.id, name: s.team.name, logo: s.team.logo },
  };
}

function mapStatus(short) {
  const map = {
    NS:'NS', '1H':'LIVE', HT:'HT', '2H':'LIVE',
    ET:'LIVE', P:'LIVE', FT:'FT', AET:'FT',
    PEN:'FT', PST:'PST', CANC:'CANC', LIVE:'LIVE',
  };
  return map[short] || short;
}

function mapEventType(type, detail) {
  if (type === 'Goal') {
    if (detail === 'Missed Penalty') return 'missed_penalty';
    if (detail === 'Penalty')        return 'penalty';
    return 'goal';
  }
  if (type === 'Card')  return detail === 'Red Card' ? 'red_card' : 'yellow_card';
  if (type === 'subst') return 'substitution';
  if (type === 'Var')   return 'var';
  return type.toLowerCase().replace(/\s+/g, '_');
}
