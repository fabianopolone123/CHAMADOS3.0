(function () {
    const ATTENDANCE_MODAL_ID = "attendanceActionModal";
    const ATTENDANCE_FORM_ID = "attendanceActionForm";
    const CARD_SELECTOR = ".ticket-card[data-ticket-number]";
    const LIST_SELECTOR = ".js-ticket-list";
    const PENDENCIA_LIST_SELECTOR = ".js-pendencia-list";
    const PENDENCIA_CARD_SELECTOR = ".pendencia-card[data-pendencia-id]";
    const ACTION_SELECTOR = "[data-ticket-action]";

    const appElement = document.querySelector(".tickets-app");
    const attendanceModalElement = document.getElementById(ATTENDANCE_MODAL_ID);
    const attendanceForm = document.getElementById(ATTENDANCE_FORM_ID);

    if (!appElement || !attendanceModalElement || !attendanceForm || typeof bootstrap === "undefined") {
        return;
    }

    const startAttendanceUrl = appElement.dataset.startAttendanceUrl;
    const finishAttendanceUrl = appElement.dataset.finishAttendanceUrl;
    const moveTicketUrl = appElement.dataset.moveTicketUrl;

    let dragInProgress = false;
    let activeTicketNumber = null;
    let timerIntervalId = null;

    const attendanceModal = bootstrap.Modal.getOrCreateInstance(attendanceModalElement);

    const attendanceFields = {
        ticketLabel: document.getElementById("attendanceModalTicketLabel"),
        actionLabel: document.getElementById("attendanceModalActionLabel"),
        ticketNumber: document.getElementById("attendanceModalTicketNumber"),
        action: document.getElementById("attendanceModalAction"),
        description: document.getElementById("attendanceModalDescription"),
        submit: document.getElementById("attendanceModalSubmit"),
    };

    function showToast(message, type) {
        if (typeof window.showAppToast === "function") {
            window.showAppToast(message, type);
        }
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function formatDurationFromSeconds(totalSeconds) {
        const safeSeconds = Math.max(Number(totalSeconds) || 0, 0);
        const hours = Math.floor(safeSeconds / 3600);
        const minutes = Math.floor((safeSeconds % 3600) / 60);
        const seconds = safeSeconds % 60;

        if (hours > 0) {
            return `${hours}h ${String(minutes).padStart(2, "0")}m`;
        }
        if (minutes > 0) {
            return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
        }
        return `${seconds}s`;
    }

    function getTicketCard(ticketNumber) {
        return document.querySelector(`.ticket-card[data-ticket-number="${ticketNumber}"]`);
    }

    function setCardActiveState(card, startedAtIso) {
        if (!card) {
            return;
        }

        card.classList.add("ticket-card--active");
        card.dataset.ticketActive = "true";
        card.dataset.ticketStartedAt = startedAtIso || "";

        const state = card.querySelector("[data-ticket-state]");
        const timer = card.querySelector("[data-ticket-timer]");
        const playButton = card.querySelector('[data-ticket-action="play"]');
        const pauseButton = card.querySelector('[data-ticket-action="pause"]');
        const stopButton = card.querySelector('[data-ticket-action="stop"]');

        if (state) {
            state.textContent = "Em atendimento";
            state.classList.add("ticket-attendance-indicator--active");
        }
        if (timer) {
            timer.classList.remove("is-hidden");
        }
        if (playButton) {
            playButton.classList.add("is-hidden");
        }
        if (pauseButton) {
            pauseButton.classList.remove("is-hidden");
        }
        if (stopButton) {
            stopButton.classList.remove("is-hidden");
        }
    }

    function setCardInactiveState(card, labelText) {
        if (!card) {
            return;
        }

        card.classList.remove("ticket-card--active");
        card.dataset.ticketActive = "false";
        card.dataset.ticketStartedAt = "";

        const state = card.querySelector("[data-ticket-state]");
        const timer = card.querySelector("[data-ticket-timer]");
        const playButton = card.querySelector('[data-ticket-action="play"]');
        const pauseButton = card.querySelector('[data-ticket-action="pause"]');
        const stopButton = card.querySelector('[data-ticket-action="stop"]');

        if (state) {
            state.textContent = labelText || "Pronto para iniciar";
            state.classList.remove("ticket-attendance-indicator--active");
        }
        if (timer) {
            timer.classList.add("is-hidden");
            timer.textContent = "0m";
        }
        if (playButton) {
            playButton.classList.remove("is-hidden");
        }
        if (pauseButton) {
            pauseButton.classList.add("is-hidden");
        }
        if (stopButton) {
            stopButton.classList.add("is-hidden");
        }
    }

    function startTimerLoop() {
        if (timerIntervalId) {
            window.clearInterval(timerIntervalId);
        }

        timerIntervalId = window.setInterval(() => {
            const activeCards = document.querySelectorAll('.ticket-card[data-ticket-active="true"]');
            activeCards.forEach((card) => {
                const startedAt = card.dataset.ticketStartedAt;
                const timer = card.querySelector("[data-ticket-timer]");
                if (!startedAt || !timer) {
                    return;
                }

                const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
                timer.textContent = formatDurationFromSeconds(seconds);
            });
        }, 1000);
    }

    function syncInitialActiveState() {
        const activeCard = document.querySelector('.ticket-card[data-ticket-active="true"]');
        activeTicketNumber = activeCard ? activeCard.dataset.ticketNumber : null;
        startTimerLoop();
    }

    function incrementClosedCount() {
        const el = document.querySelector("[data-closed-count]");
        if (el) {
            el.textContent = (parseInt(el.textContent, 10) || 0) + 1;
        }
    }

    function updateColumnCounts() {
        document.querySelectorAll(".kanban-column").forEach((column) => {
            const list = column.querySelector(LIST_SELECTOR);
            const countEl = column.querySelector(".column-count");
            if (list && countEl) {
                countEl.textContent = list.querySelectorAll(".ticket-card").length;
            }
        });
    }

    // Mantem a mensagem de coluna vazia coerente: remove quando ha cards e
    // recria (a partir de data-empty-text) quando a coluna fica sem cards.
    function syncListEmptyState(list) {
        if (!list) {
            return;
        }
        const hasCards = list.querySelector(".ticket-card") !== null;
        let emptyEl = list.querySelector(".kanban-empty");

        if (hasCards) {
            if (emptyEl) {
                emptyEl.remove();
            }
            return;
        }

        if (!emptyEl) {
            emptyEl = document.createElement("p");
            emptyEl.className = "kanban-empty";
            emptyEl.textContent = list.dataset.emptyText || "Nenhum chamado nesta coluna.";
            list.appendChild(emptyEl);
        }
    }

    // Recalcula o estado de vazio de todas as colunas, inclusive a de Pendencias.
    function refreshEmptyStates() {
        document
            .querySelectorAll(`${LIST_SELECTOR}, ${PENDENCIA_LIST_SELECTOR}`)
            .forEach(syncListEmptyState);
    }

    async function sendJson(url, payload) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify(payload),
        });

        let data = {};
        try {
            data = await response.json();
        } catch (error) {
            data = { ok: false, message: "Resposta inesperada do servidor." };
        }

        if (!response.ok || data.ok === false) {
            throw data;
        }

        return data;
    }

    function openAttendanceModal(ticketNumber, action) {
        const card = getTicketCard(ticketNumber);
        const title = card ? card.dataset.ticketTitle : "Chamado";
        const actionLabel = action === "pause" ? "Pause" : "Stop";

        attendanceFields.ticketNumber.value = ticketNumber;
        attendanceFields.action.value = action;
        attendanceFields.ticketLabel.textContent = `${ticketNumber} | ${title}`;
        attendanceFields.actionLabel.textContent = actionLabel;
        attendanceFields.description.value = "";
        attendanceFields.submit.textContent = action === "pause" ? "Enviar pausa" : "Finalizar chamado";

        attendanceModal.show();
        window.setTimeout(() => attendanceFields.description.focus(), 180);
    }

    async function handlePlay(ticketNumber) {
        const card = getTicketCard(ticketNumber);
        if (!card) {
            return;
        }

        const previous = activeTicketNumber;
        try {
            const result = await sendJson(startAttendanceUrl, { ticket_number: ticketNumber });
            // Troca de atendimento: o card anterior foi pausado no backend; reflete na tela.
            if (previous && previous !== ticketNumber) {
                const prevCard = getTicketCard(previous);
                if (prevCard) {
                    setCardInactiveState(prevCard, "Pausado");
                }
            }
            activeTicketNumber = ticketNumber;
            setCardActiveState(card, result.attendance.started_at_iso);
            startTimerLoop();
            showToast(result.message || "Atendimento iniciado com sucesso.", "success");
        } catch (error) {
            if (error.active_ticket_number) {
                activeTicketNumber = error.active_ticket_number;
            }
            showToast(error.message || "Nao foi possivel iniciar o atendimento.", "error");
        }
    }

    async function handleAttendanceSubmit(event) {
        event.preventDefault();

        const ticketNumber = attendanceFields.ticketNumber.value.trim();
        const action = attendanceFields.action.value.trim();
        const description = attendanceFields.description.value.trim();

        if (!description) {
            showToast("Descreva o que foi feito neste atendimento.", "warning");
            attendanceFields.description.focus();
            return;
        }

        attendanceFields.submit.disabled = true;

        try {
            const result = await sendJson(finishAttendanceUrl, {
                ticket_number: ticketNumber,
                action,
                description,
            });

            const card = getTicketCard(ticketNumber);
            activeTicketNumber = null;
            setCardInactiveState(card, action === "pause" ? "Pausado" : "Atendimento encerrado");

            // Stop encerra o chamado: o card sai da coluna do atendente. A coluna
            // "Chamados fechados" e apenas um resumo (consulta pela busca/modal),
            // por isso removemos o card e so incrementamos a contagem de fechados.
            if (action === "stop" && result.ticket_closed && card) {
                card.remove();
                incrementClosedCount();
                updateColumnCounts();
                refreshEmptyStates();
            }

            attendanceModal.hide();
            showToast(result.message || "Atendimento registrado com sucesso.", "success");
        } catch (error) {
            if (error.active_ticket_number) {
                activeTicketNumber = error.active_ticket_number;
            }
            showToast(error.message || "Nao foi possivel registrar o atendimento.", "error");
        } finally {
            attendanceFields.submit.disabled = false;
        }
    }

    const STATUS_BADGE_CLASSES = [
        "status-info",
        "status-warning",
        "status-muted",
        "status-success",
        "status-neutral",
        "status-danger",
    ];

    function applyBadgeState(card, statusLabel, statusClass) {
        const badge = card.querySelector("[data-status-badge]");
        if (!badge) {
            return;
        }
        if (statusLabel) {
            badge.textContent = statusLabel;
        }
        if (statusClass) {
            badge.classList.remove(...STATUS_BADGE_CLASSES);
            badge.classList.add(statusClass);
        }
    }

    function applyAttendantState(card, attendantName) {
        const row = card.querySelector("[data-attendant-row]");
        const value = card.querySelector("[data-current-attendant]");
        if (value) {
            value.textContent = attendantName || "";
        }
        if (row) {
            row.classList.toggle("is-hidden", !attendantName);
        }
    }

    async function persistMove(payload, event) {
        const card = event.item;
        try {
            const result = await sendJson(moveTicketUrl, payload);
            applyBadgeState(card, result.status_label, result.status_class);
            applyAttendantState(card, result.atendente_atual);
            updateColumnCounts();
            refreshEmptyStates();
            showToast(result.message || "Chamado movido.", "success");
        } catch (error) {
            // reverte a movimentacao visual em caso de falha
            const origin = event.from;
            const reference = origin.children[event.oldIndex] || null;
            origin.insertBefore(card, reference);
            updateColumnCounts();
            refreshEmptyStates();
            showToast(error.message || "Nao foi possivel movimentar o chamado.", "error");
        }
    }

    function isPendenciaEl(el) {
        return !!(el && el.dataset && el.dataset.pendenciaId);
    }

    // Regras de destino do drag: pendencia so vai para coluna de atendente;
    // chamado normal nao pode entrar na coluna de pendencias.
    function canDrop(dragged, toList) {
        if (!toList || !toList.dataset) {
            return false;
        }
        const toType = toList.dataset.columnType;
        if (isPendenciaEl(dragged)) {
            return toType === "atendente" || toType === "pendencia";
        }
        return toType !== "pendencia";
    }

    function handleTicketDrop(event) {
        const ticketNumber = event.item.dataset.ticketNumber;
        const target = event.to.dataset.columnType;
        const attendantId = event.to.dataset.attendantId;
        const fromAttendantId = event.from.dataset.attendantId;

        if (!ticketNumber || !target) {
            return;
        }
        if (event.from === event.to) {
            return;
        }

        // O fechamento so acontece via Stop: bloqueia o drop direto em "Chamados
        // fechados", devolvendo o card para a coluna de origem com uma mensagem.
        if (target === "fechado") {
            const card = event.item;
            const origin = event.from;
            const reference = origin.children[event.oldIndex] || null;
            origin.insertBefore(card, reference);
            updateColumnCounts();
            refreshEmptyStates();
            showToast("Para fechar o chamado, inicie o atendimento e finalize usando o botao Stop.", "warning");
            return;
        }

        if (target === "atendente" && attendantId === fromAttendantId) {
            return;
        }

        const payload = { ticket_number: ticketNumber, target: target };
        if (target === "atendente") {
            payload.attendant_id = attendantId;
        }

        // Atualiza o estado de vazio na hora (otimista); o POST confirma ou reverte.
        refreshEmptyStates();
        persistMove(payload, event);
    }

    function handlePendenciaDrop(event) {
        const target = event.to.dataset.columnType;
        // So converte quando cai em uma coluna de atendente (regra tambem no backend).
        if (event.from === event.to || target !== "atendente") {
            return;
        }
        const pendenciaId = event.item.dataset.pendenciaId;
        const attendantId = event.to.dataset.attendantId;
        refreshEmptyStates();
        convertPendencia(pendenciaId, attendantId, event);
    }

    function handleDragEnd(event) {
        window.setTimeout(() => {
            dragInProgress = false;
        }, 0);

        if (isPendenciaEl(event.item)) {
            handlePendenciaDrop(event);
            return;
        }
        handleTicketDrop(event);
    }

    function initializeDragAndDrop() {
        if (typeof Sortable === "undefined") {
            return;
        }

        const lists = document.querySelectorAll(`${LIST_SELECTOR}, ${PENDENCIA_LIST_SELECTOR}`);
        lists.forEach((listElement) => {
            Sortable.create(listElement, {
                group: "tickets-board",
                animation: 180,
                ghostClass: "ticket-card-ghost",
                chosenClass: "ticket-card-chosen",
                dragClass: "ticket-card-drag",
                filter: "button, textarea",
                preventOnFilter: false,
                onMove: (evt) => canDrop(evt.dragged, evt.to),
                onStart: () => {
                    dragInProgress = true;
                },
                onEnd: handleDragEnd,
            });
        });
    }

    async function convertPendencia(pendenciaId, attendantId, event) {
        const card = event.item;
        const convertUrl = card.dataset.convertUrl;
        try {
            const result = await sendJson(convertUrl, { attendant_id: attendantId });
            // Remove o card de pendencia e insere o card do novo chamado na coluna destino.
            card.remove();
            const wrapper = document.createElement("div");
            wrapper.innerHTML = (result.card_html || "").trim();
            const newCard = wrapper.firstElementChild;
            if (newCard) {
                event.to.appendChild(newCard);
                bindCard(newCard);
            }
            updateColumnCounts();
            refreshEmptyStates();
            showToast(result.message || "Pendencia convertida em chamado.", "success");
        } catch (error) {
            // Reverte a pendencia para a coluna original.
            const origin = event.from;
            const reference = origin.children[event.oldIndex] || null;
            origin.insertBefore(card, reference);
            updateColumnCounts();
            refreshEmptyStates();
            showToast(error.message || "Nao foi possivel converter a pendencia.", "error");
        }
    }

    function navigateToDetail(card) {
        const url = card.dataset.detailUrl;
        if (url) {
            window.location.href = url;
        }
    }

    function bindActionButton(button) {
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const card = button.closest(".ticket-card");
            if (!card) {
                return;
            }

            const ticketNumber = card.dataset.ticketNumber;
            const action = button.dataset.ticketAction;

            if (action === "play") {
                // Play so vale em coluna de atendente (regra tambem validada no backend).
                const list = card.closest(LIST_SELECTOR);
                if (!list || list.dataset.columnType !== "atendente") {
                    showToast("Arraste o chamado para uma coluna de atendente antes de iniciar o atendimento.", "warning");
                    return;
                }
                handlePlay(ticketNumber);
                return;
            }

            if (activeTicketNumber !== ticketNumber) {
                showToast("Este chamado nao possui atendimento ativo para voce.", "warning");
                return;
            }

            openAttendanceModal(ticketNumber, action);
        });
    }

    function bindCard(card) {
        if (card.dataset.bound === "true") {
            return;
        }
        card.dataset.bound = "true";

        card.addEventListener("click", (event) => {
            if (dragInProgress || event.target.closest(ACTION_SELECTOR)) {
                return;
            }
            navigateToDetail(card);
        });

        card.addEventListener("keydown", (event) => {
            if (event.target.closest(ACTION_SELECTOR)) {
                return;
            }
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                navigateToDetail(card);
            }
        });

        card.querySelectorAll(ACTION_SELECTOR).forEach(bindActionButton);
    }

    function initializeTicketCards() {
        document.querySelectorAll(CARD_SELECTOR).forEach(bindCard);
    }

    function insertNewOpenCard(cardHtml) {
        const openList = document.querySelector('.js-ticket-list[data-column-type="aberto"]');
        if (!openList) {
            window.location.reload();
            return;
        }

        const emptyState = openList.querySelector(".kanban-empty");
        if (emptyState) {
            emptyState.remove();
        }

        const wrapper = document.createElement("div");
        wrapper.innerHTML = cardHtml.trim();
        const card = wrapper.firstElementChild;
        if (!card) {
            window.location.reload();
            return;
        }

        openList.insertBefore(card, openList.firstChild);
        bindCard(card);
        updateColumnCounts();
    }

    function initializeCreateTicket() {
        const createUrl = appElement.dataset.createTicketUrl;
        const modalElement = document.getElementById("createTicketModal");
        const form = document.getElementById("createTicketForm");
        const submitButton = document.getElementById("createTicketSubmit");
        if (!createUrl || !modalElement || !form) {
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (submitButton) {
                submitButton.disabled = true;
            }

            try {
                const response = await fetch(createUrl, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookie("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: new FormData(form),
                });

                let data = {};
                try {
                    data = await response.json();
                } catch (error) {
                    data = { ok: false, message: "Resposta inesperada do servidor." };
                }

                if (!response.ok || data.ok === false) {
                    throw data;
                }

                if (data.card_html) {
                    insertNewOpenCard(data.card_html);
                }
                modal.hide();
                form.reset();
                showToast(data.message || "Chamado criado com sucesso.", "success");
            } catch (error) {
                showToast(error.message || "Nao foi possivel criar o chamado.", "error");
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
    }

    const pendenciaDetailModalElement = document.getElementById("pendenciaDetailModal");
    const pendenciaDetailModal = pendenciaDetailModalElement
        ? bootstrap.Modal.getOrCreateInstance(pendenciaDetailModalElement)
        : null;

    let currentPendenciaCard = null;

    function setPendenciaDetailField(key, value) {
        if (!pendenciaDetailModalElement) {
            return;
        }
        const el = pendenciaDetailModalElement.querySelector(`[data-pendencia-detail="${key}"]`);
        if (el) {
            el.textContent = value || "-";
        }
    }

    function resetPendenciaDeleteConfirm() {
        if (!pendenciaDetailModalElement) {
            return;
        }
        const trigger = pendenciaDetailModalElement.querySelector("[data-pendencia-delete]");
        const confirm = pendenciaDetailModalElement.querySelector("[data-pendencia-delete-confirm]");
        if (trigger) {
            trigger.hidden = false;
        }
        if (confirm) {
            confirm.hidden = true;
        }
    }

    async function openPendenciaDetail(card) {
        if (!pendenciaDetailModal) {
            return;
        }
        try {
            const response = await fetch(card.dataset.detailUrl, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const data = await response.json();
            if (!response.ok || data.ok === false) {
                throw data;
            }
            currentPendenciaCard = card;
            resetPendenciaDeleteConfirm();
            setPendenciaDetailField("titulo", data.titulo);
            setPendenciaDetailField("descricao", data.descricao);
            setPendenciaDetailField("criado_por", data.criado_por);
            setPendenciaDetailField("criado_em", data.criado_em);
            pendenciaDetailModal.show();
        } catch (error) {
            showToast(error.message || "Nao foi possivel abrir a pendencia.", "error");
        }
    }

    async function deleteCurrentPendencia() {
        const card = currentPendenciaCard;
        if (!card) {
            return;
        }
        try {
            const result = await sendJson(card.dataset.deleteUrl, {});
            card.remove();
            currentPendenciaCard = null;
            if (pendenciaDetailModal) {
                pendenciaDetailModal.hide();
            }
            updateColumnCounts();
            refreshEmptyStates();
            showToast(result.message || "Pendencia excluida.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel excluir a pendencia.", "error");
        }
    }

    if (pendenciaDetailModalElement) {
        const deleteTrigger = pendenciaDetailModalElement.querySelector("[data-pendencia-delete]");
        const deleteConfirm = pendenciaDetailModalElement.querySelector("[data-pendencia-delete-confirm]");
        const deleteCancel = pendenciaDetailModalElement.querySelector("[data-pendencia-delete-cancel]");
        const deleteYes = pendenciaDetailModalElement.querySelector("[data-pendencia-delete-yes]");
        if (deleteTrigger && deleteConfirm) {
            deleteTrigger.addEventListener("click", () => {
                deleteTrigger.hidden = true;
                deleteConfirm.hidden = false;
            });
        }
        if (deleteCancel) {
            deleteCancel.addEventListener("click", resetPendenciaDeleteConfirm);
        }
        if (deleteYes) {
            deleteYes.addEventListener("click", deleteCurrentPendencia);
        }
    }

    function bindPendenciaCard(card) {
        if (card.dataset.bound === "true") {
            return;
        }
        card.dataset.bound = "true";

        card.addEventListener("click", () => {
            if (dragInProgress) {
                return;
            }
            openPendenciaDetail(card);
        });

        card.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openPendenciaDetail(card);
            }
        });
    }

    function initializePendenciaCards() {
        document.querySelectorAll(PENDENCIA_CARD_SELECTOR).forEach(bindPendenciaCard);
    }

    function insertNewPendenciaCard(cardHtml) {
        const list = document.querySelector(PENDENCIA_LIST_SELECTOR);
        if (!list) {
            window.location.reload();
            return;
        }
        const wrapper = document.createElement("div");
        wrapper.innerHTML = (cardHtml || "").trim();
        const card = wrapper.firstElementChild;
        if (!card) {
            window.location.reload();
            return;
        }
        list.appendChild(card);
        bindPendenciaCard(card);
        updateColumnCounts();
        refreshEmptyStates();
    }

    function initializeCreatePendencia() {
        const createUrl = appElement.dataset.createPendenciaUrl;
        const modalElement = document.getElementById("createPendenciaModal");
        const form = document.getElementById("createPendenciaForm");
        const submitButton = document.getElementById("createPendenciaSubmit");
        if (!createUrl || !modalElement || !form) {
            return;
        }

        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (submitButton) {
                submitButton.disabled = true;
            }

            const titulo = form.querySelector("#createPendenciaTitulo").value.trim();
            const descricao = form.querySelector("#createPendenciaDescricao").value.trim();

            try {
                const data = await sendJson(createUrl, { titulo, descricao });
                if (data.card_html) {
                    insertNewPendenciaCard(data.card_html);
                }
                modal.hide();
                form.reset();
                showToast(data.message || "Pendencia criada com sucesso.", "success");
            } catch (error) {
                showToast(error.message || "Nao foi possivel criar a pendencia.", "error");
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            }
        });
    }

    // ----- Modal de chamados fechados (lista + pesquisa inteligente + detalhe) -----
    const closedModalElement = document.getElementById("closedTicketsModal");
    const closedSearchUrl = appElement.dataset.closedSearchUrl;
    const closedDetailUrlTemplate = appElement.dataset.closedDetailUrl;

    function initializeClosedTicketsModal() {
        const triggers = document.querySelectorAll(".js-open-closed-modal");
        if (!closedModalElement || !closedSearchUrl || !triggers.length) {
            return;
        }

        const closedModal = bootstrap.Modal.getOrCreateInstance(closedModalElement);
        const searchInput = closedModalElement.querySelector("#closedTicketsSearchInput");
        const listEl = closedModalElement.querySelector("[data-closed-list]");
        const statusEl = closedModalElement.querySelector("[data-closed-status]");
        const backButton = closedModalElement.querySelector("[data-closed-back]");
        const listViews = closedModalElement.querySelectorAll('[data-closed-view="list"]');
        const detailViews = closedModalElement.querySelectorAll('[data-closed-view="detail"]');
        const titleList = closedModalElement.querySelector('[data-closed-title="list"]');
        const titleDetail = closedModalElement.querySelector('[data-closed-title="detail"]');

        let debounceTimer = null;
        let searchController = null;
        let detailController = null;

        function toggleGroup(nodes, hidden) {
            nodes.forEach((node) => node.classList.toggle("is-hidden", hidden));
        }

        function setView(view) {
            const isDetail = view === "detail";
            toggleGroup(listViews, isDetail);
            toggleGroup(detailViews, !isDetail);
            if (titleList) {
                titleList.classList.toggle("is-hidden", isDetail);
            }
            if (titleDetail) {
                titleDetail.classList.toggle("is-hidden", !isDetail);
            }
            if (backButton) {
                backButton.classList.toggle("is-hidden", !isDetail);
            }
        }

        function setDetailField(key, value) {
            const el = closedModalElement.querySelector(`[data-closed-detail="${key}"]`);
            if (el) {
                el.textContent = value || "-";
            }
        }

        function renderList(results) {
            listEl.innerHTML = "";
            if (!results.length) {
                statusEl.textContent = "Nenhum chamado fechado encontrado.";
                return;
            }
            statusEl.textContent = `${results.length} chamado(s) encontrado(s).`;
            const fragment = document.createDocumentFragment();
            results.forEach((item) => {
                const li = document.createElement("li");
                const button = document.createElement("button");
                button.type = "button";
                button.className = "closed-tickets-item";
                button.dataset.number = item.number;

                const number = document.createElement("span");
                number.className = "closed-tickets-item__number";
                number.textContent = item.number;

                const title = document.createElement("span");
                title.className = "closed-tickets-item__title";
                title.textContent = item.title;

                button.appendChild(number);
                button.appendChild(title);
                button.addEventListener("click", () => openDetail(item.number));
                li.appendChild(button);
                fragment.appendChild(li);
            });
            listEl.appendChild(fragment);
        }

        async function loadList(query) {
            if (searchController) {
                searchController.abort();
            }
            searchController = new AbortController();
            statusEl.textContent = "Carregando...";
            try {
                const url = `${closedSearchUrl}?q=${encodeURIComponent(query || "")}`;
                const response = await fetch(url, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    signal: searchController.signal,
                });
                const data = await response.json();
                if (!response.ok || data.ok === false) {
                    throw data;
                }
                renderList(data.results || []);
            } catch (error) {
                if (error.name === "AbortError") {
                    return;
                }
                statusEl.textContent = "Nao foi possivel carregar os chamados fechados.";
                showToast(error.message || "Nao foi possivel carregar os chamados fechados.", "error");
            }
        }

        function renderAttachments(attachments) {
            const section = closedModalElement.querySelector('[data-closed-section="attachments"]');
            const container = closedModalElement.querySelector("[data-closed-attachments]");
            container.innerHTML = "";
            if (!attachments || !attachments.length) {
                section.classList.add("is-hidden");
                return;
            }
            section.classList.remove("is-hidden");
            attachments.forEach((anexo) => {
                const li = document.createElement("li");
                const link = document.createElement("a");
                link.href = anexo.url;
                link.textContent = anexo.nome;
                link.className = "closed-detail__attachment-link";
                li.appendChild(link);
                container.appendChild(li);
            });
        }

        function renderMessages(messages) {
            const section = closedModalElement.querySelector('[data-closed-section="messages"]');
            const container = closedModalElement.querySelector("[data-closed-messages]");
            container.innerHTML = "";
            if (!messages || !messages.length) {
                section.classList.add("is-hidden");
                return;
            }
            section.classList.remove("is-hidden");
            messages.forEach((msg) => {
                const bubble = document.createElement("div");
                bubble.className = "closed-message" + (msg.from_requester ? " closed-message--requester" : " closed-message--ti");

                const head = document.createElement("div");
                head.className = "closed-message__head";
                const author = document.createElement("strong");
                author.textContent = `${msg.author} - ${msg.origin_label}`;
                const time = document.createElement("span");
                time.textContent = msg.timestamp;
                head.appendChild(author);
                head.appendChild(time);

                const body = document.createElement("p");
                body.className = "closed-message__body";
                body.textContent = msg.texto;

                bubble.appendChild(head);
                bubble.appendChild(body);

                if (msg.anexos && msg.anexos.length) {
                    const anexList = document.createElement("ul");
                    anexList.className = "closed-message__anexos";
                    msg.anexos.forEach((anexo) => {
                        const li = document.createElement("li");
                        const link = document.createElement("a");
                        link.href = anexo.url;
                        link.textContent = anexo.nome;
                        li.appendChild(link);
                        anexList.appendChild(li);
                    });
                    bubble.appendChild(anexList);
                }
                container.appendChild(bubble);
            });
        }

        function renderEvents(events) {
            const section = closedModalElement.querySelector('[data-closed-section="events"]');
            const container = closedModalElement.querySelector("[data-closed-events]");
            container.innerHTML = "";
            if (!events || !events.length) {
                section.classList.add("is-hidden");
                return;
            }
            section.classList.remove("is-hidden");
            section.open = false;
            events.forEach((evento) => {
                const li = document.createElement("li");
                const meta = document.createElement("div");
                meta.className = "closed-event__meta";
                const author = document.createElement("strong");
                author.textContent = `${evento.author} - ${evento.tipo_label}`;
                const time = document.createElement("span");
                time.textContent = evento.timestamp;
                meta.appendChild(author);
                meta.appendChild(time);
                const desc = document.createElement("p");
                desc.className = "closed-event__desc";
                desc.textContent = evento.descricao;
                li.appendChild(meta);
                li.appendChild(desc);
                container.appendChild(li);
            });
        }

        async function openDetail(ticketNumber) {
            if (!closedDetailUrlTemplate) {
                return;
            }
            if (detailController) {
                detailController.abort();
            }
            detailController = new AbortController();
            const url = closedDetailUrlTemplate.replace("__NUM__", encodeURIComponent(ticketNumber));
            try {
                const response = await fetch(url, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    signal: detailController.signal,
                });
                const data = await response.json();
                if (!response.ok || data.ok === false) {
                    throw data;
                }

                setDetailField("number", data.number);
                setDetailField("title", data.title);
                setDetailField("requester", data.requester);
                setDetailField("attendant", data.current_attendant);
                setDetailField("created", data.created_at);
                setDetailField("description", data.description || "Sem descricao.");

                const statusBadge = closedModalElement.querySelector('[data-closed-detail="status"]');
                if (statusBadge) {
                    statusBadge.textContent = data.status_label || "-";
                    statusBadge.classList.remove(...STATUS_BADGE_CLASSES);
                    statusBadge.classList.add(data.status_class || "status-neutral");
                }

                const closedRow = closedModalElement.querySelector('[data-closed-detail-row="closed"]');
                if (closedRow) {
                    if (data.closed_at) {
                        closedRow.classList.remove("is-hidden");
                        setDetailField("closed", data.closed_at);
                    } else {
                        closedRow.classList.add("is-hidden");
                    }
                }

                renderAttachments(data.attachments);
                renderMessages(data.messages);
                renderEvents(data.events);
                setView("detail");
            } catch (error) {
                if (error.name === "AbortError") {
                    return;
                }
                showToast(error.message || "Nao foi possivel abrir o chamado.", "error");
            }
        }

        function openModal() {
            setView("list");
            if (searchInput) {
                searchInput.value = "";
            }
            loadList("");
            closedModal.show();
            window.setTimeout(() => searchInput && searchInput.focus(), 200);
        }

        triggers.forEach((trigger) => {
            trigger.addEventListener("click", () => {
                const number = trigger.dataset.closedNumber;
                if (number) {
                    // Card de um encerrado recente: abre direto no detalhe.
                    setView("detail");
                    closedModal.show();
                    openDetail(number);
                } else {
                    openModal();
                }
            });
        });

        if (searchInput) {
            searchInput.addEventListener("input", () => {
                if (debounceTimer) {
                    window.clearTimeout(debounceTimer);
                }
                const value = searchInput.value.trim();
                debounceTimer = window.setTimeout(() => loadList(value), 300);
            });
        }

        if (backButton) {
            backButton.addEventListener("click", () => setView("list"));
        }
    }

    function initialize() {
        attendanceForm.addEventListener("submit", handleAttendanceSubmit);
        initializeDragAndDrop();
        initializeTicketCards();
        initializePendenciaCards();
        initializeCreateTicket();
        initializeCreatePendencia();
        initializeClosedTicketsModal();
        syncInitialActiveState();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
