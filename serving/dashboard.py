"""
Weather & Holiday Insights Dashboard  (Dark-Mode Edition)
==========================================================
Insight-focused Streamlit dashboard comparing weather patterns
on holidays vs regular days for London (GB) and Manila (PH).
"""
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import cfg, DB_FILE

# ── Plotly dark template ────────────────────────────────────────────────────────
PLOT_BG     = "rgba(0,0,0,0)"
PAPER_BG    = "rgba(0,0,0,0)"
GRID_COLOR  = "rgba(255,255,255,0.08)"
TEXT_COLOR   = "#FAFAFA"
_colors     = cfg["streamlit"]["colors"]
HOLIDAY_CLR = _colors["holiday"]
REGULAR_CLR = _colors["regular"]
ACCENT      = _colors["accent"]
PALETTE     = [HOLIDAY_CLR, REGULAR_CLR]

def dark_layout(fig, **kwargs):
    """Apply consistent dark styling to any Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor=PLOT_BG,
        paper_bgcolor=PAPER_BG,
        font=dict(color=TEXT_COLOR, size=13),
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        **kwargs,
    )
    fig.update_xaxes(gridcolor=GRID_COLOR, zeroline=False)
    fig.update_yaxes(gridcolor=GRID_COLOR, zeroline=False)
    return fig

# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Weather × Holidays", page_icon="🌤️", layout="wide")

# Inject minimal CSS for dark-friendly metrics, cards, and hiding default Streamlit branding/logo
st.markdown("""
<style>
    /* Hide Streamlit default header, logo, menu and status widget */
    #MainMenu {visibility: hidden; display: none;}
    header {visibility: hidden; display: none;}
    footer {visibility: hidden; display: none;}
    [data-testid="stHeader"] {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    [data-testid="stLogo"] {display: none;}
    .viewerBadge_container__1QSob {display: none;}
    
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    div[data-testid="stMetricValue"] {font-size: 1.8rem; font-weight: 700;}
    div[data-testid="stMetricDelta"] {font-size: 0.9rem;}
    .insight-card {
        background: rgba(108,99,255,0.08);
        border-left: 4px solid #6C63FF;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 0.6rem 0 1rem 0;
        color: #FAFAFA;
    }
    .insight-card.warm {
        background: rgba(255,107,107,0.08);
        border-left-color: #FF6B6B;
    }
    .insight-card.cool {
        background: rgba(78,205,196,0.08);
        border-left-color: #4ECDC4;
    }
    .section-divider {
        border: none;
        border-top: 1px solid rgba(255,255,255,0.1);
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ── DB helper ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_conn():
    return duckdb.connect(DB_FILE, read_only=True)

def q(sql: str, params: list | None = None) -> pd.DataFrame:
    """Execute SQL with optional parameterized values to prevent SQL injection."""
    return get_conn().execute(sql, params or []).df()

def qp(sql: str, city: str) -> pd.DataFrame:
    """Parameterized city-scoped query helper."""
    return q(sql, [city])

# ── Sidebar ─────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🌤️ Weather × Holidays")
cities = q("SELECT DISTINCT city_name AS city FROM main_gold.dim_location ORDER BY city_name")["city"].tolist()
selected_city = st.sidebar.selectbox("Select City", cities)
city_cc = qp(
    "SELECT DISTINCT country_code FROM main_gold.dim_location WHERE city_name = ?",
    selected_city
)["country_code"].iloc[0]
min_date = qp(
    "SELECT MIN(date_key)::DATE FROM main_gold.fact_daily_weather WHERE city = ?",
    selected_city
).iloc[0, 0]
max_date = qp(
    "SELECT MAX(date_key)::DATE FROM main_gold.fact_daily_weather WHERE city = ?",
    selected_city
).iloc[0, 0]
st.sidebar.markdown(f"📅 **{min_date}** → **{max_date}**")
st.sidebar.markdown(f"🏳️ Country: `{city_cc}`")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏛️ Medallion Architecture")
st.sidebar.markdown("""
- **🥉 Bronze**: `bronze.weather`, `bronze.holidays`
- **🥈 Silver**: `main_silver.silver_weather_holidays`
- **🥇 Gold**: `main_gold.fact_daily_weather`, `main_gold.mart_*`
""")
st.sidebar.markdown("---")
st.sidebar.caption("Created by **Louise Guerrero**\nStack: Python · DuckDB · dbt · Streamlit · Grafana")

# ── Build combined analytical DataFrame from Medallion Gold Layer ─────────────
df = qp("""
    SELECT
        f.date_key,
        f.city,
        f.country_code,
        f.temperature_2m_max,
        f.temperature_2m_min,
        f.precipitation_sum,
        f.year,
        f.month,
        f.is_weekend,
        f.holiday_name,
        f.is_holiday
    FROM main_gold.fact_daily_weather f
    WHERE f.city = ?
    ORDER BY f.date_key
""", selected_city)

total_days   = len(df)
holiday_days = int(df["is_holiday"].sum())
regular_days = total_days - holiday_days

hol = df[df["is_holiday"]]
reg = df[~df["is_holiday"]]

avg_max_hol = hol["temperature_2m_max"].mean()
avg_max_reg = reg["temperature_2m_max"].mean()
avg_precip_hol = hol["precipitation_sum"].mean()
avg_precip_reg = reg["precipitation_sum"].mean()
temp_diff = avg_max_hol - avg_max_reg
precip_diff = avg_precip_hol - avg_precip_reg

# ════════════════════════════════════════════════════════════════════════════════
# HEADER
# ════════════════════════════════════════════════════════════════════════════════
st.markdown(f"# 📊 {selected_city} — Weather × Holiday Insights")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Days Analysed", f"{total_days:,}")
c2.metric("Public Holidays", holiday_days)
c3.metric("Avg Max Temp (Holiday)", f"{avg_max_hol:.1f}°C", delta=f"{temp_diff:+.1f}°C vs regular", delta_color="inverse")
c4.metric("Avg Precip (Holiday)", f"{avg_precip_hol:.1f} mm", delta=f"{precip_diff:+.1f} mm vs regular", delta_color="inverse")

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 1 — Key Finding
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## 🔑 Key Finding: Holiday vs Regular Day Weather")

warmer_or_cooler = "warmer" if temp_diff > 0 else "cooler"
wetter_or_drier  = "wetter" if precip_diff > 0 else "drier"

st.markdown(f"""
<div class="insight-card">
    <strong>Holidays in {selected_city} are {abs(temp_diff):.1f}°C {warmer_or_cooler}</strong>
    and <strong>{abs(precip_diff):.1f} mm {wetter_or_drier}</strong> on average
    compared to regular days. This is based on {holiday_days} holidays
    vs {regular_days:,} regular days over {(total_days/365.25):.1f} years.
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    fig = go.Figure()
    fig.add_bar(name="Holiday",     x=["Max Temp", "Min Temp"], y=[hol["temperature_2m_max"].mean(), hol["temperature_2m_min"].mean()], marker_color=HOLIDAY_CLR)
    fig.add_bar(name="Regular Day", x=["Max Temp", "Min Temp"], y=[reg["temperature_2m_max"].mean(), reg["temperature_2m_min"].mean()], marker_color=REGULAR_CLR)
    dark_layout(fig, title="Average Temperature (°C)", barmode="group", yaxis_title="°C")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    pct_rainy_hol = (hol["precipitation_sum"] > 0).mean() * 100
    pct_rainy_reg = (reg["precipitation_sum"] > 0).mean() * 100
    pct_heavy_hol = (hol["precipitation_sum"] > 5).mean() * 100
    pct_heavy_reg = (reg["precipitation_sum"] > 5).mean() * 100

    fig = go.Figure()
    fig.add_bar(name="Holiday",     x=["Any Rain (%)", "Heavy >5mm (%)"], y=[pct_rainy_hol, pct_heavy_hol], marker_color=HOLIDAY_CLR)
    fig.add_bar(name="Regular Day", x=["Any Rain (%)", "Heavy >5mm (%)"], y=[pct_rainy_reg, pct_heavy_reg], marker_color=REGULAR_CLR)
    dark_layout(fig, title="Probability of Rain", barmode="group", yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)

rain_insight = "about the same" if abs(pct_rainy_hol - pct_rainy_reg) < 3 else ("rainier" if pct_rainy_hol > pct_rainy_reg else "less rainy")
st.markdown(f"""
<div class="insight-card cool">
    <strong>☂️ Rain check:</strong> {pct_rainy_hol:.0f}% of holidays see rain vs {pct_rainy_reg:.0f}% of regular days
    — holidays are <strong>{rain_insight}</strong>.
    Pack an umbrella regardless!
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 2 — Per-Holiday Ranking
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## ☀️ Which Holidays Have the Best (and Worst) Weather?")

hol_stats = (
    hol.groupby("holiday_name")
    .agg(
        occurrences=("date_key", "count"),
        avg_max=("temperature_2m_max", "mean"),
        avg_min=("temperature_2m_min", "mean"),
        avg_precip=("precipitation_sum", "mean"),
        hottest=("temperature_2m_max", "max"),
        coldest=("temperature_2m_min", "min"),
    )
    .reset_index()
    .sort_values("avg_max", ascending=True)
)

best_holiday  = hol_stats.iloc[-1]
worst_holiday = hol_stats.iloc[0]

st.markdown(f"""
<div class="insight-card warm">
    🏆 <strong>Best weather holiday:</strong> {best_holiday['holiday_name']}
    — avg {best_holiday['avg_max']:.1f}°C, record high {best_holiday['hottest']:.1f}°C<br>
    🥶 <strong>Coldest holiday:</strong> {worst_holiday['holiday_name']}
    — avg {worst_holiday['avg_max']:.1f}°C, record low {worst_holiday['coldest']:.1f}°C
</div>
""", unsafe_allow_html=True)

fig = px.bar(
    hol_stats, y="holiday_name", x="avg_max",
    color="avg_precip",
    color_continuous_scale=["#4ECDC4", "#2C3E50", "#FF6B6B"],
    orientation="h",
    labels={"avg_max": "Avg Max Temp (°C)", "holiday_name": "", "avg_precip": "Avg Rain (mm)"},
)
dark_layout(fig, title="Holidays Ranked by Temperature (colour = avg rainfall)", height=max(420, len(hol_stats) * 30), coloraxis_colorbar_title="Rain (mm)")
st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 3 — Monthly seasonal lens
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## 📅 Monthly Lens: Does Holiday Timing Skew the Results?")

month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

monthly = (
    df.groupby(["month", "is_holiday"])
    .agg(avg_max=("temperature_2m_max", "mean"), avg_precip=("precipitation_sum", "mean"))
    .reset_index()
)
monthly["type"] = monthly["is_holiday"].map({True: "Holiday", False: "Regular"})
monthly["month_name"] = monthly["month"].map(month_map)
monthly = monthly.sort_values("month")

c1, c2 = st.columns(2)
with c1:
    fig = px.line(monthly, x="month_name", y="avg_max", color="type",
                  color_discrete_map={"Holiday": HOLIDAY_CLR, "Regular": REGULAR_CLR},
                  markers=True, labels={"avg_max":"Avg Max Temp (°C)","month_name":"","type":""})
    dark_layout(fig, title="Monthly Avg Max Temp")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.line(monthly, x="month_name", y="avg_precip", color="type",
                  color_discrete_map={"Holiday": HOLIDAY_CLR, "Regular": REGULAR_CLR},
                  markers=True, labels={"avg_precip":"Avg Precip (mm)","month_name":"","type":""})
    dark_layout(fig, title="Monthly Avg Precipitation")
    st.plotly_chart(fig, use_container_width=True)

hol_months = sorted(hol["month"].unique())
hol_month_names = ", ".join([month_map[int(m)] for m in hol_months])
st.markdown(f"""
<div class="insight-card">
    📌 <strong>Holidays concentrate in:</strong> {hol_month_names}.<br>
    The monthly view lets you control for seasonality — compare red vs teal
    within the <em>same</em> month to see if the holiday itself brings different weather.
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 4 — Year-over-year trend
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## 📈 Climate Trend: Year-over-Year")

yearly = (
    df.groupby("year")
    .agg(avg_max=("temperature_2m_max","mean"), avg_min=("temperature_2m_min","mean"),
         total_precip=("precipitation_sum","sum"), days=("date_key","count"))
    .reset_index()
)

hottest_year = yearly.loc[yearly["avg_max"].idxmax()]
wettest_year = yearly.loc[yearly["total_precip"].idxmax()]

c1, c2 = st.columns(2)
with c1:
    fig = go.Figure()
    fig.add_scatter(x=yearly["year"], y=yearly["avg_max"], name="Max", mode="lines+markers", line=dict(color=HOLIDAY_CLR, width=3))
    fig.add_scatter(x=yearly["year"], y=yearly["avg_min"], name="Min", mode="lines+markers", line=dict(color=REGULAR_CLR, width=3))
    dark_layout(fig, title="Average Temperature by Year", yaxis_title="°C")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    fig = px.bar(yearly, x="year", y="total_precip", text_auto=".0f",
                 labels={"total_precip":"Total Precip (mm)","year":""},
                 color_discrete_sequence=[ACCENT])
    dark_layout(fig, title="Annual Precipitation")
    st.plotly_chart(fig, use_container_width=True)

st.markdown(f"""
<div class="insight-card warm">
    🔥 <strong>Hottest year:</strong> {int(hottest_year['year'])} (avg max {hottest_year['avg_max']:.1f}°C)
    &nbsp;|&nbsp;
    🌊 <strong>Wettest year:</strong> {int(wettest_year['year'])} ({wettest_year['total_precip']:.0f} mm total rainfall in {int(wettest_year['days'])} days)
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 5 — Extreme records
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## 🏅 Holiday Weather Records")

c1, c2 = st.columns(2)

with c1:
    st.markdown("### 🌧️ Wettest Holidays")
    wettest = hol.nlargest(5, "precipitation_sum")[["date_key","holiday_name","precipitation_sum","temperature_2m_max"]].copy()
    wettest.columns = ["Date","Holiday","Precip (mm)","Max Temp °C"]
    wettest["Precip (mm)"] = wettest["Precip (mm)"].round(1)
    wettest["Max Temp °C"]  = wettest["Max Temp °C"].round(1)
    st.dataframe(wettest, use_container_width=True, hide_index=True)

with c2:
    st.markdown("### ☀️ Hottest & Driest Holidays")
    driest = hol[hol["precipitation_sum"] == 0].nlargest(5, "temperature_2m_max")[["date_key","holiday_name","precipitation_sum","temperature_2m_max"]].copy()
    driest.columns = ["Date","Holiday","Precip (mm)","Max Temp °C"]
    driest["Max Temp °C"] = driest["Max Temp °C"].round(1)
    if len(driest) == 0:
        st.info("No completely dry holidays recorded.")
    else:
        st.dataframe(driest, use_container_width=True, hide_index=True)

if len(wettest) > 0:
    top_wet = wettest.iloc[0]
    st.markdown(f"""
    <div class="insight-card cool">
        💧 The wettest holiday on record was <strong>{top_wet['Holiday']}</strong>
        on {top_wet['Date']} with <strong>{top_wet['Precip (mm)']} mm</strong> of rain.
    </div>
    """, unsafe_allow_html=True)

if len(driest) > 0:
    top_dry = driest.iloc[0]
    st.markdown(f"""
    <div class="insight-card warm">
        ☀️ The hottest dry holiday was <strong>{top_dry['Holiday']}</strong>
        on {top_dry['Date']} at <strong>{top_dry['Max Temp °C']}°C</strong> with zero rainfall.
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# INSIGHT 6 — Full timeline scatter
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.markdown("## 🗓️ Full Timeline — Every Day at a Glance")

st.markdown("""
<div class="insight-card">
    Each dot is one day. <span style="color:#FF6B6B;font-weight:700;">● Red = Public Holiday</span>,
    <span style="color:#4ECDC4;font-weight:700;">● Teal = Regular Day</span>.
    Hover for details.
</div>
""", unsafe_allow_html=True)

fig = px.scatter(
    df, x="date_key", y="temperature_2m_max",
    color="is_holiday",
    color_discrete_map={True: HOLIDAY_CLR, False: REGULAR_CLR},
    labels={"temperature_2m_max":"Max Temp (°C)","date_key":"","is_holiday":"Holiday?"},
    hover_data={"holiday_name": True, "precipitation_sum": True},
    opacity=0.6,
)
fig.update_traces(marker_size=4)
dark_layout(fig, title="Daily Max Temperature", height=420, showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# ── Footer ──────────────────────────────────────────────────────────────────────
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.caption("Created by **Louise Guerrero**  |  Data: Open-Meteo Historical Weather API · Nager.Date Public Holiday API  |  Stack: Python · DuckDB · dbt · Streamlit · Plotly")
