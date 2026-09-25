from __future__ import annotations

from typing import Any, Dict, Optional

from core.enterprise import EnterpriseEngine
from core.company_controller import CompanyController
from core.action_gateway import ActionGateway
from core.executor import Executor
from core.hierarchy import HierarchyEngine
from core.mission_orchestrator import MissionOrchestrator
from core.autonomy import AutonomyEngine
from core.agent_runtime import GairusRuntime


def bootstrap_enterprise() -> EnterpriseEngine:
    """
    Initialise le noyau Enterprise de Gaïrus.
    """
    return EnterpriseEngine()


def bootstrap_hierarchy(
    enterprise: EnterpriseEngine,
) -> HierarchyEngine:
    """
    Construit le moteur hiérarchique à partir de l'EnterpriseEngine.
    """
    return HierarchyEngine(enterprise=enterprise)


def bootstrap_controller(
    enterprise: EnterpriseEngine,
) -> CompanyController:
    """
    Initialise le contrôleur central de l'entreprise.
    """
    return CompanyController(
        enterprise=enterprise,
    )


def bootstrap_gateway(
    enterprise: EnterpriseEngine,
    controller: CompanyController,
) -> ActionGateway:
    """
    Initialise la passerelle de gouvernance des actions.
    """
    return ActionGateway(
        enterprise=enterprise,
        controller=controller,
    )


def bootstrap_executor(
    enterprise: EnterpriseEngine,
    controller: CompanyController,
) -> Executor:
    """
    Initialise le moteur d'exécution.
    """
    return Executor(
        enterprise=enterprise,
        controller=controller,
    )


def bootstrap_missions(
    enterprise: EnterpriseEngine,
    executor: Executor,
    hierarchy: HierarchyEngine,
) -> MissionOrchestrator:
    """
    Initialise l'orchestrateur des missions.
    """
    return MissionOrchestrator(
        enterprise=enterprise,
        executor=executor,
        controller=None,
        hierarchy=hierarchy,
    )


def bootstrap_autonomy(
    enterprise: EnterpriseEngine,
    executor: Executor,
    missions: MissionOrchestrator,
    hierarchy: HierarchyEngine,
    llm=None,
) -> AutonomyEngine:
    """
    Initialise la couche d'autonomie contrôlée.
    """
    return AutonomyEngine(
        enterprise=enterprise,
        executor=executor,
        missions=missions,
        hierarchy=hierarchy,
        llm=llm,
    )


def bootstrap_runtime(
    llm=None,
    enabled_autonomy: bool = True,
) -> GairusRuntime:
    """
    Assemble l'ensemble du système Gaïrus.

    Chaîne :

        Enterprise
            ↓
        Hierarchy
            ↓
        Controller
            ↓
        ActionGateway
            ↓
        Executor
            ↓
        Missions
            ↓
        Autonomy
            ↓
        Runtime

    L'ordre est volontaire :
    l'autonomie ne devient jamais une porte de sortie
    permettant de contourner la gouvernance.
    """

    enterprise = bootstrap_enterprise()

    hierarchy = bootstrap_hierarchy(
        enterprise,
    )

    controller = bootstrap_controller(
        enterprise,
    )

    gateway = bootstrap_gateway(
        enterprise,
        controller,
    )

    executor = bootstrap_executor(
        enterprise,
        controller,
    )

    missions = bootstrap_missions(
        enterprise,
        executor,
        hierarchy,
    )

    autonomy = bootstrap_autonomy(
        enterprise,
        executor,
        missions,
        hierarchy,
        llm=llm,
    )

    autonomy.configure(
        enabled=enabled_autonomy,
    )

    runtime = GairusRuntime(
        enterprise=enterprise,
        controller=controller,
        executor=executor,
        llm=llm,
        missions=missions,
        autonomy=autonomy,
    )

    runtime.gateway = gateway
    runtime.hierarchy = hierarchy

    return runtime


def bootstrap(
    llm=None,
    enabled_autonomy: bool = True,
) -> GairusRuntime:
    """
    Point d'entrée public du bootstrap Gaïrus.
    """
    return bootstrap_runtime(
        llm=llm,
        enabled_autonomy=enabled_autonomy,
    )


def system_summary(
    runtime: Optional[GairusRuntime],
) -> Dict[str, Any]:
    """
    Retourne un résumé exploitable du système.
    """
    if runtime is None:
        return {
            "status": "offline",
            "runtime": False,
        }

    summary: Dict[str, Any] = {
        "status": "online",
        "runtime": True,
    }

    try:
        summary["runtime_status"] = runtime.status()
    except Exception as exc:
        summary["runtime_status_error"] = str(exc)

    enterprise = getattr(runtime, "enterprise", None)

    if enterprise is not None:
        try:
            summary["enterprise"] = enterprise.dashboard()
        except Exception as exc:
            summary["enterprise_error"] = str(exc)

    hierarchy = getattr(runtime, "hierarchy", None)

    if hierarchy is not None:
        try:
            summary["hierarchy"] = hierarchy.summary()
        except Exception as exc:
            summary["hierarchy_error"] = str(exc)

    missions = getattr(runtime, "missions", None)

    if missions is not None:
        try:
            summary["missions"] = missions.dashboard()
        except Exception as exc:
            summary["missions_error"] = str(exc)

    autonomy = getattr(runtime, "autonomy", None)

    if autonomy is not None:
        try:
            summary["autonomy"] = autonomy.status()
        except Exception as exc:
            summary["autonomy_error"] = str(exc)

    return summary
