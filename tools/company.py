from core.company_controller import CompanyController

_controller = CompanyController()


def dashboard(actor_id):
    return _controller.execute(actor_id, "dashboard")


def org_chart(actor_id):
    return _controller.execute(actor_id, "org_chart")


def create_mission(
    actor_id,
    title,
    objective,
    department_id=None,
    priority="normal",
):
    return _controller.execute(
        actor_id,
        "create_mission",
        title=title,
        objective=objective,
        department_id=department_id,
        priority=priority,
    )


def create_content(
    actor_id,
    content_type,
    title,
    content,
    metadata=None,
):
    return _controller.execute(
        actor_id,
        "create_content",
        content_type=content_type,
        title=title,
        content=content,
        metadata=metadata,
    )
