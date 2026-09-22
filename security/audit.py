from datetime import datetime, timezone
import json
from pathlib import Path


class AuditLog:
    def __init__(self, path="data/audit.log"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event, data=None):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data,
        }

        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(
                entry,
                ensure_ascii=False
            ) + "\n")

        return entry

    def all(self):
        if not self.path.exists():
            return []

        result = []

        for line in self.path.read_text(
            encoding="utf-8"
        ).splitlines():
            if line.strip():
                result.append(json.loads(line))

        return result
