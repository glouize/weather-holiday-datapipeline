# 📊 Data Insights Report: London Weather × UK Public Holidays (2021–2026)

**Dataset**: 1,827 days | 69 holiday days | 1,758 regular days | Aug 2021 – Aug 2026

---

## 🔑 Key Finding: Holidays Are Slightly Cooler & Drier Than Regular Days

| Metric | Holidays (69 days) | Regular Days (1,758 days) | Difference |
|---|---|---|---|
| Avg Max Temp (°C) | **15.34** | 15.97 | −0.63°C |
| Avg Min Temp (°C) | **8.05** | 8.47 | −0.42°C |
| Avg Precipitation (mm) | **1.56** | 1.99 | −0.43 mm |

> [!NOTE]
> UK public holidays tend to cluster around winter/spring months (Christmas, New Year, Easter, bank holidays), which naturally skews the holiday average cooler. However, even accounting for seasonality (see Insight 4), holidays tend to receive **less rainfall** than their monthly peers.

---

## ☀️ Hottest & Coldest Holidays

| Holiday | Avg Max Temp | Hottest Recorded | Coldest Min Recorded |
|---|---|---|---|
| Battle of the Boyne (Jul) | **24.1°C** | 30.2°C | 13.1°C |
| Summer Bank Holiday (Aug) | **23.2°C** | 31.3°C | 10.5°C |
| Spring Bank Holiday (May) | **20.8°C** | 🔥 **33.8°C** (May 2026!) | 7.2°C |
| 2 January | **8.2°C** | 12.9°C | −0.4°C |
| New Year's Day | **9.3°C** | 11.8°C | 🥶 −0.8°C |
| St. Andrew's Day (Nov) | **9.7°C** | 11.8°C | 🥶 **−2.8°C** |

> [!IMPORTANT]
> The **Spring Bank Holiday of 2026** recorded the single hottest holiday temperature in the dataset at **33.8°C** — a remarkable outlier that was also completely dry (0mm precipitation).

---

## 🌧️ Rain Probability: Holidays vs Regular Days

| Day Type | Total Days | Rainy Days | % Rainy | Heavy Rain (>5mm) | % Heavy Rain |
|---|---|---|---|---|---|
| Holiday | 69 | 42 | **60.9%** | 8 | 11.6% |
| Regular Day | 1,758 | 1,042 | **59.3%** | 219 | 12.5% |

> [!TIP]
> Despite the slightly lower average rainfall on holidays, the **probability of experiencing at least some rain** is essentially the same (~60%). London's reputation holds — pack an umbrella regardless!

---

## 🌊 Wettest & Driest Holiday Records

````carousel
### 🌧️ Top 5 Wettest Holidays
| Date | Holiday | Precipitation | Max Temp |
|---|---|---|---|
| 2025-01-01 | New Year's Day | **10.5 mm** | 11.8°C |
| 2024-05-06 | Early May Bank Holiday | **9.7 mm** | 15.2°C |
| 2024-01-02 | 2 January | **9.6 mm** | 12.9°C |
| 2023-04-10 | Easter Monday | **9.1 mm** | 14.3°C |
| 2024-01-01 | New Year's Day | **8.3 mm** | 10.1°C |

> New Year's period dominates the wettest holiday list — 3 of the top 5 wettest holidays fall within Jan 1–2.
<!-- slide -->
### ☀️ Top 5 Driest & Warmest Holidays
| Date | Holiday | Precipitation | Max Temp |
|---|---|---|---|
| 2026-05-25 | Spring Bank Holiday | **0.0 mm** | 🔥 33.8°C |
| 2022-07-12 | Battle of the Boyne | **0.0 mm** | 30.2°C |
| 2026-07-13 | Battle of the Boyne | **0.0 mm** | 26.6°C |
| 2025-08-25 | Summer Bank Holiday | **0.0 mm** | 26.0°C |
| 2022-08-01 | Summer Bank Holiday | **0.0 mm** | 25.3°C |

> The "Battle of the Boyne" and "Summer Bank Holiday" are consistently the most pleasant UK holidays weather-wise.
````

---

## 📈 Year-over-Year Climate Trend

| Year | Avg Max Temp | Avg Min Temp | Total Annual Precip (mm) |
|---|---|---|---|
| 2021 (partial) | 14.93°C | 8.41°C | 274.7 |
| 2022 | 16.08°C | 7.80°C | 662.8 |
| 2023 | 15.55°C | 7.89°C | 781.0 |
| 2024 | 15.31°C | 8.29°C | **893.6** |
| 2025 | 16.03°C | 9.00°C | 613.4 |
| 2026 (partial) | **17.92°C** | **9.86°C** | 372.4 |

> [!WARNING]
> **2026 is tracking significantly warmer** than all previous years — both max (+1.9°C above 5-year avg) and min temps (+1.4°C) are elevated. 2024 was the wettest full year at nearly 894mm of total rainfall.

---

## 🧊 Extreme Weather & Holidays

Of the **top 5% hottest days** (92 days) in the dataset:
- **3 fell on holidays** (4.3% of all 69 holiday days)
- 87 fell on regular days (4.9% of all 1,758 regular days)

Of the **bottom 5% coldest days** (93 days):
- **5 fell on holidays** (7.2% of all holiday days)
- 88 fell on regular days (5.0% of regular days)

> [!NOTE]
> Holidays are **overrepresented in extreme cold** (7.2% vs 5.0%) — likely driven by Christmas, New Year, and early January holidays falling during the coldest weeks of the year.

---

## 📌 Summary of Actionable Insights

1. **Holiday weather is marginally cooler and drier** than average, but the difference is small and largely driven by seasonal clustering of UK holidays in colder months.
2. **Rain probability is essentially the same** (~60%) whether it's a holiday or not — classic London.
3. **New Year's period is the wettest holiday window**; **Summer/Spring Bank Holidays are the driest and warmest**.
4. **2026 is an unusually warm year** — worth monitoring for climate trend analysis.
5. **Holidays are disproportionately associated with extreme cold**, making cold-weather preparedness relevant for holiday event planning.
