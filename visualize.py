import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as gg
from plotly.subplots import make_subplots
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

#  Steamlit config 
st.set_page_config(
    page_title="VN Stock Dashboard",
    layout="wide"
)

# css custom
st.markdown("""
    <style>
    /* Tiêu đề chính chữ mảnh, thanh thoát */
    h1 {
        font-weight: 400 !important; 
        letter-spacing: -0.5px;
    }

    /* Các thẻ Metric bằng chiều cao nhau */
    div[data-testid="stMetric"] {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        padding: 12px 20px;
        border-radius: 8px;
        height: 110px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Font số Metric mảnh đẹp */
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 300 !important;
    }
    
    /* Font tiêu đề Metric */
    div[data-testid="stMetricLabel"] {
        font-weight: 400 !important;
        color: #8f96a3 !important;
    }
    </style>
""", unsafe_allow_html=True)

#  SUPABASE connect
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        st.error("No configuration found for SUPABASE_URL or SUPABASE_KEY in .env file!")
        st.stop()
    return create_client(url, key)

# supabase load data
@st.cache_data(ttl=300) 
def load_data():
    supabase = init_supabase()
    response = supabase.table("stock_prices").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date")
    return df

#  main 
st.title("📈 10 tickers VNStock Market Dashboard")
st.caption("Data source: Supabase")

df_all = load_data()

if df_all.empty:
    st.warning("No data available in the Supabase database.")
    st.stop()

# filter for sidebar
st.sidebar.header("🔍 Data filter")
tickers = sorted(df_all["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Choose a ticker:", tickers)

# on/off macd
show_ma7 = st.sidebar.checkbox("Show MA7 Indicator", value=True)
df = df_all[df_all["ticker"] == selected_ticker].copy()
latest_row = df.iloc[-1]
prev_row = df.iloc[-2] if len(df) > 1 else latest_row

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Close", f"{latest_row['close']:,}", f"{latest_row['daily_return_pct']:.2f}%")
with col2:
    st.metric("High", f"{latest_row['high']:,}")
with col3:
    st.metric("Low", f"{latest_row['low']:,}")
with col4:
    st.metric("Volume", f"{latest_row['volume']:,}")

st.markdown("")

#  Fig cread
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    subplot_titles=(f'Price - {selected_ticker}', 'Volume'),
    row_width=[0.2, 0.7]
)

# Candlestick Chart 
fig.add_trace(
    gg.Candlestick(
        x=df['trade_date'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name="OHLC"
    ), row=1, col=1
)

#  MA7 
if show_ma7:
    fig.add_trace(
        gg.Scatter(
            x=df['trade_date'], y=df['ma7'], 
            line=dict(color='orange', width=1.5), 
            name="MA7"
        ), row=1, col=1
    )

#  Volume 
fig.add_trace(
    gg.Bar(
        x=df['trade_date'], y=df['volume'], 
        name="Volume", marker_color='teal'
    ), row=2, col=1
)

#  layout
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=600,
    margin=dict(l=20, r=20, t=40, b=20),
    template="plotly_dark" 
)

st.plotly_chart(fig, use_container_width=True)

#  detail data
with st.expander("📄 Detail Data"):
    st.dataframe(df.sort_values("trade_date", ascending=False), use_container_width=True)