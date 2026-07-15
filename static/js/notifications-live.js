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

    connect();

    // Aplica um reload pendente assim que a pessoa parar de interagir.
    document.addEventListener("mouseup", () => window.setTimeout(maybeReloadBoard, 300));
    window.setInterval(maybeReloadBoard, 3000);
})();
