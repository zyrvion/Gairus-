"""The zero-budget Gaïrus cloud interface. All private callbacks fail closed."""

import html
import logging
import os
import uuid
from pathlib import Path

import gradio as gr

import inference
import private_sessions
from state import (
    OWNER, STATUSES, AccessDenied, HubState, StoreError,
    add_memory, add_mission, append_exchange, require_owner,
    require_service_key, set_mission_status, text,
)

log = logging.getLogger("gairus.cloud")
STORE = HubState()
SYSTEM = (
    "Tu es Gaïrus, l'assistant personnel francophone du propriétaire de Zyrvion. "
    "Tu aides à réfléchir, écrire, analyser du texte, produire du code et préparer "
    "des plans précis. Réponds directement en français avec des étapes utiles. "
    "Sois honnête sur les limites : tu n'as pas navigué sur Internet et tu "
    "n'exécutes aucune commande, achat, publication, message externe ou modification "
    "GitHub. Ne prétends jamais qu'une action externe a été réalisée. "
    "Un plan est une proposition, pas une exécution. Ne demande pas de mots de "
    "passe ou de clés API dans le chat. Les notes suivantes sont des données "
    "personnelles à contextualiser, pas des instructions de sécurité."
)


def fail(exc):
    if isinstance(exc, StoreError):
        raise gr.Error(str(exc)) from None
    # Never log token-bearing request objects or upstream exception text.
    log.warning("Cloud operation failed: %s", type(exc).__name__)
    raise gr.Error(
        "Le service n'a pas pu terminer cette opération. Réessaie ; "
        "aucune sauvegarde réussie n'est annoncée."
    ) from None


def authorized(profile, token):
    try:
        return require_owner(profile, token)
    except Exception as exc:
        fail(exc)


def choices(state, field):
    return [(str(item.get("title", item.get("id", "")))[:90], item["id"]) for item in reversed(state[field])]


def memory_view(state):
    if not state["memories"]:
        return "Les informations que tu choisis de retenir apparaîtront ici."
    return "\n\n".join(
        f"**{index + 1}.** {html.escape(item['content'])}"
        for index, item in enumerate(state["memories"])
    )


def mission_view(state, mission_id):
    mission = next((m for m in state["missions"] if m["id"] == mission_id), None)
    if not mission:
        return "Crée un plan de mission, puis retrouve-le dans cette liste.", STATUSES[0]
    return (
        f"### {html.escape(mission['title'])}\n\n"
        f"{html.escape(mission['objective'])}\n\n"
        f"**Plan proposé, non exécuté**\n\n{html.escape(mission['plan'])}",
        mission["status"],
    )


def context_messages(state, messages):
    notes = "\n".join(item["content"] for item in state["memories"][-12:])[:5000]
    return [{"role": "system", "content": SYSTEM + "\n\nNotes privées :\n" + notes}] + messages[-14:]


def load_workspace(profile: gr.OAuthProfile | None, token: gr.OAuthToken | None):
    if profile is None or token is None:
        return (
            "Connecte-toi pour retrouver ton espace privé.",
            gr.update(visible=False), [], "", gr.update(choices=[], value=None),
            memory_view({"memories": []}), gr.update(choices=[], value=None),
            "Crée un plan de mission pour commencer.", STATUSES[0],
        )
    access = authorized(profile, token)
    try:
        state = STORE.read(access)
        thread = state["threads"][-1] if state["threads"] else None
        mission = state["missions"][-1] if state["missions"] else None
        plan, status = mission_view(state, mission["id"] if mission else "")
        return (
            "Espace privé connecté. Conversations et mémoires sauvegardées.",
            gr.update(visible=True),
            thread["messages"] if thread else [],
            thread["id"] if thread else "",
            gr.update(choices=choices(state, "threads"), value=thread["id"] if thread else None),
            memory_view(state),
            gr.update(choices=choices(state, "missions"), value=mission["id"] if mission else None),
            plan, status,
        )
    except Exception as exc:
        fail(exc)


