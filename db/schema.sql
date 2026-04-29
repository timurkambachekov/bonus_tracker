CREATE TABLE competitions (
    id BIGSERIAL PRIMARY KEY,
    transfermarkt_code TEXT UNIQUE,
    name TEXT NOT NULL,
    country TEXT,
    season INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE clubs (
    id BIGSERIAL PRIMARY KEY,
    transfermarkt_club_id INTEGER UNIQUE,
    club_slug TEXT UNIQUE,
    club_name TEXT NOT NULL,
    competition_id BIGINT REFERENCES competitions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clubs_competition_id ON clubs(competition_id);


CREATE TABLE players (
    id BIGSERIAL PRIMARY KEY,
    transfermarkt_player_id INTEGER UNIQUE,
    player_name TEXT NOT NULL,
    position TEXT,
    date_of_birth DATE,
    nationality TEXT,
    height_m NUMERIC(4,2),
    foot TEXT,
    market_value_eur NUMERIC(14,2),
    club_id BIGINT REFERENCES clubs(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_players_club_id ON players(club_id);


CREATE TABLE app_users (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (role IN ('viewer', 'club_rep', 'admin'))
);

CREATE INDEX idx_app_users_email ON app_users(email);


CREATE TABLE app_user_clubs (
    user_id BIGINT NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, club_id)
);

CREATE INDEX idx_app_user_clubs_club_id ON app_user_clubs(club_id);


CREATE TABLE player_season_stats (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    competition_id BIGINT REFERENCES competitions(id),
    season INTEGER NOT NULL,
    squad_inclusions INTEGER,
    appearances INTEGER,
    starts INTEGER,
    full_games INTEGER,
    substitutions_on INTEGER,
    substitutions_off INTEGER,
    minutes_played INTEGER,
    goals INTEGER,
    assists INTEGER,
    yellow_cards INTEGER,
    second_yellow_cards INTEGER,
    red_cards INTEGER,
    ppg NUMERIC(4,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, club_id, competition_id, season, created_at)
);

CREATE INDEX idx_player_season_stats_player_id ON player_season_stats(player_id);
CREATE INDEX idx_player_season_stats_club_id ON player_season_stats(club_id);
CREATE INDEX idx_player_season_stats_competition_id ON player_season_stats(competition_id);
CREATE INDEX idx_player_season_stats_season ON player_season_stats(season);


CREATE TABLE contracts (
    id BIGSERIAL PRIMARY KEY,
    player_id BIGINT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    club_id BIGINT NOT NULL REFERENCES clubs(id) ON DELETE CASCADE,
    base_salary NUMERIC(14,2),
    contract_start DATE NOT NULL,
    contract_end DATE NOT NULL,
    contract_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, club_id, contract_start, contract_end),
    CHECK (contract_end >= contract_start)
);

CREATE INDEX idx_contracts_player_id ON contracts(player_id);
CREATE INDEX idx_contracts_club_id ON contracts(club_id);


CREATE TABLE contract_bonuses (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    bonus_type TEXT NOT NULL,
    competition_id BIGINT NOT NULL REFERENCES competitions(id),
    condition_operator TEXT NOT NULL DEFAULT 'and',
    bonus_value NUMERIC(14,2) NOT NULL DEFAULT 0,
    display_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (bonus_type IN ('seasonal', 'one_time', 'repeatable')),
    CHECK (condition_operator IN ('and', 'or')),
    UNIQUE (contract_id, display_order)
);

CREATE INDEX idx_contract_bonuses_contract_id ON contract_bonuses(contract_id);


CREATE TABLE contract_bonus_conditions (
    id BIGSERIAL PRIMARY KEY,
    contract_bonus_id BIGINT NOT NULL REFERENCES contract_bonuses(id) ON DELETE CASCADE,
    condition_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    threshold NUMERIC(14,2) NOT NULL,
    display_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        condition_type IN (
            'goals',
            'assists',
            'goal_contributions',
            'minutes_played',
            'squad_inclusions',
            'appearances',
            'games_played',
            'starts',
            'full_games',
            'yellow_cards',
            'red_cards'
        )
    ),
    CHECK (direction IN ('>', '<', '=', '>=', '<=')),
    UNIQUE (contract_bonus_id, display_order)
);

CREATE INDEX idx_contract_bonus_conditions_bonus_id ON contract_bonus_conditions(contract_bonus_id);


CREATE TABLE contract_bonus_binding_groups (
    id BIGSERIAL PRIMARY KEY,
    contract_id BIGINT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    group_name TEXT,
    display_order INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (contract_id, group_name),
    UNIQUE (contract_id, display_order)
);

CREATE INDEX idx_contract_bonus_binding_groups_contract_id
    ON contract_bonus_binding_groups(contract_id);


CREATE TABLE contract_bonus_binding_group_members (
    binding_group_id BIGINT NOT NULL REFERENCES contract_bonus_binding_groups(id) ON DELETE CASCADE,
    contract_bonus_id BIGINT NOT NULL REFERENCES contract_bonuses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (binding_group_id, contract_bonus_id),
    UNIQUE (contract_bonus_id)
);

CREATE INDEX idx_contract_bonus_binding_group_members_bonus_id
    ON contract_bonus_binding_group_members(contract_bonus_id);
