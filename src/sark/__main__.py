"""Entry point for running SARK as a module."""

import sys

from sark.main import app


def main() -> None:
    """Run the SARK application."""
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    sys.exit(main())
