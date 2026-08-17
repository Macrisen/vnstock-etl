Dưới đây là nội dung trọn gói của một file duy nhất **`README.md`**. Bạn chỉ cần bấm vào nút **Copy** ở góc trên khung code để dán vào dự án hoặc lưu thành file tải về:

```markdown
# 📈 VNStock Automated ETL Pipeline & Market Dashboard

Hệ thống tự động hóa toàn diện quy trình trích xuất, biến đổi và nạp dữ liệu (ETL) giá cổ phiếu thị trường Việt Nam vào cơ sở dữ liệu đám mây Supabase, kèm theo giao diện Dashboard trực quan hóa bằng Streamlit & Plotly.

---

## 🏗️ Kiến trúc hệ thống (System Architecture)

```text
[DNSE / Entrade API]
        │
        ▼ (Requests / Daily Schedule)
[GitHub Actions Runner] ─── (Transform: MA7, Return %, Volatility)
        │
        ▼ (Upsert via Supabase Client)
[Supabase (PostgreSQL)]
        │
        ▼ (Fetch via Streamlit Caching)
[Streamlit Dashboard (Interactive Charts)]

```

* **Data Source:** API mở DNSE (Entrade) lấy dữ liệu nến ngày (OHLCV).
* **Automation (CI/CD):** GitHub Actions chạy cronjob định kỳ vào 16:30 thứ 2 - thứ 6 (giờ VN).
* **Storage:** Supabase PostgreSQL Database (bảng `stock_prices`).
* **Visualization:** Streamlit + Plotly Dark Theme.

---

## 🚀 Hướng dẫn cài đặt & Triển khai

### 1. Cài đặt môi trường Local

```bash
# Clone repository
git clone [https://github.com/Macrisen/vnstock-etl.git](https://github.com/Macrisen/vnstock-etl.git)
cd vnstock-etl

# Tạo và kích hoạt virtual environment
python -m venv .venv
source .venv/bin/activate  # Trên macOS/Linux
# .venv\Scripts\activate   # Trên Windows

# Cài đặt dependencies
pip install -r requirements.txt

```

### 2. Cấu hình biến môi trường (`.env`)

Tạo file `.env` tại thư mục gốc:

```env
SUPABASE_URL=[https://your-project-id.supabase.co](https://your-project-id.supabase.co)
SUPABASE_KEY=your-supabase-service-role-or-anon-key

```

### 3. Khởi tạo bảng dữ liệu trên Supabase SQL Editor

```sql
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

```

### 4. Cấu hình GitHub Actions Secret (Cho CI/CD tự động)

Vào **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** trên GitHub và thêm 2 Secrets:

* `SUPABASE_URL`: Đường dẫn URL project Supabase.
* `SUPABASE_KEY`: Supabase API Key.

### 5. Chạy Dashboard

```bash
streamlit run app.py

```

---

## 🛠️ Nhật ký kỹ thuật & Xử lý sự cố (Troubleshooting & Engineering Log)

### 1. Lỗi giới hạn thiết bị (Device Registration Limit) & `hosting_service`

* **Hiện tượng:** Chạy trên GitHub Actions gặp lỗi:
```text
[ERROR] Failed to fetch <TICKER>: local variable 'hosting_service' referenced before assignment

```


* **Nguyên nhân:** Thư viện `vnstock` (bản 3.x) áp dụng cơ chế xác thực thiết bị phần cứng (tối đa 3 lần đổi máy/ngày). Mỗi lần GitHub Actions chạy là một máy ảo mới hoàn toàn $\rightarrow$ kích hoạt chặn thiết bị $\rightarrow$ lỗi logic gán biến nội bộ của thư viện.
* **Xử lý:** Thay thế wrapper `vnstock` bằng cách gọi trực tiếp HTTP request tới API dữ liệu qua thư viện `requests`.

---

### 2. Lỗi chặn IP Datacenter quốc tế (Geo-blocking)

* **Hiện tượng:** Code chạy trên máy cá nhân (IP Việt Nam) lấy dữ liệu bình thường, nhưng chạy trên GitHub Actions (IP nước ngoài) luôn trả về mảng rỗng `[]`.
* **Nguyên nhân:** Một số API nội địa (TCBS, SSI) chặn hoặc hạn chế lưu lượng mạng từ các dải IP máy chủ đám mây nước ngoài để phòng chống DDoS.
* **Xử lý:** Chuyển sang sử dụng endpoint của **DNSE (Entrade API)**:
```text
GET [https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from=](https://services.entrade.com.vn/chart-api/v2/ohlcs/stock?from=){from}&to={to}&symbol={symbol}&resolution=1D

```


API này phản hồi nhanh, dữ liệu chuẩn và hoạt động ổn định 100% trên GitHub runner.

---

### 3. Xử lý triệt để giá trị `null` ở các chỉ báo kỹ thuật

* **Hiện tượng:** Cột `ma7`, `volatility_7d`, `daily_return_pct` bị `null` ở các dòng dữ liệu đầu tiên.
* **Nguyên nhân:** Hàm `.rolling(window=7)` yêu cầu đủ 7 phiên liên tiếp nên 6 phiên đầu sinh ra `NaN`. Hàm `.pct_change()` ở phiên đầu tiên không có mốc so sánh cũng sinh ra `NaN`.
* **Xử lý:** Bổ sung `min_periods=1` và áp dụng chuỗi gán giá trị mặc định (`fillna`):
```python
def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("trade_date").reset_index(drop=True)
    df["daily_return_pct"] = (df["close"].pct_change() * 100).round(2).fillna(0.0)
    df["ma7"] = df["close"].rolling(window=7, min_periods=1).mean().round(2).fillna(df["close"])
    df["volatility_7d"] = df["daily_return_pct"].rolling(window=7, min_periods=1).std().round(2).fillna(0.0)
    return df

```



---

### 4. Phòng tránh trùng lặp dữ liệu bằng cơ chế Upsert

* **Hiện tượng:** Pipeline quét lùi 180 ngày để tính MA7 chuẩn xác, dẫn đến lỗi vi phạm khóa chính `primary key (ticker, trade_date)` khi ghi dữ liệu định kỳ.
* **Xử lý:** Áp dụng phương thức `.upsert()` với cờ `on_conflict`:
```python
supabase.table("stock_prices").upsert(
    records, 
    on_conflict="ticker,trade_date"
).execute()

```


Cơ chế này tự động cập nhật bản ghi cũ nếu đã tồn tại và thêm mới nếu chưa có.

```

```