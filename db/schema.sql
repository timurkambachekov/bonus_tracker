CREATE TABLE IF NOT EXISTS clubs (
    id BIGSERIAL PRIMARY KEY,
    transfermarkt_club_id INTEGER UNIQUE,
    club_slug TEXT UNIQUE,
    club_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE clubs ADD COLUMN IF NOT EXISTS club_name TEXT;

CREATE TABLE IF NOT EXISTS players (
    id BIGSERIAL PRIMARY KEY,
    transfermarkt_player_id INTEGER UNIQUE,
    player_name TEXT,
    position TEXT,
    date_of_birth DATE,
    nationality TEXT,
    height_m NUMERIC(4,2),
    foot TEXT,
    market_value_eur NUMERIC(14,2),
    club_id BIGINT REFERENCES clubs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_players_club_id ON players(club_id);

CREATE TABLE IF NOT EXISTS player_season_stats (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES players(id),
    club_id BIGINT REFERENCES clubs(id),
    season INTEGER,
    squad_inclusions INTEGER,
    appearances INTEGER,
    goals INTEGER,
    assists INTEGER,
    yellow_cards INTEGER,
    second_yellow_cards INTEGER,
    red_cards INTEGER,
    substitutions_on INTEGER,
    substitutions_off INTEGER,
    minutes_played INTEGER,
    ppg NUMERIC(4,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, club_id, season)
);

CREATE INDEX IF NOT EXISTS idx_player_season_stats_club_season ON player_season_stats(club_id, season);
ALTER TABLE player_season_stats ADD COLUMN IF NOT EXISTS squad_inclusions INTEGER;

CREATE TABLE IF NOT EXISTS contract_terms (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT REFERENCES players(id),
    club_id BIGINT REFERENCES clubs(id),
    base_salary NUMERIC(14,2),
    contract_start DATE,
    contract_end DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, club_id, contract_start, contract_end)
);

CREATE TABLE IF NOT EXISTS contract_bonuses (
    id BIGSERIAL PRIMARY KEY,
    contract_term_id BIGINT REFERENCES contract_terms(id) ON DELETE CASCADE,
    bonus_type TEXT,
    competition TEXT,
    games INTEGER DEFAULT 0,
    starts INTEGER DEFAULT 0,
    minutes INTEGER DEFAULT 0,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    bonus_value NUMERIC(14,2) DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (contract_term_id, bonus_type, competition, games, starts, minutes, goals, assists, bonus_value)
);

ALTER TABLE contract_bonuses ADD COLUMN IF NOT EXISTS bonus_type TEXT;
ALTER TABLE contract_bonuses ADD COLUMN IF NOT EXISTS competition TEXT;
ALTER TABLE contract_bonuses ADD COLUMN IF NOT EXISTS starts INTEGER DEFAULT 0;
