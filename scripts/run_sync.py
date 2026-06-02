"""直接执行 Telegram 采集（无需 uvicorn 在跑）。"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.sync import sync_channels  # noqa: E402


async def _main() -> dict:
    return await sync_channels()


def main() -> int:
    result = asyncio.run(_main())
    payload = {
        "at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "last_sync.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    new_links = int(result.get("new_links", 0))
    errors = result.get("errors") or []
    return 1 if errors and new_links == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
