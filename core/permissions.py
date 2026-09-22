class PermissionManager:
    def __init__(self):
        self.mode = "approval"

    def set_mode(self, mode):
        if mode not in {"approval", "auto", "readonly"}:
            raise ValueError("Mode invalide")
        self.mode = mode

    def allowed(self, action, risk="medium"):
        if self.mode == "readonly":
            return risk == "low"
        if self.mode == "auto":
            return True
        return risk == "low"
