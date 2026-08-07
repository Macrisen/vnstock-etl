-- Run this once in the Supabase SQL editor before the first ETL run.

create table if not exists stock_prices (
    ticker            text        not null,
    trade_date        date        not null,
    open              numeric,
    high              numeric,
    low               numeric,
    close             numeric,
    volume            bigint,
    daily_return_pct  numeric,
    ma7               numeric,
    volatility_7d     numeric,
    inserted_at       timestamptz default now(),
    primary key (ticker, trade_date)
);

create index if not exists idx_stock_prices_ticker_date
    on stock_prices (ticker, trade_date desc);
