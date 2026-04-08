-- ═══════════════════════════════════════════════════════════════
-- FanPulse World Cup 2026 — Supabase Database Schema
-- Run this entire file in: Supabase Dashboard → SQL Editor → Run
-- ═══════════════════════════════════════════════════════════════

-- ── Extensions ───────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ── Drop existing tables (safe re-run) ───────────────────────
DROP TABLE IF EXISTS ai_previews       CASCADE;
DROP TABLE IF EXISTS ai_predictions    CASCADE;
DROP TABLE IF EXISTS chat_messages     CASCADE;
DROP TABLE IF EXISTS chat_rooms        CASCADE;
DROP TABLE IF EXISTS match_events      CASCADE;
DROP TABLE IF EXISTS predictions       CASCADE;
DROP TABLE IF EXISTS league_standings  CASCADE;
DROP TABLE IF EXISTS matches           CASCADE;
DROP TABLE IF EXISTS news              CASCADE;
DROP TABLE IF EXISTS leagues           CASCADE;
DROP TABLE IF EXISTS teams             CASCADE;
DROP TABLE IF EXISTS users             CASCADE;

-- ── users ─────────────────────────────────────────────────────
CREATE TABLE users (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  username           TEXT NOT NULL UNIQUE,
  email              TEXT NOT NULL UNIQUE,
  password_hash      TEXT NOT NULL,
  display_name       TEXT,
  avatar_url         TEXT,
  country_code       TEXT,                        -- e.g. 'ZA', 'BR', 'FR'
  favourite_team_id  UUID,
  role               TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
  subscription_tier  TEXT NOT NULL DEFAULT 'free' CHECK (subscription_tier IN ('free','pro','pro_plus')),
  is_active          BOOLEAN NOT NULL DEFAULT TRUE,
  total_points       INTEGER NOT NULL DEFAULT 0,
  predictions_made   INTEGER NOT NULL DEFAULT 0,
  correct_scores     INTEGER NOT NULL DEFAULT 0,
  correct_winners    INTEGER NOT NULL DEFAULT 0,
  last_login         TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── leagues ───────────────────────────────────────────────────
CREATE TABLE leagues (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  api_id      INTEGER UNIQUE,                     -- API-Football league ID
  name        TEXT NOT NULL,
  logo_url    TEXT,
  country     TEXT,
  season      INTEGER,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert the leagues FanPulse tracks
INSERT INTO leagues (api_id, name, country, season) VALUES
  (1,   'FIFA World Cup',             'World',        2026),
  (39,  'English Premier League',     'England',      2025),
  (140, 'La Liga',                    'Spain',        2025),
  (135, 'Serie A',                    'Italy',        2025),
  (78,  'Bundesliga',                 'Germany',      2025),
  (61,  'Ligue 1',                    'France',       2025),
  (2,   'UEFA Champions League',      'Europe',       2025),
  (288, 'South African Premier Division', 'South Africa', 2025);

-- ── teams ─────────────────────────────────────────────────────
CREATE TABLE teams (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  api_id      INTEGER UNIQUE,
  name        TEXT NOT NULL,
  short_name  TEXT,
  logo_url    TEXT,
  country     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── matches ───────────────────────────────────────────────────
CREATE TABLE matches (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  api_id           INTEGER UNIQUE,
  league_id        UUID REFERENCES leagues(id),
  home_team_id     UUID REFERENCES teams(id),
  away_team_id     UUID REFERENCES teams(id),
  status           TEXT NOT NULL DEFAULT 'NS',    -- NS, LIVE, HT, FT, PST, CANC
  elapsed_minutes  INTEGER,
  home_score       INTEGER,
  away_score       INTEGER,
  home_ht_score    INTEGER,
  away_ht_score    INTEGER,
  kickoff_time     TIMESTAMPTZ,
  venue            TEXT,
  round            TEXT,
  season           INTEGER,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX matches_status_idx      ON matches(status);
CREATE INDEX matches_kickoff_idx     ON matches(kickoff_time);
CREATE INDEX matches_league_idx      ON matches(league_id);

-- ── match_events ──────────────────────────────────────────────
CREATE TABLE match_events (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id     UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  team_id      UUID REFERENCES teams(id),
  event_type   TEXT NOT NULL,                     -- goal, yellow_card, red_card, substitution, var
  player_name  TEXT,
  assist_name  TEXT,
  minute       INTEGER,
  extra_minute INTEGER,
  detail       TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX match_events_match_idx ON match_events(match_id);

-- ── league_standings ──────────────────────────────────────────
CREATE TABLE league_standings (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  league_id       UUID NOT NULL REFERENCES leagues(id),
  team_id         UUID NOT NULL REFERENCES teams(id),
  season          INTEGER NOT NULL,
  position        INTEGER,
  played          INTEGER DEFAULT 0,
  won             INTEGER DEFAULT 0,
  drawn           INTEGER DEFAULT 0,
  lost            INTEGER DEFAULT 0,
  goals_for       INTEGER DEFAULT 0,
  goals_against   INTEGER DEFAULT 0,
  goal_difference INTEGER GENERATED ALWAYS AS (goals_for - goals_against) STORED,
  points          INTEGER DEFAULT 0,
  form            TEXT,
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (league_id, team_id, season)
);

-- ── predictions ───────────────────────────────────────────────
CREATE TABLE predictions (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  match_id        UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  predicted_home  INTEGER NOT NULL CHECK (predicted_home >= 0 AND predicted_home <= 20),
  predicted_away  INTEGER NOT NULL CHECK (predicted_away >= 0 AND predicted_away <= 20),
  points_awarded  INTEGER NOT NULL DEFAULT 0,
  is_scored       BOOLEAN NOT NULL DEFAULT FALSE,
  scored_at       TIMESTAMPTZ,
  submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (user_id, match_id)
);

CREATE INDEX predictions_user_idx  ON predictions(user_id);
CREATE INDEX predictions_match_idx ON predictions(match_id);

-- ── ai_predictions ────────────────────────────────────────────
CREATE TABLE ai_predictions (
  id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id       UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  home_win_pct   INTEGER,
  draw_pct       INTEGER,
  away_win_pct   INTEGER,
  predicted_home INTEGER,
  predicted_away INTEGER,
  confidence     TEXT CHECK (confidence IN ('low','medium','high')),
  reasoning      TEXT,
  model_version  TEXT,
  generated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (match_id)
);

-- ── ai_previews ───────────────────────────────────────────────
CREATE TABLE ai_previews (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  match_id     UUID NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  content      TEXT NOT NULL,
  generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (match_id)
);

-- ── news ──────────────────────────────────────────────────────
CREATE TABLE news (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  author_id    UUID REFERENCES users(id),
  league_id    UUID REFERENCES leagues(id),
  team_id      UUID REFERENCES teams(id),
  title        TEXT NOT NULL,
  slug         TEXT NOT NULL UNIQUE,
  excerpt      TEXT,
  content      TEXT,
  cover_image  TEXT,
  tags         TEXT[] DEFAULT '{}',
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  published_at TIMESTAMPTZ,
  views        INTEGER NOT NULL DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX news_published_idx ON news(is_published, published_at DESC);
CREATE INDEX news_tags_idx      ON news USING gin(tags);

-- ── chat_rooms ────────────────────────────────────────────────
CREATE TABLE chat_rooms (
  id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          TEXT NOT NULL,
  type          TEXT NOT NULL DEFAULT 'general' CHECK (type IN ('general','match','team')),
  match_id      UUID REFERENCES matches(id),
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  message_count INTEGER NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default chat rooms
INSERT INTO chat_rooms (name, type) VALUES
  ('General World Cup', 'general'),
  ('Goals & Highlights', 'general'),
  ('Predictions Hub',   'general'),
  ('South Africa 🇿🇦',  'team');

-- ── chat_messages ─────────────────────────────────────────────
CREATE TABLE chat_messages (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  room_id    UUID NOT NULL REFERENCES chat_rooms(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  content    TEXT NOT NULL CHECK (char_length(content) <= 300),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX chat_messages_room_idx ON chat_messages(room_id, created_at DESC);

-- ── Helper function: increment chat room message count ─────────
CREATE OR REPLACE FUNCTION increment_message_count(room_id UUID)
RETURNS VOID AS $$
  UPDATE chat_rooms
  SET message_count = message_count + 1
  WHERE id = room_id;
$$ LANGUAGE SQL;

-- ── Row Level Security (RLS) ──────────────────────────────────
-- Enable RLS on all tables (service key bypasses it — safe for Worker)
ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches           ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_events      ENABLE ROW LEVEL SECURITY;
ALTER TABLE league_standings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_predictions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_previews       ENABLE ROW LEVEL SECURITY;
ALTER TABLE news              ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_rooms        ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages     ENABLE ROW LEVEL SECURITY;
ALTER TABLE leagues           ENABLE ROW LEVEL SECURITY;
ALTER TABLE teams             ENABLE ROW LEVEL SECURITY;

-- Public read access (anyone can read match data, news, leaderboard)
CREATE POLICY "public_read_matches"    ON matches          FOR SELECT USING (TRUE);
CREATE POLICY "public_read_events"     ON match_events     FOR SELECT USING (TRUE);
CREATE POLICY "public_read_standings"  ON league_standings FOR SELECT USING (TRUE);
CREATE POLICY "public_read_leagues"    ON leagues          FOR SELECT USING (TRUE);
CREATE POLICY "public_read_teams"      ON teams            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_news"       ON news             FOR SELECT USING (is_published = TRUE);
CREATE POLICY "public_read_rooms"      ON chat_rooms       FOR SELECT USING (is_active = TRUE);
CREATE POLICY "public_read_messages"   ON chat_messages    FOR SELECT USING (TRUE);
CREATE POLICY "public_read_ai_preds"   ON ai_predictions   FOR SELECT USING (TRUE);
CREATE POLICY "public_read_ai_preview" ON ai_previews      FOR SELECT USING (TRUE);
CREATE POLICY "public_read_users"      ON users            FOR SELECT USING (TRUE);
CREATE POLICY "public_read_preds"      ON predictions      FOR SELECT USING (TRUE);

-- ═══════════════════════════════════════════════════════════════
-- Done. Your database is ready.
-- ═══════════════════════════════════════════════════════════════
