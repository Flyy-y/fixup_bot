"""Container healthcheck: verifies the bot's heartbeat file is recent.

Exit 0 if the heartbeat was updated within the allowed window, else exit 1.
The bot refreshes the heartbeat every 30s once its event loop is running.
"""

import os
import sys
import time
from pathlib import Path

HEARTBEAT_FILE = Path(os.environ.get("HEARTBEAT_FILE", "/tmp/fixupx_healthy"))
MAX_AGE = int(os.environ.get("HEARTBEAT_MAX_AGE", "90"))  # seconds


def main() -> int:
    if not HEARTBEAT_FILE.exists():
        print("heartbeat file missing", file=sys.stderr)
        return 1
    age = time.time() - HEARTBEAT_FILE.stat().st_mtime
    if age > MAX_AGE:
        print(f"heartbeat stale: {age:.0f}s > {MAX_AGE}s", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
