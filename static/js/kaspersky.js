(function () {
    const app = document.querySelector(".kaspersky-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.kasperskyUpdateUrl;
    const deleteTpl = app.dataset.kasperskyDeleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };

    function normalize(value) {
        return (value || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    // ------------------------------------------------------------------
    // Abas: Dispositivos | Colaboradores
    // ------------------------------------------------------------------
    const tabs = Array.from(document.querySelectorAll(".ksp-tab"));
    const panes = Array.from(document.querySelectorAll(".ksp-pane"));
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const alvo = tab.dataset.tab;
            tabs.forEach((t) => {
                const ativo = t === tab;
                t.classList.toggle("is-active", ativo);
                t.setAttribute("aria-selected", ativo ? "true" : "false");
            });
            panes.forEach((p) => p.classList.toggle("is-hidden", p.dataset.pane !== alvo));
        });
    });

    // ------------------------------------------------------------------
    // Modais: importar, licencas e edicao do dispositivo
    // ------------------------------------------------------------------
    const importModalEl = document.getElementById("kspImportModal");
    const importModal = importModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(importModalEl) : null;
    document.getElementById("importKasperskyButton")?.addEventListener("click", () => importModal?.show());

    const licencasModalEl = document.getElementById("kspLicencasModal");
    const licencasModal = licencasModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(licencasModalEl) : null;
    document.getElementById("ksLicencasCard")?.addEventListener("click", () => licencasModal?.show());

    const modalEl = document.getElementById("kspModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("kspForm");
    const deleteForm = document.getElementById("kspDeleteForm");
    const deleteConfirm = document.getElementById("kspDeleteConfirm");
    const infoEl = document.getElementById("kspInfo");
    const ramalSelect = document.getElementById("kspRamal");

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    // Os dados tecnicos vem do portal e nao sao editaveis: aparecem so como resumo.
    function renderInfo(d) {
        if (!infoEl) return;
        const linhas = [
            ["Status", d.status || "-"],
            ["Antivirus", d.versaoApp ? `instalado (${d.versaoApp})` : "nao instalado"],
            ["Agente de Rede", d.versaoAgente || "-"],
            ["IP", d.ip || "-"],
            ["Grupo", d.grupo || "-"],
            ["Ultima conexao", d.ultimaConexao || "-"],
        ];
        infoEl.innerHTML = linhas
            .map(([k, v]) => `<div class="ksp-info__item"><span>${k}</span><strong></strong></div>`)
            .join("");
        // Preenche o valor via textContent para nao injetar HTML vindo do arquivo.
        infoEl.querySelectorAll(".ksp-info__item strong").forEach((el, i) => {
            el.textContent = linhas[i][1];
        });
    }

    function openEdit(row) {
        if (!form) return;
        const d = row.dataset;
        document.getElementById("kspModalLabel").textContent = d.nome;
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("kspSetor", d.setor === "Sem setor" ? "" : d.setor);
        setVal("kspResponsavel", d.responsavel);
        setVal("kspObservacoes", d.observacoes);
        setVal("kspRamal", d.ramal || "");
        renderInfo({
            status: row.querySelector(".ksp-badge")?.textContent.trim(),
            versaoApp: d.versaoApp,
            versaoAgente: d.versaoAgente,
            ip: d.ip,
            grupo: d.grupo,
            ultimaConexao: d.ultimaConexao,
        });
        resetDelete();
        modal?.show();
    }

    document.querySelectorAll(".js-edit-ksp").forEach((btn) => {
        btn.addEventListener("click", () => {
            const row = btn.closest(".ksp-row");
            if (row) openEdit(row);
        });
    });

    document.getElementById("kspDeleteBtn")?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("kspDeleteCancel")?.addEventListener("click", resetDelete);

    // Escolher o colaborador preenche setor e responsavel quando estiverem vazios.
    ramalSelect?.addEventListener("change", () => {
        const opcao = ramalSelect.selectedOptions[0];
        if (!opcao || !opcao.value) return;
        const setor = document.getElementById("kspSetor");
        const responsavel = document.getElementById("kspResponsavel");
        if (setor && !setor.value.trim()) setor.value = opcao.dataset.setor || "";
        if (responsavel && !responsavel.value.trim()) responsavel.value = opcao.dataset.nome || "";
    });

    // ------------------------------------------------------------------
    // Busca + filtros da aba Dispositivos
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("kspSearch");
    const statusEl = document.getElementById("kspSearchStatus");
    const noResults = document.getElementById("kspNoResults");
    const rows = Array.from(document.querySelectorAll(".ksp-row"));
    const statusChips = Array.from(document.querySelectorAll("#kspStatusChips .ips-chip"));
    const setorChips = Array.from(document.querySelectorAll("#kspSetorChips .ips-chip"));
    let situacao = "";
    let setorAtivo = "";

    function matchSituacao(row) {
        if (!situacao) return true;
        if (situacao === "critico") return row.dataset.status === "critico";
        if (situacao === "sem-antivirus") return row.dataset.antivirus === "nao";
        if (situacao === "sem-conexao") return row.dataset.conexao === "sem";
        if (situacao === "fora-export") return row.dataset.export === "nao";
        return true;
    }

    function applyFilters() {
        const termo = normalize(searchInput?.value).trim();
        let visiveis = 0;
        rows.forEach((row) => {
            const okTexto = !termo || normalize(row.dataset.search).includes(termo);
            const okSetor = !setorAtivo || row.dataset.setor === setorAtivo;
            const mostrar = okTexto && okSetor && matchSituacao(row);
            row.classList.toggle("is-hidden", !mostrar);
            if (mostrar) visiveis += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visiveis !== 0 || rows.length === 0);
        if (statusEl) {
            const filtrando = termo || setorAtivo || situacao;
            statusEl.textContent = filtrando
                ? `${visiveis} de ${rows.length} dispositivo(s) encontrado(s).`
                : `${rows.length} dispositivo(s) no total.`;
        }
    }

    searchInput?.addEventListener("input", applyFilters);

    function ligarChips(chips, aoEscolher) {
        chips.forEach((chip) => {
            chip.addEventListener("click", () => {
                chips.forEach((c) => {
                    const ativo = c === chip;
                    c.classList.toggle("is-active", ativo);
                    c.setAttribute("aria-selected", ativo ? "true" : "false");
                });
                aoEscolher(chip);
                applyFilters();
            });
        });
    }

    ligarChips(statusChips, (chip) => { situacao = chip.dataset.situacao || ""; });
    ligarChips(setorChips, (chip) => { setorAtivo = chip.dataset.setor || ""; });
    applyFilters();

    // ------------------------------------------------------------------
    // Busca + filtro da aba Colaboradores
    // ------------------------------------------------------------------
    const colabRows = Array.from(document.querySelectorAll(".ksp-colab-row"));
    const colabSearch = document.getElementById("kspColabSearch");
    const colabStatus = document.getElementById("kspColabStatus");
    const colabNoResults = document.getElementById("kspColabNoResults");
    const colabChips = Array.from(document.querySelectorAll("#kspColabChips .ips-chip"));
    let colabSituacao = "";

    function applyColabFilters() {
        const termo = normalize(colabSearch?.value).trim();
        let visiveis = 0;
        colabRows.forEach((row) => {
            const okTexto = !termo || normalize(row.dataset.search).includes(termo);
            const okSituacao = !colabSituacao || row.dataset.situacao === colabSituacao;
            const mostrar = okTexto && okSituacao;
            row.classList.toggle("is-hidden", !mostrar);
            if (mostrar) visiveis += 1;
        });
        if (colabNoResults) colabNoResults.classList.toggle("is-hidden", visiveis !== 0 || colabRows.length === 0);
        if (colabStatus) {
            const filtrando = termo || colabSituacao;
            colabStatus.textContent = filtrando
                ? `${visiveis} de ${colabRows.length} colaborador(es) encontrado(s).`
                : `${colabRows.length} colaborador(es) na lista de ramais.`;
        }
    }

    colabSearch?.addEventListener("input", applyColabFilters);
    colabChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            colabChips.forEach((c) => {
                const ativo = c === chip;
                c.classList.toggle("is-active", ativo);
                c.setAttribute("aria-selected", ativo ? "true" : "false");
            });
            colabSituacao = chip.dataset.situacao || "";
            applyColabFilters();
        });
    });
    applyColabFilters();

    // ------------------------------------------------------------------
    // Ordenacao da tabela de dispositivos
    // ------------------------------------------------------------------
    const tbody = document.getElementById("kspTableBody");
    const headers = Array.from(document.querySelectorAll("#kspTable .ips-th"));
    let sortState = { index: -1, dir: 1 };

    function cellText(row, index) {
        const cell = row.children[index];
        return cell ? cell.textContent.trim() : "";
    }

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

    headers.forEach((h) => {
        h.addEventListener("click", () => {
            const index = Number(h.dataset.sortIndex);
            if (Number.isNaN(index) || !tbody) return;
            const dir = sortState.index === index ? -sortState.dir : 1;
            sortState = { index, dir };
            const tipo = h.dataset.sortType || "text";
            rows.slice()
                .sort((a, b) => {
                    const va = cellText(a, index);
                    const vb = cellText(b, index);
                    if (tipo === "ip") {
                        const na = ipToNumber(va);
                        const nb = ipToNumber(vb);
                        if (na !== null && nb !== null) return (na - nb) * dir;
                    }
                    return va.localeCompare(vb, "pt", { sensitivity: "base", numeric: true }) * dir;
                })
                .forEach((row) => tbody.appendChild(row));
            headers.forEach((outro) => {
                const ativo = Number(outro.dataset.sortIndex) === index;
                outro.setAttribute("aria-sort", ativo ? (dir === 1 ? "ascending" : "descending") : "none");
                const ind = outro.querySelector(".ips-sort-ind");
                if (ind) ind.textContent = ativo ? (dir === 1 ? "↑" : "↓") : "";
            });
        });
    });
})();
