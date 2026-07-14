(function () {
    const app = document.querySelector(".servicos-app");
    if (!app) {
        return;
    }

    const detailTpl = app.dataset.detailUrl;
    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const anexoDeleteTpl = app.dataset.anexoDeleteUrl;
    const csrf = app.dataset.csrf;
    const hasBootstrap = typeof bootstrap !== "undefined";

    function buildUrl(template, id) {
        return template ? template.replace("/0/", `/${id}/`) : "";
    }

    function setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value == null ? "" : value;
    }

    function setText(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value == null || value === "" ? "-" : value;
    }

    // ------------------------------------------------------------------
    // Modal de cadastro / edicao
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("servicoModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("servicoForm");
    const deleteForm = document.getElementById("servicoDeleteForm");
    const deleteConfirm = document.getElementById("servicoDeleteConfirm");
    const deleteBtn = document.getElementById("servicoDeleteBtn");
    const existingWrap = document.getElementById("servicoExistingWrap");
    const existingList = document.getElementById("servicoExistingList");
    const createAction = form ? form.getAttribute("action") : "";
    const anexosInput = document.getElementById("servicoAnexos");

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function renderExisting(anexos) {
        if (!existingWrap || !existingList) return;
        existingList.innerHTML = "";
        if (!anexos || !anexos.length) {
            existingWrap.classList.add("is-hidden");
            return;
        }
        anexos.forEach((a) => {
            const li = document.createElement("li");
            li.className = "servico-existing__item";
            const link = document.createElement("a");
            link.href = a.url;
            link.target = "_blank";
            link.rel = "noopener";
            link.textContent = a.nome;
            const rm = document.createElement("form");
            rm.method = "post";
            rm.action = buildUrl(anexoDeleteTpl, a.id);
            rm.innerHTML =
                `<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">` +
                `<button type="submit" class="servico-existing__remove" title="Remover anexo">Remover</button>`;
            li.appendChild(link);
            li.appendChild(rm);
            existingList.appendChild(li);
        });
        existingWrap.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("servicoModalLabel").textContent = "Cadastrar novo servico";
        document.getElementById("servicoSubmit").textContent = "Cadastrar servico";
        form.action = createAction;
        setVal("servicoNome", "");
        setVal("servicoEmpresa", "");
        setVal("servicoData", "");
        setVal("servicoValor", "");
        setVal("servicoDescricao", "");
        if (anexosInput) anexosInput.value = "";
        renderExisting([]);
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(row) {
        if (!form || !row) return;
        const d = row.dataset;
        document.getElementById("servicoModalLabel").textContent = "Editar servico";
        document.getElementById("servicoSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("servicoNome", d.nome);
        setVal("servicoEmpresa", d.empresa);
        setVal("servicoData", d.data);
        setVal("servicoValor", (d.valor || "").replace(".", ","));
        setVal("servicoDescricao", d.descricao);
        if (anexosInput) anexosInput.value = "";
        renderExisting([]);
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
        // Busca os anexos ja cadastrados para listar com opcao de remover.
        fetch(buildUrl(detailTpl, d.id), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => { if (data && data.ok) renderExisting(data.anexos); })
            .catch(() => {});
    }

    document.getElementById("createServicoButton")?.addEventListener("click", openCreate);

    document.querySelectorAll(".js-edit-servico").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            openEdit(btn.closest(".servicos-row"));
        });
    });

    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("servicoDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Modal de detalhe (visualizacao)
    // ------------------------------------------------------------------
    const detailEl = document.getElementById("servicoDetailModal");
    const detailModal = detailEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(detailEl) : null;
    const detailFiles = document.getElementById("detailAnexos");
    const detailFilesEmpty = document.getElementById("detailAnexosEmpty");
    const detailEditBtn = document.getElementById("detailEditBtn");
    let lastDetailRow = null;

    function openDetail(row) {
        if (!detailModal || !row) return;
        lastDetailRow = row;
        const d = row.dataset;
        // Preenche imediatamente com o que ja temos na linha.
        setText("detailNome", d.nome);
        setText("detailEmpresa", d.empresa);
        setText("detailDescricao", d.descricao);
        if (detailFiles) detailFiles.innerHTML = "";
        detailFilesEmpty?.classList.add("is-hidden");
        detailModal.show();
        // Completa com os dados formatados + anexos do backend.
        fetch(buildUrl(detailTpl, d.id), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data || !data.ok) return;
                setText("detailNome", data.nome_servico);
                setText("detailEmpresa", data.empresa);
                setText("detailData", data.data_servico);
                setText("detailValor", "R$ " + data.valor_display);
                setText("detailAutor", data.criado_por);
                setText("detailDescricao", data.descricao);
                if (detailFiles) {
                    detailFiles.innerHTML = "";
                    (data.anexos || []).forEach((a) => {
                        const li = document.createElement("li");
                        const link = document.createElement("a");
                        link.href = a.url;
                        link.target = "_blank";
                        link.rel = "noopener";
                        link.innerHTML = `📎 <span>${a.nome}</span>`;
                        li.appendChild(link);
                        detailFiles.appendChild(li);
                    });
                    detailFilesEmpty?.classList.toggle("is-hidden", (data.anexos || []).length > 0);
                }
            })
            .catch(() => {});
    }

    document.querySelectorAll(".js-view-servico").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.stopPropagation();
            openDetail(btn.closest(".servicos-row"));
        });
    });

    // Clique na linha abre o detalhe (exceto nos botoes de acao).
    document.querySelectorAll(".servicos-row").forEach((row) => {
        row.addEventListener("click", (e) => {
            if (e.target.closest(".servicos-cell--actions")) return;
            openDetail(row);
        });
        row.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDetail(row);
            }
        });
    });

    detailEditBtn?.addEventListener("click", () => {
        detailModal?.hide();
        if (lastDetailRow) openEdit(lastDetailRow);
    });

    // ------------------------------------------------------------------
    // Busca client-side
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("servicoSearch");
    const statusEl = document.getElementById("servicoSearchStatus");
    const noResults = document.getElementById("servicosNoResults");
    const tbody = document.getElementById("servicosTableBody");
    const rows = Array.from(document.querySelectorAll(".servicos-row"));

    function normalize(value) {
        return (value || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        statusEl.textContent = (searchInput && searchInput.value.trim())
            ? `${visible} de ${total} servico(s) encontrado(s).`
            : `${total} servico(s) no total.`;
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
    const headers = Array.from(document.querySelectorAll(".servicos-th"));
    let sortState = { index: -1, dir: 1 };

    function cellValue(row, index, type) {
        const cell = row.children[index];
        if (!cell) return "";
        if (type === "num") {
            const raw = cell.dataset.sortValue != null ? cell.dataset.sortValue : cell.textContent;
            return parseFloat(String(raw).replace(/[^0-9.\-]/g, "")) || 0;
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
            if (type === "date") {
                // Datas exibidas como dd/mm/aaaa -> compara por ISO.
                const toIso = (s) => s.split("/").reverse().join("-");
                return toIso(va).localeCompare(toIso(vb)) * dir;
            }
            return va.localeCompare(vb, "pt", { sensitivity: "base", numeric: true }) * dir;
        });
        ordered.forEach((row) => tbody.appendChild(row));
        headers.forEach((h) => {
            const isActive = Number(h.dataset.sortIndex) === index;
            h.setAttribute("aria-sort", isActive ? (dir === 1 ? "ascending" : "descending") : "none");
            const ind = h.querySelector(".servicos-sort-ind");
            if (ind) ind.textContent = isActive ? (dir === 1 ? "↑" : "↓") : "";
        });
    }

    headers.forEach((h) => {
        h.addEventListener("click", () => {
            sortBy(Number(h.dataset.sortIndex), h.dataset.sortType || "text");
        });
    });
})();
