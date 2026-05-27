import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import sys
from pathlib import Path

def load_metrics(db_path, table_name):
    if not os.path.exists(db_path):
        print(f"Warning: {db_path} not found.")
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception as e:
        print(f"Error reading {table_name} from {db_path}: {e}")
        df = pd.DataFrame()
    conn.close()
    return df

def generate_charts(scenario_name, data_dir=None):
    print(f"Generating charts for {scenario_name}...")
    
    # 1. Resolve Paths
    if data_dir:
        base = Path(data_dir)
        provider_db = base / "provider.db"
        mfr_db = base / "manufacturer.db"
        retailer_db = base / "retailer.db"
        run_csv = base / "run.csv"
        # If run.csv not in scenario folder, check root logs
        if not run_csv.exists():
            run_csv = Path("logs/run.csv")
    else:
        provider_db = Path("provider/data/provider.db")
        mfr_db = Path("manufacturer/data/manufacturer.db")
        retailer_db = Path("retailer/data/retailer.db")
        run_csv = Path("logs/run.csv")

    # 2. Load Data
    provider_df = load_metrics(str(provider_db), "metrics")
    mfr_df = load_metrics(str(mfr_db), "metrics")
    retailer_df = load_metrics(str(retailer_db), "metrics")
    
    if not run_csv.exists():
        print(f"Error: {run_csv} not found.")
        return
        
    run_df = pd.read_csv(run_csv)
    run_df = run_df[run_df['scenario'] == scenario_name]

    if run_df.empty:
        print(f"No data found in {run_csv} for scenario: {scenario_name}")
        return

    if data_dir:
        output_dir = Path(data_dir) / "charts"
    else:
        output_dir = Path(f"logs/charts/{scenario_name}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    # Deduplicate metrics to one row per (sim_day, product) — keep last snapshot of the day
    mfr_df = mfr_df.groupby(['sim_day', 'model_name'], as_index=False).last()
    retailer_df = retailer_df.groupby(['sim_day', 'sku'], as_index=False).last()
    provider_df = provider_df.groupby(['sim_day', 'product_name'], as_index=False).last()

    # --- Chart 1: Inventory ---
    plt.figure(figsize=(10, 6))

    # Mfr Finished Stock (P3D-Classic)
    mfr_classic = mfr_df[mfr_df['model_name'] == 'P3D-Classic']
    plt.plot(mfr_classic['sim_day'], mfr_classic['finished_stock'], label='Mfr Finished (Classic)', marker='o')
    
    # Retail Stock (P3D-Classic)
    ret_classic = retailer_df[retailer_df['sku'] == 'P3D-Classic']
    plt.plot(ret_classic['sim_day'], ret_classic['stock_quantity'], label='Retail Stock (Classic)', marker='s')
    
    # Provider Part Stock (frame_kit as representative)
    pk_df = provider_df[provider_df['product_name'] == 'frame_kit']
    plt.plot(pk_df['sim_day'], pk_df['stock_quantity'], label='Provider Parts (frame_kit)', linestyle='--')

    plt.title(f"Inventory Levels - {scenario_name}")
    plt.xlabel("Simulation Day")
    plt.ylabel("Units")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "inventory.png")
    plt.close()

    # --- Chart 2: Prices ---
    plt.figure(figsize=(10, 6))
    
    # Provider Price
    plt.plot(pk_df['sim_day'], pk_df['price_tier1'], label='Provider Part (frame_kit)', marker='x')
    
    # Mfr Wholesale Price
    plt.plot(mfr_classic['sim_day'], mfr_classic['wholesale_price'], label='Mfr Wholesale (Classic)', marker='o')
    
    # Retail Price
    plt.plot(ret_classic['sim_day'], ret_classic['retail_price'], label='Retail Price (Classic)', marker='s')

    plt.title(f"Price Dynamics - {scenario_name}")
    plt.xlabel("Simulation Day")
    plt.ylabel("Price (€)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "prices.png")
    plt.close()

    # --- Chart 3: Fulfillment ---
    plt.figure(figsize=(10, 6))
    days = run_df['day']
    plt.bar(days, run_df['fulfilled'], label='Fulfilled', color='green', alpha=0.7)
    plt.bar(days, run_df['backordered'], bottom=run_df['fulfilled'], label='Backordered', color='yellow', alpha=0.7)
    plt.bar(days, run_df['stockout'], bottom=run_df['fulfilled'] + run_df['backordered'], label='Lost/Stockout', color='red', alpha=0.7)
    
    plt.plot(days, run_df['orders_placed'], color='black', label='Placed Orders', marker='.')

    plt.title(f"Daily Fulfillment - {scenario_name}")
    plt.xlabel("Simulation Day")
    plt.ylabel("Orders")
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.savefig(output_dir / "fulfillment.png")
    plt.close()

    # --- Chart 4: Events Overlay ---
    # Simplified events chart using run.csv demand/supply mods
    plt.figure(figsize=(10, 4))
    plt.step(days, run_df['demand_mod'], label='Demand Multiplier', where='post', color='blue')
    plt.step(days, run_df['supply_mod'], label='Supply Multiplier', where='post', color='orange')
    plt.step(days, run_df['lead_mod'], label='Lead Time Multiplier', where='post', color='red')
    
    plt.fill_between(days, 0, 1, where=(run_df['demand_mod'] > 1.0), color='blue', alpha=0.1, label='High Demand')
    
    plt.title(f"Scenario Events & Modifiers - {scenario_name}")
    plt.xlabel("Simulation Day")
    plt.ylabel("Modifier Value")
    plt.ylim(0, max(run_df['demand_mod'].max(), run_df['supply_mod'].max(), run_df['lead_mod'].max()) + 0.5)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(output_dir / "events.png")
    plt.close()

    print(f"Charts saved to {output_dir}")

if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Resolve which run.csv to use for scenario discovery
    if data_dir:
        run_csv_path = Path(data_dir) / "run.csv"
        if not run_csv_path.exists():
            run_csv_path = Path("logs/run.csv")
    else:
        run_csv_path = Path("logs/run.csv")

    if run_csv_path.exists():
        run_df = pd.read_csv(run_csv_path)
        scenarios = run_df['scenario'].unique()
        for s in scenarios:
            generate_charts(s, data_dir)
    else:
        print(f"Error: {run_csv_path} not found. Run the simulation first.")
