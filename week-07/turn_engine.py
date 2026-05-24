#!/usr/bin/env python3
"""Turn engine: orchestrates one simulated day across all apps."""
import argparse
import subprocess
import json
import random
import sys
from pathlib import Path
import time

try:
    import httpx
except ImportError:
    print("Error: 'httpx' not found. Run: pip install httpx")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.text import Text
    from rich.markdown import Markdown
except ImportError:
    print("Error: 'rich' not found. Run: pip install rich")
    sys.exit(1)

console = Console()

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
    try:
        response = httpx.get(f"{retailer_url}/api/catalog")
        catalog = response.json()
    except Exception as e:
        console.print(f"  [red]✗ Could not fetch catalog: {e}[/red]")
        return

    base = signal.get("base_demand", {"mean": 5, "variance": 2})
    modifier = signal.get("demand_modifier", 1.0)
    total = 0

    for item in catalog:
        model = item["sku"]
        price = item["retail_price"]
        base_price = item.get("wholesale_price", 0)
        if base_price <= 0:
            base_price = price / 1.3
        mean_orders = base["mean"] * modifier
        target_price = base_price * 1.3
        price_factor = max(0.2, 1.0 - (price - target_price) / target_price)
        adjusted_mean = mean_orders * price_factor
        n = max(0, int(random.gauss(adjusted_mean, base["variance"])))
        if n > 0:
            total += n
            console.print(f"  [cyan]{model}[/cyan]  [white]{n} orders[/white]")
            for _ in range(n):
                try:
                    httpx.post(f"{retailer_url}/api/orders",
                               json={"customer": "auto", "model": model, "quantity": 1})
                except Exception as e:
                    console.print(f"  [red]✗ Order error: {e}[/red]")

    if total == 0:
        console.print("  [dim]No orders generated[/dim]")

def prefetch_state(role, cwd):
    """Run read-only CLI commands and return combined output."""
    cli = f"./{role}-cli"
    commands = {
        "manufacturer": ["stock", "sales orders", "production status", "capacity", "price list", "purchase list", "suppliers list"],
        "retailer":     ["inventory", "customer-orders list", "purchase-orders list", "catalog"],
        "provider":     ["stock", "orders list", "catalog"],
    }
    lines = []
    for cmd in commands.get(role, []):
        try:
            result = subprocess.run(
                f"{cli} {cmd}", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
            )
            out = result.stdout.strip() or result.stderr.strip()
            lines.append(f"### {cli} {cmd}\n{out}")
        except Exception as e:
            lines.append(f"### {cli} {cmd}\nerror: {e}")
    return "\n\n".join(lines)

def run_agent_or_stub(role, skill_path, context, cwd, verbose=False):
    role_label = role.upper()

    if skill_path is None:
        console.print(f"  [dim]{role_label}  stub — no skill configured[/dim]")
        return

    abs_skill_path = Path(skill_path).absolute()
    if not abs_skill_path.exists():
        console.print(f"  [yellow]{role_label}  stub — skill not found: {skill_path}[/yellow]")
        return

    state = prefetch_state(role, cwd)
    day_val = json.loads(context).get("day", 0)

    notes = []
    if role == "manufacturer":
        if day_val == 1:
            notes.append(
                "NOTE: This is Day 1. The capacity history has no previous days. "
                "Do NOT adjust prices today — the 2-day utilisation rule requires at least 2 days of history. Hold all prices."
            )
        notes.append(
            "NOTE: Supplier names are pre-fetched below under '### ./manufacturer-cli suppliers list'. "
            "Use those exact names when calling 'purchase create --supplier <name>'. Do not guess."
        )

    notes_block = ("\n\n" + "\n".join(notes)) if notes else ""

    prompt = (
        f"Read {abs_skill_path} and make today's decisions.\n"
        f"Today's context: {context}{notes_block}\n\n"
        f"Current state (already fetched — skip all read commands, go straight to decisions):\n{state}"
    )
    start_time = time.time()

    try:
        import os
        env = os.environ.copy()
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")

        cmd = (
            "claude --print --dangerously-skip-permissions "
            "--allowedTools Bash "
            "--model claude-haiku-4-5-20251001 "
            + json.dumps(prompt)
        )

        stdout_lines = []

        console.print(f"  [bold blue]{role_label}[/bold blue] [dim]thinking...[/dim]")
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=env,
            bufsize=1
        )
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                stdout_lines.append(line)

        return_code = process.wait()
        stdout_content = "".join(stdout_lines)
        duration = time.time() - start_time

        console.print(Panel(
            Markdown(stdout_content.strip()),
            title=f"[bold blue]{role_label} AGENT[/bold blue]  [dim]{duration:.0f}s[/dim]",
            border_style="blue",
            padding=(1, 2),
        ))

        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"day-{day_val:03d}-{role}.log"
        log_file.write_text(stdout_content)

        if return_code != 0:
            console.print(f"  [red]✗ Claude exited with code {return_code}[/red]")
        else:
            console.print(f"  [dim]Log → {log_file}[/dim]")

    except Exception as e:
        console.print(f"  [red]✗ {role_label} error: {e}[/red]")

def advance_all(urls):
    console.print("\n[bold]Advancing all services...[/bold]")
    for url in urls:
        try:
            httpx.post(f"{url}/api/day/advance")
            console.print(f"  [green]✓[/green] {url}")
        except Exception as e:
            console.print(f"  [red]✗[/red] {url}: {e}")

def run_day(day, config, scenario, verbose=False):
    signal = todays_signal(day, scenario)

    modifier = signal.get("demand_modifier", 1.0)
    events = signal.get("events", [])
    event_desc = events[0].get("description", events[0]["name"]) if events else "No active events"
    modifier_color = "green" if modifier >= 1.0 else "yellow"

    console.print()
    console.rule(f"[bold white] DAY {day} [/bold white]", style="bright_blue")
    console.print(f"  [dim]Event:[/dim] {event_desc}   "
                  f"[dim]Demand:[/dim] [{modifier_color}]x{modifier}[/{modifier_color}]")
    console.print()

    console.print("[bold]Customer demand[/bold]")
    for retailer in config["retailers"]:
        generate_customer_orders(retailer["url"], signal)

    console.print()
    console.print("[bold]Agent decisions[/bold]")
    for retailer in config["retailers"]:
        run_agent_or_stub("retailer", retailer.get("skill"),
                         json.dumps(signal), retailer["path"], verbose=verbose)

    run_agent_or_stub("manufacturer",
                     config["manufacturer"].get("skill"),
                     json.dumps(signal),
                     config["manufacturer"]["path"],
                     verbose=verbose)

    for provider in config["providers"]:
        run_agent_or_stub("provider", provider.get("skill"),
                         json.dumps(signal), provider["path"], verbose=verbose)

    urls = ([r["url"] for r in config["retailers"]] +
            [config["manufacturer"]["url"]] +
            [p["url"] for p in config["providers"]])
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

    console.print(Panel(
        f"[bold]Config:[/bold] {args.config_json}   "
        f"[bold]Scenario:[/bold] {args.scenario_json}   "
        f"[bold]Days:[/bold] {args.days}",
        title="[bold cyan] DGSI Turn Engine [/bold cyan]",
        border_style="cyan",
    ))

    for day in range(1, args.days + 1):
        run_day(day, config, scenario, verbose=args.verbose)
        time.sleep(1)

    console.print()
    console.rule("[bold green] Simulation complete [/bold green]", style="green")
    console.print()
