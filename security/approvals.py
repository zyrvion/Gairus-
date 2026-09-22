class ApprovalManager:
    def request(self, action):
        return {
            "status": "approval_required",
            "action": action,
        }
