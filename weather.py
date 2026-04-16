import requests
from datetime import datetime
 
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
 
WEATHER_CODES = {
    0:  ("Clear Sky", "☀️"),
    1:  ("Mainly Clear", "🌤️"),
    2:  ("Partly Cloudy", "⛅"),
    3:  ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Icy Fog", "🌫️"),
    51: ("Light Drizzle", "🌦️"),
    53: ("Drizzle", "🌦️"),
    55: ("Heavy Drizzle", "🌧️"),
    61: ("Light Rain", "🌧️"),
    63: ("Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    71: ("Light Snow", "🌨️"),
    73: ("Snow", "❄️"),
    75: ("Heavy Snow", "❄️"),
    80: ("Light Showers", "🌦️"),
    81: ("Showers", "🌧️"),
    82: ("Heavy Showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    99: ("Thunderstorm w/ Hail", "⛈️"),
}
 
 
def get_coordinates(city: str):
    """Convert city name to lat/lon using Open-Meteo's geocoding API."""
    params = {"name": city, "count": 1, "language": "en", "format": "json"}
    response = requests.get(GEOCODING_URL, params=params)
    response.raise_for_status()
    data = response.json()
 
    if not data.get("results"):
        raise ValueError(f"City '{city}' not found. Please check the spelling.")
 
    result = data["results"][0]
    return {
        "lat": result["latitude"],
        "lon": result["longitude"],
        "city": result["name"],
        "country": result.get("country", ""),
        "country_code": result.get("country_code", "").lower(),
    }
 
 
def get_all_weather(city: str, units: str = "fahrenheit"):
    """
    Single function that fetches everything we need in one API call:
    - Current conditions
    - Hourly forecast (next 24 hours)
    - Daily forecast (7 days) with humidity + temperature
    """
    location = get_coordinates(city)
    wind_unit = "mph" if units == "fahrenheit" else "ms"
 
    params = {
        "latitude": location["lat"],
        "longitude": location["lon"],
        # Current conditions
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "wind_speed_10m",
            "weather_code",
        ],
        # Hourly for the next 24 hours
        "hourly": [
            "temperature_2m",
            "weather_code",
            "relative_humidity_2m",
        ],
        # Daily for 7 days
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "weather_code",
            "precipitation_probability_max",
            "relative_humidity_2m_mean",
        ],
        "temperature_unit": units,
        "wind_speed_unit": wind_unit,
        "forecast_days": 7,
        "timezone": "auto",
    }
 
    response = requests.get(WEATHER_URL, params=params)
    response.raise_for_status()
    data = response.json()

    timezone = data.get("timezone", "UTC")

    # ── Current ──────────────────────────────────────────────────────────────
    current = data["current"]
    code = current["weather_code"]
    description, emoji = WEATHER_CODES.get(code, ("Unknown", "🌡️"))
  
    current_weather = {
        "city": location["city"],
        "country": location["country"],
        "country_code": location["country_code"],
        "lat": location["lat"],
        "lon": location["lon"],
        "temp": current["temperature_2m"],
        "feels_like": current["apparent_temperature"],
        "humidity": current["relative_humidity_2m"],
        "wind_speed": current["wind_speed_10m"],
        "description": description,
        "emoji": emoji,
        "wind_unit": wind_unit,
        "timezone": timezone,
    }
 
    # ── Hourly (next 24 slots) ────────────────────────────────────────────────
    hourly_data = data["hourly"]
    hourly = []
    for i in range(24):
        h_code = hourly_data["weather_code"][i]
        h_desc, h_emoji = WEATHER_CODES.get(h_code, ("Unknown", "🌡️"))
        time_str = hourly_data["time"][i]  # "2024-01-15T09:00"
        hour_label = datetime.fromisoformat(time_str).strftime("%H:%M")
        hourly.append({
            "time": hour_label,
            "iso_time": time_str,
            "temp": hourly_data["temperature_2m"][i],
            "humidity": hourly_data["relative_humidity_2m"][i],
            "emoji": h_emoji,
        })
 
    # ── Daily (7 days) ────────────────────────────────────────────────────────
    daily_data = data["daily"]
    daily = []
    for i in range(7):
        d_code = daily_data["weather_code"][i]
        d_desc, d_emoji = WEATHER_CODES.get(d_code, ("Unknown", "🌡️"))
        daily.append({
            "date": daily_data["time"][i],
            "temp_max": daily_data["temperature_2m_max"][i],
            "temp_min": daily_data["temperature_2m_min"][i],
            "humidity": daily_data["relative_humidity_2m_mean"][i],
            "precipitation_probability": daily_data["precipitation_probability_max"][i],
            "description": d_desc,
            "emoji": d_emoji,
        })
 
    return current_weather, hourly, daily