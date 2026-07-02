(function () {
    const appElement = document.querySelector(".insumos-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const insumoCreateUrl = appElement.dataset.insumoCreateUrl;
    const retiradaCreateTpl = appElement.dataset.retiradaCreateUrl;

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

    function buildCard(insumo) {
        const card = document.createElement("article");
        card.className = `insumo-card insumo-card--${insumo.status}`;
        card.dataset.insumoId = insumo.id;
        card.dataset.insumoNome = insumo.nome;

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
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm btn-outline-primary insumo-retirar-btn";
        btn.dataset.retirar = "";
        btn.textContent = "Retirar";
        btn.addEventListener("click", () => openRetiradaModal(card));
        foot.appendChild(qtyWrap);
        foot.appendChild(btn);

        card.appendChild(head);
        card.appendChild(desc);
        card.appendChild(foot);
        return card;
    }

    function bindCard(card) {
        card.querySelector("[data-retirar]")?.addEventListener("click", () => openRetiradaModal(card));
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

    function prependRetiradaRow(retirada) {
        const emptyRow = retiradasBody.querySelector("[data-retiradas-empty]");
        if (emptyRow) emptyRow.remove();
        const tr = document.createElement("tr");
        const cells = [
            retirada.insumo,
            String(retirada.quantidade),
            retirada.entregue_para,
            retirada.motivo,
            retirada.registrado_por,
            retirada.criado_em,
        ];
        cells.forEach((value, index) => {
            const td = document.createElement("td");
            if (index === 3) td.className = "insumos-table__motivo";
            td.textContent = value;
            tr.appendChild(td);
        });
        retiradasBody.insertBefore(tr, retiradasBody.firstChild);
    }

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
