import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
from pathlib import Path

def load_metrics(db_path, table_name):
    if not os.path.exists(db_path):
        print(f"Warning: {db_path} not found.")
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()
    return df

def generate_charts(scenario_name):
    print(f"Generating charts for {scenario_name}...")
    
    # 1. Load Data
    provider_df = load_metrics("provider/data/provider.db", "metrics")
    mfr_df = load_metrics("manufacturer/data/manufacturer.db", "metrics")
    retailer_df = load_metrics("retailer/data/retailer.db", "metrics")
    run_df = pd.read_csv("logs/run.csv")
    run_df = run_df[run_df['scenario'] == scenario_name]

    if run_df.empty:
        print(f"No data found in logs/run.csv for scenario: {scenario_name}")
        return

    output_dir = Path(f"docs/charts/{scenario_name}")
    output_dir.mkdir(parents=True, exist_ok=True)

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
    # Detect scenarios from run.csv
    if os.path.exists("logs/run.csv"):
        run_df = pd.read_csv("logs/run.csv")
        scenarios = run_df['scenario'].unique()
        for s in scenarios:
            generate_charts(s)
    else:
        print("logs/run.csv not found. Run the simulation first.")
