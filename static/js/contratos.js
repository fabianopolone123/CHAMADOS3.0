(function () {
    const appElement = document.querySelector(".contratos-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const requisicaoCreateUrl = appElement.dataset.requisicaoCreateUrl;
    const requisicaoDetailTpl = appElement.dataset.requisicaoDetailUrl;
    const orcamentoCreateTpl = appElement.dataset.orcamentoCreateUrl;
    const suborcamentoCreateTpl = appElement.dataset.suborcamentoCreateUrl;
    const orcamentoAprovarTpl = appElement.dataset.orcamentoAprovarUrl;
    const requisicaoMarcarEntregueTpl = appElement.dataset.requisicaoMarcarEntregueUrl;

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

    async function sendForm(url, formData) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "X-CSRFToken": getCookie("csrftoken"),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData,
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

    // ------------------------------------------------------------------
    // Criacao de requisicao
    // ------------------------------------------------------------------
    const requisicoesList = document.getElementById("requisicoesList");
    const createReqModalEl = document.getElementById("createRequisicaoModal");
    const createReqModal = createReqModalEl ? bootstrap.Modal.getOrCreateInstance(createReqModalEl) : null;
    const createReqForm = document.getElementById("createRequisicaoForm");

    document.getElementById("createRequisicaoButton")?.addEventListener("click", () => {
        createReqForm?.reset();
        createReqModal?.show();
    });

    function addRequisicaoToList(req) {
        const empty = requisicoesList.querySelector(".requisicoes-empty");
        if (empty) {
            empty.remove();
        }
        const li = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "requisicao-item";
        button.dataset.requisicaoId = req.id;

        if (req.codigo) {
            const code = document.createElement("span");
            code.className = "requisicao-item__code";
            code.textContent = req.codigo;
            button.appendChild(code);
        }

        const title = document.createElement("span");
        title.className = "requisicao-item__title";
        title.textContent = req.titulo;

        const badge = document.createElement("span");
        badge.className = `status-badge contrato-status contrato-status--${req.status}`;
        badge.textContent = req.status_label;

        button.appendChild(title);
        button.appendChild(badge);
        button.addEventListener("click", () => openRequisicaoDetail(req.id));
        li.appendChild(button);
        requisicoesList.insertBefore(li, requisicoesList.firstChild);
    }

    createReqForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = document.getElementById("createRequisicaoSubmit");
        if (submit) submit.disabled = true;
        try {
            const data = await sendJson(requisicaoCreateUrl, {
                titulo: document.getElementById("requisicaoTitulo").value.trim(),
                tipo: document.getElementById("requisicaoTipo").value,
                texto: document.getElementById("requisicaoTexto").value.trim(),
            });
            addRequisicaoToList(data.requisicao);
            createReqModal?.hide();
            createReqForm.reset();
            showToast(data.message || "Requisicao criada.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel criar a requisicao.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ------------------------------------------------------------------
    // Detalhe da requisicao
    // ------------------------------------------------------------------
    const detailModalEl = document.getElementById("requisicaoDetailModal");
    const detailModal = detailModalEl ? bootstrap.Modal.getOrCreateInstance(detailModalEl) : null;
    let currentRequisicaoId = null;
    let currentRequisicaoStatus = null;

    function setDetailField(key, value) {
        const el = detailModalEl.querySelector(`[data-req-detail="${key}"]`);
        if (el) el.textContent = value || "-";
    }

    function makeInfo(label, value) {
        const wrap = document.createElement("div");
        const b = document.createElement("b");
        b.textContent = label;
        const span = document.createElement("span");
        span.textContent = value;
        wrap.appendChild(b);
        wrap.appendChild(span);
        return wrap;
    }

    function renderMediaRow(item) {
        const row = document.createElement("div");
        row.className = "orcamento-media-row";
        if (item.foto_url) {
            const img = document.createElement("img");
            img.className = "orcamento-thumb";
            img.src = item.foto_url;
            img.alt = "Foto do produto";
            img.addEventListener("click", () => window.open(item.foto_url, "_blank"));
            row.appendChild(img);
        }
        if (item.link) {
            const a = document.createElement("a");
            a.className = "orcamento-link";
            a.href = item.link;
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = "Link do produto";
            row.appendChild(a);
        }
        (item.documentos || []).forEach((doc) => {
            const a = document.createElement("a");
            a.className = "orcamento-doc-link";
            a.href = doc.url;
            a.textContent = doc.nome;
            row.appendChild(a);
        });
        return row;
    }

    function renderSuborcamento(sub) {
        const card = document.createElement("div");
        card.className = "suborcamento-card";
        const title = document.createElement("p");
        title.className = "suborcamento-card__title";
        title.textContent = sub.titulo;
        card.appendChild(title);

        const grid = document.createElement("div");
        grid.className = "orcamento-card__grid";
        grid.appendChild(makeInfo("Loja", sub.loja));
        grid.appendChild(makeInfo("Moeda", sub.moeda));
        grid.appendChild(makeInfo("Valor", sub.valor));
        grid.appendChild(makeInfo("Qtd", String(sub.quantidade)));
        grid.appendChild(makeInfo("Frete", sub.frete));
        grid.appendChild(makeInfo("Desconto", sub.desconto));
        card.appendChild(grid);

        card.appendChild(renderMediaRow(sub));

        const total = document.createElement("div");
        total.className = "orcamento-total-row";
        const label = document.createElement("span");
        label.className = "suborcamento-card__meta";
        label.textContent = "Total do suborcamento";
        const badge = document.createElement("span");
        badge.className = "orcamento-total-badge";
        badge.textContent = sub.total_display;
        total.appendChild(label);
        total.appendChild(badge);
        card.appendChild(total);
        return card;
    }

    function renderOrcamento(orc) {
        const card = document.createElement("div");
        card.className = "orcamento-card" + (orc.aprovado ? " orcamento-card--aprovado" : "");

        const head = document.createElement("div");
        head.className = "orcamento-card__head";
        const headLeft = document.createElement("div");
        const title = document.createElement("h6");
        title.className = "orcamento-card__title";
        title.textContent = orc.titulo;
        const loja = document.createElement("span");
        loja.className = "orcamento-card__loja";
        loja.textContent = orc.loja;
        headLeft.appendChild(title);
        headLeft.appendChild(loja);
        head.appendChild(headLeft);
        if (orc.aprovado) {
            const chip = document.createElement("span");
            chip.className = "orcamento-aprovado-chip";
            chip.textContent = orc.aprovado_em ? `Aprovado em ${orc.aprovado_em}` : "Aprovado";
            head.appendChild(chip);
        }
        card.appendChild(head);

        const grid = document.createElement("div");
        grid.className = "orcamento-card__grid";
        grid.appendChild(makeInfo("Moeda", orc.moeda));
        grid.appendChild(makeInfo("Valor", orc.valor));
        grid.appendChild(makeInfo("Qtd", String(orc.quantidade)));
        grid.appendChild(makeInfo("Frete", orc.frete));
        grid.appendChild(makeInfo("Desconto", orc.desconto));
        grid.appendChild(makeInfo("Subtotal", orc.subtotal_display));
        card.appendChild(grid);

        card.appendChild(renderMediaRow(orc));

        const totalRow = document.createElement("div");
        totalRow.className = "orcamento-total-row";
        const t1 = document.createElement("span");
        t1.className = "orcamento-total-badge";
        t1.textContent = `Total: ${orc.total_display}`;
        const t2 = document.createElement("span");
        t2.className = "orcamento-total-badge orcamento-total-badge--final";
        t2.textContent = `Total + suborcamentos: ${orc.total_com_suborcamentos_display}`;
        totalRow.appendChild(t1);
        totalRow.appendChild(t2);
        card.appendChild(totalRow);

        if (orc.suborcamentos && orc.suborcamentos.length) {
            const subList = document.createElement("div");
            subList.className = "suborcamentos-list";
            orc.suborcamentos.forEach((sub) => subList.appendChild(renderSuborcamento(sub)));
            card.appendChild(subList);
        }

        const actions = document.createElement("div");
        actions.className = "orcamento-card__actions";

        const entregue = currentRequisicaoStatus === "entregue";
        if (orc.aprovado && entregue) {
            // Requisicao ja entregue: mostra o estado, sem acao.
            const done = document.createElement("span");
            done.className = "orcamento-entregue-chip";
            done.textContent = "Entregue";
            actions.appendChild(done);
        } else if (orc.aprovado) {
            // Aprovado e aguardando entrega: botao vira "Marcar entregue".
            const deliverBtn = document.createElement("button");
            deliverBtn.type = "button";
            deliverBtn.className = "btn btn-sm btn-success marcar-entregue-btn";
            deliverBtn.textContent = "Marcar entregue";
            deliverBtn.addEventListener("click", () => marcarEntregue(deliverBtn));
            actions.appendChild(deliverBtn);

            const undoBtn = document.createElement("button");
            undoBtn.type = "button";
            undoBtn.className = "btn btn-sm btn-outline-secondary aprovar-orcamento-btn";
            undoBtn.textContent = "Remover aprovacao";
            undoBtn.addEventListener("click", () => aprovarOrcamento(orc.id, undoBtn));
            actions.appendChild(undoBtn);
        } else if (!entregue) {
            // Nao aprovado (e requisicao nao entregue): permite aprovar.
            const approveBtn = document.createElement("button");
            approveBtn.type = "button";
            approveBtn.className = "btn btn-sm btn-success aprovar-orcamento-btn";
            approveBtn.textContent = "Aprovar orcamento";
            approveBtn.addEventListener("click", () => aprovarOrcamento(orc.id, approveBtn));
            actions.appendChild(approveBtn);
        }

        const addSub = document.createElement("button");
        addSub.type = "button";
        addSub.className = "btn btn-light btn-sm add-suborcamento-btn";
        addSub.textContent = "+ Suborcamento";
        addSub.addEventListener("click", () => openOrcamentoForm("suborcamento", orc.id, orc.titulo));
        actions.appendChild(addSub);

        card.appendChild(actions);

        return card;
    }

    function updateRequisicaoListBadge(id, status, statusLabel) {
        const btn = requisicoesList?.querySelector(`.requisicao-item[data-requisicao-id="${id}"]`);
        const badge = btn ? btn.querySelector(".status-badge") : null;
        if (badge) {
            badge.className = `status-badge contrato-status contrato-status--${status}`;
            badge.textContent = statusLabel;
        }
    }

    async function aprovarOrcamento(orcamentoId, button) {
        if (!orcamentoAprovarTpl) {
            return;
        }
        if (button) {
            button.disabled = true;
        }
        try {
            const data = await sendJson(buildUrl(orcamentoAprovarTpl, orcamentoId), {});
            // Recarrega o detalhe (destaque do aprovado + status da requisicao).
            if (currentRequisicaoId) {
                await loadRequisicaoDetail(currentRequisicaoId);
            }
            updateRequisicaoListBadge(data.requisicao_id, data.requisicao_status, data.requisicao_status_label);
            showToast(data.message || "Orcamento atualizado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel aprovar o orcamento.", "error");
            if (button) {
                button.disabled = false;
            }
        }
    }

    async function marcarEntregue(button) {
        if (!requisicaoMarcarEntregueTpl || !currentRequisicaoId) {
            return;
        }
        if (button) {
            button.disabled = true;
        }
        try {
            const data = await sendJson(buildUrl(requisicaoMarcarEntregueTpl, currentRequisicaoId), {});
            await loadRequisicaoDetail(currentRequisicaoId);
            updateRequisicaoListBadge(data.requisicao_id, data.requisicao_status, data.requisicao_status_label);
            showToast(data.message || "Requisicao entregue.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel marcar como entregue.", "error");
            if (button) {
                button.disabled = false;
            }
        }
    }

    function renderOrcamentos(orcamentos) {
        const container = detailModalEl.querySelector("[data-orcamentos]");
        const empty = detailModalEl.querySelector("[data-orcamentos-empty]");
        container.innerHTML = "";
        if (!orcamentos || !orcamentos.length) {
            empty.classList.remove("is-hidden");
            return;
        }
        empty.classList.add("is-hidden");
        orcamentos.forEach((orc) => container.appendChild(renderOrcamento(orc)));
    }

    function renderTimeline(eventos) {
        const list = detailModalEl.querySelector("[data-req-timeline]");
        const empty = detailModalEl.querySelector("[data-req-timeline-empty]");
        if (!list) {
            return;
        }
        list.innerHTML = "";
        if (!eventos || !eventos.length) {
            if (empty) empty.classList.remove("is-hidden");
            return;
        }
        if (empty) empty.classList.add("is-hidden");
        eventos.forEach((ev) => {
            const li = document.createElement("li");
            li.className = `requisicao-timeline__item requisicao-timeline__item--${ev.tipo}`;
            const head = document.createElement("div");
            head.className = "requisicao-timeline__head";
            const data = document.createElement("span");
            data.className = "requisicao-timeline__date";
            data.textContent = ev.data;
            const autor = document.createElement("span");
            autor.className = "requisicao-timeline__author";
            autor.textContent = ev.usuario;
            head.appendChild(data);
            head.appendChild(autor);
            const desc = document.createElement("p");
            desc.className = "requisicao-timeline__desc";
            desc.textContent = ev.descricao;
            li.appendChild(head);
            li.appendChild(desc);
            list.appendChild(li);
        });
    }

    async function loadRequisicaoDetail(id) {
        const data = await sendGet(buildUrl(requisicaoDetailTpl, id));
        const req = data.requisicao;
        currentRequisicaoStatus = req.status;
        setDetailField("codigo", req.codigo || "Requisicao");
        setDetailField("titulo", req.titulo);
        setDetailField("tipo", req.tipo_label);
        setDetailField("criado_por", req.criado_por);
        setDetailField("criado_em", req.criado_em);
        setDetailField("texto", req.texto || "Sem texto.");
        const statusBadge = detailModalEl.querySelector('[data-req-detail="status"]');
        if (statusBadge) {
            statusBadge.textContent = req.status_label;
            statusBadge.className = `status-badge contrato-status contrato-status--${req.status}`;
        }
        renderOrcamentos(data.orcamentos);
        renderTimeline(data.eventos);
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

    async function openRequisicaoDetail(id) {
        try {
            currentRequisicaoId = id;
            await loadRequisicaoDetail(id);
            detailModal?.show();
        } catch (error) {
            showToast(error.message || "Nao foi possivel abrir a requisicao.", "error");
        }
    }

    // liga os itens ja renderizados no servidor
    requisicoesList?.querySelectorAll(".requisicao-item").forEach((btn) => {
        btn.addEventListener("click", () => openRequisicaoDetail(btn.dataset.requisicaoId));
    });

    // botao "+ Orcamento" dentro do detalhe
    detailModalEl?.querySelector("[data-add-orcamento]")?.addEventListener("click", () => {
        if (currentRequisicaoId) {
            openOrcamentoForm("orcamento", currentRequisicaoId, null);
        }
    });

    // ------------------------------------------------------------------
    // Exclusao de requisicao (com confirmacao)
    // ------------------------------------------------------------------
    const requisicaoDeleteTpl = appElement.dataset.requisicaoDeleteUrl;
    const deleteModalEl = document.getElementById("requisicaoDeleteModal");
    const deleteModal = deleteModalEl ? bootstrap.Modal.getOrCreateInstance(deleteModalEl) : null;
    let returnToDetailFromDelete = false;

    function removeRequisicaoFromList(id) {
        const btn = requisicoesList?.querySelector(`.requisicao-item[data-requisicao-id="${id}"]`);
        const li = btn ? btn.closest("li") : null;
        if (li) li.remove();
        if (requisicoesList && !requisicoesList.querySelector(".requisicao-item") && !requisicoesList.querySelector(".requisicoes-empty")) {
            const p = document.createElement("p");
            p.className = "requisicoes-empty";
            p.textContent = requisicoesList.dataset.emptyText || "Nenhuma requisicao cadastrada ainda.";
            requisicoesList.appendChild(p);
        }
    }

    // abre a confirmacao (empilha sobre o detalhe: esconde e reabre ao cancelar)
    detailModalEl?.querySelector("[data-delete-requisicao]")?.addEventListener("click", () => {
        if (!currentRequisicaoId || !deleteModal) return;
        returnToDetailFromDelete = true;
        detailModal?.hide();
        deleteModal.show();
    });

    deleteModalEl?.addEventListener("hidden.bs.modal", () => {
        if (returnToDetailFromDelete && currentRequisicaoId) {
            detailModal?.show();
        }
        returnToDetailFromDelete = false;
    });

    deleteModalEl?.querySelector("[data-confirm-delete-requisicao]")?.addEventListener("click", async (event) => {
        const button = event.currentTarget;
        if (!currentRequisicaoId || !requisicaoDeleteTpl) return;
        button.disabled = true;
        try {
            const data = await sendJson(buildUrl(requisicaoDeleteTpl, currentRequisicaoId), {});
            returnToDetailFromDelete = false; // sucesso: nao reabre o detalhe
            removeRequisicaoFromList(currentRequisicaoId);
            currentRequisicaoId = null;
            deleteModal?.hide();
            showToast(data.message || "Requisicao excluida.", "success");
        } catch (error) {
            // erro: mantem a requisicao; o detalhe reabre ao fechar a confirmacao
            deleteModal?.hide();
            showToast(error.message || "Nao foi possivel excluir a requisicao.", "error");
        } finally {
            button.disabled = false;
        }
    });

    // ------------------------------------------------------------------
    // Formulario de orcamento / suborcamento (+ captura de print)
    // ------------------------------------------------------------------
    const orcFormModalEl = document.getElementById("orcamentoFormModal");
    const orcFormModal = orcFormModalEl ? bootstrap.Modal.getOrCreateInstance(orcFormModalEl) : null;
    const orcForm = document.getElementById("orcamentoForm");

    let formMode = "orcamento"; // "orcamento" | "suborcamento"
    let formParentId = null;
    let returnToDetail = false;
    let capturedFile = null;

    const fotoInput = orcFormModalEl.querySelector("[data-foto-input]");
    const fotoPreviewWrap = orcFormModalEl.querySelector("[data-foto-preview-wrap]");
    const fotoPreviewImg = orcFormModalEl.querySelector("[data-foto-preview]");
    const printHint = orcFormModalEl.querySelector("[data-print-hint]");
    const workspace = orcFormModalEl.querySelector("[data-print-workspace]");
    const printCanvas = orcFormModalEl.querySelector("[data-print-canvas]");
    const printSelection = orcFormModalEl.querySelector("[data-print-selection]");
    const cropButton = orcFormModalEl.querySelector("[data-print-crop]");

    function resetFoto() {
        capturedFile = null;
        if (fotoInput) fotoInput.value = "";
        if (fotoPreviewImg) fotoPreviewImg.src = "";
        fotoPreviewWrap?.classList.add("is-hidden");
    }

    function showFotoPreview(url) {
        if (fotoPreviewImg) fotoPreviewImg.src = url;
        fotoPreviewWrap?.classList.remove("is-hidden");
    }

    function hideWorkspace() {
        workspace?.classList.add("is-hidden");
        printSelection?.classList.add("is-hidden");
        if (cropButton) cropButton.disabled = true;
    }

    function openOrcamentoForm(mode, parentId, parentTitle) {
        formMode = mode;
        formParentId = parentId;
        orcForm.reset();
        resetFoto();
        hideWorkspace();
        if (printHint) printHint.textContent = "";

        const kicker = orcFormModalEl.querySelector("[data-orc-kicker]");
        const title = orcFormModalEl.querySelector("[data-orc-title]");
        const submit = orcFormModalEl.querySelector("[data-orc-submit]");
        if (mode === "suborcamento") {
            kicker.textContent = "Suborcamento";
            title.textContent = parentTitle ? `Novo suborcamento de: ${parentTitle}` : "Novo suborcamento";
            submit.textContent = "Salvar suborcamento";
        } else {
            kicker.textContent = "Orcamento";
            title.textContent = "Novo orcamento";
            submit.textContent = "Salvar orcamento";
        }

        // Empilha sobre o detalhe: esconde o detalhe e reabre ao fechar o form.
        returnToDetail = detailModalEl.classList.contains("show");
        if (returnToDetail) {
            detailModal?.hide();
        }
        orcFormModal?.show();
    }

    // reabre o detalhe ao fechar o form (cancelar ou apos salvar)
    orcFormModalEl?.addEventListener("hidden.bs.modal", () => {
        if (returnToDetail && currentRequisicaoId) {
            detailModal?.show();
        }
        returnToDetail = false;
    });

    fotoInput?.addEventListener("change", () => {
        capturedFile = null; // arquivo manual tem prioridade do proprio input
        const file = fotoInput.files && fotoInput.files[0];
        if (file) {
            showFotoPreview(URL.createObjectURL(file));
        } else {
            fotoPreviewWrap?.classList.add("is-hidden");
        }
    });

    orcFormModalEl.querySelector("[data-foto-remove]")?.addEventListener("click", resetFoto);

    orcForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = orcFormModalEl.querySelector("[data-orc-submit]");
        if (submit) submit.disabled = true;

        const formData = new FormData(orcForm);
        // print recortado tem prioridade como foto_produto
        if (capturedFile) {
            formData.set("foto_produto", capturedFile, capturedFile.name);
        }

        const url =
            formMode === "suborcamento"
                ? buildUrl(suborcamentoCreateTpl, formParentId)
                : buildUrl(orcamentoCreateTpl, formParentId);

        try {
            const data = await sendForm(url, formData);
            // atualiza o detalhe antes de reabri-lo
            if (currentRequisicaoId) {
                await loadRequisicaoDetail(currentRequisicaoId);
            }
            orcFormModal?.hide();
            showToast(data.message || "Salvo com sucesso.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel salvar. Verifique os campos.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------- Captura de tela + recorte ----------
    const printStartButton = orcFormModalEl.querySelector("[data-print-start]");
    let selection = null;
    let dragging = false;
    let dragStart = null;

    async function startPrintCapture() {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
            if (printHint) {
                printHint.textContent = "Seu navegador nao suporta captura de tela. Anexe uma imagem manualmente.";
            }
            showToast("Captura de tela indisponivel neste navegador. Use o campo de imagem.", "warning");
            return;
        }
        let stream;
        try {
            stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
        } catch (error) {
            // usuario cancelou ou negou: nao trava o formulario
            if (printHint) printHint.textContent = "Captura cancelada.";
            return;
        }
        try {
            const video = document.createElement("video");
            video.srcObject = stream;
            video.muted = true;
            await video.play();
            await new Promise((resolve) => requestAnimationFrame(resolve));

            const w = video.videoWidth || 1280;
            const h = video.videoHeight || 720;
            printCanvas.width = w;
            printCanvas.height = h;
            printCanvas.getContext("2d").drawImage(video, 0, 0, w, h);

            selection = null;
            printSelection.classList.add("is-hidden");
            if (cropButton) cropButton.disabled = true;
            workspace.classList.remove("is-hidden");
            if (printHint) printHint.textContent = "Selecione a area e clique em Usar recorte.";
        } catch (error) {
            showToast("Nao foi possivel processar a captura.", "error");
        } finally {
            stream.getTracks().forEach((track) => track.stop());
        }
    }

    function canvasScale() {
        return {
            x: printCanvas.width / printCanvas.clientWidth,
            y: printCanvas.height / printCanvas.clientHeight,
        };
    }

    printCanvas?.addEventListener("mousedown", (event) => {
        dragging = true;
        const rect = printCanvas.getBoundingClientRect();
        dragStart = { x: event.clientX - rect.left, y: event.clientY - rect.top };
        selection = { x: dragStart.x, y: dragStart.y, w: 0, h: 0 };
        printSelection.classList.remove("is-hidden");
        updateSelectionBox();
    });

    printCanvas?.addEventListener("mousemove", (event) => {
        if (!dragging) return;
        const rect = printCanvas.getBoundingClientRect();
        const cx = event.clientX - rect.left;
        const cy = event.clientY - rect.top;
        selection = {
            x: Math.min(cx, dragStart.x),
            y: Math.min(cy, dragStart.y),
            w: Math.abs(cx - dragStart.x),
            h: Math.abs(cy - dragStart.y),
        };
        updateSelectionBox();
    });

    function endDrag() {
        if (!dragging) return;
        dragging = false;
        if (cropButton) cropButton.disabled = !(selection && selection.w > 4 && selection.h > 4);
    }
    printCanvas?.addEventListener("mouseup", endDrag);
    printCanvas?.addEventListener("mouseleave", endDrag);

    function updateSelectionBox() {
        if (!selection) return;
        // canvas esta dentro do wrap; offset do canvas relativo ao wrap
        printSelection.style.left = `${printCanvas.offsetLeft + selection.x}px`;
        printSelection.style.top = `${printCanvas.offsetTop + selection.y}px`;
        printSelection.style.width = `${selection.w}px`;
        printSelection.style.height = `${selection.h}px`;
    }

    cropButton?.addEventListener("click", () => {
        if (!selection || selection.w < 4 || selection.h < 4) return;
        const scale = canvasScale();
        const sx = selection.x * scale.x;
        const sy = selection.y * scale.y;
        const sw = selection.w * scale.x;
        const sh = selection.h * scale.y;
        const out = document.createElement("canvas");
        out.width = Math.round(sw);
        out.height = Math.round(sh);
        out.getContext("2d").drawImage(printCanvas, sx, sy, sw, sh, 0, 0, sw, sh);
        out.toBlob((blob) => {
            if (!blob) {
                showToast("Nao foi possivel gerar a imagem recortada.", "error");
                return;
            }
            capturedFile = new File([blob], "print.png", { type: "image/png" });
            if (fotoInput) fotoInput.value = ""; // print substitui a foto manual
            showFotoPreview(URL.createObjectURL(blob));
            hideWorkspace();
            if (printHint) printHint.textContent = "Print recortado anexado como foto do produto.";
        }, "image/png");
    });

    orcFormModalEl.querySelector("[data-print-cancel]")?.addEventListener("click", hideWorkspace);
    printStartButton?.addEventListener("click", startPrintCapture);
})();
