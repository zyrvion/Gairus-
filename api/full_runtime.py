from __future__ import annotations

from typing import Any, Dict, Optional

from core.full_bootstrap import (
    FullGairusRuntime,
    get_full_runtime,
    build_full_runtime,
    reset_full_runtime,
)


def runtime() -> FullGairusRuntime:
    return get_full_runtime()


def status() -> Dict[str, Any]:
    return runtime().status()


def dashboard() -> Dict[str, Any]:
    return runtime().dashboard()


def think(
    prompt: str,
    context: Optional[Dict[str, Any]] = None,
):
    return runtime().think(
        prompt,
        context=context or {},
    )


def run(
    actor_id: str,
    action: str,
    **kwargs: Any,
):
    return runtime().run(
        actor_id=actor_id,
        action=action,
        **kwargs,
    )


def create_mission(
    actor_id: str,
    title: str,
    objective: str,
    **kwargs: Any,
):
    return runtime().create_mission(
        actor_id=actor_id,
        title=title,
        objective=objective,
        **kwargs,
    )


def delegate(
    mission_id: str,
    employee_id: str,
    delegator_id: Optional[str] = None,
):
    return runtime().delegate(
        mission_id=mission_id,
        employee_id=employee_id,
        delegator_id=delegator_id,
    )


def escalate(
    actor_id: str,
    reason: str,
    action: Optional[str] = None,
    mission_id: Optional[str] = None,
    target_level: Optional[str] = None,
):
    return runtime().escalate(
        actor_id=actor_id,
        reason=reason,
        action=action,
        mission_id=mission_id,
        target_level=target_level,
    )


def send_slack(
    channel: str,
    text: str,
    **kwargs: Any,
):
    return runtime().send_slack(
        channel=channel,
        text=text,
        **kwargs,
    )


__all__ = [
    "FullGairusRuntime",
    "get_full_runtime",
    "build_full_runtime",
    "reset_full_runtime",
    "runtime",
    "status",
    "dashboard",
    "think",
    "run",
    "create_mission",
    "delegate",
    "escalate",
    "send_slack",
]
