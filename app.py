"""Smart Water IoT Dashboard — Jakarta.

Real-time (simulated) water-quality monitoring for 5 Jakarta sensor nodes.
Refresh is MANUAL via a button — there is no auto-refresh loop.

Author : Avatar Putra Sigit
GitHub : qurrrrsebastian-prog
"""

import os
import sys
import time
import random
from datetime import datetime
from typing import Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def load_data() -> pd.DataFrame:
    """Load the simulated sensor data from CSV.

    Returns:
        A DataFrame of sensor readings, or an empty DataFrame if the file
        is missing.
    """
    try:
        if not os.path.exists(DATA_PATH):
            st.error("Run: python data/generate_dummy_iot.py first")
            return pd.DataFrame()
        df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"])
        return df
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load data: {exc}")
        return pd.DataFrame()


def get_alert_status(row: pd.Series) -> Tuple[str, str]:
    """Determine the alert status for a single sensor reading.

    Args:
        row: A row containing pH, turbidity_NTU and temperature_C.

    Returns:
        A tuple of (status, color) where status is
        "Normal"/"Warning"/"Critical".
    """
    try:
        ph = float(row["pH"])
        turbidity = float(row["turbidity_NTU"])
        temp = float(row["temperature_C"])

        # Critical conditions.
        if ph < 6 or ph > 8.5 or turbidity > 50 or temp > 35:
            return "Critical", "red"
        # Warning conditions.
        if (
            (6 <= ph < 6.5)
            or (8 < ph <= 8.5)
            or (40 <= turbidity <= 50)
            or (33 <= temp <= 35)
        ):
            return "Warning", "orange"
        return "Normal", "green"
    except Exception:  # noqa: BLE001
        return "Normal", "green"


def create_gauge(
    value: float,
    title: str,
    min_val: float,
    max_val: float,
    threshold_warning: float,
    threshold_critical: float,
) -> go.Figure:
    """Build a gauge chart with green/yellow/red color zones.

    Args:
        value: Current value to display.
        title: Gauge title.
        min_val: Minimum of the axis range.
        max_val: Maximum of the axis range.
        threshold_warning: Start of the warning (yellow) zone.
        threshold_critical: Start of the critical (red) zone.

    Returns:
        A Plotly gauge figure.
    """
    try:
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=value,
                title={"text": title},
                gauge={
                    "axis": {"range": [min_val, max_val]},
                    "bar": {"color": "#1f77b4"},
                    "steps": [
                        {"range": [min_val, threshold_warning], "color": "#c8e6c9"},
                        {
                            "range": [threshold_warning, threshold_critical],
                            "color": "#fff9c4",
                        },
                        {"range": [threshold_critical, max_val], "color": "#ffcdd2"},
                    ],
                },
            )
        )
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    except Exception:  # noqa: BLE001
        return go.Figure()


def simulate_refresh(df: pd.DataFrame) -> pd.DataFrame:
    """Append one fresh simulated reading per node (manual refresh only).

    Args:
        df: The existing sensor DataFrame.

    Returns:
        The DataFrame with new rows appended for the current timestamp.
    """
    try:
        if df.empty:
            return df
        now = pd.Timestamp.now().floor("h")
        new_rows = []
        for node in ALL_NODES:
            ref = df[df["node_name"] == node]
            if ref.empty:
                continue
            coords = ref.iloc[-1]
            new_rows.append(
                {
                    "timestamp": now,
                    "node_name": node,
                    "latitude": coords["latitude"],
                    "longitude": coords["longitude"],
                    "pH": round(float(np.clip(random.gauss(7.2, 0.5), 5.5, 8.8)), 2),
                    "turbidity_NTU": round(
                        float(np.clip(random.gauss(35, 18), 10, 95)), 1
                    ),
                    "temperature_C": round(
                        float(np.clip(random.gauss(31, 2.2), 28, 38)), 1
                    ),
                    "flow_rate_Ls": round(
                        float(np.clip(random.gauss(120, 40), 50, 200)), 1
                    ),
                }
            )
        return pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    except Exception:  # noqa: BLE001
        return df


# --------------------------------------------------------------------------- #
# Session state
# --------------------------------------------------------------------------- #
if "data" not in st.session_state:
    st.session_state.data = load_data()


# --------------------------------------------------------------------------- #
# Sidebar controls
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🎛️ Controls")
    node_selector = st.multiselect(
        "Sensor Nodes",
        ALL_NODES,
        default=ALL_NODES,
    )
    if st.button("🔄 Refresh Data", type="primary"):
        st.session_state.data = simulate_refresh(st.session_state.data)
    st.caption("Click Refresh to simulate new sensor reading")


# --------------------------------------------------------------------------- #
# Main dashboard
# --------------------------------------------------------------------------- #
st.title("💧 Smart Water IoT Dashboard — Jakarta")
st.caption(
    "Real-time monitoring for urban water management | Smart Water Competition"
)

df = st.session_state.data

if df.empty:
    st.warning("No data available. Run: python data/generate_dummy_iot.py")
    st.stop()

# Filter by selected nodes.
if node_selector:
    df = df[df["node_name"].isin(node_selector)]

if df.empty:
    st.warning("No nodes selected. Choose at least one sensor node.")
    st.stop()

df = df.sort_values("timestamp")

# --------------------------------------------------------------------------- #
# Row 1 — latest metrics with delta vs previous hour
# --------------------------------------------------------------------------- #
latest_ts = df["timestamp"].max()
latest = df[df["timestamp"] == latest_ts]
prev_times = sorted(df["timestamp"].unique())
prev_ts = prev_times[-2] if len(prev_times) > 1 else latest_ts
previous = df[df["timestamp"] == prev_ts]


