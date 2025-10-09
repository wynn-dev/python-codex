"""Entry point for Codex CLI."""

import sys
from .app import run


def main():
    """Main entry point."""
    try:
        run()
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

