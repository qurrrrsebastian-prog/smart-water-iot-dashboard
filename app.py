"""Smart Water IoT Dashboard — Jakarta (v2.0 production upgrade).

Real-time (simulated) water-quality monitoring for 5 Jakarta sensor nodes.
v2.0 adds SQLite persistence, configurable thresholds, an alert-history log,
auto-refresh, historical analytics with anomaly detection, per-node drill-down,
and date-range export.

Author: Avatar Putra Sigit | GitHub: qurrrrsebastian-prog
"""

import os
import random
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import database as db
from security import sanitize_input  # noqa: F401  (available for future inputs)
from ui_components import render_header, render_footer, PRIMARY

# --------------------------------------------------------------------------- #
# Page configuration
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Smart Water IoT Dashboard",
    layout="wide",
    page_icon="💧",
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "iot_sensor_data.csv")
ALL_NODES = ["Ciliwung", "Cisadane", "Citarum", "Sunter", "Pesanggrahan"]
METRIC_LABELS = {
    "pH": "pH",
    "turbidity_NTU": "Turbidity (NTU)",
    "temperature_C": "Temperature (°C)",
    "flow_rate_Ls": "Flow Rate (L/s)",
}


# --------------------------------------------------------------------------- #
# Bootstrapping — initialise DB and seed from CSV on first run
# --------------------------------------------------------------------------- #
@st.cache_resource
def bootstrap() -> bool:
    """Create tables and seed sensor data once per process."""
    db.init_db()
    if db.reading_count() == 0 and os.path.exists(DATA_PATH):
        seed = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        inserted = db.seed_from_dataframe(seed)
        db.add_log("seed_data", f"Seeded {inserted} readings from CSV", "system")
    return True


bootstrap()


# --------------------------------------------------------------------------- #
# Alert evaluation (threshold-driven)
# --------------------------------------------------------------------------- #
def get_alert_status(row: pd.Series, thresholds: dict) -> Tuple[str, str, list]:
    """Determine alert status for a reading using configurable thresholds.

    Returns (status, color, breaches) where breaches lists human-readable
    descriptions of any metric out of range.
    """
    status = "Normal"
    breaches = []
    for metric in ("pH", "turbidity_NTU", "temperature_C", "flow_rate_Ls"):
        t = thresholds.get(metric)
        if not t:
            continue
        try:
            val = float(row[metric])
        except Exception:  # noqa: BLE001
            continue
        if val < t["critical_low"] or val > t["critical_high"]:
            status = "Critical"
            breaches.append(f"{METRIC_LABELS[metric]}={val:g} (critical)")
        elif val < t["warning_low"] or val > t["warning_high"]:
            if status != "Critical":
                status = "Warning"
            breaches.append(f"{METRIC_LABELS[metric]}={val:g} (warning)")
    color = {"Critical": "red", "Warning": "orange", "Normal": "green"}[status]
    return status, color, breaches


