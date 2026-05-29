import argparse
from pathlib import Path
import uvicorn
from dashboard.app import create_app


def main():
    parser = argparse.ArgumentParser(description="Live supply chain dashboard")
    parser.add_argument("--config", default="config/sim.json", help="path to sim.json")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--refresh", type=int, default=2, help="browser refresh interval (seconds)")
    args = parser.parse_args()
    app = create_app(Path(args.config), refresh=args.refresh)
    print(f"Dashboard → http://{args.host}:{args.port}  (config: {args.config}, refresh: {args.refresh}s)")
    uvicorn.run(app, host=args.host, port=args.port, reload=False, log_level="warning")


if __name__ == "__main__":
    main()
