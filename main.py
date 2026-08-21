import argparse
from pathlib import Path

from budget_agent.session_manager import SessionManager
from budget_agent.storage import Storage


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-first financial budgeting agent")
    parser.add_argument("--mode", choices=["cli", "web"], default="cli")
    parser.add_argument("--db", default=str(Path("data") / "budget_agent.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--use-ollama", action="store_true")
    args = parser.parse_args()

    storage = Storage(args.db)
    if args.mode == "cli":
        SessionManager(storage).run_cli_session(use_ollama=args.use_ollama)
        storage.close()
        return

    try:
        from budget_agent.web_ui import create_app
    except ImportError as exc:
        storage.close()
        raise SystemExit(
            "Web mode needs Flask. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    app = create_app(storage)
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
