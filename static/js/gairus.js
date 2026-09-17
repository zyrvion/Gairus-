const GAIRUS_API = "/api/chat";

const state = {
    isSending: false,
    autonomy: false,
    memory: true,
    tools: true,
    model: "auto"
};

const $ = (id) => document.getElementById(id);

const messages = $("messages");
const messageInput = $("messageInput");
const sendButton = $("sendButton");
const newChat = $("newChat");
const modelSelect = $("modelSelect");
const memoryToggle = $("memoryToggle");
const toolsToggle = $("toolsToggle");
const autonomyToggle = $("autonomyToggle");
const activityList = $("activityList");
const clearActivity = $("clearActivity");
const mobileMenu = $("mobileMenu");
const closePanel = $("closePanel");
const sidebar = $("sidebar");
const overlay = $("overlay");

function addActivity(title, description) {
    if (!activityList) return;

    const item = document.createElement("div");
    item.className = "activity-item";
    item.innerHTML = `
        <strong>${escapeHtml(title)}</strong>
        <span>${escapeHtml(description)}</span>
    `;

    activityList.prepend(item);

    while (activityList.children.length > 20) {
        activityList.removeChild(activityList.lastChild);
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function scrollMessages() {
    if (messages) {
        messages.scrollTop = messages.scrollHeight;
    }
}

function addMessage(text, role) {
    if (!messages) return;

    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const content = document.createElement("div");
    content.className = "message-content";
    content.textContent = text;

    wrapper.appendChild(content);
    messages.appendChild(wrapper);
    scrollMessages();
}

function clearWelcome() {
    const welcome = $("welcome");
    if (welcome) welcome.remove();
}

function setSending(value) {
    state.isSending = value;

    if (sendButton) {
        sendButton.disabled = value;
        sendButton.style.opacity = value ? "0.6" : "1";
    }

    if (messageInput) {
        messageInput.disabled = value;
    }
}

function getReply(data) {
    if (!data) return "Le serveur n'a retourné aucune réponse.";

    return (
        data.reply ||
        data.response ||
        data.message ||
        data.answer ||
        data.content ||
        "Réponse vide du serveur."
    );
}

async function sendMessage() {
    if (!messageInput || state.isSending) return;

    const text = messageInput.value.trim();
    if (!text) return;

    clearWelcome();
    addMessage(text, "user");
    messageInput.value = "";
    setSending(true);
    addActivity("Message envoyé", "Connexion au backend Gaïrus");

    try {
        const response = await fetch(GAIRUS_API, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            body: JSON.stringify({
                message: text
            })
        });

        const rawText = await response.text();
        let data;

        try {
            data = JSON.parse(rawText);
        } catch {
            throw new Error(`Réponse serveur invalide : ${rawText.slice(0, 160)}`);
        }

        if (!response.ok) {
            throw new Error(data.error || data.reply || `Erreur HTTP ${response.status}`);
        }

        addMessage(getReply(data), "assistant");
        addActivity("Réponse reçue", "Gaïrus a répondu");
    } catch (error) {
        addMessage(
            `Connexion impossible : ${error.message}`,
            "assistant"
        );
        addActivity("Erreur", error.message);
    } finally {
        setSending(false);
        if (messageInput) messageInput.focus();
    }
}

function startNewConversation() {
    if (messages) messages.innerHTML = "";

    const welcome = document.createElement("div");
    welcome.id = "welcome";
    welcome.className = "welcome";
    welcome.innerHTML = `
        <h2>Bonjour, je suis Gaïrus.</h2>
        <p>Comment puis-je vous aider aujourd'hui ?</p>
    `;

    if (messages) messages.appendChild(welcome);

    addActivity("Nouvelle conversation", "Espace de discussion réinitialisé");
    if (messageInput) messageInput.focus();
}

function updateStatus(id, enabled, activeText, inactiveText) {
    const element = $(id);
    if (!element) return;

    element.textContent = enabled ? activeText : inactiveText;
    element.classList.toggle("active", enabled);
}

function toggleSidebar(open) {
    if (sidebar) sidebar.classList.toggle("open", open);
    if (overlay) overlay.classList.toggle("visible", open);
}

if (sendButton) {
    sendButton.addEventListener("click", sendMessage);
}

if (messageInput) {
    messageInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
}

if (newChat) {
    newChat.addEventListener("click", startNewConversation);
}

if (modelSelect) {
    modelSelect.addEventListener("change", () => {
        state.model = modelSelect.value;
        updateStatus("modelStatus", true, state.model, "Auto");
        addActivity("Modèle", `Modèle sélectionné : ${state.model}`);
    });
}

if (memoryToggle) {
    memoryToggle.addEventListener("change", () => {
        state.memory = memoryToggle.checked;
        updateStatus("memoryStatus", state.memory, "Activée", "Désactivée");
        addActivity(
            "Mémoire",
            state.memory ? "Mémoire activée" : "Mémoire désactivée"
        );
    });
}

if (toolsToggle) {
    toolsToggle.addEventListener("change", () => {
        state.tools = toolsToggle.checked;
        updateStatus("toolStatus", state.tools, "Activés", "Désactivés");
        addActivity(
            "Outils",
            state.tools ? "Outils activés" : "Outils désactivés"
        );
    });
}

if (autonomyToggle) {
    autonomyToggle.addEventListener("change", () => {
        state.autonomy = autonomyToggle.checked;
        addActivity(
            "Autonomie",
            state.autonomy ? "Mode autonome activé" : "Mode autonome désactivé"
        );
    });
}

if (clearActivity) {
    clearActivity.addEventListener("click", () => {
        if (activityList) activityList.innerHTML = "";
    });
}

if (mobileMenu) {
    mobileMenu.addEventListener("click", () => {
        toggleSidebar(true);
    });
}

if (closePanel) {
    closePanel.addEventListener("click", () => {
        toggleSidebar(false);
    });
}

if (overlay) {
    overlay.addEventListener("click", () => {
        toggleSidebar(false);
    });
}

const quickButtons = document.querySelectorAll(
    "[data-message], [data-prompt], [data-action]"
);

quickButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const value =
            button.dataset.message ||
            button.dataset.prompt ||
            button.dataset.action;

        if (!value || !messageInput) return;

        messageInput.value = value;
        messageInput.focus();
    });
});

addActivity("Interface prête", "Gaïrus est connecté au backend Render");
