(function () {
    const appElement = document.querySelector(".emprestimos-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const createUrl = appElement.dataset.emprestimoCreateUrl;
    const detailTpl = appElement.dataset.emprestimoDetailUrl;
    const termoTpl = appElement.dataset.emprestimoTermoUrl;
    const anexarTpl = appElement.dataset.emprestimoAnexarUrl;
    const marcarOkTpl = appElement.dataset.emprestimoMarcarOkUrl;
    const assinaturaCreateUrl = appElement.dataset.assinaturaCreateUrl;

    const tbody = document.getElementById("emprestimosBody");
    const EMP_STATUS_CLASSES = [
        "emp-status--aguardando", "emp-status--assinada_ok", "emp-status--em_andamento",
        "emp-status--devolvido", "emp-status--cancelado",
    ];

    function buildUrl(template, id) {
        return template.replace("/0/", `/${id}/`);
    }
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(";").shift();
        return "";
    }
    function showToast(message, type) {
        if (typeof window.showAppToast === "function") window.showAppToast(message, type);
    }
    async function sendForm(url, formData) {
        const response = await fetch(url, {
            method: "POST",
            headers: { "X-CSRFToken": getCookie("csrftoken"), "X-Requested-With": "XMLHttpRequest" },
            body: formData,
        });
        let data = {};
        try { data = await response.json(); } catch (e) { data = { ok: false, message: "Resposta inesperada do servidor." }; }
        if (!response.ok || data.ok === false) throw data;
        return data;
    }
    async function sendGet(url) {
        const response = await fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        let data = {};
        try { data = await response.json(); } catch (e) { data = { ok: false, message: "Resposta inesperada do servidor." }; }
        if (!response.ok || data.ok === false) throw data;
        return data;
    }

    // ---------------- Lista ----------------
    function buildRow(emp) {
        const tr = document.createElement("tr");
        tr.className = "emprestimo-row";
        tr.dataset.emprestimoId = emp.id;
        const cols = [
            { v: emp.colaborador_nome, cls: "emprestimo-row__nome" },
            { v: emp.empresa },
            { v: emp.equipamento_principal },
            { v: String(emp.equipamentos_count) },
            { v: emp.data_emprestimo },
            { v: emp.devolucao },
        ];
        cols.forEach((c) => {
            const td = document.createElement("td");
            if (c.cls) td.className = c.cls;
            td.textContent = c.v;
            tr.appendChild(td);
        });
        const tdStatus = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = `status-badge emp-status emp-status--${emp.status}`;
        badge.textContent = emp.status_label;
        tdStatus.appendChild(badge);
        tr.appendChild(tdStatus);
        tr.addEventListener("click", () => openDetail(emp.id));
        return tr;
    }

    tbody?.querySelectorAll(".emprestimo-row").forEach((tr) => {
        tr.addEventListener("click", () => openDetail(tr.dataset.emprestimoId));
    });

    // ---------------- Assinatura ----------------
    const assinaturaModalEl = document.getElementById("createAssinaturaModal");
    const assinaturaModal = assinaturaModalEl ? bootstrap.Modal.getOrCreateInstance(assinaturaModalEl) : null;
    const assinaturaForm = document.getElementById("createAssinaturaForm");
    const assinaturaSelect = document.getElementById("emprestimoAssinatura");

    document.getElementById("openAssinaturaButton")?.addEventListener("click", () => {
        assinaturaForm?.reset();
        assinaturaModal?.show();
    });

    assinaturaForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = document.getElementById("createAssinaturaSubmit");
        if (submit) submit.disabled = true;
        try {
            const data = await sendForm(assinaturaCreateUrl, new FormData(assinaturaForm));
            if (assinaturaSelect) {
                const opt = document.createElement("option");
                opt.value = data.assinatura.id;
                opt.textContent = data.assinatura.nome_responsavel;
                assinaturaSelect.appendChild(opt);
                assinaturaSelect.value = data.assinatura.id;
            }
            assinaturaModal?.hide();
            assinaturaForm.reset();
            showToast(data.message || "Assinatura cadastrada.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel cadastrar a assinatura.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------------- Cadastro de emprestimo ----------------
    const createModalEl = document.getElementById("createEmprestimoModal");
    const createModal = createModalEl ? bootstrap.Modal.getOrCreateInstance(createModalEl) : null;
    const createForm = document.getElementById("createEmprestimoForm");
    const equipContainer = document.getElementById("equipamentosContainer");
    const equipTemplate = document.getElementById("equipamentoTemplate");
    let equipIndex = 0;

    function addEquipamentoBloco() {
        const html = equipTemplate.innerHTML.replace(/__I__/g, String(equipIndex));
        const wrapper = document.createElement("div");
        wrapper.innerHTML = html.trim();
        const bloco = wrapper.firstElementChild;
        bloco.dataset.equipIndex = equipIndex;
        bloco.querySelector("[data-equip-titulo]").textContent = `Equipamento ${equipContainer.children.length + 1}`;
        bloco.querySelector("[data-remove-equip]").addEventListener("click", () => {
            bloco.remove();
            renumerarBlocos();
        });
        equipContainer.appendChild(bloco);
        equipIndex += 1;
    }

    function renumerarBlocos() {
        equipContainer.querySelectorAll("[data-equip-bloco]").forEach((bloco, i) => {
            bloco.querySelector("[data-equip-titulo]").textContent = `Equipamento ${i + 1}`;
        });
    }

    document.getElementById("createEmprestimoButton")?.addEventListener("click", () => {
        createForm?.reset();
        equipContainer.innerHTML = "";
        equipIndex = 0;
        addEquipamentoBloco();
        createModal?.show();
    });

    document.getElementById("addEquipamentoButton")?.addEventListener("click", addEquipamentoBloco);

    createForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = document.getElementById("createEmprestimoSubmit");
        if (submit) submit.disabled = true;
        try {
            const formData = new FormData(createForm);
            formData.set("equipamentos_count", String(equipIndex));
            const data = await sendForm(createUrl, formData);
            const emptyRow = tbody.querySelector("[data-emprestimos-empty]");
            if (emptyRow) emptyRow.remove();
            tbody.insertBefore(buildRow(data.emprestimo), tbody.firstChild);
            createModal?.hide();
            showToast(data.message || "Emprestimo cadastrado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel cadastrar o emprestimo.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------------- Detalhe ----------------
    const detailModalEl = document.getElementById("emprestimoDetailModal");
    const detailModal = detailModalEl ? bootstrap.Modal.getOrCreateInstance(detailModalEl) : null;
    const anexarForm = document.getElementById("anexarTermoForm");
    let currentEmprestimoId = null;

    function setField(key, value) {
        const el = detailModalEl.querySelector(`[data-emp-detail="${key}"]`);
        if (el) el.textContent = value || "-";
    }

    function renderEquipamentos(equipamentos) {
        const container = detailModalEl.querySelector("[data-emp-equipamentos]");
        container.innerHTML = "";
        (equipamentos || []).forEach((eq, i) => {
            const card = document.createElement("div");
            card.className = "emp-equip-card";
            const title = document.createElement("p");
            title.className = "emp-equip-card__title";
            const partes = [eq.marca, eq.modelo].filter(Boolean).join(" ");
            title.textContent = `Equipamento ${i + 1}: ${eq.tipo_equipamento}${partes ? " " + partes : ""}`;
            const meta = document.createElement("div");
            meta.className = "emp-equip-card__meta";
            meta.textContent = `Serie: ${eq.numero_serie} | Patrimonio: ${eq.patrimonio_etiqueta} | Acessorios: ${eq.acessorios_entregues}`;
            card.appendChild(title);
            card.appendChild(meta);
            if (eq.fotos && eq.fotos.length) {
                const fotos = document.createElement("div");
                fotos.className = "emp-equip-fotos";
                eq.fotos.forEach((f) => {
                    const img = document.createElement("img");
                    img.src = f.url;
                    img.alt = f.nome;
                    img.addEventListener("click", () => window.open(f.url, "_blank"));
                    fotos.appendChild(img);
                });
                card.appendChild(fotos);
            }
            container.appendChild(card);
        });
    }

    function applyStatusBadge(status, statusLabel) {
        const badge = detailModalEl.querySelector("[data-emp-detail-status]");
        if (badge) {
            badge.textContent = statusLabel;
            badge.classList.remove(...EMP_STATUS_CLASSES);
            badge.classList.add(`emp-status--${status}`);
        }
    }

    function renderAssinadoInfo(data) {
        const sem = detailModalEl.querySelector("[data-emp-sem-assinado]");
        const meta = detailModalEl.querySelector("[data-emp-assinado-meta]");
        const link = detailModalEl.querySelector("[data-emp-assinado-link]");
        const quando = detailModalEl.querySelector("[data-emp-assinado-quando]");
        if (data.termo_assinado_url) {
            sem.classList.add("is-hidden");
            meta.classList.remove("is-hidden");
            link.href = data.termo_assinado_url;
            const partes = [];
            if (data.termo_assinado_em) partes.push(`Anexado em ${data.termo_assinado_em}`);
            if (data.termo_assinado_por) partes.push(`por ${data.termo_assinado_por}`);
            if (data.termo_assinado_ok) partes.push("(OK)");
            quando.textContent = partes.join(" ");
        } else {
            sem.classList.remove("is-hidden");
            meta.classList.add("is-hidden");
        }
    }

    async function openDetail(id) {
        try {
            currentEmprestimoId = id;
            const data = await sendGet(buildUrl(detailTpl, id));
            setField("colaborador_nome", data.colaborador_nome);
            setField("empresa", data.empresa);
            setField("cpf", data.cpf);
            setField("email", data.email);
            setField("telefone", data.telefone);
            setField("data_emprestimo", data.data_emprestimo);
            setField("devolucao", data.devolucao);
            setField("assinatura_responsavel", data.assinatura_responsavel);
            setField("criado_por", data.criado_por);
            setField("observacoes_internas", data.observacoes_internas || "Sem observacoes.");
            applyStatusBadge(data.status, data.status_label);
            renderEquipamentos(data.equipamentos);

            const baixar = detailModalEl.querySelector("[data-emp-baixar-termo]");
            if (data.termo_pdf_url) {
                baixar.href = data.termo_pdf_url;
                baixar.classList.remove("is-hidden");
            } else {
                baixar.classList.add("is-hidden");
            }
            renderAssinadoInfo(data);
            detailModal?.show();
        } catch (error) {
            showToast(error.message || "Nao foi possivel abrir o emprestimo.", "error");
        }
    }

    anexarForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        if (!currentEmprestimoId) return;
        const submit = anexarForm.querySelector("[data-anexar-submit]");
        if (submit) submit.disabled = true;
        try {
            const data = await sendForm(buildUrl(anexarTpl, currentEmprestimoId), new FormData(anexarForm));
            renderAssinadoInfo({
                termo_assinado_url: data.termo_assinado_url,
                termo_assinado_em: data.termo_assinado_em,
                termo_assinado_por: data.termo_assinado_por,
                termo_assinado_ok: false,
            });
            anexarForm.reset();
            showToast(data.message || "Termo assinado anexado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel anexar o termo.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    detailModalEl?.querySelector("[data-marcar-ok]")?.addEventListener("click", async () => {
        if (!currentEmprestimoId) return;
        try {
            const data = await sendForm(buildUrl(marcarOkTpl, currentEmprestimoId), new FormData());
            applyStatusBadge(data.status, data.status_label);
            // atualiza o badge na linha da tabela
            const row = tbody.querySelector(`.emprestimo-row[data-emprestimo-id="${currentEmprestimoId}"] .emp-status`);
            if (row) {
                row.textContent = data.status_label;
                row.classList.remove(...EMP_STATUS_CLASSES);
                row.classList.add(`emp-status--${data.status}`);
            }
            showToast(data.message || "Documentacao marcada como OK.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel marcar a documentacao.", "error");
        }
    });
})();
