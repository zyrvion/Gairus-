from datetime import datetime, timezone


class AuditLog:
    def __init__(self):
        self.events = []

    def record(self, event, data=None):
        entry = {
            "time": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "data": data,
        }
        self.events.append(entry)
        return entry

    def all(self):
        return list(self.events)
