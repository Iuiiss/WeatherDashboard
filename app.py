import streamlit as st
import streamlit.components.v1 as components
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
from weather import get_all_weather

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Earth Flow", page_icon="🌍", layout="wide")

# Hide Streamlit's default header/footer for a cleaner look
st.markdown("""
<style>
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 0 !important; }
    body { background-color: #0d1117; }
    .stSidebar, .stTextInput, div[data-testid="stSidebar"] * {
        font-family: 'Syne', sans-serif !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }
    div[data-testid="stTextInput"] input {
        font-family: 'Syne', sans-serif !important;
    }
    .stRadio label span {
        font-family: 'Syne', sans-serif !important;
    }
    div[data-testid="stTextInput"] {
        margin-top: 10px;
    }
    div[data-testid="stTextInput"] input {
        font-family: 'Syne', sans-serif !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state: remember the last searched city ────────────────────────────
if "city" not in st.session_state:
    st.session_state.city = "New York"
if "units" not in st.session_state:
    st.session_state.units = "fahrenheit"

# ── Top bar: search + unit toggle ────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    city_input = st.text_input("", placeholder="Search city...", value=st.session_state.city, label_visibility="collapsed")

if city_input and city_input != st.session_state.city:
    st.session_state.city = city_input
    st.rerun()

units = st.session_state.units
with col3:
    unit_choice = st.radio("", ["°F", "°C"], 
                          index=0 if st.session_state.units == "fahrenheit" else 1,
                          horizontal=True, label_visibility="collapsed")
    new_units = "fahrenheit" if unit_choice == "°F" else "celsius"
    if new_units != units:
        st.session_state.units = new_units
        st.rerun()

units = st.session_state.units
temp_symbol = "°F" if units == "fahrenheit" else "°C"

# ── Fetch data ────────────────────────────────────────────────────────────────
try:
    current, hourly, daily = get_all_weather(st.session_state.city, units)
except ValueError as e:
    st.error(str(e))
    st.stop()
except Exception as e:
    st.error(f"Something went wrong: {e}")
    st.stop()

# ── Prepare data for the HTML dashboard ──────────────────────────────────────
today = datetime.now().strftime("%B %d, %y")
flag_url = f"https://flagcdn.com/64x48/{current['country_code']}.png"
weather_emoji = current.get('emoji', '🌡️')

timezone_str = current.get('timezone', 'UTC')
try:
    tz = ZoneInfo(timezone_str)
    local_now = datetime.now(tz)
except Exception:
    local_now = datetime.now()
local_hour = local_now.strftime("%Y-%m-%dT%H:00")

def build_hourly_cards():
    cards = []
    for h in hourly:
        is_current = h.get('iso_time') == local_hour
        extra_class = 'current-hour' if is_current else ''
        cards.append(f"""<div class="hour-card {extra_class}">
          <div class="hour-time">{h['time']}</div>
          <div class="hour-emoji">{h['emoji']}</div>
          <div class="hour-temp">{h['temp']:.0f}{temp_symbol}</div>
        </div>""")
    return ''.join(cards)

hourly_cards = build_hourly_cards()

# Weekly chart data as JSON (passed into JS)
weekly_labels = json.dumps([
    datetime.strptime(d["date"], "%Y-%m-%d").strftime("%b %d") for d in daily
])
weekly_temps   = json.dumps([d["temp_max"] for d in daily])
weekly_humidity = json.dumps([d["humidity"] for d in daily])

# ── Build the full HTML dashboard ─────────────────────────────────────────────
html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root {{
    --bg:        #0d1117;
    --card:      #161b22;
    --card2:     #21262d;
    --accent:    #58a6ff;
    --pink:      #c0557a;
    --text:      #e6edf3;
    --muted:     #8b949e;
    --border:    #30363d;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
    padding: 24px;
    padding-left: env(safe-area-inset-left, 24px);
    padding-right: env(safe-area-inset-right, 24px);
    padding-top: env(safe-area-inset-top, 24px);
    padding-bottom: env(safe-area-inset-bottom, 24px);
    max-width: 1400px;
    margin: 0 auto;
    overflow-x: hidden;
  }}

  /* ── Top bar ── */
  .topbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 28px;
  }}
  .brand {{ display: flex; align-items: center; gap: 10px; }}
  .brand-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text);
  }}
  .brand-date {{ font-size: 0.8rem; color: var(--muted); margin-top: 2px; }}

  /* ── Section titles ── */
  .section-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1.5rem;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--text);
  }}

  /* ── Today overview row ── */
  .today-row {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
    margin-bottom: 32px;
  }}

  /* ── Current weather card ── */
  .current-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    min-height: 280px;
    width: 100%;
    overflow: hidden;
  }}
  .current-top {{
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 20px;
  }}
  .flag {{ border-radius: 6px; height: 40px; }}
  .city-name {{
    font-family: 'Syne', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
  }}
  .metrics {{
    display: flex;
    gap: 32px;
    margin-bottom: 20px;
  }}
  .metric-val {{
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: var(--text);
  }}
  .metric-label {{ font-size: 0.75rem; color: var(--muted); margin-top: 2px; }}

  /* ── Hourly strip ── */
  .hourly-strip {{
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }}
  .hour-card {{
    background: var(--card2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 10px;
    text-align: center;
    min-width: 58px;
    flex-shrink: 0;
    transition: border-color 0.2s;
  }}
  .hour-card:hover {{ border-color: var(--accent); }}
  .hour-card.current-hour {{
    border-color: var(--accent);
    background: rgba(88,166,255,0.15);
  }}
  .hour-time {{ font-size: 0.7rem; color: var(--muted); }}
  .hour-emoji {{ font-size: 1.2rem; margin: 4px 0; }}
  .hour-temp {{ font-size: 0.85rem; font-weight: 500; }}

  /* ── Map card ── */
  .map-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    min-height: 280px;
    width: 100%;
    -webkit-overflow-scrolling: touch;
  }}
  #map {{ width: 100%; height: 100%; min-height: 280px; }}

  /* ── Weekly charts ── */
  .weekly-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }}
  .chart-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
  }}
  .chart-title {{
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 16px;
    color: var(--text);
  }}

  @media (max-width: 1024px) {{
    .today-row {{ grid-template-columns: 1fr; }}
    .weekly-row {{ grid-template-columns: 1fr; }}
  }}

  @media (max-width: 768px) {{
    body {{ 
      padding: 16px; 
      padding-bottom: 40px; 
      padding-left: env(safe-area-inset-left, 16px);
      padding-right: env(safe-area-inset-right, 16px);
      padding-top: env(safe-area-inset-top, 16px);
      min-height: -webkit-fill-available; 
    }}
    .topbar {{ margin-bottom: 16px; }}
    .brand-title {{ font-size: 1.2rem; }}
    .today-row {{ grid-template-columns: 1fr; grid-template-rows: auto; gap: 12px; margin-bottom: 24px; }}
    .map-card {{ grid-row: span 1; }}
    .weekly-row {{ grid-template-columns: 1fr; gap: 12px; }}
    .current-card, .map-card, .chart-card {{ padding: 16px; }}
    .section-title {{ font-size: 1.2rem; margin-bottom: 12px; }}
    .metric-val {{ font-size: 1.4rem; }}
    .metrics {{ gap: 16px; margin-bottom: 16px; }}
    .hourly-strip {{ gap: 6px; }}
    .hour-card {{ min-width: 50px; padding: 6px 8px; }}
    .chart-title {{ font-size: 0.9rem; margin-bottom: 12px; }}
  }}
</style>
</head>
<body>

<!-- ── Top bar ── -->
<div class="topbar">
  <div class="brand">
    <span style="font-size:1.8rem">{weather_emoji}</span>
    <div>
      <div class="brand-title">Earth Flow</div>
      <div class="brand-date">{today}</div>
    </div>
  </div>
</div>

<!-- ── Today Overviews ── -->
<div class="section-title">Today's Overview</div>
<div class="today-row">

  <!-- Current weather + hourly strip -->
  <div class="current-card">
    <div class="current-top">
      <img class="flag" src="{flag_url}" onerror="this.style.display='none'" />
      <div>
        <div class="city-name">{current['city']}, {current['country']}</div>
        <div style="font-size:0.8rem;color:var(--muted)">{current['description']}</div>
      </div>
    </div>
    <div class="metrics">
      <div>
        <div class="metric-val">{current['temp']:.1f}{temp_symbol}</div>
        <div class="metric-label">Temperature</div>
      </div>
      <div>
        <div class="metric-val">{current['humidity']}%</div>
        <div class="metric-label">Humidity</div>
      </div>
      <div>
        <div class="metric-val">{current['wind_speed']} {current['wind_unit']}</div>
        <div class="metric-label">Wind Speed</div>
      </div>
    </div>
    <div class="hourly-strip">
      {hourly_cards}
    </div>
  </div>

  <!-- Map -->
  <div class="map-card">
    <div id="map"></div>
  </div>

</div>

<!-- ── Weekly Overview ── -->
<div class="section-title">Weekly Overview</div>
<div class="weekly-row">

  <div class="chart-card">
    <div class="chart-title">Average Weekly Humidity</div>
    <canvas id="humidityChart"></canvas>
  </div>

  <div class="chart-card">
    <div class="chart-title">Average Weekly Temperature</div>
    <canvas id="tempChart"></canvas>
  </div>

</div>

<script>
  // ── Map ──────────────────────────────────────────────────────────────────
  const map = L.map('map', {{
    center: [{current['lat']}, {current['lon']}],
    zoom: 10,
    zoomControl: false
  }});
  
  // Add zoom control to top-right
  L.control.zoom({{position: 'topright'}}).addTo(map);
  
  // Base map
  const baseLayer = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors',
    maxZoom: 18
  }}).addTo(map);
  
  // Temperature layer
  const tempLayer = L.tileLayer('https://tile.openweathermap.org/map/temp_new/{{z}}/{{x}}/{{y}}.png?appid={OPENWEATHER_API_KEY}', {{
    attribution: '© OpenWeatherMap',
    opacity: 0.7,
    maxZoom: 18
  }});
  
  // Custom temperature toggle button
  const tempBtn = L.control({{position: 'topright'}});
  tempBtn.onAdd = function() {{
    const div = L.DomUtil.create('div', 'temp-toggle');
    div.innerHTML = '<button id="tempToggle" style="background:#161b22;color:#e6edf3;border:1px solid #30363d;padding:8px 12px;border-radius:8px;cursor:pointer;font-size:12px;">🌡️ Temperature</button>';
    return div;
  }};
  tempBtn.addTo(map);
  
  let tempActive = false;
  document.getElementById('tempToggle').addEventListener('click', function() {{
    tempActive = !tempActive;
    if (tempActive) {{
      tempLayer.addTo(map);
      this.style.borderColor = '#58a6ff';
    }} else {{
      map.removeLayer(tempLayer);
      this.style.borderColor = '#30363d';
    }}
  }});
  
  // Marker
  L.marker([{current['lat']}, {current['lon']}]).addTo(map)
    .bindPopup("{current['city']}").openPopup();
  
  // Fix for mobile
  setTimeout(() => map.invalidateSize(), 100);
  window.addEventListener('resize', () => map.invalidateSize());

  // ── Chart defaults ───────────────────────────────────────────────────────
  Chart.defaults.color = '#8b949e';
  Chart.defaults.font.family = 'DM Sans';

  const labels   = {weekly_labels};
  const temps    = {weekly_temps};
  const humidity = {weekly_humidity};

  // ── Humidity line chart ──────────────────────────────────────────────────
  new Chart(document.getElementById('humidityChart'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{
        label: 'Humidity %',
        data: humidity,
        borderColor: '#58a6ff',
        backgroundColor: 'rgba(88,166,255,0.08)',
        borderWidth: 2.5,
        pointRadius: 4,
        pointBackgroundColor: '#58a6ff',
        tension: 0.4,
        fill: true,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{
          min: 0, max: 100,
          grid: {{ color: 'rgba(48,54,61,0.8)' }},
          ticks: {{ callback: v => v + '%' }}
        }},
        x: {{ grid: {{ color: 'rgba(48,54,61,0.8)' }} }}
      }}
    }}
  }});

  // ── Temperature area chart ───────────────────────────────────────────────
  new Chart(document.getElementById('tempChart'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [{{
        label: 'Temp {temp_symbol}',
        data: temps,
        borderColor: '#c0557a',
        backgroundColor: 'rgba(192,85,122,0.25)',
        borderWidth: 2.5,
        pointRadius: 4,
        pointBackgroundColor: '#c0557a',
        tension: 0.4,
        fill: true,
      }}]
    }},
    options: {{
      responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{
        y: {{
          grid: {{ color: 'rgba(48,54,61,0.8)' }},
          ticks: {{ callback: v => v + '{temp_symbol}' }}
        }},
        x: {{ grid: {{ color: 'rgba(48,54,61,0.8)' }} }}
      }}
    }}
  }});
</script>
</body>
</html>
"""

# ── Render inside Streamlit ───────────────────────────────────────────────────
components.html(html, height=1200, scrolling=True)