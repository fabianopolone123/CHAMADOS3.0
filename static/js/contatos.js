/* Modulo Contatos: pessoa + computador (GLPI) + e-mail + ramal + antivirus.
   (Nao confundir com contratos.js, que e o modulo Requisicoes.) */
(function () {
    const app = document.querySelector(".contatos-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.computadorUpdateUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";
    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");

    function normalize(value) {
        return (value || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    }

    // ------------------------------------------------------------------
    // Modais: importar CSV do GLPI e detalhe/vinculo do computador
    // ------------------------------------------------------------------
    const importModalEl = document.getElementById("ctImportModal");
    const importModal = importModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(importModalEl) : null;
    document.getElementById("importContatosButton")?.addEventListener("click", () => importModal?.show());

    const pcModalEl = document.getElementById("ctPcModal");
    const pcModal = pcModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(pcModalEl) : null;
    const pcForm = document.getElementById("ctPcForm");
    const pcInfo = document.getElementById("ctPcInfo");
    const pcRamal = document.getElementById("ctPcRamal");

    function renderInfo(d, temAntivirus, noImport) {
        if (!pcInfo) return;
        const linhas = [
            ["Usuario no GLPI", d.pcUsuario || "-"],
            ["Tipo", d.pcTipo || "-"],
            ["Fabricante", d.pcFabricante || "-"],
            ["Modelo", d.pcModelo || "-"],
            ["Processador", d.pcProcessador || "-"],
            ["Sistema", d.pcSistema || "-"],
            ["Localizacao", d.pcLocal || "-"],
            ["Status", d.pcStatus || "-"],
            ["Antivirus", temAntivirus ? "instalado (Kaspersky)" : "nao encontrado no Kaspersky"],
            ["Atualizado no GLPI", d.pcAtualizado || "-"],
        ];
        if (noImport === "nao") {
            linhas.push(["Atencao", "nao veio na ultima importacao do GLPI"]);
        }
        pcInfo.innerHTML = linhas
            .map(([k]) => `<div class="ksp-info__item"><span>${k}</span><strong></strong></div>`)
            .join("");
        pcInfo.querySelectorAll(".ksp-info__item strong").forEach((el, i) => {
            el.textContent = linhas[i][1];
        });
    }

    document.querySelectorAll(".js-pc").forEach((btn) => {
        btn.addEventListener("click", () => {
            const d = btn.dataset;
            document.getElementById("ctPcModalLabel").textContent = d.pcNome;
            if (pcForm) pcForm.action = buildUrl(updateTpl, d.pcId);
            renderInfo(d, d.pcAntivirus === "sim", d.pcImport);
            if (pcRamal) pcRamal.value = d.pcRamal || "";
            pcModal?.show();
        });
    });

    // ------------------------------------------------------------------
    // Busca + filtros
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("ctSearch");
    const statusEl = document.getElementById("ctStatus");
    const noResults = document.getElementById("ctNoResults");
    const rows = Array.from(document.querySelectorAll(".ct-row"));
    const chips = Array.from(document.querySelectorAll("#ctChips .ips-chip"));
    const setorChips = Array.from(document.querySelectorAll("#ctSetorChips .ips-chip"));
    let filtro = "";
    let setorAtivo = "";

    function matchFiltro(row) {
        if (!filtro) return true;
        if (filtro === "com-computador") return row.dataset.computador === "sim";
        if (filtro === "sem-computador") return row.dataset.computador === "nao";
        if (filtro === "sem-antivirus") {
            return row.dataset.computador === "sim" && row.dataset.antivirus === "nao";
        }
        if (filtro === "sem-ramal") return row.dataset.ramalCadastrado === "nao";
        return true;
    }

    function applyFilters() {
        const termo = normalize(searchInput?.value).trim();
        let visiveis = 0;
        rows.forEach((row) => {
            const okTexto = !termo || normalize(row.dataset.search).includes(termo);
            const okSetor = !setorAtivo || row.dataset.setor === setorAtivo;
            const mostrar = okTexto && okSetor && matchFiltro(row);
            row.classList.toggle("is-hidden", !mostrar);
            if (mostrar) visiveis += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visiveis !== 0 || rows.length === 0);
        if (statusEl) {
            const filtrando = termo || setorAtivo || filtro;
            statusEl.textContent = filtrando
                ? `${visiveis} de ${rows.length} contato(s) encontrado(s).`
                : `${rows.length} contato(s) no total.`;
        }
    }

    searchInput?.addEventListener("input", applyFilters);

    function ligarChips(lista, aoEscolher) {
        lista.forEach((chip) => {
            chip.addEventListener("click", () => {
                lista.forEach((c) => {
                    const ativo = c === chip;
                    c.classList.toggle("is-active", ativo);
                    c.setAttribute("aria-selected", ativo ? "true" : "false");
                });
                aoEscolher(chip);
                applyFilters();
            });
        });
    }

    ligarChips(chips, (chip) => { filtro = chip.dataset.filtro || ""; });
    ligarChips(setorChips, (chip) => { setorAtivo = chip.dataset.setor || ""; });
    applyFilters();
})();
