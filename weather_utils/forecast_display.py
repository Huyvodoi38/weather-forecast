import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from weather_utils.regions import AQUACULTURE_REGIONS, get_weather_warnings_for_region

def display_region_forecast(region_name, weather_data=None):
    region = AQUACULTURE_REGIONS[region_name]
    st.markdown(f"""
    <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, {region['color']} 0%, {region['color']}80 100%); border-radius: 15px; margin-bottom: 20px; color: white;'>
        <h1>{region['icon']} {region_name}</h1>
        <h3>📍 {region['city']} - {region['lat']:.4f}°N, {region['lon']:.4f}°E</h3>
        <p style='font-size: 16px; margin-top: 10px;'>{region['description']}</p>
    </div>
    """, unsafe_allow_html=True)
    if weather_data is not None and not weather_data.empty:
        # Làm tròn tọa độ
        lat = round(region['lat'], 2)
        lon = round(region['lon'], 2)
        # Hiển thị các chỉ số tổng hợp/ngày
        col1, col2, col3 = st.columns(3)
        if 't2m' in weather_data.columns:
            min_temp = weather_data['t2m'].min()
            max_temp = weather_data['t2m'].max()
            mean_temp = weather_data['t2m'].mean()
            with col1:
                st.metric("🌡️ Nhiệt độ (min-max)", f"{min_temp:.1f}°C - {max_temp:.1f}°C")
        if 'tp' in weather_data.columns:
            total_precip = weather_data['tp'].sum() * 1000
            with col2:
                st.metric("🌧️ Lượng mưa dự báo", f"{total_precip:.1f}mm")
        if 'u10' in weather_data.columns and 'v10' in weather_data.columns:
            wind_speeds = np.sqrt(weather_data['u10']**2 + weather_data['v10']**2)
            max_wind = wind_speeds.max() if not wind_speeds.empty else 0
            with col3:
                st.metric("💨 Gió mạnh nhất", f"{max_wind:.1f}m/s")
        warnings = get_weather_warnings_for_region(region_name, weather_data)
        st.markdown("### 📢 Cảnh báo chuyên biệt cho nuôi trồng thủy sản")
        for warning in warnings:
            if warning["type"] == "danger":
                st.markdown(f"""
                <div class=\"danger-box\">
                    <h4>{warning['title']}</h4>
                    <p>{warning['message']}</p>
                </div>
                """, unsafe_allow_html=True)
            elif warning["type"] == "warning":
                st.markdown(f"""
                <div class=\"warning-box\">
                    <h4>{warning['title']}</h4>
                    <p>{warning['message']}</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class=\"success-box\">
                    <h4>{warning['title']}</h4>
                    <p>{warning['message']}</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("### 🐟 Thông tin loài nuôi")
        species_cols = st.columns(min(3, len(region['main_species'])))
        for i, species in enumerate(region['main_species'][:6]):
            with species_cols[i % 3]:
                st.info(f"**{species}**\n\nNhiệt độ tối ưu: {region['temp_range']['optimal']}\nĐộ mặn: {region['salinity']}")
        # Biểu đồ xu hướng nhiệt độ chỉ vẽ nếu có dữ liệu
        # if 't2m' in weather_data.columns and len(weather_data['t2m'].dropna()) > 0:
        #     st.markdown("### 📊 Xu hướng nhiệt độ")
        #     daily_temps = weather_data.groupby('date')['t2m'].agg(['min', 'max', 'mean']).reset_index()
        #     if not daily_temps.empty:
        #         fig, ax = plt.subplots(figsize=(12, 6))
        #         ax.fill_between(daily_temps['date'], daily_temps['min'], daily_temps['max'], 
        #                        alpha=0.3, color=region['color'], label='Khoảng nhiệt độ')
        #         ax.plot(daily_temps['date'], daily_temps['mean'], color=region['color'], 
        #                linewidth=3, marker='o', label='Nhiệt độ trung bình')
        #         ax.axhline(y=region['temp_range']['min'], color='red', linestyle='--', alpha=0.7, label='Nhiệt độ tối thiểu')
        #         ax.axhline(y=region['temp_range']['max'], color='red', linestyle='--', alpha=0.7, label='Nhiệt độ tối đa')
        #         ax.set_xlabel('Ngày')
        #         ax.set_ylabel('Nhiệt độ (°C)')
        #         ax.set_title(f'Dự báo nhiệt độ cho {region_name}')
        #         ax.legend()
        #         ax.grid(True, alpha=0.3)
        #         plt.xticks(rotation=45)
        #         plt.tight_layout()
        #         st.pyplot(fig)
    else:
        st.warning("Không có dữ liệu dự báo cho ngày này.") 