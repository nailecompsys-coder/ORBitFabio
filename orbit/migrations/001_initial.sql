-- ORBit initial schema (from Northstar build spec). Idempotent where possible.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'trader',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS otp_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) NOT NULL,
    code VARCHAR(10) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    opend_port INTEGER NOT NULL,
    moomoo_account_id VARCHAR(50),
    trd_env VARCHAR(20) DEFAULT 'SIMULATE',
    expo_push_token VARCHAR(200),
    connected_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS bot_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    strategy VARCHAR(50) DEFAULT 'FABIO',
    status VARCHAR(20) DEFAULT 'idle',
    symbols TEXT[] DEFAULT ARRAY['SPY', 'QQQ', 'NVDA']::text[],
    trd_env VARCHAR(20) DEFAULT 'SIMULATE',
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    UNIQUE(user_id)
);

CREATE TABLE IF NOT EXISTS trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES bot_sessions(id),
    symbol VARCHAR(10) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    option_code VARCHAR(50),
    strike NUMERIC,
    expiry DATE,
    contracts INTEGER,
    entry_price NUMERIC,
    exit_price NUMERIC,
    entry_time TIMESTAMPTZ,
    exit_time TIMESTAMPTZ,
    exit_reason VARCHAR(50),
    pnl NUMERIC,
    return_pct NUMERIC,
    vix NUMERIC,
    or_atr_pct NUMERIC,
    vix_regime VARCHAR(50),
    day_color VARCHAR(20),
    trend VARCHAR(20),
    status VARCHAR(20) DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS bot_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bot_events_user_time ON bot_events(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    winners INTEGER DEFAULT 0,
    losers INTEGER DEFAULT 0,
    win_rate NUMERIC,
    net_pnl NUMERIC,
    gross_win NUMERIC,
    gross_loss NUMERIC,
    capital NUMERIC,
    daily_return NUMERIC,
    proven_edge NUMERIC,
    UNIQUE(user_id, date)
);
