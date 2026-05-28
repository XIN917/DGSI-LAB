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
        # Fallback to logs root if not in the specific dir
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
    
    run_df = pd.DataFrame()
    if run_csv.exists():
        try:
            full_run_df = pd.read_csv(run_csv)
            run_df = full_run_df[full_run_df['scenario'] == scenario_name]
        except Exception as e:
            print(f"Warning: Could not parse {run_csv}: {e}")

    if data_dir:
        output_dir = Path(data_dir) / "charts"
    else:
        output_dir = Path(f"logs/charts/{scenario_name}")
    
    output_dir.mkdir(parents=True, exist_ok=True)

    # Deduplicate metrics
    if not mfr_df.empty:
        mfr_df = mfr_df.groupby(['sim_day', 'model_name'], as_index=False).last()
    if not retailer_df.empty:
        retailer_df = retailer_df.groupby(['sim_day', 'sku'], as_index=False).last()
    if not provider_df.empty:
        provider_df = provider_df.groupby(['sim_day', 'product_name'], as_index=False).last()

    # --- Chart 1: Inventory ---
    if not mfr_df.empty or not retailer_df.empty or not provider_df.empty:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Top Plot: Finished Goods
        if not mfr_df.empty:
            for model in mfr_df['model_name'].unique():
                sub = mfr_df[mfr_df['model_name'] == model]
                ax1.plot(sub['sim_day'], sub['finished_stock'], label=f'Mfr {model}', marker='o', alpha=0.8)
        
        if not retailer_df.empty:
            for sku in retailer_df['sku'].unique():
                sub = retailer_df[retailer_df['sku'] == sku]
                ax1.plot(sub['sim_day'], sub['stock_quantity'], label=f'Retail {sku}', marker='s', alpha=0.8)
        
        ax1.set_title(f"Finished Goods Inventory - {scenario_name}")
        ax1.set_ylabel("Units")
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Bottom Plot: Raw Materials (Parts)
        if not provider_df.empty:
            parts = provider_df['product_name'].unique()
            for part in parts:
                sub = provider_df[provider_df['product_name'] == part]
                ax2.plot(sub['sim_day'], sub['stock_quantity'], label=f'Part {part}', linestyle='-', alpha=0.6)

            ax2.set_title(f"Raw Materials Inventory (Provider) - {scenario_name}")
            ax2.set_xlabel("Simulation Day")
            ax2.set_ylabel("Units")
            ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='x-small', ncol=2)
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / "inventory.png")
        plt.close()

    # --- Chart 2: Prices ---
    if not mfr_df.empty or not retailer_df.empty or not provider_df.empty:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), sharex=True)
        
        # Top Plot: Retail & Wholesale
        if not mfr_df.empty:
            for model in mfr_df['model_name'].unique():
                sub = mfr_df[mfr_df['model_name'] == model]
                ax1.plot(sub['sim_day'], sub['wholesale_price'], label=f'Mfr Wholesale {model}', marker='o', alpha=0.8)
        
        if not retailer_df.empty:
            for sku in retailer_df['sku'].unique():
                sub = retailer_df[retailer_df['sku'] == sku]
                ax1.plot(sub['sim_day'], sub['retail_price'], label=f'Retail {sku}', marker='s', alpha=0.8)

        ax1.set_title(f"Finished Goods Pricing - {scenario_name}")
        ax1.set_ylabel("Price (€)")
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax1.grid(True, alpha=0.3)

        # Bottom Plot: Part Prices
        if not provider_df.empty:
            parts = provider_df['product_name'].unique()
            for part in parts:
                sub = provider_df[provider_df['product_name'] == part]
                ax2.plot(sub['sim_day'], sub['price_tier1'], label=f'Part {part}', linestyle='-', alpha=0.7)

            ax2.set_title(f"Part Pricing (Provider) - {scenario_name}")
            ax2.set_xlabel("Simulation Day")
            ax2.set_ylabel("Price (€)")
            ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='x-small', ncol=2)
            ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / "prices.png")
        plt.close()

    # --- Chart 3: Fulfillment (Requires run_df) ---
    if not run_df.empty:
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

        # --- Chart 4: Events Overlay (Requires run_df) ---
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
    else:
        print(f"Skipping Fulfillment and Events charts for {scenario_name} (no CSV data).")

    print(f"Charts saved to {output_dir}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])
        if data_dir.is_dir():
            # Use folder name as scenario name (e.g., "calm-market_1")
            scenario = data_dir.name
            generate_charts(scenario, data_dir)
        else:
            print(f"Error: {data_dir} is not a directory.")
    else:
        # Default: process all scenarios found in logs/run.csv
        run_csv_path = Path("logs/run.csv")
        if run_csv_path.exists():
            run_df = pd.read_csv(run_csv_path)
            for s in run_df['scenario'].unique():
                generate_charts(s)
        else:
            print(f"Error: logs/run.csv not found. Provide a directory path to visualize archived databases.")
