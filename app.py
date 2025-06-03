import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime
import locale
import calendar
from google.cloud import bigquery
from google.oauth2 import service_account

st.set_page_config(layout="wide")

# Set Vietnamese locale
try:
    locale.setlocale(locale.LC_ALL, 'vi_VN.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'vi_VN')
    except:
        pass

# Đường dẫn file CSV cho dữ liệu lịch sử
HISTORICAL_CSV_PATH = r"./output_from_grib (6).csv"

# BigQuery configuration
# Thay đổi các thông tin sau theo project của bạn
# silicon-stock-452315-h4.weather_forecast.weather-forecasts
BIGQUERY_PROJECT_ID = "silicon-stock-452315-h4"
BIGQUERY_DATASET_ID = "weather_forecast"
BIGQUERY_TABLE_ID = "weather-forecast"
BIGQUERY_CREDENTIALS_PATH = "./silicon-stock-452315-h4-7d9ea6110a14.json"  

# Custom CSS for sidebar
st.markdown("""
    <style>
    .sidebar .sidebar-content {
        background-color: #f0f2f6;
    }
    .sidebar-title {
        font-size: 24px;
        font-weight: bold;
        color: #22223b;
        padding: 20px 0;
        text-align: center;
        border-bottom: 2px solid #e0e0e0;
        margin-bottom: 20px;
    }
    .sidebar-section {
        padding: 10px 0;
        border-bottom: 1px solid #e0e0e0;
    }
    .sidebar-section:last-child {
        border-bottom: none;
    }
    /* Custom radio button style */
    div[data-baseweb="radio"] > div {
        padding: 8px 16px;
        border-radius: 12px;
        margin-bottom: 8px;
        transition: background 0.2s;
    }
    div[data-baseweb="radio"] > div:hover {
        background: #e9ecef;
    }
    div[data-baseweb="radio"] label {
        font-size: 18px;
        font-weight: 600;
        color: #22223b;
        padding-left: 6px;
    }
    /* Custom checked color */
    div[data-baseweb="radio"] input[type="radio"]:checked + div {
        background: linear-gradient(90deg, #4ea8de 0%, #48bfe3 100%);
    }
    /* Custom radio dot color */
    div[data-baseweb="radio"] input[type="radio"]:checked {
        accent-color: #4ea8de;
    }
    h1, h2, h3 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar with enhanced styling
with st.sidebar:
    st.markdown('<div class="sidebar-title">Weather Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    section = st.radio(
        "Select Analysis Type",
        ["Yearly Analysis", "Monthly Analysis", "Daily Analysis", "Weather Forecast"],
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Add some spacing
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Add information section
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("### About")
    st.markdown("""
    This application provides comprehensive weather data analysis and forecasting tools.
    - Historical data analysis
    - Weather forecasting (BigQuery)
    - Interactive visualizations
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# Initialize BigQuery client
@st.cache_resource
def init_bigquery_client():
    """Initialize BigQuery client with credentials"""
    try:
        if BIGQUERY_CREDENTIALS_PATH and os.path.exists(BIGQUERY_CREDENTIALS_PATH):
            credentials = service_account.Credentials.from_service_account_file(
                BIGQUERY_CREDENTIALS_PATH
            )
            client = bigquery.Client(credentials=credentials, project=BIGQUERY_PROJECT_ID)
        else:
            # Use default credentials (for Google Cloud environments)
            client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
        return client
    except Exception as e:
        st.error(f"Error initializing BigQuery client: {e}")
        return None

# Đọc dữ liệu lịch sử
@st.cache_data
def load_historical_data():
    df = pd.read_csv(HISTORICAL_CSV_PATH)
    df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.date
    df['hour'] = df['time'].dt.hour
    df['month'] = df['time'].dt.month
    df['year'] = df['time'].dt.year
    df['day_name'] = df['time'].dt.strftime('%A')
    df['month_name'] = df['time'].dt.strftime('%B')
    # Convert temperature from Kelvin to Celsius
    if 't2m' in df.columns:
        df['t2m'] = df['t2m'] - 273.15
    return df

# Đọc dữ liệu dự báo từ BigQuery
# Đọc dữ liệu dự báo từ BigQuery
@st.cache_data
def load_forecast_data_from_bigquery():
    """Load forecast data from BigQuery with deduplication by max ID"""
    client = bigquery.Client.from_service_account_json(BIGQUERY_CREDENTIALS_PATH)
    if client is None:
        st.error("Cannot connect to BigQuery. Please check your credentials.")
        return pd.DataFrame()
    
    try:
        # Query với window function để lấy bản ghi có ID lớn nhất cho mỗi combination của time, lat, lon
        # Sửa lỗi: không thể PARTITION BY với FLOAT64, nên sử dụng CONCAT để tạo string key
        query = f"""
        WITH ranked_data AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY CONCAT(CAST(time AS STRING), '_', CAST(lat AS STRING), '_', CAST(lon AS STRING))
                    ORDER BY id DESC
                ) as rn
            FROM `{BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.{BIGQUERY_TABLE_ID}`
            WHERE DATE(time) >= '2025-05-25' 
            AND DATE(time) <= '2025-06-04'
        )
        SELECT 
            time as time,
            lat as latitude,
            lon as longitude,
            `2m_temperature` as temperature_2m,
            mean_sea_level_pressure as mean_sea_level_pressure,
            total_precipitation_6hr as total_precipitation_6hr,
            `10m_u_component_of_wind` as u10,
            `10m_v_component_of_wind` as v10
        FROM ranked_data
        WHERE rn = 1
        ORDER BY time, latitude, longitude
        """
        
        # Execute query
        df = client.query(query).to_dataframe()
        
        if df.empty:
            st.warning("No forecast data found in BigQuery for the period 2025-05-25 to 2025-06-04.")
            return pd.DataFrame()
        
        # Log deduplication info
        st.sidebar.info(f"Loaded {len(df)} records after deduplication (ID-based)")
        
        # Rename columns to match historical data format
        df = df.rename(columns={
            'temperature_2m': 't2m',
            'mean_sea_level_pressure': 'msl',
            'total_precipitation_6hr': 'tp'
        })
        
        # Process datetime columns
        df['time'] = pd.to_datetime(df['time'])
        df['date'] = df['time'].dt.date
        df['hour'] = df['time'].dt.hour
        df['month'] = df['time'].dt.month
        df['year'] = df['time'].dt.year
        df['day_name'] = df['time'].dt.strftime('%A')
        df['month_name'] = df['time'].dt.strftime('%B')
        
        # Convert temperature from Kelvin to Celsius if needed
        if 't2m' in df.columns:
            # Check if temperature is in Kelvin (> 200) or Celsius
            if df['t2m'].mean() > 200:
                df['t2m'] = df['t2m'] - 273.15 + 6
        
        return df
        
    except Exception as e:
        st.error(f"Error loading data from BigQuery: {e}")
        return pd.DataFrame()
# Configuration section in sidebar for BigQuery
if section == "Weather Forecast":
    with st.sidebar:
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("### BigQuery Settings")
        
        # Allow users to input BigQuery settings
        project_id = st.text_input("Project ID", value=BIGQUERY_PROJECT_ID)
        dataset_id = st.text_input("Dataset ID", value=BIGQUERY_DATASET_ID)
        table_id = st.text_input("Table ID", value=BIGQUERY_TABLE_ID)
        
        # Display data period info
        st.info("📅 Forecast Period: 2025-05-25 to 2025-06-04")
        st.info("🔄 Auto-deduplication by max ID")
        
        if st.button("Update BigQuery Settings"):
            BIGQUERY_PROJECT_ID = project_id
            BIGQUERY_DATASET_ID = dataset_id
            BIGQUERY_TABLE_ID = table_id
            st.success("Settings updated!")
        
        st.markdown('</div>', unsafe_allow_html=True)

# Load data based on section
if section in ["Yearly Analysis", "Monthly Analysis", "Daily Analysis"]:
    df = load_historical_data()
    if not df.empty:
        latitude_min, latitude_max = float(df['latitude'].min()), float(df['latitude'].max())
        longitude_min, longitude_max = float(df['longitude'].min()), float(df['longitude'].max())
    else:
        st.error("Cannot load historical data.")
        st.stop()
else:
    # Load forecast data from BigQuery
    df = load_forecast_data_from_bigquery()
    if df.empty:
        st.error("Cannot load forecast data from BigQuery.")
        st.stop()

# Rest of the code remains the same for analysis sections
if section == "Yearly Analysis":
    st.markdown("<h1 style='color:#22223b;'>Yearly Weather Data Analysis</h1>", unsafe_allow_html=True)
    years = sorted(df['year'].unique())
    selected_year = st.selectbox('Select Year', years)
    filtered_df = df[df['year'] == selected_year]
    st.write(f"Selected Year: {selected_year}")
    col1, col2 = st.columns(2)
    with col1:
        lat = st.slider('Select Latitude', min_value=latitude_min, max_value=latitude_max, value=latitude_min, step=0.25, format="%.2f")
    with col2:
        lon = st.slider('Select Longitude', min_value=longitude_min, max_value=longitude_max, value=longitude_min, step=0.25, format="%.2f")

    # Lọc dữ liệu theo lat/lon
    point_df = filtered_df[(filtered_df['latitude'] == lat) & (filtered_df['longitude'] == lon)]
    if not point_df.empty:
        # Tính max/min nhiệt độ và tổng lượng mưa theo tháng (tp sang mm)
        month_stats = point_df.groupby('month').agg({
            't2m': ['max', 'min'],
            'tp': 'sum'
        }).reset_index()
        month_stats.columns = ['month', 'max_temp', 'min_temp', 'total_precip']
        month_stats['total_precip'] = month_stats['total_precip'] * 1000  # m -> mm
        # Nhãn tháng đẹp: T1, T2, ...
        month_stats['month_label'] = month_stats['month'].apply(lambda x: f"T{x}")

        col1, col2 = st.columns([2,2])
        with col1:
            fig, ax1 = plt.subplots(figsize=(7,5))
            ax1.bar(month_stats['month_label'], month_stats['total_precip'], color='dodgerblue', alpha=0.6, label='Total Precipitation')
            ax1.set_ylabel('Rainfall (mm)', color='dodgerblue')
            ax1.tick_params(axis='y', labelcolor='dodgerblue')
            ax1.set_xlabel('Month')
            ax2 = ax1.twinx()
            ax2.plot(month_stats['month_label'], month_stats['max_temp'], color='crimson', marker='o', label='Max Temperature')
            ax2.plot(month_stats['month_label'], month_stats['min_temp'], color='forestgreen', marker='o', label='Min Temperature')
            ax2.set_ylabel('Temperature (°C)', color='crimson')
            ax2.tick_params(axis='y', labelcolor='crimson')
            plt.xticks(month_stats['month_label'])
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
            plt.title('Temperature and Rainfall Analysis by Month')
            st.pyplot(fig, use_container_width=False)
        with col2:
            pie_data = month_stats[month_stats['total_precip'] > 0]
            if not pie_data.empty:
                values = pie_data['total_precip']
                months = pie_data['month_label']
                colors = plt.cm.tab20.colors
                def autopct_func(pct):
                    return f'{pct:.1f}%' if pct > 7 else ''
                fig2, ax3 = plt.subplots(figsize=(7,5))
                wedges, texts, autotexts = ax3.pie(
                    values,
                    labels=None,
                    autopct=autopct_func,
                    startangle=90,
                    colors=colors,
                    textprops={'fontsize': 12, 'weight': 'bold'}
                )
                ax3.legend(wedges, months, title="Month", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=11)
                ax3.set_title('Rainfall Distribution by Month', fontsize=14, weight='bold')
                st.pyplot(fig2, use_container_width=False)
            else:
                st.info('No rainfall data for this year at the selected location.')
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
    else:
        st.warning('No data for this location in the selected year.')
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)

elif section == "Monthly Analysis":
    st.markdown("<h1 style='color:#22223b;'>Monthly Weather Data Analysis</h1>", unsafe_allow_html=True)
    years = sorted(df['year'].unique())
    selected_year = st.selectbox('Select Year', years)
    months = sorted(df[df['year'] == selected_year]['month'].unique())
    selected_month = st.selectbox('Select Month', months, format_func=lambda x: f"{x:02d}")
    filtered_df = df[(df['year'] == selected_year) & (df['month'] == selected_month)]
    st.write(f"Selected Month: {selected_month:02d}/{selected_year}")
    col1, col2 = st.columns(2)
    with col1:
        lat = st.slider('Select Latitude', min_value=latitude_min, max_value=latitude_max, value=latitude_min, step=0.25, format="%.2f")
    with col2:
        lon = st.slider('Select Longitude', min_value=longitude_min, max_value=longitude_max, value=longitude_min, step=0.25, format="%.2f")

    # Lọc dữ liệu theo lat/lon
    point_df = filtered_df[(filtered_df['latitude'] == lat) & (filtered_df['longitude'] == lon)]
    if not point_df.empty:
        # Tính max/min nhiệt độ và tổng lượng mưa theo ngày (tp sang mm)
        daily_stats = point_df.groupby('date').agg({
            't2m': ['max', 'min'],
            'tp': 'sum'
        }).reset_index()
        daily_stats.columns = ['date', 'max_temp', 'min_temp', 'total_precip']
        daily_stats['total_precip'] = daily_stats['total_precip'] * 1000  # m -> mm

        col1, col2 = st.columns([2,2])
        with col1:
            fig, ax1 = plt.subplots(figsize=(7,5))
            ax1.bar(daily_stats['date'], daily_stats['total_precip'], color='dodgerblue', alpha=0.6, label='Total Precipitation')
            ax1.set_ylabel('Rainfall (mm)', color='dodgerblue')
            ax1.tick_params(axis='y', labelcolor='dodgerblue')
            ax1.set_xlabel('Date')
            ax2 = ax1.twinx()
            ax2.plot(daily_stats['date'], daily_stats['max_temp'], color='crimson', marker='o', label='Max Temperature')
            ax2.plot(daily_stats['date'], daily_stats['min_temp'], color='forestgreen', marker='o', label='Min Temperature')
            ax2.set_ylabel('Temperature (°C)', color='crimson')
            ax2.tick_params(axis='y', labelcolor='crimson')
            fig.autofmt_xdate(rotation=45)
            ax1.legend(loc='upper left')
            ax2.legend(loc='upper right')
            plt.title('Temperature and Rainfall Analysis')
            st.pyplot(fig, use_container_width=False)
        with col2:
            pie_data = daily_stats[daily_stats['total_precip'] > 0]
            if not pie_data.empty:
                # Pie chart: chỉ hiện % >7%, không label trực tiếp, legend bên cạnh
                values = pie_data['total_precip']
                dates = pie_data['date'].astype(str)
                colors = plt.cm.tab20.colors
                def autopct_func(pct):
                    return f'{pct:.1f}%' if pct > 7 else ''
                fig2, ax3 = plt.subplots(figsize=(7,5))
                wedges, texts, autotexts = ax3.pie(
                    values,
                    labels=None, # Không label trực tiếp
                    autopct=autopct_func,
                    startangle=90,
                    colors=colors,
                    textprops={'fontsize': 12, 'weight': 'bold'}
                )
                # Thêm legend bên cạnh
                ax3.legend(wedges, dates, title="Date", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=11)
                ax3.set_title('Rainfall Distribution by Day', fontsize=14, weight='bold')
                st.pyplot(fig2, use_container_width=False)
            else:
                st.info('No rainfall data for this month at the selected location.')
        # Kéo dài trang cho đẹp
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
    else:
        st.warning('No data for this location in the selected month.')
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)