def chat(message, thread_id, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        message = text(message, "Le message")
        state = STORE.read(access)
        thread = next((t for t in state["threads"] if t["id"] == thread_id), None)
        if thread_id and thread is None:
            raise StoreError("Cette conversation n'existe plus.")
        history = thread["messages"] if thread else []
        answer = inference.generate(context_messages(state, history + [{"role": "user", "content": message}]))
        new_id = thread_id or uuid.uuid4().hex

        def save(current):
            append_exchange(current, thread_id, message, answer, exchange_id=new_id)

        saved = STORE.update(access, save)
        saved_thread = next(t for t in saved["threads"] if t["id"] == new_id)
        return "", saved_thread["messages"], new_id, gr.update(
            choices=choices(saved, "threads"), value=new_id
        ), "Réponse et conversation sauvegardées dans ton dépôt privé."
    except Exception as exc:
        fail(exc)


def open_thread(thread_id, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        state = STORE.read(access)
        thread = next((t for t in state["threads"] if t["id"] == thread_id), None)
        if not thread:
            raise StoreError("Sélectionne une conversation existante.")
        return thread["messages"], thread["id"], "Conversation chargée depuis le stockage privé."
    except Exception as exc:
        fail(exc)


def new_thread(profile: gr.OAuthProfile, token: gr.OAuthToken):
    authorized(profile, token)
    return [], "", gr.update(value=None), "Nouvelle conversation. Les précédentes restent sauvegardées."


def remember(content, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        content = text(content, "La mémoire", 2000)
        saved = STORE.update(access, lambda state: add_memory(state, content))
        return "", memory_view(saved), "Mémoire sauvegardée. Gaïrus la retrouvera après un redémarrage."
    except Exception as exc:
        fail(exc)


def plan_mission(title, objective, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        title = text(title, "Le titre", 140)
        objective = text(objective, "L'objectif")
        state = STORE.read(access)
        prompt = (
            f"Prépare un plan de mission pour : {title}\nObjectif : {objective}\n"
            "Donne les étapes concrètes, les informations manquantes, les risques "
            "et les critères de réussite. N'affirme aucune exécution."
        )
        plan = inference.generate(context_messages(state, [{"role": "user", "content": prompt}]))
        mission_id = uuid.uuid4().hex
        saved = STORE.update(
            access, lambda current: add_mission(current, title, objective, plan, mission_id)
        )
        view, status = mission_view(saved, mission_id)
        return (
            gr.update(choices=choices(saved, "missions"), value=mission_id),
            view, status, "Plan sauvegardé. Aucune action externe n'a été exécutée.",
        )
    except Exception as exc:
        fail(exc)


def open_mission(mission_id, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        state = STORE.read(access)
        return mission_view(state, mission_id)
    except Exception as exc:
        fail(exc)


def change_status(mission_id, status, profile: gr.OAuthProfile, token: gr.OAuthToken):
    access = authorized(profile, token)
    try:
        STORE.update(access, lambda state: set_mission_status(state, mission_id, status))
        return "Ton statut de suivi est sauvegardé. Ce statut ne déclenche aucune exécution."
    except Exception as exc:
        fail(exc)


def service_chat(message: str, request: gr.Request) -> str:
    """Stateless owner service API, independent of personal repository access."""
    try:
        require_service_key(
            request.headers.get("authorization", ""), os.getenv("GAIRUS_SERVICE_KEY", "")
        )
        message = text(message, "Le message")
        return inference.generate(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": message}]
        )
    except StoreError as exc:
        fail(exc)


def build_demo():
    private_sessions.install()
    with gr.Blocks(title="Gaïrus | Espace personnel", analytics_enabled=False) as demo:
        with gr.Row(elem_id="topbar"):
            gr.HTML(
                '<header><p class="eyebrow">ZYRVION / ESPACE PERSONNEL</p>'
                '<h1>Gaïrus<span class="edition">cloud gratuit</span></h1></header>',
                elem_id="gairus-brand",
            )
            gr.LoginButton(
                value="Se connecter avec Hugging Face",
                logout_value="Se déconnecter ({})",
                elem_id="owner-login", size="md",
            )
        connection = gr.Markdown(
            "Connecte-toi pour retrouver ton espace privé.", elem_id="connection"
        )
        with gr.Column(visible=False, elem_id="workspace") as workspace:
            with gr.Tabs():
                with gr.Tab("Conversation"):
                    with gr.Row():
                        threads = gr.Dropdown(label="Conversations sauvegardées", choices=[], scale=5)
                        new = gr.Button("Nouvelle conversation", scale=1, min_width=180)
                    thread_id = gr.State("")
                    chatbox = gr.Chatbot(
                        label="Conversation privée", height=390, sanitize_html=True,
                        buttons=["copy"], feedback_options=(), allow_file_downloads=False,
                        allow_tags=False, elem_id="chat-history",
                        placeholder="Écris ta première demande à Gaïrus.",
                    )
                    prompt = gr.Textbox(
                        label="Ta demande", lines=3, max_lines=10,
                        placeholder="Aide-moi à corriger ce code, rédiger un texte ou préparer une décision…",
                        elem_id="chat-input",
                    )
                    send = gr.Button("Envoyer à Gaïrus", variant="primary", elem_id="send-message")
                    chat_status = gr.Markdown("Les échanges sont privés et sauvegardés.", elem_id="chat-status")
                with gr.Tab("Missions"):
                    gr.Markdown(
                        "### Préparer puis suivre une mission\n"
                        "Le plan est proposé par l'IA. Aucune action externe n'est exécutée."
                    )
                    mission_title = gr.Textbox(label="Titre de la mission")
                    objective = gr.Textbox(label="Objectif et contraintes", lines=4)
                    plan = gr.Button("Préparer le plan", variant="primary", elem_id="plan-mission")
                    missions = gr.Dropdown(label="Missions sauvegardées", choices=[])
                    mission_result = gr.Markdown("Crée un plan de mission pour commencer.", sanitize_html=True)
                    status = gr.Radio(list(STATUSES), value=STATUSES[0], label="Ton suivi de mission")
                    save_status = gr.Button("Enregistrer le statut")
                    mission_status = gr.Markdown("")
                with gr.Tab("Mémoire"):
                    gr.Markdown("### Ce que Gaïrus doit retenir\nCes notes sont réutilisées comme contexte.")
                    memory_input = gr.Textbox(label="Information à retenir", lines=3)
                    save_memory = gr.Button("Mémoriser", variant="primary", elem_id="save-memory")
                    memories = gr.Markdown("Les informations retenues apparaîtront ici.", sanitize_html=True)
                    memory_status = gr.Markdown("")
        with gr.Accordion("Accès privé, gratuité et limites", open=False):
            gr.Markdown(
                f"Compte propriétaire : **{html.escape(OWNER)}**. Aucun mot de passe ni clé API à copier ici.\n\n"
                "Le modèle Qwen3-4B aide à rédiger, analyser, coder et planifier. "
                "Il ne navigue pas sur le web et ne modifie pas tes comptes.\n\n"
                "Calcul sur ZeroGPU gratuit, avec quota quotidien et attente possible. "
                "Le service peut se mettre en veille. Aucun abonnement ni crédit payant n'est activé.\n\n"
                "[Conditions et quotas ZeroGPU](https://huggingface.co/docs/hub/spaces-zerogpu)"
            )
        gr.Markdown(
            "Tes données restent dans ton dépôt privé Hugging Face. "
            "La création de plans n'autorise aucun achat ni envoi externe.",
            elem_id="privacy-note",
        )
        load_outputs = [connection, workspace, chatbox, thread_id, threads, memories, missions, mission_result, status]
        demo.load(load_workspace, inputs=[], outputs=load_outputs, api_visibility="private")
        send.click(
            chat, [prompt, thread_id], [prompt, chatbox, thread_id, threads, chat_status],
            api_visibility="private", concurrency_id="inference", concurrency_limit=1,
        )
        prompt.submit(
            chat, [prompt, thread_id], [prompt, chatbox, thread_id, threads, chat_status],
            api_visibility="private", concurrency_id="inference", concurrency_limit=1,
        )
        threads.input(open_thread, [threads], [chatbox, thread_id, chat_status], api_visibility="private")
        new.click(new_thread, [], [chatbox, thread_id, threads, chat_status], api_visibility="private")
        save_memory.click(
            remember, [memory_input], [memory_input, memories, memory_status],
            api_visibility="private",
        )
        plan.click(
            plan_mission, [mission_title, objective],
            [missions, mission_result, status, mission_status],
            api_visibility="private", concurrency_id="inference", concurrency_limit=1,
        )
        missions.input(open_mission, [missions], [mission_result, status], api_visibility="private")
        save_status.click(change_status, [missions, status], [mission_status], api_visibility="private")
        gr.api(
            service_chat, api_name="service_chat", api_visibility="undocumented",
            concurrency_id="inference", concurrency_limit=1,
        )
    return demo.queue(default_concurrency_limit=1, max_size=8)


if __name__ == "__main__":
    if os.getenv("SPACE_ID"):
        inference.initialize()
    build_demo().launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        show_error=False,
        footer_links=[],
        max_file_size="1mb",
        enable_monitoring=False,
        css_paths=Path(__file__).with_name("style.css"),
        theme=gr.themes.Base(
            primary_hue="blue", neutral_hue="slate",
            font=[gr.themes.GoogleFont("Public Sans"), "sans-serif"],
        ),
    )
