"""Entry point for Codex CLI."""

import sys
import argparse
from pathlib import Path
from .app import run


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Codex CLI - AI Coding Assistant powered by Claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codex                    # Run in current directory
  codex /path/to/project   # Run in specific directory
  codex ../other-project   # Run in relative directory
  codex --workspace ~/dev  # Use --workspace flag
        """
    )
    
    parser.add_argument(
        'workspace',
        nargs='?',
        default='.',
        help='Workspace directory to open (default: current directory)'
    )
    
    parser.add_argument(
        '-w', '--workspace',
        dest='workspace_flag',
        help='Workspace directory to open (alternative syntax)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='Codex CLI 0.1.0'
    )
    
    args = parser.parse_args()
    
    # Determine workspace path
    workspace_path = args.workspace_flag if args.workspace_flag else args.workspace
    workspace_path = Path(workspace_path).resolve()
    
    # Validate workspace
    if not workspace_path.exists():
        print(f"Error: Directory '{workspace_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not workspace_path.is_dir():
        print(f"Error: '{workspace_path}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    try:
        run(workspace_path)
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
