"""
VN Stock Price ETL
------------------
Extracts daily OHLCV price data for a list of Vietnamese stock tickers
(via the vnstock library), computes a few derived indicators, and loads
the result into a Supabase (Postgres) table.

Designed to run daily via GitHub Actions (see .github/workflows/daily_etl.yml)
or manually: `python etl.py`

Env vars required (see .env.example):
    SUPABASE_URL       - your Supabase project URL
    SUPABASE_KEY       - service_role or anon key with insert/upsert rights
"""

import os
import sys
import logging
from datetime import datetime, timedelta

import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

#load_dotenv()  # reads .env in the current folder and always wins,
                # even if a stray empty SUPABASE_URL/KEY is already set in the
                # shell session (local runs only — GitHub Actions injects
                # secrets as real env vars instead, .env is not used there)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TICKERS = ["FPT","ACB","MWG","HPG","VNM", "VCB","BID", "MWG","SHS","VIX","GAS"]  # edit this list as you like
LOOKBACK_DAYS = 30          # how many days of history to (re)fetch each run
                             # (used only when BACKFILL_START_DATE is None)

BACKFILL_START_DATE = None  # set a fixed "YYYY-MM-DD" to backfill from
                             # that date instead of using LOOKBACK_DAYS.
                             # Set back to None once your backfill run is done,
                             # so daily automated runs stay fast (last 30 days
                             # only) instead of re-fetching the full history
                             # every single day.
TABLE_NAME = "stock_prices"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("vn-stock-etl")


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

def fetch_price_history(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Pull daily OHLCV history for one ticker from vnstock (VCI source)."""
    from vnstock.explorer.vci import Quote

    log.info(f"Fetching {ticker} from {start} to {end}")
    q = Quote(symbol=ticker, show_log=False)
    df = q.history(start=start, end=end, interval="1D")

    if df is None or df.empty:
        log.warning(f"No data returned for {ticker}")
        return pd.DataFrame()

    df["ticker"] = ticker
    return df


def extract(tickers: list[str], lookback_days: int) -> pd.DataFrame:
    end = datetime.today().strftime("%Y-%m-%d")
    if BACKFILL_START_DATE:
        start = BACKFILL_START_DATE
    else:
        start = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    frames = []
    for t in tickers:
        try:
            frames.append(fetch_price_history(t, start, end))
        except Exception as e:
            # One bad ticker shouldn't kill the whole pipeline
            log.error(f"Failed to fetch {t}: {e}")

    if not frames:
        raise RuntimeError("No data fetched for any ticker — aborting.")

    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

def transform(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # vnstock returns columns: time, open, high, low, close, volume
    df["time"] = pd.to_datetime(df["time"]).dt.date
    df = df.drop_duplicates(subset=["ticker", "time"])
    df = df.sort_values(["ticker", "time"])

    # Derived indicators — the kind of feature engineering an analyst would want
    df["daily_return_pct"] = (
        df.groupby("ticker")["close"].pct_change() * 100
    ).round(2)

    df["ma7"] = (
        df.groupby("ticker")["close"]
        .transform(lambda s: s.rolling(window=7, min_periods=1).mean())
        .round(2)
    )

    df["volatility_7d"] = (
        df.groupby("ticker")["daily_return_pct"]
        .transform(lambda s: s.rolling(window=7, min_periods=2).std())
        .round(2)
    )

    df = df.rename(columns={"time": "trade_date"})

    cols = [
        "ticker", "trade_date", "open", "high", "low", "close", "volume",
        "daily_return_pct", "ma7", "volatility_7d",
    ]
    df = df[cols]

    # Supabase/JSON needs native python types, not numpy/NaT
    df = df.astype(object).where(pd.notnull(df), None)
    df["trade_date"] = df["trade_date"].astype(str)

    return df


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()

    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set in Environment / Secrets"
        )

    return create_client(url, key)


def load(df: pd.DataFrame, client: Client) -> None:
    records = df.to_dict(orient="records")
    log.info(f"Upserting {len(records)} rows into '{TABLE_NAME}'")

    # Upsert on (ticker, trade_date) so re-running the ETL is idempotent
    # instead of creating duplicate rows.
    batch_size = 500
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(TABLE_NAME).upsert(
            batch, on_conflict="ticker,trade_date"
        ).execute()

    log.info("Load complete.")


# ---------------------------------------------------------------------------
# Pipeline entrypoint
# ---------------------------------------------------------------------------

def run() -> None:
    log.info(f"Starting ETL for tickers: {TICKERS}")
    raw = extract(TICKERS, LOOKBACK_DAYS)
    clean = transform(raw)
    client = get_supabase_client()
    load(clean, client)
    log.info(f"Done. {len(clean)} rows processed across {clean['ticker'].nunique()} tickers.")


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log.error(f"ETL failed: {e}")
        sys.exit(1)