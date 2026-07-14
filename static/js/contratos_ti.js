(function () {
    const app = document.querySelector(".contratosti-app");
    if (!app) {
        return;
    }

    const detailTpl = app.dataset.detailUrl;
    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const anexoDeleteTpl = app.dataset.anexoDeleteUrl;
    const csrf = app.dataset.csrf;
    const hasBootstrap = typeof bootstrap !== "undefined";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };
    const setText = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v == null || v === "" ? "-" : v; };

    // ------------------------------------------------------------------
    // Modal cadastro / edicao
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("contratoModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("contratoForm");
    const deleteForm = document.getElementById("contratoDeleteForm");
    const deleteConfirm = document.getElementById("contratoDeleteConfirm");
    const deleteBtn = document.getElementById("contratoDeleteBtn");
    const existingWrap = document.getElementById("contratoExistingWrap");
    const existingList = document.getElementById("contratoExistingList");
    const anexosInput = document.getElementById("contratoAnexos");
    const createAction = form ? form.getAttribute("action") : "";

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function renderExisting(anexos) {
        if (!existingWrap || !existingList) return;
        existingList.innerHTML = "";
        if (!anexos || !anexos.length) { existingWrap.classList.add("is-hidden"); return; }
        anexos.forEach((a) => {
            const li = document.createElement("li");
            li.className = "ctr-existing__item";
            const link = document.createElement("a");
            link.href = a.url; link.target = "_blank"; link.rel = "noopener"; link.textContent = a.nome;
            const rm = document.createElement("form");
            rm.method = "post"; rm.action = buildUrl(anexoDeleteTpl, a.id);
            rm.innerHTML = `<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">` +
                `<button type="submit" class="ctr-existing__remove" title="Remover anexo">Remover</button>`;
            li.appendChild(link); li.appendChild(rm);
            existingList.appendChild(li);
        });
        existingWrap.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("contratoModalLabel").textContent = "Cadastrar novo contrato";
        document.getElementById("contratoSubmit").textContent = "Cadastrar contrato";
        form.action = createAction;
        ["contratoNome","contratoValor","contratoForma","contratoCartao","contratoInicio","contratoFim","contratoEncerrado","contratoObservacoes"].forEach((id) => setVal(id, ""));
        setVal("contratoPeriodicidade", "mensal");
        if (anexosInput) anexosInput.value = "";
        renderExisting([]);
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(row) {
        if (!form || !row) return;
        const d = row.dataset;
        document.getElementById("contratoModalLabel").textContent = "Editar contrato";
        document.getElementById("contratoSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("contratoNome", d.nome);
        setVal("contratoValor", (d.valor || "").replace(".", ","));
        setVal("contratoPeriodicidade", d.periodicidade || "mensal");
        setVal("contratoForma", d.forma);
        setVal("contratoCartao", d.cartao);
        setVal("contratoInicio", d.inicio);
        setVal("contratoFim", d.fim);
        setVal("contratoEncerrado", d.encerrado);
        setVal("contratoObservacoes", d.observacoes);
        if (anexosInput) anexosInput.value = "";
        renderExisting([]);
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
        fetch(buildUrl(detailTpl, d.id), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => { if (data && data.ok) renderExisting(data.anexos); })
            .catch(() => {});
    }

    document.getElementById("createContratoButton")?.addEventListener("click", openCreate);
    document.querySelectorAll(".js-edit-contrato").forEach((btn) => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); openEdit(btn.closest(".ctr-row")); });
    });
    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("contratoDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Modal detalhe
    // ------------------------------------------------------------------
    const detailEl = document.getElementById("contratoDetailModal");
    const detailModal = detailEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(detailEl) : null;
    const detailFiles = document.getElementById("ctrDetailAnexos");
    const detailFilesEmpty = document.getElementById("ctrDetailAnexosEmpty");
    const detailStatus = document.getElementById("ctrDetailStatus");
    let lastRow = null;

    function openDetail(row) {
        if (!detailModal || !row) return;
        lastRow = row;
        const d = row.dataset;
        setText("ctrDetailNome", d.nome);
        setText("ctrDetailObs", d.observacoes);
        if (detailFiles) detailFiles.innerHTML = "";
        detailFilesEmpty?.classList.add("is-hidden");
        detailModal.show();
        fetch(buildUrl(detailTpl, d.id), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data || !data.ok) return;
                setText("ctrDetailNome", data.nome);
                setText("ctrDetailValor", "R$ " + data.valor_display);
                setText("ctrDetailPeriodicidade", data.periodicidade);
                setText("ctrDetailPagamento", data.forma_pagamento + (data.final_cartao ? ` (final ${data.final_cartao})` : ""));
                setText("ctrDetailInicio", data.inicio);
                setText("ctrDetailFim", data.fim);
                setText("ctrDetailEncerrado", data.encerrado_em);
                setText("ctrDetailObs", data.observacoes);
                if (detailStatus) {
                    detailStatus.textContent = data.esta_ativo ? "Ativo" : "Encerrado";
                    detailStatus.className = "ctr-badge " + (data.esta_ativo ? "ctr-badge--ativo" : "ctr-badge--encerrado");
                }
                if (detailFiles) {
                    detailFiles.innerHTML = "";
                    (data.anexos || []).forEach((a) => {
                        const li = document.createElement("li");
                        const link = document.createElement("a");
                        link.href = a.url; link.target = "_blank"; link.rel = "noopener";
                        link.innerHTML = `📎 <span>${a.nome}</span>`;
                        li.appendChild(link);
                        detailFiles.appendChild(li);
                    });
                    detailFilesEmpty?.classList.toggle("is-hidden", (data.anexos || []).length > 0);
                }
            })
            .catch(() => {});
    }

    document.querySelectorAll(".js-view-contrato").forEach((btn) => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); openDetail(btn.closest(".ctr-row")); });
    });
    document.querySelectorAll(".ctr-row").forEach((row) => {
        row.addEventListener("click", (e) => { if (e.target.closest(".ctr-cell--actions")) return; openDetail(row); });
        row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetail(row); } });
    });
    document.getElementById("ctrDetailEditBtn")?.addEventListener("click", () => {
        detailModal?.hide();
        if (lastRow) openEdit(lastRow);
    });

    // ------------------------------------------------------------------
    // Busca
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("contratoSearch");
    const statusEl = document.getElementById("contratoSearchStatus");
    const noResults = document.getElementById("contratosNoResults");
    const tbody = document.getElementById("contratosTableBody");
    const rows = Array.from(document.querySelectorAll(".ctr-row"));

    const normalize = (v) => (v || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        statusEl.textContent = (searchInput && searchInput.value.trim())
            ? `${visible} de ${total} contrato(s) encontrado(s).`
            : `${total} contrato(s) no total.`;
    }

    function filterRows() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        rows.forEach((row) => {
            const match = !term || normalize(row.dataset.search).includes(term);
            row.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterRows);
    updateStatus(rows.length);

    // ------------------------------------------------------------------
    // Ordenacao por cabecalho
    // ------------------------------------------------------------------
    const headers = Array.from(document.querySelectorAll(".ctr-th"));
    let sortState = { index: -1, dir: 1 };

    function cellValue(row, index, type) {
        const cell = row.children[index];
        if (!cell) return "";
        if (type === "num" || type === "date") {
            const raw = cell.dataset.sortValue != null ? cell.dataset.sortValue : cell.textContent;
            if (type === "num") return parseFloat(String(raw).replace(/[^0-9.\-]/g, "")) || 0;
            return String(raw); // date ISO (yyyy-mm-dd) ou vazio
        }
        return cell.textContent.trim();
    }

    function sortBy(index, type) {
        const dir = sortState.index === index ? -sortState.dir : 1;
        sortState = { index, dir };
        const ordered = rows.slice().sort((a, b) => {
            const va = cellValue(a, index, type);
            const vb = cellValue(b, index, type);
            if (type === "num") return (va - vb) * dir;
            return String(va).localeCompare(String(vb), "pt", { sensitivity: "base", numeric: true }) * dir;
        });
        ordered.forEach((row) => tbody.appendChild(row));
        headers.forEach((h) => {
            const isActive = Number(h.dataset.sortIndex) === index;
            h.setAttribute("aria-sort", isActive ? (dir === 1 ? "ascending" : "descending") : "none");
            const ind = h.querySelector(".ctr-sort-ind");
            if (ind) ind.textContent = isActive ? (dir === 1 ? "↑" : "↓") : "";
        });
    }

    headers.forEach((h) => {
        h.addEventListener("click", () => sortBy(Number(h.dataset.sortIndex), h.dataset.sortType || "text"));
    });
})();
