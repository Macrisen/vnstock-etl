# 📈 VN Stock Price ETL & Dashboard Pipeline

An automated daily ETL pipeline that extracts Vietnamese stock price data, computes key trading indicators, stores them in a Postgres (Supabase) warehouse, and visualizes them on an interactive Streamlit Web Dashboard.

🔗 **[Live Demo App](https://vnstock-etl-mpmgx6ztsvtsqynzemor4z.streamlit.app/)**

---

## 🌟 Features

* **Automated Data Extraction:** Fetches daily OHLCV price history for key tickers (FPT, ACB, MWG, HPG, VNM, VCB, SHS, VIX, GAS, etc.) via `vnstock`.
* **Data Transformation:** Cleans duplicates, computes daily returns (%), 7-day Moving Averages (MA7), and rolling metrics using `pandas`.
* **Idempotent Storage:** Upserts transformed data into a Supabase (Postgres) table using `(ticker, trade_date)` as a composite primary key to prevent duplicate records.
* **Scheduled Orchestration:** Runs automatically on weekdays via GitHub Actions (scheduled cron job).
* **Interactive Dashboard:** Built with Streamlit and Plotly for real-time stock visualization, dark-mode charts, and customizable indicator filters.

---

## 🏗️ Architecture
vnstock API ──> extract() ──> transform() ──> Supabase (Postgres) ──> Streamlit Dashboard
^                          (Live Web App)
GitHub Actions Cron (Daily, Mon–Fri)
---

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Extract & Transform** | Python 3.14, `pandas`, `vnstock` |
| **Data Warehouse** | Supabase (Hosted Postgres) |
| **Orchestration** | GitHub Actions (Scheduled Cron) |
| **Visualization** | Streamlit, Plotly |

---

## 🚀 Local Setup

### 1. Clone & Dependencies
```bash
git clone [https://github.com/Macrisen/vnstock-etl.git](https://github.com/Macrisen/vnstock-etl.git)
cd vnstock-etl

# Install requirements
pip3 install -r requirements.txt
