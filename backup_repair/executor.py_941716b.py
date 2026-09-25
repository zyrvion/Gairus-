class Executor:
    def __init__(self, permissions):
        self.permissions = permissions

    def execute(self, action, risk="medium", handler=None):
        if not self.permissions.allowed(action, risk):
            return {
                "status": "approval_required",
                "action": action,
            }

        if handler:
            return handler()

        return {
            "status": "completed",
            "action": action,
        }
