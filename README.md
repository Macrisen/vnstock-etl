# VN Stock Price ETL Pipeline

Automated daily pipeline that extracts Vietnamese stock price data, computes
basic trading indicators, and loads it into a Postgres (Supabase) warehouse —
built to practice real ETL/orchestration concepts beyond one-off notebooks.

## Overview

Each weekday, the pipeline:
1. **Extracts** daily OHLCV price history for a configurable list of tickers
   (FPT, HPG, VNM, VCB, MWG by default) via the `vnstock` library.
2. **Transforms** the raw data: cleans duplicates, and derives daily return %,
   7-day moving average, and 7-day rolling volatility per ticker.
3. **Loads** the result into a Supabase (Postgres) table using an idempotent
   upsert (`ticker`, `trade_date` as composite key), so re-running the job
   never creates duplicate rows.
4. **Orchestrates** automatically via a GitHub Actions cron schedule
   (weekdays, shortly after VN market open) — no manual trigger needed.

## Architecture

```
vnstock API ──> extract() ──> transform() ──> Supabase (Postgres) ──> BI tool
                                                     ^
                                    GitHub Actions cron (daily, Mon–Fri)
```

## Tech stack

| Stage         | Tool                          |
|---------------|--------------------------------|
| Extract       | Python, `vnstock`              |
| Transform     | pandas                         |
| Load          | Supabase (Postgres), `supabase-py` |
| Orchestration | GitHub Actions (scheduled cron)|
| Warehouse     | Postgres (Supabase-hosted)     |

## Setup (for Mac)

1. Create a free [Supabase](https://supabase.com) project.
2. Run `schema.sql` in the Supabase SQL editor to create the `stock_prices` table.
3. Copy `.env.example` to `.env` and fill in your Supabase URL + key (for local runs).
4. Install dependencies:
   ```bash
   pip3 install -r requirements.txt
   ```
5. Run locally:
   ```bash
   python3 etl.py
   ```

## Running it automatically (GitHub Actions)

1. Push this repo to GitHub.
2. In the repo settings, add two secrets: `SUPABASE_URL` and `SUPABASE_KEY`.
3. The workflow in `.github/workflows/daily_etl.yml` will run automatically
   on weekdays, or you can trigger it manually from the **Actions** tab.

## Possible next steps

- Add a Streamlit or Power BI dashboard on top of the `stock_prices` table.
- Add data-quality checks (e.g. flag missing trading days, price outliers).
- Extend to fundamental data (P/E, ROE) for a valuation-screening view.

## Disclaimer

For educational/portfolio purposes only — not investment advice.
