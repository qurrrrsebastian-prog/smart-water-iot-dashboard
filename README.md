# Project #18 — Smart Water IoT Dashboard

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/IoT-00A4E4?style=flat&logo=raspberrypi&logoColor=white" />
  <img src="https://img.shields.io/badge/Dashboard-7B2CBF?style=flat" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" />
</p>

> Dashboard monitoring kualitas air Jakarta real-time dengan data sensor IoT simulasi. Proyek tim Smart Water Universitas Budi Luhur.

---

## Demo Langsung

[![Deploy to Streamlit Cloud](https://img.shields.io/badge/Deploy-Streamlit%20Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://share.streamlit.io/deploy?repository=qurrrrsebastian-prog/smart-water-iot-dashboard)

**Tech Stack:** `Streamlit` · `Pandas` · `Plotly` · `IoT Simulation`

---

## Fitur

| Fitur | Status |
|-------|--------|
| Real-time sensor data simulation | ✅ |
| pH, TDS, turbidity monitoring | ✅ |
| Interactive charts (Plotly) | ✅ |
| Historical data trend | ✅ |
| Alert system (threshold) | ✅ |
| Tema gelap AVA purple | ✅ |

---

## Cara Menjalankan

```bash
git clone https://github.com/qurrrrsebastian-prog/smart-water-iot-dashboard.git
cd smart-water-iot-dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Deploy ke Streamlit Cloud (GRATIS)

1. [share.streamlit.io](https://share.streamlit.io) → Login GitHub
2. **New app** → Pilih repo ini
3. **Deploy** (tidak perlu API key!)

---

## Struktur Project

```
smart-water-iot-dashboard/
├── app.py              # Main Streamlit app (13KB)
├── requirements.txt    # Dependencies
├── data/               # Sensor data samples
├── .streamlit/
│   └── config.toml    # AVA purple branding
├── .gitignore
└── LICENSE            # MIT License
```

---

**Dibuat oleh:** [Avatar Putra Sigit](https://github.com/qurrrrsebastian-prog) · Tim Smart Water — Universitas Budi Luhur