def create_gauge(value, title, min_val, max_val, t_warning, t_critical) -> go.Figure:
    """Build a gauge chart with green/yellow/red zones."""
    try:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": title},
                gauge={
                    "axis": {"range": [min_val, max_val]},
                    "bar": {"color": PRIMARY},
                    "steps": [
                        {"range": [min_val, t_warning], "color": "#c8e6c9"},
                        {"range": [t_warning, t_critical], "color": "#fff9c4"},
                        {"range": [t_critical, max_val], "color": "#ffcdd2"},
                    ],
                },
            )
        )
        fig.update_layout(height=240, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    except Exception:  # noqa: BLE001
        return go.Figure()


def simulate_and_persist(thresholds: dict) -> int:
    """Generate one fresh reading per node, persist it, and log any alerts.

    Returns the number of new readings inserted.
    """
    df = db.load_readings()
    if df.empty:
        return 0
    now = pd.Timestamp.now().floor("h").isoformat()
    inserted = 0
    for node in ALL_NODES:
        ref = df[df["node_name"] == node]
        if ref.empty:
            continue
        coords = ref.iloc[-1]
        reading = {
            "pH": round(float(np.clip(random.gauss(7.2, 0.5), 5.5, 8.8)), 2),
            "turbidity_NTU": round(float(np.clip(random.gauss(35, 18), 10, 95)), 1),
            "temperature_C": round(float(np.clip(random.gauss(31, 2.2), 28, 38)), 1),
            "flow_rate_Ls": round(float(np.clip(random.gauss(120, 40), 50, 200)), 1),
        }
        status, _, breaches = get_alert_status(pd.Series(reading), thresholds)
        db.insert_reading(
            now, node, float(coords["latitude"]), float(coords["longitude"]),
            reading["pH"], reading["turbidity_NTU"], reading["temperature_C"],
            reading["flow_rate_Ls"], status,
        )
        inserted += 1
        if status in ("Warning", "Critical"):
            db.log_alert(node, "; ".join(breaches) or "threshold breach", status,
                         "; ".join(breaches))
    db.add_log("refresh", f"Inserted {inserted} readings", "operator")
    return inserted


def _avg(frame: pd.DataFrame, col: str) -> float:
    """Mean of a column, or 0.0 if empty/error."""
    try:
        return float(frame[col].mean())
    except Exception:  # noqa: BLE001
        return 0.0


# --------------------------------------------------------------------------- #
# Header + control strip (full-width, no sidebar)
# --------------------------------------------------------------------------- #
render_header(
    "💧 Smart Water IoT Dashboard — Jakarta",
    "Real-time water-quality monitoring across 5 sensor nodes · v2.0 Azure IoT",
)

thresholds = db.get_thresholds()

c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
with c1:
    node_selector = st.multiselect("Sensor Nodes", ALL_NODES, default=ALL_NODES)
with c2:
    refresh_choice = st.selectbox(
        "Auto-refresh", ["Manual", "5s", "10s", "30s", "60s"], index=0
    )
with c3:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh Now", type="primary", use_container_width=True):
        n = simulate_and_persist(thresholds)
        st.toast(f"Inserted {n} new readings", icon="✅")
        st.rerun()
with c4:
    st.metric("Readings", f"{db.reading_count():,}")

# Auto-refresh via meta-refresh (version-independent, no extra deps).
_interval = {"5s": 5, "10s": 10, "30s": 30, "60s": 60}.get(refresh_choice)
if _interval:
    st.markdown(
        f'<meta http-equiv="refresh" content="{_interval}">', unsafe_allow_html=True
    )
    st.caption(f"⏱️ Auto-refreshing every {_interval}s — open Settings to pause.")

# Load + filter data.
df_all = db.load_readings()
if df_all.empty:
    st.warning("No data available. Run: python data/generate_dummy_iot.py")
    st.stop()

df = df_all[df_all["node_name"].isin(node_selector)] if node_selector else df_all
if df.empty:
    st.warning("No nodes selected. Choose at least one sensor node.")
    st.stop()
df = df.sort_values("timestamp")

# --------------------------------------------------------------------------- #
# Tabs
# --------------------------------------------------------------------------- #
tab_live, tab_analytics, tab_alerts, tab_node, tab_settings, tab_export = st.tabs(
    ["📊 Live Dashboard", "📈 Analytics", "🚨 Alerts", "🔍 Node Detail",
     "⚙️ Settings", "💾 Data & Export"]
)

# --------------------------------------------------------------------------- #
# TAB 1 — Live dashboard (metrics + map + trends + table)
# --------------------------------------------------------------------------- #
with tab_live:
    latest_ts = df["timestamp"].max()
    latest = df[df["timestamp"] == latest_ts]
    times = sorted(df["timestamp"].unique())
    prev_ts = times[-2] if len(times) > 1 else latest_ts
    previous = df[df["timestamp"] == prev_ts]

    m1, m2, m3, m4 = st.columns(4)
    ph_now, ph_prev = _avg(latest, "pH"), _avg(previous, "pH")
    turb_now, turb_prev = _avg(latest, "turbidity_NTU"), _avg(previous, "turbidity_NTU")
    temp_now, temp_prev = _avg(latest, "temperature_C"), _avg(previous, "temperature_C")
    flow_now, flow_prev = _avg(latest, "flow_rate_Ls"), _avg(previous, "flow_rate_Ls")
    m1.metric("pH (avg)", f"{ph_now:.2f}", delta=f"{ph_now - ph_prev:+.2f}")
    m2.metric("Turbidity (NTU)", f"{turb_now:.1f}",
              delta=f"{turb_now - turb_prev:+.1f}", delta_color="inverse")
    m3.metric("Temperature (°C)", f"{temp_now:.1f}",
              delta=f"{temp_now - temp_prev:+.1f}", delta_color="inverse")
    m4.metric("Flow Rate (L/s)", f"{flow_now:.1f}", delta=f"{flow_now - flow_prev:+.1f}")

    st.divider()

    latest_per_node = (
        df.sort_values("timestamp").groupby("node_name", as_index=False).last()
    )
    evals = latest_per_node.apply(lambda r: get_alert_status(r, thresholds), axis=1)
    latest_per_node = latest_per_node.assign(
        status=[e[0] for e in evals], color=[e[1] for e in evals]
    )

    map_col, alert_col = st.columns([3, 2])
    with map_col:
        st.subheader("🗺️ Sensor Network")
        try:
            fig_map = px.scatter_geo(
                latest_per_node, lat="latitude", lon="longitude", color="status",
                hover_name="node_name",
                hover_data={"pH": True, "turbidity_NTU": True, "temperature_C": True,
                            "latitude": False, "longitude": False},
                color_discrete_map={"Normal": "green", "Warning": "orange",
                                    "Critical": "red"},
                size_max=18,
            )
            fig_map.update_traces(marker=dict(size=14))
            fig_map.update_geos(center=dict(lat=-6.21, lon=106.83),
                                projection_scale=180, showland=True,
                                landcolor="#1C1F26", showcountries=True)
            fig_map.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_map, use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Map render error: {exc}")

    with alert_col:
        st.subheader("🚨 Live Alerts")
        any_alert = False
        for _, nr in latest_per_node.iterrows():
            detail = (f"pH {nr['pH']:.2f} | Turb {nr['turbidity_NTU']:.1f} NTU | "
                      f"Temp {nr['temperature_C']:.1f}°C")
            if nr["status"] == "Critical":
                st.error(f"**{nr['node_name']}** — CRITICAL\n\n{detail}")
                any_alert = True
            elif nr["status"] == "Warning":
                st.warning(f"**{nr['node_name']}** — Warning\n\n{detail}")
                any_alert = True
        if not any_alert:
            st.success("All nodes within normal parameters. ✅")

    st.divider()
    st.subheader("📈 Historical Trends")

    def _line(metric: str, title: str) -> None:
        try:
            fig = px.line(df, x="timestamp", y=metric, color="node_name",
                          labels={"timestamp": "Time", metric: METRIC_LABELS[metric],
                                  "node_name": "Node"})
            fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10),
                              title=title)
            st.plotly_chart(fig, use_container_width=True)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Chart error ({metric}): {exc}")

    g1, g2 = st.columns(2)
    with g1:
        _line("pH", "pH over time")
    with g2:
        _line("turbidity_NTU", "Turbidity over time")
    g3, g4 = st.columns(2)
    with g3:
        _line("temperature_C", "Temperature over time")
    with g4:
        _line("flow_rate_Ls", "Flow rate over time")

    st.divider()
    st.subheader("📋 Latest 24 Readings")
    try:
        recent = df.sort_values("timestamp", ascending=False).head(24).copy()
        recent["status"] = recent.apply(
            lambda r: get_alert_status(r, thresholds)[0], axis=1
        )

        def _highlight(row):
            color = {"Critical": "background-color: #5c1a1a",
                     "Warning": "background-color: #5c4d1a"}.get(row["status"], "")
            return [color] * len(row)

        cols = ["timestamp", "node_name", "pH", "turbidity_NTU", "temperature_C",
                "flow_rate_Ls", "status"]
        st.dataframe(recent[cols].style.apply(_highlight, axis=1),
                     use_container_width=True, hide_index=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Table render error: {exc}")
        st.dataframe(df.tail(24), use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# TAB 2 — Analytics (weekly/monthly aggregation + anomaly detection)
# --------------------------------------------------------------------------- #
with tab_analytics:
    st.subheader("📈 Historical Analytics")
    period = st.radio("Aggregation", ["Daily", "Weekly", "Monthly"],
                      horizontal=True, index=0)
    freq = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[period]
    metric_sel = st.selectbox("Metric", list(METRIC_LABELS.keys()),
                              format_func=lambda m: METRIC_LABELS[m])
    try:
        agg = (df.set_index("timestamp")
                 .groupby("node_name")[metric_sel]
                 .resample(freq).mean().reset_index())
        fig = px.line(agg, x="timestamp", y=metric_sel, color="node_name",
                      markers=True,
                      labels={metric_sel: METRIC_LABELS[metric_sel]})
        fig.update_layout(height=380, title=f"{period} average — {METRIC_LABELS[metric_sel]}")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Aggregation error: {exc}")

    st.divider()
    st.subheader("🔬 Anomaly Detection (z-score > 3)")
    st.caption("Per-node statistical outliers across the selected window.")
    try:
        anomalies = []
        for node, grp in df.groupby("node_name"):
            for metric in METRIC_LABELS:
                vals = grp[metric].astype(float)
                std = vals.std()
                if std and std > 0:
                    z = (vals - vals.mean()) / std
                    flagged = grp.loc[z.abs() > 3, ["timestamp", metric]]
                    for _, fr in flagged.iterrows():
                        anomalies.append({
                            "node_name": node, "metric": METRIC_LABELS[metric],
                            "timestamp": fr["timestamp"], "value": round(fr[metric], 2),
                        })
        if anomalies:
            adf = pd.DataFrame(anomalies).sort_values("timestamp", ascending=False)
            st.dataframe(adf, use_container_width=True, hide_index=True)
            st.info(f"Detected {len(adf)} anomalous readings.")
        else:
            st.success("No statistical anomalies detected in the current window. ✅")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Anomaly detection error: {exc}")

# --------------------------------------------------------------------------- #
# TAB 3 — Alert history log
# --------------------------------------------------------------------------- #
with tab_alerts:
    st.subheader("🚨 Alert History Log")
    a1, a2, a3 = st.columns([2, 2, 2])
    show_open = a1.toggle("Show open alerts only", value=False)
    if a2.button("✅ Resolve all open", use_container_width=True):
        db.resolve_all_alerts()
        db.add_log("resolve_all_alerts", "", "operator")
        st.toast("All open alerts resolved", icon="✅")
        st.rerun()
    alerts = db.get_alerts(only_open=show_open)
    if alerts.empty:
        st.success("No alerts recorded yet. ✅")
    else:
        a3.metric("Open alerts", int((alerts["resolved"] == 0).sum()))
        disp = alerts.copy()
        disp["resolved"] = disp["resolved"].map({0: "Open", 1: "Resolved"})
        st.dataframe(
            disp[["id", "timestamp", "node_name", "severity", "details", "resolved"]],
            use_container_width=True, hide_index=True,
        )
        open_ids = alerts.loc[alerts["resolved"] == 0, "id"].tolist()
        if open_ids:
            rc1, rc2 = st.columns([2, 1])
            sel = rc1.selectbox("Resolve a specific alert (id)", open_ids)
            if rc2.button("Resolve selected", use_container_width=True):
                db.resolve_alert(int(sel))
                db.add_log("resolve_alert", f"id={sel}", "operator")
                st.rerun()

# --------------------------------------------------------------------------- #
# TAB 4 — Node drill-down
# --------------------------------------------------------------------------- #
with tab_node:
    st.subheader("🔍 Node Drill-down")
    node = st.selectbox("Select node", ALL_NODES)
    ndf = df_all[df_all["node_name"] == node].sort_values("timestamp")
    if ndf.empty:
        st.warning("No data for this node.")
    else:
        last = ndf.iloc[-1]
        status, color, breaches = get_alert_status(last, thresholds)
        st.markdown(f"### {node} — current status: :{ 'red' if status=='Critical' else 'orange' if status=='Warning' else 'green'}[{status}]")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("pH", f"{last['pH']:.2f}")
        d2.metric("Turbidity (NTU)", f"{last['turbidity_NTU']:.1f}")
        d3.metric("Temperature (°C)", f"{last['temperature_C']:.1f}")
        d4.metric("Flow (L/s)", f"{last['flow_rate_Ls']:.1f}")
        if breaches:
            st.warning("Breaches: " + "; ".join(breaches))

        gcols = st.columns(2)
        with gcols[0]:
            t = thresholds["pH"]
            st.plotly_chart(create_gauge(last["pH"], "pH", 5.0, 9.0,
                            t["warning_high"], t["critical_high"]),
                            use_container_width=True)
        with gcols[1]:
            t = thresholds["turbidity_NTU"]
            st.plotly_chart(create_gauge(last["turbidity_NTU"], "Turbidity (NTU)",
                            0, 100, t["warning_high"], t["critical_high"]),
                            use_container_width=True)
        gcols2 = st.columns(2)
        with gcols2[0]:
            t = thresholds["temperature_C"]
            st.plotly_chart(create_gauge(last["temperature_C"], "Temperature (°C)",
                            25, 40, t["warning_high"], t["critical_high"]),
                            use_container_width=True)
        with gcols2[1]:
            t = thresholds["flow_rate_Ls"]
            st.plotly_chart(create_gauge(last["flow_rate_Ls"], "Flow (L/s)",
                            0, 220, t["warning_high"], t["critical_high"]),
                            use_container_width=True)

        st.divider()
        m = st.selectbox("History metric", list(METRIC_LABELS.keys()),
                         format_func=lambda x: METRIC_LABELS[x], key="node_hist")
        fig = px.area(ndf, x="timestamp", y=m,
                      labels={m: METRIC_LABELS[m]}, title=f"{node} — {METRIC_LABELS[m]}")
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------- #
# TAB 5 — Settings (threshold config panel)
# --------------------------------------------------------------------------- #
with tab_settings:
    st.subheader("⚙️ Threshold Configuration")
    st.caption("Adjust Warning / Critical bounds. Saved to SQLite and applied live.")
    with st.form("threshold_form"):
        new_vals = {}
        for metric in METRIC_LABELS:
            t = thresholds[metric]
            st.markdown(f"**{METRIC_LABELS[metric]}**")
            cc = st.columns(4)
            new_vals[metric] = (
                cc[0].number_input(f"Crit low · {metric}", value=float(t["critical_low"]),
                                   key=f"cl_{metric}", format="%.2f"),
                cc[1].number_input(f"Warn low · {metric}", value=float(t["warning_low"]),
                                   key=f"wl_{metric}", format="%.2f"),
                cc[2].number_input(f"Warn high · {metric}", value=float(t["warning_high"]),
                                   key=f"wh_{metric}", format="%.2f"),
                cc[3].number_input(f"Crit high · {metric}", value=float(t["critical_high"]),
                                   key=f"ch_{metric}", format="%.2f"),
            )
        saved = st.form_submit_button("💾 Save thresholds", type="primary")
        if saved:
            for metric, (cl, wl, wh, ch) in new_vals.items():
                db.update_threshold(metric, wl, wh, cl, ch)
            db.add_log("update_thresholds", "Threshold config updated", "admin")
            st.success("Thresholds saved.")
            st.rerun()
    if st.button("↩️ Reset to defaults"):
        db.reset_thresholds()
        db.add_log("reset_thresholds", "", "admin")
        st.rerun()

# --------------------------------------------------------------------------- #
# TAB 6 — Data & export (date-range picker)
# --------------------------------------------------------------------------- #
with tab_export:
    st.subheader("💾 Data & Export")
    min_d = df_all["timestamp"].min().date()
    max_d = df_all["timestamp"].max().date()
    dr = st.date_input("Date range", value=(min_d, max_d),
                       min_value=min_d, max_value=max_d)
    if isinstance(dr, (list, tuple)) and len(dr) == 2:
        start, end = dr
        mask = (df_all["timestamp"].dt.date >= start) & (df_all["timestamp"].dt.date <= end)
        out = df_all[mask]
        if node_selector:
            out = out[out["node_name"].isin(node_selector)]
        st.caption(f"{len(out):,} readings between {start} and {end}.")
        st.dataframe(out.tail(200), use_container_width=True, hide_index=True)
        cexp1, cexp2 = st.columns(2)
        cexp1.download_button(
            "⬇️ Download CSV", out.to_csv(index=False).encode("utf-8"),
            file_name=f"water_readings_{start}_{end}.csv", mime="text/csv",
            use_container_width=True,
        )
        cexp2.download_button(
            "⬇️ Download JSON",
            out.to_json(orient="records", date_format="iso").encode("utf-8"),
            file_name=f"water_readings_{start}_{end}.json", mime="application/json",
            use_container_width=True,
        )
    else:
        st.info("Select a start and end date.")

# UPDATED: pass active project for footer navigation highlight
render_footer(active_project="#18 IoT")
