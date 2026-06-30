(function () {
    const appElement = document.querySelector(".history-app");
    const searchInput = document.getElementById("historySearchInput");
    const resultsBody = document.getElementById("historyResultsBody");
    const loadingElement = document.getElementById("historySearchLoading");
    const emptyState = document.getElementById("historyEmptyState");
    const countElement = document.getElementById("historyCount");

    if (!appElement || !searchInput || !resultsBody || !loadingElement || !emptyState || !countElement) {
        return;
    }

    const searchUrl = appElement.dataset.historySearchUrl;
    let debounceId = null;
    let activeRequestId = 0;

    function showToast(message, type) {
        if (typeof window.showAppToast === "function") {
            window.showAppToast(message, type);
        }
    }

    function escapeHtml(value) {
        const element = document.createElement("div");
        element.textContent = value == null ? "" : String(value);
        return element.innerHTML;
    }

    function getTypeBadgeClass(type) {
        if (type === "pause") {
            return "history-badge--pause";
        }
        if (type === "stop") {
            return "history-badge--stop";
        }
        return "history-badge--active";
    }

    function setLoading(isLoading) {
        loadingElement.classList.toggle("is-hidden", !isLoading);
    }

    function setEmptyState(isEmpty) {
        emptyState.classList.toggle("is-hidden", !isEmpty);
    }

    function renderResults(results) {
        countElement.textContent = String(results.length);

        if (!Array.isArray(results) || results.length === 0) {
            resultsBody.innerHTML = "";
            setEmptyState(true);
            return;
        }

        setEmptyState(false);
        resultsBody.innerHTML = results
            .map((row) => `
                <tr>
                    <td><span class="history-ticket">${escapeHtml(row.ticket_number)}</span></td>
                    <td>${escapeHtml(row.ticket_title)}</td>
                    <td>
                        <div class="history-attendant">
                            <strong>${escapeHtml(row.attendant_name)}</strong>
                            <span>${escapeHtml(row.attendant_username)}</span>
                        </div>
                    </td>
                    <td>${escapeHtml(row.started_at)}</td>
                    <td>${escapeHtml(row.finished_at)}</td>
                    <td><span class="history-badge history-badge--duration">${escapeHtml(row.duration)}</span></td>
                    <td><span class="history-badge ${getTypeBadgeClass(row.type)}">${escapeHtml(row.type)}</span></td>
                    <td class="history-description">${escapeHtml(row.description)}</td>
                </tr>
            `)
            .join("");
    }

    async function fetchResults(query) {
        activeRequestId += 1;
        const requestId = activeRequestId;
        const url = `${searchUrl}?q=${encodeURIComponent(query)}`;

        setLoading(true);

        try {
            const response = await fetch(url, {
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                },
            });

            const data = await response.json();
            if (!response.ok || data.ok === false) {
                throw new Error(data.message || "Nao foi possivel carregar o historico.");
            }

            if (requestId !== activeRequestId) {
                return;
            }

            renderResults(data.results || []);
        } catch (error) {
            if (requestId !== activeRequestId) {
                return;
            }

            showToast(error.message || "Erro ao pesquisar historico de atendimentos.", "error");
        } finally {
            if (requestId === activeRequestId) {
                setLoading(false);
            }
        }
    }

    function handleSearchInput() {
        window.clearTimeout(debounceId);
        debounceId = window.setTimeout(() => {
            fetchResults(searchInput.value.trim());
        }, 320);
    }

    searchInput.addEventListener("input", handleSearchInput);
})();
