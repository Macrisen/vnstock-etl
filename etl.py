import os
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

# 2. Danh sách 10 mã cổ phiếu
TICKERS = ["FPT", "MWG", "VCB", "HPG", "TCB", "SSI", "VHM", "VIC", "MSN", "MBB"]

def fetch_ticker_data(ticker: str, days: int = 180) -> pd.DataFrame:
    """Lấy dữ liệu từ DNSE API (không chặn IP quốc tế)."""
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
                df = pd.DataFrame({
                    "trade_date": [datetime.fromtimestamp(ts).strftime("%Y-%m-%d") for ts in data["t"]],
                    "open": data["o"],
                    "high": data["h"],
                    "low": data["l"],
                    "close": data["c"],
                    "volume": data["v"],
                    "ticker": ticker
                })
                return df
    except Exception as e:
        logging.error(f"Error fetching {ticker}: {e}")
    return pd.DataFrame()
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
  """Tính toán các chỉ báo kỹ thuật và loại bỏ hoàn toàn giá trị null."""
  df = df.sort_values("trade_date").reset_index(drop=True)

  # 1. Tính Daily Return Pct (Dòng đầu tiên được gán bằng 0.0 thay vì NaN)
  df["daily_return_pct"] = (
      (df["close"].pct_change() * 100).round(2).fillna(0.0)
  )

  # 2. Tính MA7 với min_periods=1 (Có bao nhiêu phiên tính bấy nhiêu, không bị null)
  df["ma7"] = df["close"].rolling(window=7, min_periods=1).mean().round(2)

  # 3. Tính Volatility 7D (Độ lệch chuẩn 7 ngày, dòng đầu điền 0.0)
  df["volatility_7d"] = (
      df["daily_return_pct"].rolling(window=7, min_periods=1).std().round(2)
  )
  df["volatility_7d"] = df["volatility_7d"].fillna(0.0)

  # 4. Chốt chặn cuối: Thay thế mọi giá trị NaN còn sót lại bằng giá trị phù hợp
  df["ma7"] = df["ma7"].fillna(df["close"])

  return df
def upsert_to_supabase(df: pd.DataFrame):
    """Đẩy dữ liệu vào bảng stock_prices (Upsert dựa trên ticker + trade_date)."""
    records = df.to_dict(orient="records")
    # Upsert giúp cập nhật nếu ngày đó đã tồn tại hoặc thêm mới nếu chưa có
    supabase.table("stock_prices").upsert(records, on_conflict="ticker,trade_date").execute()

def main():
    logging.info("Starting Daily Stock ETL Pipeline...")
    total_records = 0
    
    for ticker in TICKERS:
        logging.info(f"Processing {ticker}...")
        raw_df = fetch_ticker_data(ticker)
        if not raw_df.empty:
            clean_df = transform_data(raw_df)
            upsert_to_supabase(clean_df)
            total_records += len(clean_df)
            logging.info(f"Upserted {len(clean_df)} rows for {ticker}")
        else:
            logging.warning(f"No data fetched for {ticker}")
            
    logging.info(f"ETL completed! Total records processed: {total_records}")

if __name__ == "__main__":
    main()