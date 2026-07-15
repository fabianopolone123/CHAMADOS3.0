(function () {
    const appElement = document.querySelector(".insumos-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const insumoCreateUrl = appElement.dataset.insumoCreateUrl;
    const insumoUpdateTpl = appElement.dataset.insumoUpdateUrl;
    const insumoEntradaTpl = appElement.dataset.insumoEntradaUrl;
    const insumoDeleteTpl = appElement.dataset.insumoDeleteUrl;
    const retiradaCreateTpl = appElement.dataset.retiradaCreateUrl;

    const EDIT_ICON = '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>';

    const grid = document.getElementById("insumosGrid");
    const retiradasBody = document.getElementById("retiradasBody");

    const STATUS_CLASSES = ["insumo-card--disponivel", "insumo-card--baixo", "insumo-card--zerado"];
    const BADGE_CLASSES = ["insumo-status--disponivel", "insumo-status--baixo", "insumo-status--zerado"];

    function buildUrl(template, id) {
        return template.replace("/0/", `/${id}/`);
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function showToast(message, type) {
        if (typeof window.showAppToast === "function") {
            window.showAppToast(message, type);
        }
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

    // ---------------- Cards de estoque ----------------
    function applyCardStatus(card, insumo) {
        card.classList.remove(...STATUS_CLASSES);
        card.classList.add(`insumo-card--${insumo.status}`);
        const qty = card.querySelector("[data-insumo-qty]");
        if (qty) qty.textContent = insumo.quantidade_atual;
        const badge = card.querySelector("[data-insumo-status]");
        if (badge) {
            badge.textContent = insumo.status_label;
            badge.classList.remove(...BADGE_CLASSES);
            badge.classList.add(`insumo-status--${insumo.status}`);
        }
    }

    function applyCardFull(card, insumo) {
        applyCardStatus(card, insumo);
        card.dataset.insumoNome = insumo.nome;
        card.dataset.insumoDescricao = insumo.descricao || "";
        card.dataset.insumoObservacao = insumo.observacao || "";
        const name = card.querySelector(".insumo-card__name");
        if (name) name.textContent = insumo.nome;
        const desc = card.querySelector(".insumo-card__desc");
        if (desc) desc.textContent = insumo.descricao || "Sem descricao.";
    }

    function buildCard(insumo) {
        const card = document.createElement("article");
        card.className = `insumo-card insumo-card--${insumo.status}`;
        card.dataset.insumoId = insumo.id;
        card.dataset.insumoNome = insumo.nome;
        card.dataset.insumoDescricao = insumo.descricao || "";
        card.dataset.insumoObservacao = insumo.observacao || "";

        const head = document.createElement("div");
        head.className = "insumo-card__head";
        const name = document.createElement("h4");
        name.className = "insumo-card__name";
        name.textContent = insumo.nome;
        const badge = document.createElement("span");
        badge.className = `status-badge insumo-status insumo-status--${insumo.status}`;
        badge.dataset.insumoStatus = "";
        badge.textContent = insumo.status_label;
        head.appendChild(name);
        head.appendChild(badge);

        const desc = document.createElement("p");
        desc.className = "insumo-card__desc";
        desc.textContent = insumo.descricao || "Sem descricao.";

        const foot = document.createElement("div");
        foot.className = "insumo-card__foot";
        const qtyWrap = document.createElement("span");
        qtyWrap.className = "insumo-card__qty";
        qtyWrap.append("Em estoque: ");
        const qtyStrong = document.createElement("strong");
        qtyStrong.dataset.insumoQty = "";
        qtyStrong.textContent = insumo.quantidade_atual;
        qtyWrap.appendChild(qtyStrong);
        const actions = document.createElement("span");
        actions.className = "insumo-card__actions";
        const editarBtn = document.createElement("button");
        editarBtn.type = "button";
        editarBtn.className = "insumo-icon-btn";
        editarBtn.dataset.editar = "";
        editarBtn.title = "Editar insumo";
        editarBtn.setAttribute("aria-label", "Editar insumo");
        editarBtn.innerHTML = EDIT_ICON;
        editarBtn.addEventListener("click", () => openEditModal(card));
        const minusBtn = document.createElement("button");
        minusBtn.type = "button";
        minusBtn.className = "insumo-step-btn insumo-step-btn--minus";
        minusBtn.dataset.retirar = "";
        minusBtn.title = "Retirar (baixa de estoque)";
        minusBtn.setAttribute("aria-label", "Retirar");
        minusBtn.innerHTML = "&minus;";
        minusBtn.addEventListener("click", () => openRetiradaModal(card));
        const plusBtn = document.createElement("button");
        plusBtn.type = "button";
        plusBtn.className = "insumo-step-btn insumo-step-btn--plus";
        plusBtn.dataset.entrada = "";
        plusBtn.title = "Entrada (adicionar ao estoque)";
        plusBtn.setAttribute("aria-label", "Adicionar");
        plusBtn.textContent = "+";
        plusBtn.addEventListener("click", () => openEntradaModal(card));
        actions.appendChild(editarBtn);
        actions.appendChild(minusBtn);
        actions.appendChild(plusBtn);
        foot.appendChild(qtyWrap);
        foot.appendChild(actions);

        card.appendChild(head);
        card.appendChild(desc);
        card.appendChild(foot);
        return card;
    }

    function bindCard(card) {
        card.querySelector("[data-retirar]")?.addEventListener("click", () => openRetiradaModal(card));
        card.querySelector("[data-editar]")?.addEventListener("click", () => openEditModal(card));
        card.querySelector("[data-entrada]")?.addEventListener("click", () => openEntradaModal(card));
    }

    // ---------------- Modal de cadastro ----------------
    const createModalEl = document.getElementById("createInsumoModal");
    const createModal = createModalEl ? bootstrap.Modal.getOrCreateInstance(createModalEl) : null;
    const createForm = document.getElementById("createInsumoForm");

    document.getElementById("createInsumoButton")?.addEventListener("click", () => {
        createForm?.reset();
        createModal?.show();
    });

    createForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = document.getElementById("createInsumoSubmit");
        if (submit) submit.disabled = true;
        try {
            const data = await sendJson(insumoCreateUrl, {
                nome: document.getElementById("insumoNome").value.trim(),
                descricao: document.getElementById("insumoDescricao").value.trim(),
                quantidade_inicial: document.getElementById("insumoQuantidade").value,
                observacao: document.getElementById("insumoObservacao").value.trim(),
            });
            const empty = grid.querySelector(".insumos-empty");
            if (empty) empty.remove();
            grid.insertBefore(buildCard(data.insumo), grid.firstChild);
            createModal?.hide();
            createForm.reset();
            showToast(data.message || "Insumo cadastrado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel cadastrar o insumo.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------------- Modal de edicao ----------------
    const editModalEl = document.getElementById("editInsumoModal");
    const editModal = editModalEl ? bootstrap.Modal.getOrCreateInstance(editModalEl) : null;
    const editForm = document.getElementById("editInsumoForm");
    let editingCard = null;

    const delTrigger = editModalEl?.querySelector("[data-insumo-delete]");
    const delConfirm = editModalEl?.querySelector("[data-insumo-delete-confirm]");

    function resetDeleteConfirm() {
        if (delTrigger) delTrigger.hidden = false;
        if (delConfirm) delConfirm.hidden = true;
    }

    function openEditModal(card) {
        editingCard = card;
        document.getElementById("editInsumoNome").value = card.dataset.insumoNome || "";
        document.getElementById("editInsumoDescricao").value = card.dataset.insumoDescricao || "";
        document.getElementById("editInsumoObservacao").value = card.dataset.insumoObservacao || "";
        resetDeleteConfirm();
        editModal?.show();
    }

    editForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!editingCard) return;
        const submit = document.getElementById("editInsumoSubmit");
        if (submit) submit.disabled = true;
        try {
            const url = buildUrl(insumoUpdateTpl, editingCard.dataset.insumoId);
            const data = await sendJson(url, {
                nome: document.getElementById("editInsumoNome").value.trim(),
                descricao: document.getElementById("editInsumoDescricao").value.trim(),
                observacao: document.getElementById("editInsumoObservacao").value.trim(),
            });
            applyCardFull(editingCard, data.insumo);
            editModal?.hide();
            showToast(data.message || "Insumo atualizado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel atualizar o insumo.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    delTrigger?.addEventListener("click", () => {
        delTrigger.hidden = true;
        if (delConfirm) delConfirm.hidden = false;
    });
    editModalEl?.querySelector("[data-insumo-delete-cancel]")?.addEventListener("click", resetDeleteConfirm);
    editModalEl?.querySelector("[data-insumo-delete-yes]")?.addEventListener("click", async () => {
        if (!editingCard) return;
        try {
            const url = buildUrl(insumoDeleteTpl, editingCard.dataset.insumoId);
            const data = await sendJson(url, {});
            editingCard.remove();
            editingCard = null;
            editModal?.hide();
            showToast(data.message || "Insumo excluido.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel excluir o insumo.", "error");
        }
    });

    // ---------------- Modal de entrada (+) ----------------
    const entradaModalEl = document.getElementById("entradaInsumoModal");
    const entradaModal = entradaModalEl ? bootstrap.Modal.getOrCreateInstance(entradaModalEl) : null;
    const entradaForm = document.getElementById("entradaInsumoForm");
    let entradaCard = null;

    function openEntradaModal(card) {
        entradaCard = card;
        entradaModalEl.querySelector("[data-entrada-insumo]").textContent = card.dataset.insumoNome || "Insumo";
        entradaModalEl.querySelector("[data-entrada-atual]").textContent =
            card.querySelector("[data-insumo-qty]")?.textContent || "0";
        entradaForm.reset();
        document.getElementById("entradaQuantidade").value = 1;
        entradaModal?.show();
    }

    entradaForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!entradaCard) return;
        const submit = document.getElementById("entradaSubmit");
        if (submit) submit.disabled = true;
        try {
            const url = buildUrl(insumoEntradaTpl, entradaCard.dataset.insumoId);
            const data = await sendJson(url, { quantidade: document.getElementById("entradaQuantidade").value });
            applyCardStatus(entradaCard, data.insumo);
            if (data.retirada) prependRetiradaRow(data.retirada);
            entradaModal?.hide();
            showToast(data.message || "Entrada registrada.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel registrar a entrada.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------------- Modal de retirada ----------------
    const retiradaModalEl = document.getElementById("retiradaModal");
    const retiradaModal = retiradaModalEl ? bootstrap.Modal.getOrCreateInstance(retiradaModalEl) : null;
    const retiradaForm = document.getElementById("retiradaForm");
    let currentCard = null;

    function openRetiradaModal(card) {
        currentCard = card;
        const nome = card.dataset.insumoNome || "Insumo";
        const disponivel = card.querySelector("[data-insumo-qty]")?.textContent || "0";
        retiradaModalEl.querySelector("[data-retirada-insumo]").textContent = nome;
        retiradaModalEl.querySelector("[data-retirada-disponivel]").textContent = disponivel;
        retiradaForm.reset();
        document.getElementById("retiradaQuantidade").value = 1;
        document.getElementById("retiradaQuantidade").max = disponivel;
        retiradaModal?.show();
    }

    function buildRetiradaRow(mov) {
        const tr = document.createElement("tr");
        const tipoTd = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `mov-badge mov-badge--${mov.tipo}`;
        badge.textContent = mov.tipo_label;
        tipoTd.appendChild(badge);
        tr.appendChild(tipoTd);
        const cells = [
            mov.insumo,
            String(mov.quantidade),
            mov.entregue_para,
            mov.motivo,
            mov.registrado_por,
            mov.criado_em,
        ];
        cells.forEach((value, index) => {
            const td = document.createElement("td");
            if (index === 3) td.className = "insumos-table__motivo";
            td.textContent = value;
            tr.appendChild(td);
        });
        return tr;
    }

    function prependRetiradaRow(retirada) {
        const emptyRow = retiradasBody.querySelector("[data-retiradas-empty]");
        if (emptyRow) emptyRow.remove();
        retiradasBody.insertBefore(buildRetiradaRow(retirada), retiradasBody.firstChild);
    }

    function renderRetiradas(lista) {
        retiradasBody.innerHTML = "";
        if (!lista.length) {
            const tr = document.createElement("tr");
            tr.dataset.retiradasEmpty = "";
            const td = document.createElement("td");
            td.colSpan = 7;
            td.className = "insumos-empty";
            td.textContent = "Nenhuma movimentacao encontrada.";
            tr.appendChild(td);
            retiradasBody.appendChild(tr);
            return;
        }
        const frag = document.createDocumentFragment();
        lista.forEach((r) => frag.appendChild(buildRetiradaRow(r)));
        retiradasBody.appendChild(frag);
    }

    // ---------------- Busca no historico de retiradas ----------------
    const retiradasSearchUrl = appElement.dataset.retiradasSearchUrl;
    const searchInput = document.getElementById("retiradasSearch");
    let searchTimer = null;
    let searchController = null;

    async function runRetiradasSearch(q) {
        if (!retiradasSearchUrl) return;
        if (searchController) searchController.abort();
        searchController = new AbortController();
        try {
            const resp = await fetch(`${retiradasSearchUrl}?q=${encodeURIComponent(q || "")}`, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
                signal: searchController.signal,
            });
            const data = await resp.json();
            if (!resp.ok || data.ok === false) throw data;
            renderRetiradas(data.resultados || []);
        } catch (error) {
            if (error.name === "AbortError") return;
            showToast(error.message || "Nao foi possivel pesquisar as retiradas.", "error");
        }
    }

    searchInput?.addEventListener("input", () => {
        if (searchTimer) window.clearTimeout(searchTimer);
        const value = searchInput.value.trim();
        searchTimer = window.setTimeout(() => runRetiradasSearch(value), 300);
    });

    retiradaForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!currentCard) return;
        const submit = document.getElementById("retiradaSubmit");
        if (submit) submit.disabled = true;
        try {
            const url = buildUrl(retiradaCreateTpl, currentCard.dataset.insumoId);
            const data = await sendJson(url, {
                quantidade: document.getElementById("retiradaQuantidade").value,
                entregue_para: document.getElementById("retiradaEntreguePara").value.trim(),
                motivo: document.getElementById("retiradaMotivo").value.trim(),
            });
            applyCardStatus(currentCard, data.insumo);
            prependRetiradaRow(data.retirada);
            retiradaModal?.hide();
            showToast(data.message || "Retirada registrada.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel registrar a retirada.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // liga os cards ja renderizados no servidor
    grid?.querySelectorAll(".insumo-card").forEach(bindCard);
})();
