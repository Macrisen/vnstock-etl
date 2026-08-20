import os
import time
from datetime import datetime, timedelta
import logging
import pandas as pd
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 1. Kết nối Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment variables.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Danh sách 20 mã cổ phiếu
TICKERS = [
    "FPT", "MWG", "VCB", "HPG", "TCB", 
    "SSI", "VHM", "VIC", "MSN", "MBB",
    "VNM", "GAS", "STB", "VPB", "ACB",
    "HDB", "CTG", "VRE", "PLX", "POW"
]

def fetch_ticker_data(ticker: str, days: int = 400) -> pd.DataFrame:
    """Lấy dữ liệu từ DNSE API (400 ngày để đủ tính MA200)."""
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    
    from_ts = int(start_dt.timestamp())
    to_ts = int(end_dt.timestamp())
    
    url = f"https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from={from_ts}&to={to_ts}&symbol={ticker}&resolution=1D"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            if "t" in data and len(data["t"]) > 0:
                return pd.DataFrame({
                    "trade_date": [datetime.fromtimestamp(ts).strftime("%Y-%m-%d") for ts in data["t"]],
                    "open": data["o"],
                    "high": data["h"],
                    "low": data["l"],
                    "close": data["c"],
                    "volume": data["v"],
                    "ticker": ticker
                })
    except Exception as e:
        logging.error(f"Error fetching {ticker}: {e}")
    return pd.DataFrame()

def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán Daily Return, Moving Averages và Bollinger Bands."""
    df = df.sort_values("trade_date").reset_index(drop=True)

    # 1. Daily Return (%) & Volatility 7D
    df["daily_return_pct"] = (df["close"].pct_change() * 100).round(2).fillna(0.0)
    df["volatility_7d"] = (
        df["daily_return_pct"].rolling(window=7, min_periods=1).std().round(2).fillna(0.0)
    )

    # 2. Moving Averages (MA7, MA20, MA50, MA100, MA200)
    ma_windows = [7, 20, 50, 100, 200]
    for w in ma_windows:
        df[f"ma{w}"] = df["close"].rolling(window=w, min_periods=1).mean().round(2)
        df[f"ma{w}"] = df[f"ma{w}"].fillna(df["close"])

    # 3. Bollinger Bands (20, 2)
    # Độ lệch chuẩn 20 phiên
    std20 = df["close"].rolling(window=20, min_periods=1).std().fillna(0.0)
    
    df["bb_upper"] = (df["ma20"] + (2 * std20)).round(2)
    df["bb_lower"] = (df["ma20"] - (2 * std20)).round(2)

    return df

def upsert_to_supabase(df: pd.DataFrame):
    """Đẩy dữ liệu vào bảng stock_prices."""
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    supabase.table("stock_prices").upsert(records, on_conflict="ticker,trade_date").execute()

def main():
    logging.info(f"Starting Stock ETL Pipeline for {len(TICKERS)} tickers...")
    total_records = 0
    
    for ticker in TICKERS:
        logging.info(f"Processing {ticker}...")
        raw_df = fetch_ticker_data(ticker, days=400)
        
        if not raw_df.empty:
            clean_df = transform_data(raw_df)
            upsert_to_supabase(clean_df)
            total_records += len(clean_df)
            logging.info(f"Upserted {len(clean_df)} rows for {ticker}")
        else:
            logging.warning(f"No data fetched for {ticker}")
            
        time.sleep(0.5)
            
    logging.info(f"ETL completed! Total records processed: {total_records}")

if __name__ == "__main__":
    main()