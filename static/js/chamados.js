(function () {
    const ATTENDANCE_MODAL_ID = "attendanceActionModal";
    const ATTENDANCE_FORM_ID = "attendanceActionForm";
    const CARD_SELECTOR = ".ticket-card[data-ticket-number]";
    const LIST_SELECTOR = ".js-ticket-list";
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

    function refreshEmptyStates() {
        document.querySelectorAll(LIST_SELECTOR).forEach(syncListEmptyState);
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
        attendanceFields.submit.textContent = action === "pause" ? "Enviar pausa" : "Enviar encerramento";

        attendanceModal.show();
        window.setTimeout(() => attendanceFields.description.focus(), 180);
    }

    async function handlePlay(ticketNumber) {
        if (activeTicketNumber && activeTicketNumber !== ticketNumber) {
            showToast("Ja existe um atendimento em andamento. Pause ou finalize antes de iniciar outro.", "warning");
            return;
        }

        const card = getTicketCard(ticketNumber);
        if (!card) {
            return;
        }

        try {
            const result = await sendJson(startAttendanceUrl, { ticket_number: ticketNumber });
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

    function initializeDragAndDrop() {
        if (typeof Sortable === "undefined") {
            return;
        }

        document.querySelectorAll(LIST_SELECTOR).forEach((listElement) => {
            Sortable.create(listElement, {
                group: "tickets-board",
                animation: 180,
                ghostClass: "ticket-card-ghost",
                chosenClass: "ticket-card-chosen",
                dragClass: "ticket-card-drag",
                filter: "button, textarea",
                preventOnFilter: false,
                onStart: () => {
                    dragInProgress = true;
                },
                onEnd: (event) => {
                    window.setTimeout(() => {
                        dragInProgress = false;
                    }, 0);

                    const ticketNumber = event.item.dataset.ticketNumber;
                    const target = event.to.dataset.columnType;
                    const attendantId = event.to.dataset.attendantId;
                    const fromAttendantId = event.from.dataset.attendantId;

                    if (!ticketNumber || !target) {
                        return;
                    }

                    // sem mudanca real de coluna
                    if (event.from === event.to) {
                        return;
                    }
                    // mesma coluna de atendente (por seguranca)
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
                },
            });
        });
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

    function initialize() {
        attendanceForm.addEventListener("submit", handleAttendanceSubmit);
        initializeDragAndDrop();
        initializeTicketCards();
        initializeCreateTicket();
        syncInitialActiveState();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
