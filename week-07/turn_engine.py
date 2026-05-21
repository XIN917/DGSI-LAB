#!/usr/bin/env python3
"""Turn engine: orchestrates one simulated day across all apps."""
import argparse
import shlex
import subprocess
import json
import random
import sys
from pathlib import Path
import time

# Try to import httpx, if not available, we will suggest installing it
try:
    import httpx
except ImportError:
    print("Error: 'httpx' library not found. Please install it with 'pip install httpx'.")
    sys.exit(1)

def load_config(path):
    return json.loads(Path(path).read_text())

def load_scenario(path):
    return json.loads(Path(path).read_text())

def todays_signal(day, scenario):
    signal = {"day": day, "events": []}
    for event in scenario.get("events", []):
        if event["start_day"] <= day <= event["end_day"]:
            signal["events"].append(event)
            signal["demand_modifier"] = event.get("demand_modifier", 1.0)
    
    signal.setdefault("demand_modifier", 1.0)
    signal["base_demand"] = scenario.get("base_demand", {"mean": 5, "variance": 2})
    return signal

def generate_customer_orders(retailer_url, signal):
    print(f"Generating customer orders for {retailer_url}...")
    try:
        response = httpx.get(f"{retailer_url}/api/catalog")
        catalog = response.json()
    except Exception as e:
        print(f"Error fetching catalog: {e}")
        return

    # Deterministic generator from Part 1
    base = signal.get("base_demand", {"mean": 5, "variance": 2})
    modifier = signal.get("demand_modifier", 1.0)
    
    for item in catalog:
        model = item["sku"]
        price = item["retail_price"]
        # Use wholesale_price as base_price for demand curve, or a default
        base_price = item.get("wholesale_price", 0)
        if base_price <= 0:
            base_price = price / 1.3
        
        mean_orders = base["mean"] * modifier
        # Higher prices -> less demand
        target_price = base_price * 1.3
        price_factor = max(0.2, 1.0 - (price - target_price) / target_price)
        adjusted_mean = mean_orders * price_factor
        n = max(0, int(random.gauss(adjusted_mean, base["variance"])))
        
        if n > 0:
            print(f"  Placing {n} orders for {model}")
            for _ in range(n):
                try:
                    httpx.post(f"{retailer_url}/api/orders",
                               json={"customer": "auto", "model": model, "quantity": 1})
                except Exception as e:
                    print(f"  Error placing order: {e}")

def run_agent_or_stub(role, skill_path, context, cwd, verbose=False):
    """Phase 1: stub. Phase 2: call claude --print."""
    if skill_path is None:
        print(f"[stub] {role} would make decisions here")
        return
    
    abs_skill_path = Path(skill_path).absolute()
    if not abs_skill_path.exists():
        print(f"[{role}] Warning: skill file not found at {abs_skill_path}")
        print(f"[stub] {role} would make decisions here")
        return
    
    if verbose:
        print(f"Running agent for {role} using skill file {abs_skill_path}...")
        print("  (This typically takes 1-2 minutes. Please wait...)")
    else:
        print(f"Running agent for {role}...")
    prompt = f"""
You are the {role} agent for this simulation.
Skill file path: {abs_skill_path}
Today's context: {context}
Execute your daily decisions following the skill's decision framework.
Do NOT advance the day - the turn engine does that.
"""
    start_time = time.time()
    try:
        day_val = json.loads(context).get("day", 0)
        # Week 7 uses Claude Code with --print flag
        command = [
            "claude",
            "--print",
            prompt
        ]
        if verbose:
            safe_command = " ".join(shlex.quote(p) for p in command)
            print(f"  Claude command: {safe_command}")
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            bufsize=1
        )

        stdout_lines = []
        # Use simple prefix to distinguish agent output
        print(f"\n--- {role.upper()} AGENT START ---")
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end="", flush=True)
                stdout_lines.append(line)
        print(f"--- {role.upper()} AGENT END ---\n")

        return_code = process.wait()
        stdout_content = "".join(stdout_lines)
        duration = time.time() - start_time
        print(f"  Done! Execution took {duration:.1f}s")

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"day-{day_val:03d}-{role}.log"
        log_file.write_text(stdout_content)

        if return_code != 0:
            print(f"[{role}] Claude exited with return code {return_code}")
        else:
            print(f"[{role}] Agent execution complete. Log saved to {log_file}")
    except subprocess.TimeoutExpired as e:
        print(f"[{role}] Error: Agent execution timed out after 180s")
        stdout_content = "".join(stdout_lines)
        if stdout_content:
            print(stdout_content)
    except Exception as e:
        print(f"[{role}] Error: {e}")
def advance_all(urls):
    print("Advancing all apps to the next day...")
    for url in urls:
        try:
            httpx.post(f"{url}/api/day/advance")
            print(f"  {url} advanced.")
        except Exception as e:
            print(f"  Error advancing {url}: {e}")

def run_day(day, config, scenario, verbose=False):
    signal = todays_signal(day, scenario)
    if verbose:
        print(f"\n{'='*60}\n DAY {day} signal={signal}\n{'='*60}")
    else:
        print(f"\n--- DAY {day} ---")
    
    # 1. Generate customer orders
    for retailer in config["retailers"]:
        generate_customer_orders(retailer["url"], signal)
    
    # 2. Run agents/stubs
    # Retailers first (downstream)
    for retailer in config["retailers"]:
        run_agent_or_stub("retailer", retailer.get("skill"), 
                         json.dumps(signal), retailer["path"], verbose=verbose)
    
    # Manufacturer
    run_agent_or_stub("manufacturer", 
                     config["manufacturer"].get("skill"), 
                     json.dumps(signal), 
                     config["manufacturer"]["path"],
                     verbose=verbose)
    
    # Providers
    for provider in config["providers"]:
        run_agent_or_stub("provider", provider.get("skill"), 
                         json.dumps(signal), provider["path"], verbose=verbose)
    
    # 3. Advance all
    urls = [r["url"] for r in config["retailers"]] + \
           [config["manufacturer"]["url"]] + \
           [p["url"] for p in config["providers"]]
    advance_all(urls)

def parse_args():
    parser = argparse.ArgumentParser(description="Run the DGSI turn engine simulation.")
    parser.add_argument("config_json", help="Config JSON path")
    parser.add_argument("scenario_json", help="Scenario JSON path")
    parser.add_argument("days", type=int, help="Number of days to simulate")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print full agent action output and debug details")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    config = load_config(args.config_json)
    scenario = load_scenario(args.scenario_json)

    # Start simulation from current day across apps
    # For Week 7 POC, we just run for N days
    for day in range(1, args.days + 1):
        run_day(day, config, scenario, verbose=args.verbose)
        time.sleep(1) # Brief pause between days
