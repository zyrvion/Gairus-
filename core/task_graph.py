class TaskGraph:
    def __init__(self):
        self.nodes = {}

    def add(self, node_id, action, depends_on=None):
        self.nodes[node_id] = {
            "id": node_id,
            "action": action,
            "depends_on": depends_on or [],
            "status": "pending",
        }

    def ready(self):
        completed = {
            node_id
            for node_id, node in self.nodes.items()
            if node["status"] == "completed"
        }

        return [
            node for node in self.nodes.values()
            if node["status"] == "pending"
            and all(dep in completed for dep in node["depends_on"])
        ]

    def complete(self, node_id):
        if node_id in self.nodes:
            self.nodes[node_id]["status"] = "completed"

    def fail(self, node_id, error=None):
        if node_id in self.nodes:
            self.nodes[node_id]["status"] = "failed"
            self.nodes[node_id]["error"] = error