elif section == "Daily Analysis":
    st.markdown("<h1 style='color:#22223b;'>Daily Weather Data Analysis</h1>", unsafe_allow_html=True)

    # Các trường có thể chọn
    available_fields = {
        'Temperature (°C)': 't2m',
        'Mean Sea Level Pressure': 'msl',
        'U Wind Component': 'u10',
        'V Wind Component': 'v10',
        'Total Precipitation': 'tp'
    }
    existing_fields = {k: v for k, v in available_fields.items() if v in df.columns}

    selected_field = st.selectbox('Select Attribute for Trend', list(existing_fields.keys()))
    dates = sorted(df['date'].unique())
    selected_date = st.selectbox('Select Date', dates, format_func=lambda x: x.strftime('%Y/%m/%d'))

    col1, col2 = st.columns(2)
    with col1:
        lat = st.slider('Select Latitude', min_value=latitude_min, max_value=latitude_max, value=latitude_min, step=0.25, format="%.2f")
    with col2:
        lon = st.slider('Select Longitude', min_value=longitude_min, max_value=longitude_max, value=longitude_min, step=0.25, format="%.2f")

    df_point = df[(df['date'] == selected_date) & (df['latitude'] == lat) & (df['longitude'] == lon)]

    st.markdown(f"**{selected_field} Trend (6-hourly)**")
    if not df_point.empty:
        # Lấy trung bình theo từng giờ (thực tế chỉ có mỗi 6 tiếng/lần)
        df_hour = df_point.groupby('hour')[existing_fields[selected_field]].mean().reset_index()
        y_data = df_hour[existing_fields[selected_field]]
        # Nếu là trường lượng mưa thì chuyển sang mm
        if existing_fields[selected_field] == 'tp':
            y_data = y_data * 1000
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df_hour['hour'], y_data, marker='o', color='b', linewidth=2, markersize=5)
        ax.set_xlabel('Hour', fontsize=10)
        ax.set_ylabel(selected_field + (' (mm)' if existing_fields[selected_field]=='tp' else ''), fontsize=10)
        ax.set_title(f"{selected_field} Trend on {selected_date}", fontsize=12)
        ax.tick_params(axis='both', labelsize=9)
        ax.grid(True)
        plt.xticks(df_hour['hour'])
        col_left, col_center, col_right = st.columns([1,3,1])
        with col_center:
            st.pyplot(fig, use_container_width=False)
    else:
        st.warning('No data for this location on selected date.')

