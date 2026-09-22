from pathlib import Path
from datetime import datetime, timezone
import json


class ContentEngine:
    TYPES = {
        "article",
        "email",
        "report",
        "proposal",
        "script",
        "social_post",
        "documentation",
        "presentation",
        "business_plan",
        "meeting_report",
        "marketing_campaign",
    }

    def __init__(self, output_dir="data/content"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, content_type, title, content, metadata=None):
        if content_type not in self.TYPES:
            raise ValueError(
                f"Type de contenu non supporté: {content_type}"
            )

        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d_%H%M%S"
        )

        safe_title = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in title
        )[:80]

        path = self.output_dir / f"{timestamp}_{safe_title}.json"

        payload = {
            "type": content_type,
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "status": "created",
            "type": content_type,
            "title": title,
            "path": str(path),
        }
