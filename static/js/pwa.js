/* Installation is independent from login; credentials and tasks stay out of caches. */
(() => {
  "use strict";
  const panel = document.querySelector("#pwaPanel");
  const status = document.querySelector("#pwaStatus");
  const install = document.querySelector("#pwaInstall");
  const update = document.querySelector("#pwaUpdate");
  const help = document.querySelector("#pwaHelp");
  let installPrompt = null;
  let registration = null;
  let updating = false;
  let lastCheck = 0;
  let wasControlled = false;

  function measure() {
    document.documentElement.style.setProperty(
      "--pwa-height", `${panel.getBoundingClientRect().height}px`
    );
  }
  function standalone() {
    return matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  }
  function installed() {
    install.hidden = true;
    help.hidden = true;
    status.textContent = "Gaïrus · Application installée";
    measure();
  }
  function readyUpdate() {
    update.hidden = false;
    status.textContent = "Mise à jour prête. Actualiser effacera le texte non envoyé.";
    measure();
  }

  window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    installPrompt = event;
    install.hidden = false;
  });
  window.addEventListener("appinstalled", installed);
  install.addEventListener("click", async () => {
    if (!installPrompt) {
      help.hidden = !help.hidden;
      install.setAttribute("aria-expanded", String(!help.hidden));
      measure();
      return;
    }
    const prompt = installPrompt;
    installPrompt = null;
    try {
      await prompt.prompt();
      const choice = await prompt.userChoice;
      if (choice.outcome !== "accepted") {
        status.textContent = "Installation annulée. Gaïrus reste accessible sur le web.";
      }
    } catch {
      help.hidden = false;
    }
    measure();
  });
  update.addEventListener("click", () => {
    updating = true;
    update.disabled = true;
    if (registration?.waiting) {
      registration.waiting.postMessage({type:"GAIRUS_ACTIVATE_UPDATE"});
    } else {
      window.location.reload();
    }
  });

  function networkStatus() {
    if (!navigator.onLine) {
      status.textContent = "Hors connexion. Aucune tâche n’est envoyée ou exécutée.";
    } else if (!update.hidden) {
      readyUpdate();
    } else {
      status.textContent = standalone()
        ? "Gaïrus · Application installée"
        : "Gaïrus · Web et écran d’accueil, à la même adresse";
    }
    measure();
  }
  window.addEventListener("online", networkStatus);
  window.addEventListener("offline", networkStatus);
  window.addEventListener("resize", measure);
  if ("ResizeObserver" in window) new ResizeObserver(measure).observe(panel);
  if (standalone()) installed();
  networkStatus();

  // Sandboxed previews cannot install a PWA; the direct HTTPS app can.
  if (window.top !== window.self || !window.isSecureContext ||
      !("serviceWorker" in navigator)) {
    help.textContent = "Ouvrez l’adresse directe de Gaïrus dans votre navigateur pour l’ajouter à l’écran d’accueil.";
    return;
  }
  wasControlled = Boolean(navigator.serviceWorker.controller);
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (updating) {
      updating = false;
      window.location.reload();
    } else if (wasControlled) {
      readyUpdate();
    }
    wasControlled = true;
  });
  navigator.serviceWorker.register("/sw.js", {scope:"/", updateViaCache:"none"})
    .then(reg => {
      registration = reg;
      if (reg.waiting) readyUpdate();
      reg.addEventListener("updatefound", () => {
        const worker = reg.installing;
        if (!worker) return;
        worker.addEventListener("statechange", () => {
          if (worker.state === "installed" && reg.waiting &&
              navigator.serviceWorker.controller) readyUpdate();
        });
      });
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && Date.now() - lastCheck > 60000) {
          lastCheck = Date.now();
          reg.update().catch(() => {});
        }
      });
    }).catch(() => {
      status.textContent = "Gaïrus reste accessible sur le web. L’installation n’est pas disponible dans ce navigateur.";
      measure();
    });
})();
