class Sandbox:
    def __init__(self):
        self.enabled = True

    def check(self, operation):
        return {
            "allowed": self.enabled,
            "operation": operation,
        }
