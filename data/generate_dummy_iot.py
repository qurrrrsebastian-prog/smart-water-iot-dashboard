"""Generate simulated IoT water-quality sensor data for the dashboard.

Produces 7 days of hourly readings for 5 Jakarta sensor nodes and writes
them to ``data/iot_sensor_data.csv``. No hardware or API required.

Author : Avatar Putra Sigit
GitHub : qurrrrsebastian-prog
"""

import os
from typing import Dict, List

import numpy as np
import pandas as pd

# Sensor nodes with geographic coordinates.
NODES: Dict[str, Dict[str, float]] = {
    "Ciliwung": {"latitude": -6.225, "longitude": 106.90},
    "Cisadane": {"latitude": -6.18, "longitude": 106.63},
    "Citarum": {"latitude": -6.24, "longitude": 107.02},
    "Sunter": {"latitude": -6.14, "longitude": 106.87},
    "Pesanggrahan": {"latitude": -6.27, "longitude": 106.78},
}

HOURS = 7 * 24  # 7 days of hourly data.


def generate_data(seed: int = 42) -> pd.DataFrame:
    """Generate the simulated sensor dataset.

    Args:
        seed: Random seed for reproducibility.

    Returns:
        A DataFrame with one row per node per hour.
    """
    try:
        rng = np.random.default_rng(seed)
        timestamps = pd.date_range(
            end=pd.Timestamp.now().floor("h"),
            periods=HOURS,
            freq="h",
        )

        rows: List[Dict[str, object]] = []
        for node_name, coords in NODES.items():
            for ts in timestamps:
                ph = float(np.clip(rng.normal(7.2, 0.4), 5.5, 8.8))
                turbidity = float(np.clip(rng.normal(35, 15), 10, 80))
                temperature = float(np.clip(rng.normal(31, 1.8), 28, 36))
                flow_rate = float(np.clip(rng.normal(120, 35), 50, 200))

                # Occasional natural pH spikes.
                if rng.random() < 0.02:
                    ph = float(rng.choice([5.5, 8.8]))

                rows.append(
                    {
                        "timestamp": ts,
                        "node_name": node_name,
                        "latitude": coords["latitude"],
                        "longitude": coords["longitude"],
                        "pH": round(ph, 2),
                        "turbidity_NTU": round(turbidity, 1),
                        "temperature_C": round(temperature, 1),
                        "flow_rate_Ls": round(flow_rate, 1),
                    }
                )

        df = pd.DataFrame(rows)

        # Inject 5-10 deliberate anomalies to trigger alerts.
        n_anomalies = int(rng.integers(5, 11))
        anomaly_idx = rng.choice(df.index, size=n_anomalies, replace=False)
        for idx in anomaly_idx:
            if rng.random() < 0.5:
                df.at[idx, "turbidity_NTU"] = round(float(rng.uniform(61, 95)), 1)
            else:
                df.at[idx, "temperature_C"] = round(float(rng.uniform(35.1, 38)), 1)

        return df
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to generate data: {exc}") from exc


def main() -> None:
    """Generate the dataset and save it to CSV."""
    try:
        df = generate_data()
        out_dir = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(out_dir, "iot_sensor_data.csv")
        df.to_csv(out_path, index=False)
        print(f"Generated {len(df)} rows of sensor data across {len(NODES)} nodes.")
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
