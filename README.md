# 💧 Smart Water IoT Dashboard — Jakarta

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?logo=plotly&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white)

Real-time water-quality monitoring dashboard for Jakarta's rivers and canals. Simulates **5 IoT sensor nodes** streaming pH, turbidity, temperature, and flow-rate data — **no hardware and no API key required**.

Built for the **Smart Water Competition** as a proof-of-concept for low-cost urban water monitoring.

---

## ✨ Features

- **5 sensor nodes** across Jakarta (Ciliwung, Cisadane, Citarum, Sunter, Pesanggrahan) with real coordinates.
- **Real-time simulation** — click **Refresh** to push a fresh reading per node. No auto-refresh loop, no infinite reruns.
- **Anomaly detection** — automatic Normal / Warning / Critical classification on pH, turbidity, and temperature thresholds.
- **Geo map** — color-coded node markers (green / yellow / red) on a Jakarta-centered map.
- **Historical trends** — 7-day line charts for all four metrics.
- **Live alerts panel** + color-coded 24-hour data table.

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| UI | Streamlit (wide layout) |
| Charts & maps | Plotly Express / Graph Objects |
| Data | Pandas + NumPy (seeded simulation) |
| Language | Python 3.14 |

---

## 🚀 Run It

**No API key needed.**

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate the simulated dataset (840 rows)
python data/generate_dummy_iot.py

# 3. Launch the dashboard
streamlit run app.py
```

---

## 🎬 Demo Example

After generating data and launching:

- The **metrics row** shows the latest network averages with hour-over-hour deltas.
- The **map** flags any node breaching a threshold in red.
- Clicking **🔄 Refresh Data** injects a new hourly reading per node — occasionally tripping a Critical alert (turbidity > 60 NTU or temp > 35 °C) to demonstrate the alert system.

---

## 📊 Key Insights

1. **840 rows** generated per run — 5 nodes × 168 hourly readings (7 days), fully reproducible with `seed=42`.
2. **5–10 anomalies** injected per dataset, exercising both the Warning and Critical alert paths.
3. **3-tier alert logic** evaluated on every reading: Critical (pH <6 / >8.5, turbidity >50 NTU, temp >35 °C) down to Normal — surfaced live with zero manual inspection.

> ⚠️ **Note:** Refresh is **manual only** by design — there is no `st.rerun()` loop, which keeps the app stable and avoids runaway reruns during a live demo.

---

## 👤 Author

**Avatar Putra Sigit**
- GitHub: [qurrrrsebastian-prog](https://github.com/qurrrrsebastian-prog)
- LinkedIn: [avatarputrasigit](https://www.linkedin.com/in/avatarputrasigit)
