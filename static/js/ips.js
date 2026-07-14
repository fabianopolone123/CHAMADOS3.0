(function () {
    const app = document.querySelector(".ips-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.ipUpdateUrl;
    const deleteTpl = app.dataset.ipDeleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    function buildUrl(template, id) {
        return template ? template.replace("/0/", `/${id}/`) : "";
    }

    function setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value == null ? "" : value;
    }

    // ------------------------------------------------------------------
    // Modal (cadastrar / editar / excluir)
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("ipModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("ipForm");
    const deleteForm = document.getElementById("ipDeleteForm");
    const deleteConfirm = document.getElementById("ipDeleteConfirm");
    const deleteBtn = document.getElementById("ipDeleteBtn");
    const createAction = form ? form.getAttribute("action") : "";

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("ipModalLabel").textContent = "Cadastrar novo IP";
        document.getElementById("ipSubmit").textContent = "Cadastrar IP";
        form.action = createAction;
        setVal("ipCategoria", "");
        setVal("ipEndereco", "");
        setVal("ipNome", "");
        setVal("ipFabricante", "");
        setVal("ipMac", "");
        setVal("ipAcesso", "");
        setVal("ipObservacoes", "");
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(d) {
        if (!form) return;
        document.getElementById("ipModalLabel").textContent = "Editar IP";
        document.getElementById("ipSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("ipCategoria", d.categoria);
        setVal("ipEndereco", d.endereco);
        setVal("ipNome", d.nome);
        setVal("ipFabricante", d.fabricante);
        setVal("ipMac", d.mac);
        setVal("ipAcesso", d.acesso);
        setVal("ipObservacoes", d.observacoes);
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
    }

    document.getElementById("createIpButton")?.addEventListener("click", openCreate);

    document.querySelectorAll(".js-edit-ip").forEach((btn) => {
        btn.addEventListener("click", () => {
            const row = btn.closest(".ips-row");
            if (row) openEdit(row.dataset);
        });
    });

    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("ipDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Busca inteligente + filtro por categoria (chips)
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("ipSearch");
    const statusEl = document.getElementById("ipSearchStatus");
    const noResults = document.getElementById("ipsNoResults");
    const chips = Array.from(document.querySelectorAll(".ips-chip"));
    const rows = Array.from(document.querySelectorAll(".ips-row"));
    let activeCategory = "";

    function normalize(value) {
        return (value || "")
            .toString()
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "")
            .toLowerCase();
    }

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        const filtering = (searchInput && searchInput.value.trim()) || activeCategory;
        statusEl.textContent = filtering
            ? `${visible} de ${total} IP(s) encontrado(s).`
            : `${total} IP(s) no total.`;
    }

    function applyFilters() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        rows.forEach((row) => {
            const matchText = !term || normalize(row.dataset.search).includes(term);
            const matchCat = !activeCategory || row.dataset.categoria === activeCategory;
            const show = matchText && matchCat;
            row.classList.toggle("is-hidden", !show);
            if (show) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", applyFilters);

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeCategory = chip.dataset.category || "";
            chips.forEach((c) => {
                const isActive = c === chip;
                c.classList.toggle("is-active", isActive);
                c.setAttribute("aria-selected", isActive ? "true" : "false");
            });
            applyFilters();
        });
    });

    updateStatus(rows.length);

    // ------------------------------------------------------------------
    // Ordenacao ao clicar nos cabecalhos
    // ------------------------------------------------------------------
    const tbody = document.getElementById("ipsTableBody");
    const headers = Array.from(document.querySelectorAll(".ips-th"));
    let sortState = { index: -1, dir: 1 };

    function cellText(row, index) {
        const cell = row.children[index];
        return cell ? cell.textContent.trim() : "";
    }

    // Converte "192.168.22.10" em um numero comparavel (ordena por octeto).
    function ipToNumber(value) {
        const parts = (value || "").split(".");
        if (parts.length !== 4) return null;
        let num = 0;
        for (const p of parts) {
            const n = parseInt(p, 10);
            if (Number.isNaN(n)) return null;
            num = num * 256 + n;
        }
        return num;
    }

    function sortBy(index, type) {
        const dir = sortState.index === index ? -sortState.dir : 1;
        sortState = { index, dir };
        const ordered = rows.slice().sort((a, b) => {
            const va = cellText(a, index);
            const vb = cellText(b, index);
            if (type === "ip") {
                const na = ipToNumber(va);
                const nb = ipToNumber(vb);
                if (na !== null && nb !== null) return (na - nb) * dir;
            }
            return va.localeCompare(vb, "pt", { sensitivity: "base", numeric: true }) * dir;
        });
        ordered.forEach((row) => tbody.appendChild(row));
        headers.forEach((h) => {
            const isActive = Number(h.dataset.sortIndex) === index;
            h.setAttribute("aria-sort", isActive ? (dir === 1 ? "ascending" : "descending") : "none");
            const ind = h.querySelector(".ips-sort-ind");
            if (ind) ind.textContent = isActive ? (dir === 1 ? "↑" : "↓") : "";
        });
    }

    headers.forEach((h) => {
        h.addEventListener("click", () => {
            sortBy(Number(h.dataset.sortIndex), h.dataset.sortType || "text");
        });
    });
})();
