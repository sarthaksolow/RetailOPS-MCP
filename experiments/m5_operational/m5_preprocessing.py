"""
M5 Dataset Preprocessing and Validation Module.
Extracts, structures, and validates standardized store-item series from raw M5 files.

Frozen Parameters:
- Store: CA_1
- Items: 5 series across FOODS, HOUSEHOLD, HOBBIES
- Evaluation Horizon: H = 28 days (d_1914 to d_1941, corresponding to 2016-04-25 to 2016-05-22)
- Training Partition: d_1 to d_1913 (2011-01-29 to 2016-04-24)
"""
import os
import sys
import json
import hashlib
import pandas as pd
from typing import Dict, Any, List

SELECTED_SERIES = [
    {
        "series_id": "CA_1_FOODS_1_004",
        "store_id": "CA_1",
        "item_id": "FOODS_1_004",
        "cat_id": "FOODS",
        "dept_id": "FOODS_1",
        "unit_sell_price": 1.96,
        "unit_procurement_cost": 1.18,  # ~60% of sell price wholesale baseline
        "holding_cost_rate": 0.001       # 0.1% of unit cost per day
    },
    {
        "series_id": "CA_1_FOODS_1_012",
        "store_id": "CA_1",
        "item_id": "FOODS_1_012",
        "cat_id": "FOODS",
        "dept_id": "FOODS_1",
        "unit_sell_price": 5.64,
        "unit_procurement_cost": 3.38,
        "holding_cost_rate": 0.001
    },
    {
        "series_id": "CA_1_HOUSEHOLD_1_007",
        "store_id": "CA_1",
        "item_id": "HOUSEHOLD_1_007",
        "cat_id": "HOUSEHOLD",
        "dept_id": "HOUSEHOLD_1",
        "unit_sell_price": 1.48,
        "unit_procurement_cost": 0.89,
        "holding_cost_rate": 0.001
    },
    {
        "series_id": "CA_1_HOBBIES_1_004",
        "store_id": "CA_1",
        "item_id": "HOBBIES_1_004",
        "cat_id": "HOBBIES",
        "dept_id": "HOBBIES_1",
        "unit_sell_price": 4.64,
        "unit_procurement_cost": 2.78,
        "holding_cost_rate": 0.001
    },
    {
        "series_id": "CA_1_HOBBIES_1_008",
        "store_id": "CA_1",
        "item_id": "HOBBIES_1_008",
        "cat_id": "HOBBIES",
        "dept_id": "HOBBIES_1",
        "unit_sell_price": 0.48,
        "unit_procurement_cost": 0.29,
        "holding_cost_rate": 0.001
    }
]


def compute_file_sha256(filepath: str) -> str:
    """Compute standard SHA-256 hash for raw file audit verification."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()


def extract_and_save_m5_subset(
    raw_dir: str = "data/m5/raw",
    processed_dir: str = "data/m5/processed"
) -> Dict[str, Any]:
    """
    Extracts the selected store-item evaluation series from raw M5 CSVs and saves
    structured daily time-series and metadata to the processed directory.
    """
    sales_file = os.path.join(raw_dir, "sales_train_evaluation.csv")
    calendar_file = os.path.join(raw_dir, "calendar.csv")
    prices_file = os.path.join(raw_dir, "sell_prices.csv")

    for f in [sales_file, calendar_file, prices_file]:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Required raw M5 file missing: {f}")

    os.makedirs(processed_dir, exist_ok=True)

    # 1. Load Calendar mapping (d_1 to d_1941 to dates and events)
    cal_df = pd.read_csv(calendar_file)
    cal_df["d"] = [f"d_{i+1}" for i in range(len(cal_df))]
    cal_map = cal_df.set_index("d")[["date", "wm_yr_wk", "weekday", "event_name_1"]].to_dict("index")

    # 2. Extract selected items from sales_train_evaluation
    target_items = [s["item_id"] for s in SELECTED_SERIES]
    
    extracted_series = {}
    for chunk in pd.read_csv(sales_file, chunksize=5000):
        sub = chunk[(chunk["store_id"] == "CA_1") & (chunk["item_id"].isin(target_items))]
        for _, row in sub.iterrows():
            item_id = row["item_id"]
            series_id = f"CA_1_{item_id}"
            
            # Map daily sales values
            daily_records = []
            for d_idx in range(1, 1942):
                col = f"d_{d_idx}"
                sale = int(row[col])
                c_info = cal_map.get(col, {})
                daily_records.append({
                    "d": col,
                    "day_index": d_idx,
                    "date": c_info.get("date"),
                    "weekday": c_info.get("weekday"),
                    "event_name": c_info.get("event_name_1") if pd.notna(c_info.get("event_name_1")) else None,
                    "sales": sale
                })
            
            # Attach matched config
            meta = next(s for s in SELECTED_SERIES if s["series_id"] == series_id)
            
            extracted_series[series_id] = {
                "metadata": meta,
                "total_days": len(daily_records),
                "train_records": daily_records[:1913],   # d_1 to d_1913
                "eval_records": daily_records[1913:1941]  # d_1914 to d_1941 (H=28)
            }

    # 3. Save standardized processed dataset
    out_file = os.path.join(processed_dir, "m5_evaluation_series.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(extracted_series, f, indent=2)

    return {
        "status": "success",
        "output_file": out_file,
        "series_count": len(extracted_series),
        "train_horizon_days": 1913,
        "eval_horizon_days": 28,
        "eval_date_range": ["2016-04-25", "2016-05-22"]
    }


def load_processed_m5_series(processed_dir: str = "data/m5/processed") -> Dict[str, Any]:
    """Load the standardized processed evaluation series."""
    file_path = os.path.join(processed_dir, "m5_evaluation_series.json")
    if not os.path.exists(file_path):
        # Extract on demand if raw files are available
        extract_and_save_m5_subset()
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
