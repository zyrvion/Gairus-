from core.action_gateway import ActionGateway
class Executor:

    def authorize_action(
        self,
        actor_id=None,
        action="",
        tool=None,
        amount=None,
    ):
        """
        Contrôle obligatoire avant une action Enterprise.
        """
        return self.action_gateway.authorize(
            actor_id=actor_id,
            action=action,
            tool=tool,
            amount=amount,
        )


    def __init__(self, permissions, 
        self.enterprise = enterprise
        self.controller = controller
        self.action_gateway = ActionGateway(
            enterprise=enterprise,
            controller=controller,
        )
enterprise=None, controller=None):
        self.permissions = permissions

    def execute(self, action, risk="medium", handler=None):

        # ========================================================
        # ENTERPRISE GOVERNANCE EXECUTION GATE
        # ========================================================
        #
        # Compatibilité :
        #   - ancien appel Executor : aucun actor_id => inchangé
        #   - appel Enterprise : actor_id => gouvernance obligatoire
        #
        _actor_id = locals().get("actor_id")
        _amount = locals().get("amount")
        _tool = locals().get("tool")

        if _actor_id is not None:
            _action = locals().get("action")
            if _action is None:
                _action = locals().get("operation")
            if _action is None:
                _action = _tool or "execute"

            self.authorize_action(
                actor_id=_actor_id,
                action=_action,
                tool=_tool,
                amount=_amount,
            )

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
