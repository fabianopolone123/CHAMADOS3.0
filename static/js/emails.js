(function () {
    const appElement = document.querySelector(".emails-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const detailTpl = appElement.dataset.emailDetailUrl;

    function buildUrl(template, id) {
        return template.replace("/0/", `/${id}/`);
    }

    function showToast(message, type) {
        if (typeof window.showAppToast === "function") {
            window.showAppToast(message, type);
        }
    }

    async function sendGet(url) {
        const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
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

    // ---------------- Importar ----------------
    const importModalEl = document.getElementById("importEmailModal");
    const importModal = importModalEl ? bootstrap.Modal.getOrCreateInstance(importModalEl) : null;
    document.getElementById("importEmailButton")?.addEventListener("click", () => importModal?.show());

    // ---------------- Busca (client-side, instantanea) ----------------
    const searchInput = document.getElementById("emailSearch");
    const statusEl = document.getElementById("emailSearchStatus");
    const noResults = document.getElementById("emailsNoResults");
    const rows = Array.from(document.querySelectorAll(".emails-row"));

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        if (!searchInput || !searchInput.value.trim()) {
            statusEl.textContent = `${total} conta(s) no total.`;
        } else {
            statusEl.textContent = `${visible} de ${total} conta(s) encontrada(s).`;
        }
    }

    function filterRows() {
        const term = (searchInput?.value || "").trim().toLowerCase();
        let visible = 0;
        rows.forEach((row) => {
            const haystack = row.dataset.search || "";
            const match = !term || haystack.indexOf(term) !== -1;
            row.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterRows);
    updateStatus(rows.length);

    // ---------------- Detalhe ----------------
    const detailModalEl = document.getElementById("emailDetailModal");
    const detailModal = detailModalEl ? bootstrap.Modal.getOrCreateInstance(detailModalEl) : null;

    function setField(key, value) {
        const el = detailModalEl.querySelector(`[data-email-detail="${key}"]`);
        if (!el) return;
        if (typeof value === "boolean") {
            el.textContent = value ? "Sim" : "Nao";
        } else {
            el.textContent = value || "-";
        }
    }

    function setStatusBadge(data) {
        const badge = detailModalEl.querySelector("[data-email-detail-status]");
        if (!badge) return;
        badge.textContent = data.status || "-";
        badge.classList.remove("status-success", "status-warning", "status-muted");
        badge.classList.add(data.is_ativo ? "status-success" : "status-warning");
    }

    async function openDetail(id) {
        try {
            const data = await sendGet(buildUrl(detailTpl, id));
            detailModalEl.querySelectorAll("[data-email-detail]").forEach((el) => {
                setField(el.dataset.emailDetail, data[el.dataset.emailDetail]);
            });
            setStatusBadge(data);
            detailModal?.show();
        } catch (error) {
            showToast(error.message || "Nao foi possivel abrir a conta.", "error");
        }
    }

    rows.forEach((row) => {
        row.addEventListener("click", () => openDetail(row.dataset.contaId));
        row.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openDetail(row.dataset.contaId);
            }
        });
    });
})();
