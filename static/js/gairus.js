(() => {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const API = {
        status: "/api/status",
        chat: "/api/chat",
        memory: "/api/memory",
        missions: "/api/missions",
        tasks: "/api/tasks",
        actions: "/api/actions",
        events: "/api/events",
        approvals: "/api/approvals"
    };

    const state = {
        isSending: false,
        autonomy: false,
        memory: true,
        tools: true,
        model: "auto",
        provider: null,
        modelUsed: null,
        conversationId: null
    };

    const messages = $("messages");
    const messageInput = $("messageInput");
    const sendButton = $("sendButton");
    const newChat = $("newChat");
    const autonomyToggle = $("autonomyToggle");
    const mobileMenu = $("mobileMenu");
    const sidebar = $("sidebar");
    const clearActivity = $("clearActivity");

    function addActivity(title, details = "") {
        const list = $("activityList");
        if (!list) return;

        const item = document.createElement("div");
        item.className = "activity-item";

        const strong = document.createElement("strong");
        strong.textContent = title;

        const span = document.createElement("span");
        span.textContent = details;

        item.appendChild(strong);
        item.appendChild(span);
        list.prepend(item);

        while (list.children.length > 30) {
            list.removeChild(list.lastChild);
        }
    }

    function addMessage(text, role = "assistant", meta = "") {
        if (!messages) return;

        const wrapper = document.createElement("div");
        wrapper.className = `message ${role}`;

        const content = document.createElement("div");
        content.className = "message-content";
        content.textContent = text;

        wrapper.appendChild(content);

        if (meta) {
            const metadata = document.createElement("small");
            metadata.className = "message-meta";
            metadata.textContent = meta;
            wrapper.appendChild(metadata);
        }

        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    function getReply(data) {
        if (!data) return "Le serveur n'a retourné aucune réponse.";

        return (
            data.reply ||
            data.message ||
            data.error ||
            "Réponse vide."
        );
    }

    async function apiFetch(url, options = {}) {
        const response = await fetch(url, {
            ...options,
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {})
            }
        });

        const text = await response.text();

        let data = {};

        try {
            data = text ? JSON.parse(text) : {};
        } catch {
            data = { raw: text };
        }

        if (!response.ok) {
            throw new Error(
                data.error ||
                data.message ||
                data.raw ||
                `Erreur HTTP ${response.status}`
            );
        }

        return data;
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

    function updateStatusUI(data = {}) {
        const values = {
            agentStatus: data.status || "online",
            systemStatus: data.status || "online",
            memoryStatus: "Active",
            autonomyStatus: data.autonomy ? "Active" : "En attente",
            providerStatus: state.provider || "Auto",
            modelStatus: state.modelUsed || "Auto"
        };

        Object.entries(values).forEach(([id, value]) => {
            const node = $(id);
            if (node) node.textContent = value;
        });
    }

    function buildRuntimePanel() {
        if ($("gairusRuntimePanel")) return;

        const panel = document.createElement("section");
        panel.id = "gairusRuntimePanel";
        panel.className = "gairus-runtime-panel";

        panel.innerHTML = `
            <div class="gairus-runtime-header">
                <strong>État de Gaïrus</strong>
                <span id="gairusRuntimeStatus">Connexion...</span>
            </div>

            <div class="gairus-runtime-grid">
                <div>
                    <small>Agent</small>
                    <strong id="runtimeAgent">Gaïrus</strong>
                </div>

                <div>
                    <small>Cerveau</small>
                    <strong id="runtimeBrain">Orchestrator</strong>
                </div>

                <div>
                    <small>Fournisseur</small>
                    <strong id="runtimeProvider">Auto</strong>
                </div>

                <div>
                    <small>Modèle</small>
                    <strong id="runtimeModel">Auto</strong>
                </div>

                <div>
                    <small>Missions</small>
                    <strong id="runtimeMissions">0</strong>
                </div>

                <div>
                    <small>Tâches</small>
                    <strong id="runtimeTasks">0</strong>
                </div>

                <div>
                    <small>Actions</small>
                    <strong id="runtimeActions">0</strong>
                </div>

                <div>
                    <small>Événements</small>
                    <strong id="runtimeEvents">0</strong>
                </div>
            </div>
        `;

        const target =
            document.querySelector(".messages")?.parentElement ||
            document.querySelector("main") ||
            document.body;

        target.appendChild(panel);
    }

    function updateRuntimePanel(data = {}) {
        const set = (id, value) => {
            const node = $(id);
            if (node) node.textContent = String(value ?? "");
        };

        set("gairusRuntimeStatus", data.status || "online");
        set("runtimeAgent", data.agent || "Gaïrus");
        set("runtimeBrain", data.brain || "orchestrator");
        set(
            "runtimeProvider",
            data.provider || state.provider || "Auto"
        );
        set(
            "runtimeModel",
            data.model || state.modelUsed || "Auto"
        );
    }

    async function loadStatus() {
        try {
            const data = await apiFetch(API.status);

            state.autonomy = Boolean(data.autonomy);

            if (autonomyToggle) {
                autonomyToggle.checked = state.autonomy;
            }

            updateStatusUI(data);
            updateRuntimePanel(data);

            addActivity(
                "Gaïrus en ligne",
                `${data.status || "online"}`
            );

            return data;
        } catch (error) {
            addActivity(
                "Statut indisponible",
                error.message
            );

            return null;
        }
    }

    async function sendMessage() {
        if (state.isSending || !messageInput) return;

        const text = messageInput.value.trim();
        if (!text) return;

        addMessage(text, "user");
        messageInput.value = "";

        setSending(true);

        addActivity(
            "Nouvelle demande",
            text
        );

        try {
            const data = await apiFetch(
                API.chat,
                {
                    method: "POST",
                    body: JSON.stringify({
                        message: text,
                        conversation_id: state.conversationId,
                        memory: state.memory,
                        tools: state.tools,
                        model: state.model
                    })
                }
            );

            state.provider = data.provider || null;
            state.modelUsed = data.model || null;

            const meta = [
                data.brain
                    ? `cerveau: ${data.brain}`
                    : "",
                data.provider
                    ? `fournisseur: ${data.provider}`
                    : "",
                data.model
                    ? `modèle: ${data.model}`
                    : ""
            ]
                .filter(Boolean)
                .join(" · ");

            addMessage(
                getReply(data),
                "assistant",
                meta
            );

            addActivity(
                "Réponse générée",
                [
                    data.brain || "orchestrator",
                    data.provider || "auto",
                    data.model || "auto"
                ].join(" · ")
            );

            updateRuntimePanel(data);

            await refreshAll();
        } catch (error) {
            addMessage(
                `Erreur : ${error.message}`,
                "assistant"
            );

            addActivity(
                "Erreur",
                error.message
            );
        } finally {
            setSending(false);

            if (messageInput) {
                messageInput.focus();
            }
        }
    }

    function resetChat() {
        if (!messages) return;

        messages.innerHTML = "";

        const welcome = document.createElement("div");
        welcome.id = "welcome";
        welcome.className = "welcome";

        welcome.innerHTML = `
            <h2>Gaïrus</h2>
            <p>Prêt. Donne-moi une mission.</p>
        `;

        messages.appendChild(welcome);

        state.conversationId = null;

        addActivity(
            "Nouvelle conversation",
            "Conversation réinitialisée"
        );
    }

    async function loadCollection(endpoint, label, renderer) {
        try {
            const data = await apiFetch(endpoint);

            const items =
                Array.isArray(data)
                    ? data
                    : (
                        data.items ||
                        data.data ||
                        []
                    );

            renderer(items);

            return items;
        } catch (error) {
            addActivity(
                `${label} indisponible`,
                error.message
            );

            renderer([]);

            return [];
        }
    }

    function renderSimpleList(id, items, emptyText, titleFields) {
        const node = $(id);
        if (!node) return;

        node.innerHTML = "";

        if (!items.length) {
            node.innerHTML = `<span>${emptyText}</span>`;
            return;
        }

        items.slice(0, 30).forEach(item => {
            const el = document.createElement("div");
            el.className = "gairus-list-item";

            const title = document.createElement("strong");

            let value = "";

            for (const field of titleFields) {
                if (item[field]) {
                    value = item[field];
                    break;
                }
            }

            title.textContent =
                value ||
                `Élément #${item.id ?? ""}`;

            const status = document.createElement("span");

            status.textContent =
                item.status ||
                item.result ||
                item.details ||
                "";

            el.appendChild(title);
            el.appendChild(status);

            node.appendChild(el);
        });
    }

    function renderMissions(items) {
        renderSimpleList(
            "missionsList",
            items,
            "Aucune mission.",
            ["title", "name", "description"]
        );

        const node = $("runtimeMissions");
        if (node) node.textContent = items.length;
    }

    function renderTasks(items) {
        renderSimpleList(
            "tasksList",
            items,
            "Aucune tâche.",
            ["title", "name", "description"]
        );

        const node = $("runtimeTasks");
        if (node) node.textContent = items.length;
    }

    function renderActions(items) {
        renderSimpleList(
            "actionsList",
            items,
            "Aucune action.",
            ["action", "name", "title"]
        );

        const node = $("runtimeActions");
        if (node) node.textContent = items.length;
    }

    function renderEvents(items) {
        renderSimpleList(
            "eventsList",
            items,
            "Aucun événement.",
            ["event", "type", "title"]
        );

        const node = $("runtimeEvents");
        if (node) node.textContent = items.length;
    }

    function renderApprovals(items) {
        renderSimpleList(
            "approvalsList",
            items,
            "Aucune approbation en attente.",
            ["action", "title", "name"]
        );
    }

    async function refreshMemory() {
        return loadCollection(
            API.memory,
            "Mémoire",
            items => {
                renderSimpleList(
                    "memoryList",
                    items,
                    "Aucune mémoire.",
                    ["content", "memory", "title", "name"]
                );
            }
        );
    }

    async function refreshAll() {
        await Promise.all([
            loadCollection(
                API.missions,
                "Missions",
                renderMissions
            ),
            loadCollection(
                API.tasks,
                "Tâches",
                renderTasks
            ),
            loadCollection(
                API.actions,
                "Actions",
                renderActions
            ),
            loadCollection(
                API.events,
                "Événements",
                renderEvents
            ),
            loadCollection(
                API.approvals,
                "Approbations",
                renderApprovals
            )
        ]);
    }

    async function saveMemory() {
        const input =
            $("memoryInput") ||
            $("memoryText");

        if (!input || !input.value.trim()) return;

        try {
            await apiFetch(
                API.memory,
                {
                    method: "POST",
                    body: JSON.stringify({
                        content: input.value.trim()
                    })
                }
            );

            input.value = "";

            addActivity(
                "Mémoire enregistrée",
                "Nouvelle mémoire ajoutée"
            );

            await refreshMemory();
        } catch (error) {
            addActivity(
                "Erreur mémoire",
                error.message
            );
        }
    }

    function bindEvents() {
        if (sendButton) {
            sendButton.addEventListener(
                "click",
                sendMessage
            );
        }

        if (messageInput) {
            messageInput.addEventListener(
                "keydown",
                event => {
                    if (
                        event.key === "Enter" &&
                        !event.shiftKey
                    ) {
                        event.preventDefault();
                        sendMessage();
                    }
                }
            );
        }

        if (newChat) {
            newChat.addEventListener(
                "click",
                resetChat
            );
        }

        if (autonomyToggle) {
            autonomyToggle.addEventListener(
                "change",
                () => {
                    state.autonomy =
                        autonomyToggle.checked;

                    addActivity(
                        "Autonomie",
                        state.autonomy
                            ? "Demandée"
                            : "Désactivée"
                    );
                }
            );
        }

        if (clearActivity) {
            clearActivity.addEventListener(
                "click",
                () => {
                    const list = $("activityList");
                    if (list) list.innerHTML = "";
                }
            );
        }

        if (mobileMenu && sidebar) {
            mobileMenu.addEventListener(
                "click",
                () => {
                    sidebar.classList.toggle("open");
                }
            );
        }

        const memoryButton =
            $("saveMemory") ||
            $("memorySaveButton");

        if (memoryButton) {
            memoryButton.addEventListener(
                "click",
                saveMemory
            );
        }
    }

    function installRuntimeStyle() {
        if ($("gairusRuntimeStyle")) return;

        const style = document.createElement("style");
        style.id = "gairusRuntimeStyle";

        style.textContent = `
            .gairus-runtime-panel {
                margin: 16px;
                padding: 16px;
                border-radius: 16px;
                background: rgba(255,255,255,.04);
                border: 1px solid rgba(255,255,255,.08);
            }

            .gairus-runtime-header {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                margin-bottom: 14px;
            }

            .gairus-runtime-grid {
                display: grid;
                grid-template-columns:
                    repeat(auto-fit,minmax(120px,1fr));
                gap: 10px;
            }

            .gairus-runtime-grid > div {
                padding: 10px;
                border-radius: 12px;
                background: rgba(255,255,255,.03);
            }

            .gairus-runtime-grid small,
            .gairus-runtime-grid strong {
                display: block;
            }

            .gairus-runtime-grid small {
                opacity: .6;
                margin-bottom: 4px;
            }

            .gairus-runtime-grid strong {
                overflow-wrap: anywhere;
            }

            .gairus-list-item {
                display: flex;
                justify-content: space-between;
                gap: 12px;
                padding: 8px 0;
            }

            .gairus-list-item span {
                opacity: .65;
                text-align: right;
            }
        `;

        document.head.appendChild(style);
    }

    async function init() {
        installRuntimeStyle();
        buildRuntimePanel();
        bindEvents();

        await loadStatus();
        await refreshMemory();
        await refreshAll();

        addActivity(
            "Interface prête",
            "Gaïrus est connecté au backend"
        );
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            init
        );
    } else {
        init();
    }
})();
