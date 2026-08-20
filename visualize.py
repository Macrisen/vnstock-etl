import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as gg
from plotly.subplots import make_subplots
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Steamlit config 
st.set_page_config(
    page_title="VN Stock Dashboard",
    layout="wide"
)

# CSS Custom
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

# SUPABASE connect
@st.cache_resource
def init_supabase():
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = os.environ.get("SUPABASE_KEY", "").strip()
    if not url or not key:
        st.error("No configuration found for SUPABASE_URL or SUPABASE_KEY in .env file!")
        st.stop()
    return create_client(url, key)

# Supabase load data
@st.cache_data(ttl=300) 
def load_data():
    supabase = init_supabase()
    response = supabase.table("stock_prices").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if not df.empty:
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date")
    return df

# Main Header
st.title("📈 20 Tickers VNStock Market Dashboard")
st.caption("Data source: Supabase")

df_all = load_data()

if df_all.empty:
    st.warning("No data available in the Supabase database.")
    st.stop()

# Sidebar: Lọc mã cổ phiếu
st.sidebar.header("🔍 Data filter")
tickers = sorted(df_all["ticker"].unique())
selected_ticker = st.sidebar.selectbox("Choose a ticker:", tickers)

# Sidebar: Bật/tắt Chỉ báo Kỹ thuật
st.sidebar.subheader("📊 Technical Indicators")
show_bb = st.sidebar.checkbox("Bollinger Bands (20, 2)", value=True)
show_ma7 = st.sidebar.checkbox("MA7", value=False)
show_ma20 = st.sidebar.checkbox("MA20", value=True)
show_ma50 = st.sidebar.checkbox("MA50", value=True)
show_ma100 = st.sidebar.checkbox("MA100", value=False)
show_ma200 = st.sidebar.checkbox("MA200", value=False)

# Lọc dữ liệu theo mã được chọn
df = df_all[df_all["ticker"] == selected_ticker].copy()
latest_row = df.iloc[-1]
prev_row = df.iloc[-2] if len(df) > 1 else latest_row

# Hiển thị Metrics tổng quan
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

# Khởi tạo đồ thị kết hợp Subplots (Price + Volume)
fig = make_subplots(
    rows=2, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.03, 
    subplot_titles=(f'Price & Indicators - {selected_ticker}', 'Volume'),
    row_width=[0.2, 0.7]
)

# 1. Candlestick Chart 
fig.add_trace(
    gg.Candlestick(
        x=df['trade_date'],
        open=df['open'], high=df['high'],
        low=df['low'], close=df['close'],
        name="OHLC"
    ), row=1, col=1
)

# 2. Bollinger Bands
if show_bb and "bb_upper" in df.columns and "bb_lower" in df.columns:
    # Dải trên
    fig.add_trace(
        gg.Scatter(
            x=df['trade_date'], y=df['bb_upper'],
            line=dict(color='rgba(66, 165, 245, 0.4)', width=1, dash='dot'),
            name="BB Upper"
        ), row=1, col=1
    )
    # Dải dưới kèm tô bóng
    fig.add_trace(
        gg.Scatter(
            x=df['trade_date'], y=df['bb_lower'],
            line=dict(color='rgba(66, 165, 245, 0.4)', width=1, dash='dot'),
            fill='tonexty',
            fillcolor='rgba(66, 165, 245, 0.08)',
            name="BB Lower"
        ), row=1, col=1
    )

# 3. Moving Averages
ma_configs = [
    (show_ma7, "ma7", "#FF9800", "MA7", 1.2),
    (show_ma20, "ma20", "#29B6F6", "MA20", 1.5),
    (show_ma50, "ma50", "#AB47BC", "MA50", 1.5),
    (show_ma100, "ma100", "#26A69A", "MA100", 1.5),
    (show_ma200, "ma200", "#EF5350", "MA200", 2.0),
]

for is_visible, col_name, color, label, width in ma_configs:
    if is_visible and col_name in df.columns:
        fig.add_trace(
            gg.Scatter(
                x=df['trade_date'], y=df[col_name],
                line=dict(color=color, width=width),
                name=label
            ), row=1, col=1
        )

# 4. Volume Bar Chart
fig.add_trace(
    gg.Bar(
        x=df['trade_date'], y=df['volume'], 
        name="Volume", marker_color='#26a69a'
    ), row=2, col=1
)

# Layout hoàn chỉnh
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=650,
    margin=dict(l=20, r=20, t=40, b=20),
    template="plotly_dark",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

st.plotly_chart(fig, use_container_width=True)

# Bảng chi tiết dữ liệu
with st.expander("📄 Detail Data"):
    st.dataframe(df.sort_values("trade_date", ascending=False), use_container_width=True)