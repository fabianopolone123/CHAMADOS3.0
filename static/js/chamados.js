(function () {
    const DATA_ELEMENT_ID = "ticket-details-data";
    const DETAILS_MODAL_ID = "ticketDetailsModal";
    const ATTENDANCE_MODAL_ID = "attendanceActionModal";
    const ATTENDANCE_FORM_ID = "attendanceActionForm";
    const TOGGLE_SELECTOR = ".ticket-card[data-ticket-number]";
    const LIST_SELECTOR = ".js-ticket-list";
    const ACTION_SELECTOR = "[data-ticket-action]";

    const appElement = document.querySelector(".tickets-app");
    const ticketDataElement = document.getElementById(DATA_ELEMENT_ID);
    const detailsModalElement = document.getElementById(DETAILS_MODAL_ID);
    const attendanceModalElement = document.getElementById(ATTENDANCE_MODAL_ID);
    const attendanceForm = document.getElementById(ATTENDANCE_FORM_ID);

    if (!appElement || !ticketDataElement || !detailsModalElement || !attendanceModalElement || !attendanceForm || typeof bootstrap === "undefined") {
        return;
    }

    const startAttendanceUrl = appElement.dataset.startAttendanceUrl;
    const finishAttendanceUrl = appElement.dataset.finishAttendanceUrl;

    let ticketDetails = {};
    let dragInProgress = false;
    let activeTicketNumber = null;
    let timerIntervalId = null;

    try {
        ticketDetails = JSON.parse(ticketDataElement.textContent || "{}");
    } catch (error) {
        console.warn("Nao foi possivel carregar os dados dos chamados.", error);
    }

    const detailsModal = bootstrap.Modal.getOrCreateInstance(detailsModalElement);
    const attendanceModal = bootstrap.Modal.getOrCreateInstance(attendanceModalElement);

    const detailFields = {
        number: document.getElementById("ticketModalNumber"),
        title: document.getElementById("ticketDetailsModalLabel"),
        description: document.getElementById("ticketModalDescription"),
        requester: document.getElementById("ticketModalRequester"),
        requesterEmail: document.getElementById("ticketModalRequesterEmail"),
        department: document.getElementById("ticketModalDepartment"),
        category: document.getElementById("ticketModalCategory"),
        subcategory: document.getElementById("ticketModalSubcategory"),
        priority: document.getElementById("ticketModalPriority"),
        status: document.getElementById("ticketModalStatus"),
        responsible: document.getElementById("ticketModalResponsible"),
        openedAt: document.getElementById("ticketModalOpenedAt"),
        timeOpen: document.getElementById("ticketModalTimeOpen"),
        lastUpdate: document.getElementById("ticketModalLastUpdate"),
        source: document.getElementById("ticketModalSource"),
        attachments: document.getElementById("ticketModalAttachments"),
        history: document.getElementById("ticketModalHistory"),
    };

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

    function setTextContent(element, value, fallback = "-") {
        if (!element) {
            return;
        }
        element.textContent = value && String(value).trim() ? String(value) : fallback;
    }

    function setPill(element, value, className) {
        if (!element) {
            return;
        }

        element.className = `ticket-modal__pill ${className || ""}`.trim();
        element.textContent = value && String(value).trim() ? String(value) : "-";
    }

    function createEmptyState(message) {
        const empty = document.createElement("div");
        empty.className = "ticket-modal__empty";
        empty.textContent = message;
        return empty;
    }

    function renderAttachments(container, attachments) {
        if (!container) {
            return;
        }

        container.replaceChildren();

        if (!Array.isArray(attachments) || attachments.length === 0) {
            container.appendChild(createEmptyState("Nenhum anexo mockado para este chamado."));
            return;
        }

        attachments.forEach((attachment) => {
            const item = document.createElement("div");
            item.className = "ticket-modal__attachment";

            const icon = document.createElement("span");
            icon.className = "ticket-modal__attachment-icon";
            icon.textContent = attachment.file_type === "Imagem" ? "IMG" : attachment.file_type === "Texto" ? "TXT" : "DOC";

            const info = document.createElement("div");
            info.className = "ticket-modal__attachment-info";

            const name = document.createElement("strong");
            name.textContent = attachment.name || "Arquivo";

            const meta = document.createElement("span");
            meta.textContent = [attachment.file_type, attachment.size].filter(Boolean).join(" | ");

            info.append(name, meta);
            item.append(icon, info);
            container.appendChild(item);
        });
    }

    function renderHistory(container, history) {
        if (!container) {
            return;
        }

        container.replaceChildren();

        if (!Array.isArray(history) || history.length === 0) {
            container.appendChild(createEmptyState("Sem historico mockado para este chamado."));
            return;
        }

        history.forEach((entry) => {
            const item = document.createElement("article");
            item.className = "ticket-modal__timeline-item";

            const marker = document.createElement("span");
            marker.className = `ticket-modal__timeline-marker ticket-modal__timeline-marker--${entry.kind || "comment"}`;

            const content = document.createElement("div");
            content.className = "ticket-modal__timeline-content";

            const head = document.createElement("div");
            head.className = "ticket-modal__timeline-head";

            const author = document.createElement("strong");
            author.textContent = entry.author || "Sistema";

            const timestamp = document.createElement("span");
            timestamp.textContent = entry.timestamp || "-";

            const message = document.createElement("p");
            message.textContent = entry.message || "";

            head.append(author, timestamp);
            content.append(head, message);
            item.append(marker, content);
            container.appendChild(item);
        });
    }

    function applyTicketDetails(ticket) {
        if (!ticket) {
            return;
        }

        setTextContent(detailFields.number, ticket.number);
        setTextContent(detailFields.title, ticket.title);
        setTextContent(detailFields.description, ticket.description);
        setTextContent(detailFields.requester, ticket.requester);
        setTextContent(detailFields.requesterEmail, ticket.requester_email);
        setTextContent(detailFields.department, ticket.department);
        setTextContent(detailFields.category, ticket.category);
        setTextContent(detailFields.subcategory, ticket.subcategory || "Sem subcategoria");
        setTextContent(detailFields.responsible, ticket.responsible_attendant || "Nao atribuido");
        setTextContent(detailFields.openedAt, ticket.opened_at);
        setTextContent(detailFields.timeOpen, ticket.opened_time);
        setTextContent(detailFields.lastUpdate, ticket.last_update);
        setTextContent(detailFields.source, ticket.source);
        setPill(detailFields.priority, ticket.priority, ticket.priority_class);
        setPill(detailFields.status, ticket.status, ticket.status_class);
        renderAttachments(detailFields.attachments, ticket.attachments);
        renderHistory(detailFields.history, ticket.history);
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

    function updateTicketDetailAttendance(ticketNumber, attendanceState) {
        const ticket = ticketDetails[ticketNumber];
        if (!ticket) {
            return;
        }

        ticket.attendance = attendanceState || {
            is_active: false,
            started_at_iso: "",
            started_at_display: "",
            elapsed_display: "",
        };
    }

    function appendTicketHistory(ticketNumber, historyEntry) {
        const ticket = ticketDetails[ticketNumber];
        if (!ticket) {
            return;
        }

        if (!Array.isArray(ticket.history)) {
            ticket.history = [];
        }

        ticket.history.unshift(historyEntry);
        ticket.last_update = historyEntry.timestamp || ticket.last_update;
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

    function openDetailsModal(ticketNumber) {
        const ticket = ticketDetails[ticketNumber];
        if (!ticket) {
            console.warn(`Detalhes do chamado nao encontrados para ${ticketNumber}.`);
            return;
        }

        applyTicketDetails(ticket);
        detailsModal.show();
    }

    function openAttendanceModal(ticketNumber, action) {
        const ticket = ticketDetails[ticketNumber];
        const actionLabel = action === "pause" ? "Pause" : "Stop";

        attendanceFields.ticketNumber.value = ticketNumber;
        attendanceFields.action.value = action;
        attendanceFields.ticketLabel.textContent = `${ticketNumber} | ${ticket ? ticket.title : "Chamado"}`;
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
            updateTicketDetailAttendance(ticketNumber, {
                is_active: true,
                started_at_iso: result.attendance.started_at_iso,
                started_at_display: result.attendance.started_at_display,
                elapsed_display: result.attendance.elapsed_display,
            });
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
            updateTicketDetailAttendance(ticketNumber, {
                is_active: false,
                started_at_iso: "",
                started_at_display: "",
                elapsed_display: "",
            });
            appendTicketHistory(ticketNumber, result.history_entry);
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

                    const fromColumn = event.from.dataset.column;
                    const toColumn = event.to.dataset.column;
                    const ticketNumber = event.item.dataset.ticketNumber || event.item.querySelector(".ticket-number")?.textContent?.trim();

                    // TODO: persistir a reatribuicao do chamado no backend.
                    console.info("Movimentacao visual de chamado", {
                        ticketNumber,
                        fromColumn,
                        toColumn,
                    });
                },
            });
        });
    }

    function initializeTicketCards() {
        document.querySelectorAll(TOGGLE_SELECTOR).forEach((card) => {
            const ticketNumber = card.dataset.ticketNumber;

            card.addEventListener("click", (event) => {
                if (dragInProgress || event.target.closest(ACTION_SELECTOR)) {
                    return;
                }
                openDetailsModal(ticketNumber);
            });

            card.addEventListener("keydown", (event) => {
                if (event.target.closest(ACTION_SELECTOR)) {
                    return;
                }
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    openDetailsModal(ticketNumber);
                }
            });
        });
    }

    function initializeActionButtons() {
        document.querySelectorAll(ACTION_SELECTOR).forEach((button) => {
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
        });
    }

    function initialize() {
        attendanceForm.addEventListener("submit", handleAttendanceSubmit);
        initializeDragAndDrop();
        initializeTicketCards();
        initializeActionButtons();
        syncInitialActiveState();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initialize);
    } else {
        initialize();
    }
})();
