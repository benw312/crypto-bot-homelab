CREATE TABLE IF NOT EXISTS market_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION,
    volume DOUBLE PRECISION
);

SELECT create_hypertable('market_data', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS sentiment_data (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    score DOUBLE PRECISION,
    source TEXT
);

SELECT create_hypertable('sentiment_data', 'time', if_not_exists => TRUE);
