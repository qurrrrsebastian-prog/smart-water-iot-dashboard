"""database.py — SQLite persistence for the Smart Water IoT Dashboard.
Author: Avatar Putra Sigit | GitHub: qurrrrsebastian-prog
"""
import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

# Sensible default thresholds matching the original alert logic.
DEFAULT_THRESHOLDS = {
    # metric: (warning_low, warning_high, critical_low, critical_high)
    "pH": (6.5, 8.0, 6.0, 8.5),
    "turbidity_NTU": (0.0, 40.0, 0.0, 50.0),
    "temperature_C": (0.0, 33.0, 0.0, 35.0),
    "flow_rate_Ls": (60.0, 180.0, 40.0, 200.0),
}


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row access by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables and seed default thresholds. Call once at app start."""
    conn = get_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
            node_name TEXT, latitude REAL, longitude REAL,
            ph REAL, turbidity_ntu REAL, temperature_c REAL, flow_rate_ls REAL,
            alert_status TEXT DEFAULT 'Normal');
        CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT,
            node_name TEXT, alert_type TEXT, severity TEXT, details TEXT,
            resolved BOOLEAN DEFAULT 0);
        CREATE TABLE IF NOT EXISTS threshold_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, metric TEXT UNIQUE,
            warning_low REAL, warning_high REAL, critical_low REAL, critical_high REAL);
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, user TEXT,
            action TEXT, details TEXT);
        CREATE INDEX IF NOT EXISTS idx_readings_ts ON sensor_readings(timestamp);
        CREATE INDEX IF NOT EXISTS idx_readings_node ON sensor_readings(node_name);
        """
    )
    # Seed default thresholds if absent.
    for metric, (wl, wh, cl, ch) in DEFAULT_THRESHOLDS.items():
        conn.execute(
            """INSERT OR IGNORE INTO threshold_config
               (metric, warning_low, warning_high, critical_low, critical_high)
               VALUES (?, ?, ?, ?, ?)""",
            (metric, wl, wh, cl, ch),
        )
    conn.commit()
    conn.close()


def add_log(action: str, details: str = "", user: str = "anonymous") -> None:
    """Append an entry to the audit log."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO audit_log (timestamp, user, action, details) VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(timespec="seconds"), user, action, details),
    )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Sensor readings
# --------------------------------------------------------------------------- #
def reading_count() -> int:
    """Return the number of sensor readings stored."""
    conn = get_connection()
    n = conn.execute("SELECT COUNT(*) AS c FROM sensor_readings").fetchone()["c"]
    conn.close()
    return int(n)


def seed_from_dataframe(df: pd.DataFrame) -> int:
    """Bulk insert readings from a DataFrame (used for first-run seeding).

    Expects original CSV columns: timestamp, node_name, latitude, longitude,
    pH, turbidity_NTU, temperature_C, flow_rate_Ls.
    Returns the number of rows inserted.
    """
    if df.empty:
        return 0
    conn = get_connection()
    rows = []
    for _, r in df.iterrows():
        rows.append(
            (
                str(r["timestamp"]),
                r["node_name"],
                float(r["latitude"]),
                float(r["longitude"]),
                float(r["pH"]),
                float(r["turbidity_NTU"]),
                float(r["temperature_C"]),
                float(r["flow_rate_Ls"]),
                r.get("alert_status", "Normal") if hasattr(r, "get") else "Normal",
            )
        )
    conn.executemany(
        """INSERT INTO sensor_readings
           (timestamp, node_name, latitude, longitude, ph, turbidity_ntu,
            temperature_c, flow_rate_ls, alert_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def insert_reading(
    timestamp: str,
    node_name: str,
    latitude: float,
    longitude: float,
    ph: float,
    turbidity: float,
    temperature: float,
    flow_rate: float,
    alert_status: str = "Normal",
) -> None:
    """Insert a single new sensor reading."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO sensor_readings
           (timestamp, node_name, latitude, longitude, ph, turbidity_ntu,
            temperature_c, flow_rate_ls, alert_status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp, node_name, latitude, longitude, ph, turbidity, temperature,
         flow_rate, alert_status),
    )
    conn.commit()
    conn.close()


# Map DB column names back to the app's expected CSV-style column names.
_COL_MAP = {
    "ph": "pH",
    "turbidity_ntu": "turbidity_NTU",
    "temperature_c": "temperature_C",
    "flow_rate_ls": "flow_rate_Ls",
}


def load_readings() -> pd.DataFrame:
    """Load all readings as a DataFrame using app-style column names."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT timestamp, node_name, latitude, longitude, ph, turbidity_ntu, "
        "temperature_c, flow_rate_ls, alert_status FROM sensor_readings "
        "ORDER BY timestamp",
        conn,
        parse_dates=["timestamp"],
    )
    conn.close()
    return df.rename(columns=_COL_MAP)


# --------------------------------------------------------------------------- #
# Thresholds
# --------------------------------------------------------------------------- #
def get_thresholds() -> Dict[str, Dict[str, float]]:
    """Return all thresholds keyed by metric name."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM threshold_config").fetchall()
    conn.close()
    return {
        r["metric"]: {
            "warning_low": r["warning_low"],
            "warning_high": r["warning_high"],
            "critical_low": r["critical_low"],
            "critical_high": r["critical_high"],
        }
        for r in rows
    }


def update_threshold(
    metric: str,
    warning_low: float,
    warning_high: float,
    critical_low: float,
    critical_high: float,
) -> None:
    """Update the threshold bounds for one metric."""
    conn = get_connection()
    conn.execute(
        """UPDATE threshold_config
           SET warning_low=?, warning_high=?, critical_low=?, critical_high=?
           WHERE metric=?""",
        (warning_low, warning_high, critical_low, critical_high, metric),
    )
    conn.commit()
    conn.close()


def reset_thresholds() -> None:
    """Reset all thresholds to their defaults."""
    conn = get_connection()
    for metric, (wl, wh, cl, ch) in DEFAULT_THRESHOLDS.items():
        conn.execute(
            """UPDATE threshold_config
               SET warning_low=?, warning_high=?, critical_low=?, critical_high=?
               WHERE metric=?""",
            (wl, wh, cl, ch, metric),
        )
    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
def log_alert(node_name: str, alert_type: str, severity: str, details: str) -> None:
    """Record an alert event (de-duplicated against the latest open alert)."""
    conn = get_connection()
    existing = conn.execute(
        """SELECT id FROM alert_log
           WHERE node_name=? AND alert_type=? AND severity=? AND resolved=0
           ORDER BY id DESC LIMIT 1""",
        (node_name, alert_type, severity),
    ).fetchone()
    if existing is None:
        conn.execute(
            """INSERT INTO alert_log (timestamp, node_name, alert_type, severity, details, resolved)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (datetime.now().isoformat(timespec="seconds"), node_name, alert_type,
             severity, details),
        )
        conn.commit()
    conn.close()


def get_alerts(only_open: bool = False) -> pd.DataFrame:
    """Return the alert log as a DataFrame."""
    conn = get_connection()
    q = "SELECT * FROM alert_log"
    if only_open:
        q += " WHERE resolved=0"
    q += " ORDER BY id DESC"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def resolve_alert(alert_id: int) -> None:
    """Mark a single alert as resolved."""
    conn = get_connection()
    conn.execute("UPDATE alert_log SET resolved=1 WHERE id=?", (alert_id,))
    conn.commit()
    conn.close()


def resolve_all_alerts() -> None:
    """Mark every open alert as resolved."""
    conn = get_connection()
    conn.execute("UPDATE alert_log SET resolved=1 WHERE resolved=0")
    conn.commit()
    conn.close()
