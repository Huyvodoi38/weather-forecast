AQUACULTURE_REGIONS = {
    "Quảng Ninh": {
        "lat": 21.0,
        "lon": 107.0,
        "city": "Hạ Long",
        "main_species": ["Tu hài", "Ngao", "Hàu", "Cá song (cá mú)", "Tôm sú", "Tôm thẻ chân trắng", "Rong biển"],
        "description": "Vùng biển Cô Tô, Vân Đồn nổi tiếng với nuôi lồng bè, và các đầm nuôi nước lợ ven biển.",
        "icon": "🦪",
        "color": "#FF6B6B",
        "temp_range": {"min": 18, "max": 32, "optimal": "22-28°C"},
        "salinity": "15-35‰",
        "special_warnings": {
            "cold": "Nhiệt độ <18°C: Nguy hiểm cho tu hài và hàu. Cần che phủ lồng bè.",
            "hot": "Nhiệt độ >32°C: Tăng cường sục khí, thay nước cho ao nuôi tôm.",
            "rain": "Mưa lớn: Kiểm tra độ mặn, tránh nước ngọt pha loãng quá mức."
        }
    },
    "Tiền Hải (Thái Bình)": {
        "lat": 20.5,
        "lon": 106.5,
        "city": "Tiền Hải",
        "main_species": ["Ngao (nghêu)", "Vẹm", "Cá bống bớp", "Tôm sú", "Tôm thẻ chân trắng", "Rươi"],
        "description": "Đặc biệt có các vùng nuôi ngao ven biển quy mô lớn.",
        "icon": "🦐",
        "color": "#4ECDC4",
        "temp_range": {"min": 16, "max": 30, "optimal": "20-26°C"},
        "salinity": "10-25‰",
        "special_warnings": {
            "cold": "Nhiệt độ <16°C: Nguy hiểm cho ngao và tôm. Tăng độ sâu ao nuôi.",
            "hot": "Nhiệt độ >30°C: Giảm mật độ nuôi, tăng cường thông gió.",
            "rain": "Mưa lớn: Đặc biệt nguy hiểm cho nuôi rươi, cần kiểm tra pH."
        }
    },
    "Kiến Thụy (Hải Phòng)": {
        "lat": 20.5,
        "lon": 106.5,
        "city": "Kiến Thụy",
        "main_species": ["Tôm sú", "Cá vược", "Cá rô phi", "Ngao", "Tôm thẻ chân trắng"],
        "description": "Một số vùng kết hợp mô hình lúa - cá, hoặc nuôi sinh thái (hữu cơ).",
        "icon": "🐟",
        "color": "#45B7D1",
        "temp_range": {"min": 18, "max": 30, "optimal": "22-28°C"},
        "salinity": "5-20‰",
        "special_warnings": {
            "cold": "Nhiệt độ <18°C: Ảnh hưởng đến cá rô phi và tôm. Cần biện pháp giữ ấm.",
            "hot": "Nhiệt độ >30°C: Tăng cường sục khí cho ao cá, giảm lượng thức ăn.",
            "rain": "Mưa lớn: Kiểm tra hệ thống thoát nước, tránh ngập úng ao nuôi."
        }
    }
}

import numpy as np

def get_weather_warnings_for_region(region_name, weather_data):
    """Generate specific weather warnings for aquaculture region"""
    region = AQUACULTURE_REGIONS[region_name]
    warnings = []
    if not weather_data.empty:
        # Temperature warnings
        if 't2m' in weather_data.columns:
            min_temp = weather_data['t2m'].min()
            max_temp = weather_data['t2m'].max()
            if min_temp < region["temp_range"]["min"]:
                warnings.append({
                    "type": "danger",
                    "title": "🌡️ Cảnh báo nhiệt độ thấp",
                    "message": region["special_warnings"]["cold"]
                })
            elif max_temp > region["temp_range"]["max"]:
                warnings.append({
                    "type": "warning", 
                    "title": "🌡️ Cảnh báo nhiệt độ cao",
                    "message": region["special_warnings"]["hot"]
                })
            else:
                warnings.append({
                    "type": "success",
                    "title": "🌡️ Nhiệt độ phù hợp",
                    "message": f"Nhiệt độ trong khoảng tối ưu {region['temp_range']['optimal']} cho {', '.join(region['main_species'][:3])}."
                })
        # Precipitation warnings
        if 'tp' in weather_data.columns:
            total_precip = weather_data['tp'].sum() * 1000
            if total_precip > 100:
                warnings.append({
                    "type": "danger",
                    "title": "🌧️ Cảnh báo mưa lớn",
                    "message": region["special_warnings"]["rain"]
                })
            elif total_precip > 50:
                warnings.append({
                    "type": "warning",
                    "title": "🌧️ Cảnh báo mưa vừa",
                    "message": "Theo dõi độ mặn và pH. Tăng cường sục khí."
                })
        # Wind warnings
        if 'u10' in weather_data.columns and 'v10' in weather_data.columns:
            wind_speeds = np.sqrt(weather_data['u10']**2 + weather_data['v10']**2)
            max_wind = wind_speeds.max()
            if max_wind > 15:
                warnings.append({
                    "type": "danger",
                    "title": "💨 Cảnh báo gió mạnh",
                    "message": "Cố định lồng bè, ngừng cho ăn, kiểm tra thiết bị neo đậu."
                })
            elif max_wind > 10:
                warnings.append({
                    "type": "warning",
                    "title": "💨 Cảnh báo gió vừa",
                    "message": "Kiểm tra hệ thống neo đậu, giảm hoạt động trên biển."
                })
    return warnings 