def _avg(frame: pd.DataFrame, col: str) -> float:
    """Return the mean of a column, or 0.0 if empty."""
    try:
        return float(frame[col].mean())
    except Exception:  # noqa: BLE001
        return 0.0


m1, m2, m3, m4 = st.columns(4)
ph_now, ph_prev = _avg(latest, "pH"), _avg(previous, "pH")
turb_now, turb_prev = _avg(latest, "turbidity_NTU"), _avg(previous, "turbidity_NTU")
temp_now, temp_prev = _avg(latest, "temperature_C"), _avg(previous, "temperature_C")
flow_now, flow_prev = _avg(latest, "flow_rate_Ls"), _avg(previous, "flow_rate_Ls")

# For pH, closer to 7 is better; for turbidity/temp, lower is better.
m1.metric("pH (avg)", f"{ph_now:.2f}", delta=f"{ph_now - ph_prev:+.2f}")
m2.metric(
    "Turbidity (NTU)",
    f"{turb_now:.1f}",
    delta=f"{turb_now - turb_prev:+.1f}",
    delta_color="inverse",
)
m3.metric(
    "Temperature (°C)",
    f"{temp_now:.1f}",
    delta=f"{temp_now - temp_prev:+.1f}",
    delta_color="inverse",
)
m4.metric("Flow Rate (L/s)", f"{flow_now:.1f}", delta=f"{flow_now - flow_prev:+.1f}")

st.divider()

# --------------------------------------------------------------------------- #
# Row 2 — map + alerts
# --------------------------------------------------------------------------- #
map_col, alert_col = st.columns([3, 2])

with map_col:
    st.subheader("🗺️ Sensor Network")
    latest_per_node = (
        df.sort_values("timestamp").groupby("node_name", as_index=False).last()
    )
    statuses = latest_per_node.apply(get_alert_status, axis=1)
    latest_per_node = latest_per_node.assign(
        status=[s[0] for s in statuses],
        color=[s[1] for s in statuses],
    )
    try:
        fig_map = px.scatter_geo(
            latest_per_node,
            lat="latitude",
            lon="longitude",
            color="status",
            hover_name="node_name",
            hover_data={
                "pH": True,
                "turbidity_NTU": True,
                "temperature_C": True,
                "latitude": False,
                "longitude": False,
            },
            color_discrete_map={
                "Normal": "green",
                "Warning": "orange",
                "Critical": "red",
            },
            size_max=18,
        )
        fig_map.update_traces(marker=dict(size=14))
        fig_map.update_geos(
            center=dict(lat=-6.21, lon=106.83),
            projection_scale=180,
            showland=True,
            landcolor="#eef2f5",
            showcountries=True,
        )
        fig_map.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig_map, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Map render error: {exc}")

with alert_col:
    st.subheader("🚨 Alerts")
    any_alert = False
    for _, node_row in latest_per_node.iterrows():
        status = node_row["status"]
        name = node_row["node_name"]
        detail = (
            f"pH {node_row['pH']:.2f} | "
            f"Turb {node_row['turbidity_NTU']:.1f} NTU | "
            f"Temp {node_row['temperature_C']:.1f}°C"
        )
        if status == "Critical":
            st.error(f"**{name}** — CRITICAL\n\n{detail}")
            any_alert = True
        elif status == "Warning":
            st.warning(f"**{name}** — Warning\n\n{detail}")
            any_alert = True
    if not any_alert:
        st.success("All nodes operating within normal parameters. ✅")

st.divider()

# --------------------------------------------------------------------------- #
# Rows 3 & 4 — historical trends
# --------------------------------------------------------------------------- #
def _line(metric: str, title: str, y_label: str) -> None:
    """Render a per-node line chart for a metric over time."""
    try:
        fig = px.line(
            df,
            x="timestamp",
            y=metric,
            color="node_name",
            labels={"timestamp": "Waktu", metric: y_label, "node_name": "Node"},
        )
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10), title=title)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Chart error ({metric}): {exc}")


st.subheader("📈 Historical Trends (7 days)")
r3c1, r3c2 = st.columns(2)
with r3c1:
    _line("pH", "pH over time", "pH")
with r3c2:
    _line("turbidity_NTU", "Turbidity over time", "NTU")

r4c1, r4c2 = st.columns(2)
with r4c1:
    _line("temperature_C", "Temperature over time", "°C")
with r4c2:
    _line("flow_rate_Ls", "Flow rate over time", "L/s")

st.divider()

# --------------------------------------------------------------------------- #
# Row 5 — latest 24 hours table
# --------------------------------------------------------------------------- #
st.subheader("📋 Latest 24 Hours")
try:
    recent = df.sort_values("timestamp", ascending=False).head(24).copy()
    recent_status = recent.apply(get_alert_status, axis=1)
    recent["status"] = [s[0] for s in recent_status]

    def _highlight(row: pd.Series) -> list:
        """Return background styles per status for a table row."""
        color = {
            "Critical": "background-color: #ffcdd2",
            "Warning": "background-color: #fff9c4",
        }.get(row["status"], "")
        return [color] * len(row)

    styled = recent[
        [
            "timestamp",
            "node_name",
            "pH",
            "turbidity_NTU",
            "temperature_C",
            "flow_rate_Ls",
            "status",
        ]
    ].style.apply(_highlight, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as exc:  # noqa: BLE001
    st.error(f"Table render error: {exc}")
    st.dataframe(df.tail(24), use_container_width=True, hide_index=True)
