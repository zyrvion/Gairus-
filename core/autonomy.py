from __future__ import annotations

from typing import Any, Dict, List, Optional


class AutonomyEngine:
    """
    Couche de planification autonome de Gaïrus.

    L'autonomie sert à :
    - analyser un objectif ;
    - produire un plan ;
    - ordonner les étapes ;
    - choisir les prochaines actions ;
    - suivre l'état d'exécution.

    Elle ne contourne jamais Executor, ActionGateway
    ou GovernanceGate.
    """

    def __init__(
        self,
        enterprise=None,
        executor=None,
        missions=None,
        hierarchy=None,
        llm=None,
    ):
        self.enterprise = enterprise
        self.executor = executor
        self.missions = missions
        self.hierarchy = hierarchy
        self.llm = llm

        self.enabled = True

        self._plans: Dict[str, Dict[str, Any]] = {}

    def configure(self, enabled: bool = True):
        self.enabled = bool(enabled)
        return self.status()

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "plans": len(self._plans),
            "executor": self.executor is not None,
            "enterprise": self.enterprise is not None,
            "mission_orchestrator": self.missions is not None,
            "hierarchy": self.hierarchy is not None,
            "llm": self.llm is not None,
        }

    def analyze(
        self,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not objective:
            raise ValueError("Objective is required")

        context = context or {}

        return {
            "objective": objective,
            "context": context,
            "constraints": self._extract_constraints(context),
            "risks": self._identify_risks(objective, context),
        }

    def _extract_constraints(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        constraints = context.get("constraints", [])

        if isinstance(constraints, str):
            return [constraints]

        if isinstance(constraints, list):
            return list(constraints)

        return []

    def _identify_risks(
        self,
        objective: str,
        context: Dict[str, Any],
    ) -> List[str]:
        risks = []

        text = objective.lower()

        sensitive_terms = {
            "banque": "financial_operation",
            "virement": "financial_operation",
            "paiement": "financial_operation",
            "contrat": "legal_operation",
            "signature": "legal_operation",
            "juridique": "legal_operation",
            "licenciement": "employment_operation",
            "capital": "capital_operation",
            "actionnaire": "shareholder_operation",
            "administratif": "official_filing",
        }

        for keyword, risk in sensitive_terms.items():
            if keyword in text and risk not in risks:
                risks.append(risk)

        if context.get("amount"):
            risks.append("financial_amount")

        if context.get("external_system"):
            risks.append("external_system")

        return risks

    def build_plan(
        self,
        objective: str,
        actor_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Gaïrus autonomy is disabled")

        analysis = self.analyze(
            objective=objective,
            context=context,
        )

        if steps is None:
            steps = self._generate_default_steps(
                objective=objective,
                context=context or {},
            )

        normalized_steps = []

        for index, step in enumerate(steps, start=1):
            if isinstance(step, str):
                step = {
                    "action": step,
                }

            item = dict(step)

            item.setdefault("step_id", f"step-{index}")
            item.setdefault("status", "pending")
            item.setdefault("order", index)

            normalized_steps.append(item)

        plan_id = f"plan-{len(self._plans) + 1}"

        plan = {
            "plan_id": plan_id,
            "objective": objective,
            "actor_id": actor_id,
            "analysis": analysis,
            "steps": normalized_steps,
            "status": "planned",
            "current_step": 0,
            "context": context or {},
        }

        self._plans[plan_id] = plan

        return dict(plan)

    def _generate_default_steps(
        self,
        objective: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Générateur de plan minimal et déterministe.

        Un LLM peut enrichir le plan plus tard, mais il ne reçoit
        jamais le pouvoir d'exécuter directement une action.
        """
        return [
            {
                "action": "analyze",
                "description": "Analyser l'objectif et ses contraintes",
            },
            {
                "action": "plan",
                "description": "Construire le plan opérationnel",
            },
            {
                "action": "execute",
                "description": "Exécuter les étapes autorisées",
            },
            {
                "action": "review",
                "description": "Vérifier le résultat",
            },
        ]

    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        plan = self._plans.get(plan_id)

        if plan is None:
            return None

        return dict(plan)

    def list_plans(self, status: Optional[str] = None):
        plans = list(self._plans.values())

        if status is not None:
            plans = [
                plan
                for plan in plans
                if plan.get("status") == status
            ]

        return [dict(plan) for plan in plans]

    def start_plan(self, plan_id: str) -> Dict[str, Any]:
        plan = self._require_plan(plan_id)

        plan["status"] = "running"

        return dict(plan)

    def _require_plan(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)

        if plan is None:
            raise KeyError(f"Unknown plan: {plan_id}")

        return plan

    def next_step(self, plan_id: str) -> Optional[Dict[str, Any]]:
        plan = self._require_plan(plan_id)

        steps = plan.get("steps", [])

        current = plan.get("current_step", 0)

        if current >= len(steps):
            plan["status"] = "completed"
            return None

        return dict(steps[current])

    def mark_step(
        self,
        plan_id: str,
        status: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        plan = self._require_plan(plan_id)

        steps = plan.get("steps", [])
        current = plan.get("current_step", 0)

        if current >= len(steps):
            plan["status"] = "completed"
            return dict(plan)

        step = steps[current]

        step["status"] = status

        if result is not None:
            step["result"] = result

        if error is not None:
            step["error"] = error

        if status == "completed":
            plan["current_step"] = current + 1

            if plan["current_step"] >= len(steps):
                plan["status"] = "completed"

        elif status in {
            "blocked",
            "waiting_approval",
            "failed",
        }:
            plan["status"] = status

        return dict(plan)

    def execute_next(
        self,
        plan_id: str,
        actor_id: str,
        handler=None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Exécute uniquement l'étape courante.

        L'action réelle passe obligatoirement par Executor.
        """
        plan = self._require_plan(plan_id)

        if self.executor is None:
            raise RuntimeError("Executor is not configured")

        step = self.next_step(plan_id)

        if step is None:
            return {
                "status": "completed",
                "plan_id": plan_id,
            }

        action = step.get("action")

        if action in {"analyze", "plan", "review"}:
            result = {
                "status": "ok",
                "action": action,
                "message": step.get("description", ""),
            }

            self.mark_step(
                plan_id,
                "completed",
                result=result,
            )

            return {
                "status": "ok",
                "plan_id": plan_id,
                "step": step,
                "result": result,
            }

        try:
            result = self.executor.execute(
                action=action,
                handler=handler,
                actor_id=actor_id,
                mission_id=plan.get("mission_id"),
                metadata={
                    "plan_id": plan_id,
                    "step_id": step.get("step_id"),
                    **kwargs,
                },
            )

            if isinstance(result, dict):
                result_status = result.get("status")

                if result_status in {
                    "approval_required",
                    "waiting_approval",
                }:
                    self.mark_step(
                        plan_id,
                        "waiting_approval",
                        result=result,
                    )

                elif result_status in {
                    "blocked",
                    "denied",
                    "forbidden",
                }:
                    self.mark_step(
                        plan_id,
                        "blocked",
                        result=result,
                    )

                elif result_status in {
                    "error",
                    "failed",
                }:
                    self.mark_step(
                        plan_id,
                        "failed",
                        result=result,
                        error=result.get("error"),
                    )

                else:
                    self.mark_step(
                        plan_id,
                        "completed",
                        result=result,
                    )
            else:
                self.mark_step(
                    plan_id,
                    "completed",
                    result=result,
                )

            return {
                "status": "ok",
                "plan_id": plan_id,
                "step": step,
                "result": result,
            }

        except PermissionError as exc:
            self.mark_step(
                plan_id,
                "blocked",
                error=str(exc),
            )

            return {
                "status": "blocked",
                "plan_id": plan_id,
                "step": step,
                "error": str(exc),
            }

        except Exception as exc:
            self.mark_step(
                plan_id,
                "failed",
                error=str(exc),
            )

            return {
                "status": "error",
                "plan_id": plan_id,
                "step": step,
                "error": str(exc),
                "error_type": exc.__class__.__name__,
            }

    def run_plan(
        self,
        plan_id: str,
        actor_id: str,
        max_steps: int = 100,
        handler=None,
        **kwargs,
    ) -> Dict[str, Any]:
        plan = self._require_plan(plan_id)

        self.start_plan(plan_id)

        executed = []

        for _ in range(max_steps):
            step = self.next_step(plan_id)

            if step is None:
                break

            result = self.execute_next(
                plan_id=plan_id,
                actor_id=actor_id,
                handler=handler,
                **kwargs,
            )

            executed.append(result)

            current_plan = self._require_plan(plan_id)

            if current_plan.get("status") in {
                "blocked",
                "waiting_approval",
                "failed",
                "completed",
            }:
                break

        return {
            "status": self._require_plan(plan_id).get("status"),
            "plan_id": plan_id,
            "executed_steps": executed,
            "plan": dict(self._require_plan(plan_id)),
        }

    def attach_mission(
        self,
        plan_id: str,
        mission_id: str,
    ) -> Dict[str, Any]:
        plan = self._require_plan(plan_id)

        plan["mission_id"] = mission_id

        return dict(plan)

    def cancel_plan(
        self,
        plan_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        plan = self._require_plan(plan_id)

        plan["status"] = "cancelled"

        if reason is not None:
            plan["cancel_reason"] = reason

        return dict(plan)

    def dashboard(self) -> Dict[str, Any]:
        plans = list(self._plans.values())

        counts: Dict[str, int] = {}

        for plan in plans:
            status = plan.get("status", "planned")
            counts[status] = counts.get(status, 0) + 1

        return {
            "total": len(plans),
            "by_status": counts,
            "running": counts.get("running", 0),
            "completed": counts.get("completed", 0),
            "blocked": counts.get("blocked", 0),
            "waiting_approval": counts.get("waiting_approval", 0),
            "failed": counts.get("failed", 0),
        }
