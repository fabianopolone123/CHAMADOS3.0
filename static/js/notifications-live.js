/* Notificacoes em tempo real (SSE).
 * Recebe os eventos de chamado empurrados pelo servidor (/notificacoes/stream/)
 * e mostra um popup; quando o evento mexe no quadro e a pessoa esta no Kanban,
 * atualiza a tela (respeitando arrasto/modal aberto). */
(function () {
    if (document.body.dataset.ti !== "1") {
        return;
    }
    const url = window.NOTIFICACOES_STREAM_URL;
    if (!url || typeof EventSource === "undefined") {
        return;
    }

    let pendingBoardReload = false;

    // ---- Permissao de notificacao do navegador (Web Notifications API) ----
    const BELL = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path></svg>';
    const BELL_OFF = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.73 21a2 2 0 0 1-3.46 0"></path><path d="M18.63 13A17.9 17.9 0 0 1 18 8"></path><path d="M6.26 6.26A5.86 5.86 0 0 0 6 8c0 7-3 9-3 9h14"></path><path d="M18 8a6 6 0 0 0-9.33-5"></path><path d="m2 2 20 20"></path></svg>';

    function nativeState() {
        if (typeof Notification === "undefined") {
            return "unsupported"; // contexto inseguro (HTTP) ou navegador sem suporte
        }
        return Notification.permission; // granted | denied | default
    }

    function renderPermBtn() {
        const btn = document.getElementById("notifPermBtn");
        if (!btn) {
            return;
        }
        const st = nativeState();
        btn.classList.remove("notif-perm-btn--on", "notif-perm-btn--off", "notif-perm-btn--ask");
        if (st === "granted") {
            btn.innerHTML = BELL;
            btn.classList.add("notif-perm-btn--on");
            btn.title = "Notificacoes do navegador ativas";
        } else if (st === "default") {
            btn.innerHTML = BELL_OFF;
            btn.classList.add("notif-perm-btn--ask");
            btn.title = "Clique para ativar as notificacoes do navegador";
        } else if (st === "denied") {
            btn.innerHTML = BELL_OFF;
            btn.classList.add("notif-perm-btn--off");
            btn.title = "Notificacoes bloqueadas — libere nas configuracoes do navegador (cadeado do site)";
        } else {
            btn.innerHTML = BELL_OFF;
            btn.classList.add("notif-perm-btn--off");
            btn.title = "Notificacoes do navegador indisponiveis (requer HTTPS). Os avisos aparecem na tela.";
        }
    }

    function bindPermBtn() {
        const btn = document.getElementById("notifPermBtn");
        if (!btn) {
            return;
        }
        btn.addEventListener("click", () => {
            const st = nativeState();
            if (st === "granted") {
                if (window.showAppToast) window.showAppToast("Notificacoes do navegador ja estao ativas.", "success");
            } else if (st === "default") {
                Notification.requestPermission().then(renderPermBtn);
            } else if (st === "denied") {
                if (window.showAppToast) window.showAppToast("As notificacoes estao bloqueadas. Libere no cadeado do site > Notificacoes.", "warning");
            } else {
                if (window.showAppToast) window.showAppToast("Notificacoes do navegador precisam de HTTPS. Os avisos continuam aparecendo na tela.", "info");
            }
        });
    }

    function notifyNative(title, body, numero) {
        if (nativeState() !== "granted") {
            return;
        }
        try {
            new Notification(title, { body: body, tag: "ch-" + numero });
        } catch (_) {
            /* ignora */
        }
    }

    function onKanban() {
        return document.querySelector(".kanban-page") !== null;
    }

    function boardBusy() {
        // Nao recarrega no meio de um arrasto ou com algum modal aberto.
        return window.__kanbanDragging === true || document.querySelector(".modal.show") !== null;
    }

    function maybeReloadBoard() {
        if (pendingBoardReload && onKanban() && !boardBusy()) {
            pendingBoardReload = false;
            window.location.reload();
        }
    }

    function handleEvent(ev) {
        const numero = ev.numero || "Chamado";
        const msg = `${numero}: ${ev.descricao || ""}`.trim();
        if (typeof window.showAppToast === "function") {
            window.showAppToast(msg, "info", { title: ev.titulo || "Atualizacao de chamado", timeout: 9000 });
        }
        notifyNative(`${numero} - ${ev.titulo || "Chamado"}`, ev.descricao || "", numero);
        if (ev.board && onKanban()) {
            pendingBoardReload = true;
        }
        maybeReloadBoard();
    }

    function connect() {
        const es = new EventSource(url);
        es.onmessage = (event) => {
            let data;
            try {
                data = JSON.parse(event.data);
            } catch (_) {
                return;
            }
            handleEvent(data);
        };
        es.onerror = () => {
            // O EventSource reconecta sozinho (retry definido pelo servidor).
        };
    }

    renderPermBtn();
    bindPermBtn();
    connect();

    // Aplica um reload pendente assim que a pessoa parar de interagir.
    document.addEventListener("mouseup", () => window.setTimeout(maybeReloadBoard, 300));
    window.setInterval(maybeReloadBoard, 3000);
})();