else:  # Weather Forecast section
    st.markdown("<h1 style='color:#22223b;'>Weather Forecast (BigQuery)</h1>", unsafe_allow_html=True)
    

    # Chọn trường dữ liệu dự báo
    forecast_fields = {
        'Mean Sea Level Pressure': 'msl',
        'Temperature (°C)': 't2m',
        'Precipitation (6hr)': 'tp',
        'U Wind 10m': 'u10',
        'V Wind 10m': 'v10',
    }
    
    selected_forecast_field = st.selectbox('Select Attribute for Trend', list(forecast_fields.keys()))
    dates = sorted(df['date'].unique())
    selected_date = st.selectbox('Select Date', dates, format_func=lambda x: x.strftime('%Y/%m/%d'))
    
    col1, col2 = st.columns(2)
    with col1:
        lat = st.slider('Select Latitude', min_value=float(df['latitude'].min()), max_value=float(df['latitude'].max()), value=float(df['latitude'].min()), step=0.25, format="%.2f")
    with col2:
        lon = st.slider('Select Longitude', min_value=float(df['longitude'].min()), max_value=float(df['longitude'].max()), value=float(df['longitude'].min()), step=0.25, format="%.2f")
    
    df_point = df[(df['latitude'] == lat) & (df['longitude'] == lon) & (df['date'] == selected_date)]
    
    # Thêm phần cảnh báo thời tiết cho nuôi trồng thủy sản
    st.markdown("### 🐟 Cảnh báo thời tiết cho nuôi trồng thủy sản")
    
    # Lấy dữ liệu cho ngày được chọn
    temp_data = df_point[df_point['t2m'].notna()]
    precip_data = df_point[df_point['tp'].notna()]
    wind_data = df_point[(df_point['u10'].notna()) & (df_point['v10'].notna())]
    
    if not temp_data.empty:
        min_temp = temp_data['t2m'].min()
        max_temp = temp_data['t2m'].max()
        
        # Hiển thị thông tin nhiệt độ
        st.metric("Nhiệt độ dự báo", f"{min_temp:.1f}°C - {max_temp:.1f}°C")
        
        # Cảnh báo dựa trên ngưỡng nhiệt độ
        if min_temp < 16:
            st.error("⚠️ Cảnh báo: Nhiệt độ có thể xuống dưới 16°C - nguy hiểm cho thủy sản!")
            st.markdown("""
            **Khuyến nghị:**
            - Tăng độ sâu ao nuôi lên ít nhất 2m
            - Che phủ ao bằng bạt hoặc lưới
            - Giảm 50% lượng thức ăn
            - Theo dõi sức khỏe thủy sản mỗi 4 giờ
            - Chuẩn bị hệ thống sưởi dự phòng
            """)
        elif min_temp < 20:
            st.warning("⚠️ Lưu ý: Nhiệt độ có thể xuống dưới 20°C - cần theo dõi chặt chẽ")
            st.markdown("""
            **Khuyến nghị:**
            - Theo dõi nhiệt độ nước mỗi 6 giờ
            - Chuẩn bị phương án che phủ ao
            - Giảm 30% lượng thức ăn
            - Tăng cường sục khí
            """)
        else:
            st.success("✅ Nhiệt độ trong khoảng an toàn cho thủy sản")
    
    # Cảnh báo lượng mưa
    if not precip_data.empty:
        total_precip = precip_data['tp'].sum() * 1000  # Chuyển từ m sang mm
        st.metric("Lượng mưa dự báo", f"{total_precip:.1f} mm")
        
        if total_precip > 100:
            st.error("⚠️ Cảnh báo: Lượng mưa rất lớn (>100mm) - nguy hiểm cho ao nuôi")
            st.markdown("""
            **Khuyến nghị:**
            - Kiểm tra và nâng cấp hệ thống thoát nước
            - Đo pH nước mỗi 4 giờ (duy trì 6.5-8.5)
            - Ngừng cho ăn trong ngày mưa
            - Tăng cường sục khí
            - Theo dõi nồng độ oxy mỗi 2 giờ
            - Chuẩn bị vôi để điều chỉnh pH
            """)
        elif total_precip > 50:
            st.warning("⚠️ Cảnh báo: Lượng mưa lớn có thể ảnh hưởng đến ao nuôi")
            st.markdown("""
            **Khuyến nghị:**
            - Kiểm tra hệ thống thoát nước
            - Đo pH nước mỗi 6 giờ
            - Giảm 50% lượng thức ăn
            - Tăng cường sục khí
            - Theo dõi nồng độ oxy mỗi 4 giờ
            """)
    
    # Cảnh báo gió
    if not wind_data.empty:
        wind_speeds = np.sqrt(wind_data['u10']**2 + wind_data['v10']**2)
        max_wind = wind_speeds.max()
        st.metric("Tốc độ gió tối đa dự báo", f"{max_wind:.1f} m/s")
        
        if max_wind > 15:
            st.error("⚠️ Cảnh báo: Gió rất mạnh (>15 m/s) - nguy hiểm cho ao nuôi")
            st.markdown("""
            **Khuyến nghị:**
            - Cố định tất cả thiết bị trên ao
            - Che chắn ao bằng lưới chắn gió
            - Ngừng cho ăn trong thời gian gió mạnh
            - Tăng cường theo dõi chất lượng nước mỗi 4 giờ
            - Chuẩn bị máy phát điện dự phòng
            """)
        elif max_wind > 10:
            st.warning("⚠️ Cảnh báo: Gió mạnh có thể ảnh hưởng đến ao nuôi")
            st.markdown("""
            **Khuyến nghị:**
            - Cố định các thiết bị trên ao
            - Che chắn ao để tránh bụi và vật lạ
            - Giảm 50% lượng thức ăn
            - Tăng cường theo dõi chất lượng nước mỗi 6 giờ
            """)
    
    # Cảnh báo áp suất khí quyển
    if 'msl' in df_point.columns and df_point['msl'].notna().any():
        pressure_data = df_point[df_point['msl'].notna()]
        min_pressure = pressure_data['msl'].min() / 100  # Chuyển từ Pa sang hPa
        max_pressure = pressure_data['msl'].max() / 100
        
        st.metric("Áp suất khí quyển dự báo", f"{min_pressure:.1f} - {max_pressure:.1f} hPa")
        
        if min_pressure < 990:
            st.error("⚠️ Cảnh báo: Áp suất khí quyển rất thấp (<990 hPa) - nguy hiểm cho thủy sản")
            st.markdown("""
            **Khuyến nghị:**
            - Tăng cường sục khí 24/24
            - Theo dõi nồng độ oxy mỗi 2 giờ
            - Giảm 70% mật độ nuôi tạm thời
            - Ngừng cho ăn
            - Chuẩn bị máy phát điện dự phòng
            """)
        elif min_pressure < 1000:
            st.warning("⚠️ Lưu ý: Áp suất khí quyển thấp có thể ảnh hưởng đến sức khỏe thủy sản")
            st.markdown("""
            **Khuyến nghị:**
            - Tăng cường sục khí
            - Theo dõi nồng độ oxy mỗi 4 giờ
            - Giảm 50% mật độ nuôi tạm thời
            - Giảm 50% lượng thức ăn
            """)
    
    st.markdown(f"**{selected_forecast_field} Trend (Hourly)**")
    
    if not df_point.empty:
        if 'level' in df_point.columns:
            min_level = df_point['level'].min()
            df_point = df_point[df_point['level'] == min_level]
        
        df_hour = df_point.groupby('hour')[forecast_fields[selected_forecast_field]].mean().reset_index()
        y_data = df_hour[forecast_fields[selected_forecast_field]]
        
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        ax2.plot(df_hour['hour'], y_data, marker='o', color='b', linewidth=2, markersize=5)
        ax2.set_xlabel('Hour', fontsize=10)
        ax2.set_ylabel(selected_forecast_field, fontsize=10)
        ax2.set_title(f"{selected_forecast_field} Trend on {selected_date}", fontsize=12)
        ax2.tick_params(axis='both', labelsize=9)
        ax2.grid(True)
        plt.xticks(df_hour['hour'])
        col_left, col_center, col_right = st.columns([1,3,1])
        with col_center:
            st.pyplot(fig2, use_container_width=False)

    else:
        # Chọn trường dữ liệu dự báo
        forecast_fields = {
            'Mean Sea Level Pressure': 'msl',
            'Temperature (°C)': 't2m',
            'Precipitation (6hr)': 'tp',
            'U Wind 10m': 'u10',
            'V Wind 10m': 'v10',
        }
        
        # Filter fields that exist in the data
        existing_forecast_fields = {k: v for k, v in forecast_fields.items() if v in df.columns}
        
        if not existing_forecast_fields:
            st.error("No forecast fields found in the data.")
        else:
            selected_forecast_field = st.selectbox('Select Attribute for Trend', list(existing_forecast_fields.keys()))
            dates = sorted(df['date'].unique())
            selected_date = st.selectbox('Select Date', dates, format_func=lambda x: x.strftime('%Y/%m/%d'))
            
            col1, col2 = st.columns(2)
            with col1:
                lat = st.slider('Select Latitude', min_value=float(df['latitude'].min()), max_value=float(df['latitude'].max()), value=float(df['latitude'].min()), step=0.25, format="%.2f")
            with col2:
                lon = st.slider('Select Longitude', min_value=float(df['longitude'].min()), max_value=float(df['longitude'].max()), value=float(df['longitude'].min()), step=0.25, format="%.2f")
            
            df_point = df[(df['latitude'] == lat) & (df['longitude'] == lon) & (df['date'] == selected_date)]
            st.markdown(f"**{selected_forecast_field} Trend (Hourly)**")
            
            if not df_point.empty:
                if 'level' in df_point.columns:
                    min_level = df_point['level'].min()
                    df_point = df_point[df_point['level'] == min_level]
                
                df_hour = df_point.groupby('hour')[existing_forecast_fields[selected_forecast_field]].mean().reset_index()
                y_data = df_hour[existing_forecast_fields[selected_forecast_field]]
                
                fig2, ax2 = plt.subplots(figsize=(8,4))
                ax2.plot(df_hour['hour'], y_data, marker='o', color='b')
                ax2.set_xlabel('Hour')
                ax2.set_ylabel(selected_forecast_field)
                ax2.set_title(f"{selected_forecast_field} Trend on {selected_date}")
                ax2.grid(True)
                plt.xticks(df_hour['hour'])
                st.pyplot(fig2)
                
                # Display data summary
                st.markdown("### Data Summary")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Records", len(df_point))
                with col2:
                    st.metric("Date Range", f"{df['date'].min()} to {df['date'].max()}")
                with col3:
                    st.metric("Location", f"Lat {lat:.2f}, Lon {lon:.2f}")
                
                # Display unique dates available
                unique_dates = sorted(df['date'].unique())
                st.markdown("### Available Forecast Dates")
                date_cols = st.columns(min(5, len(unique_dates)))
                for i, date in enumerate(unique_dates[:10]):  # Show first 10 dates
                    with date_cols[i % 5]:
                        st.write(f"📅 {date}")
                        
                if len(unique_dates) > 10:
                    st.write(f"... and {len(unique_dates) - 10} more dates")
                
            else:
                st.warning('No forecast data for this location on selected date.')
                st.info("Available locations and dates:")
                if not df.empty:
                    location_summary = df.groupby(['latitude', 'longitude']).size().reset_index(name='count')
                    st.dataframe(location_summary.head(10))