(function () {
    const appElement = document.querySelector(".ramais-app");
    if (!appElement) {
        return;
    }

    const updateTpl = appElement.dataset.ramalUpdateUrl;
    const deleteTpl = appElement.dataset.ramalDeleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    function buildUrl(template, id) {
        return template ? template.replace("/0/", `/${id}/`) : "";
    }

    function getCookie(name) {
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; ${name}=`);
        return partes.length === 2 ? partes.pop().split(";").shift() : "";
    }

    // Liga um par select(conta) + input(email): escolher no select preenche o
    // e-mail e, se vazio, o colaborador; digitar no e-mail solta a vinculacao.
    function wireEmailPair(selectId, emailId, colaboradorId) {
        const select = document.getElementById(selectId);
        const emailInput = document.getElementById(emailId);
        const colaboradorInput = document.getElementById(colaboradorId);
        if (!select || !emailInput) return;
        select.addEventListener("change", () => {
            const opt = select.options[select.selectedIndex];
            if (!opt || !opt.value) return;
            const email = opt.getAttribute("data-email") || "";
            const nome = opt.getAttribute("data-nome") || "";
            if (email) emailInput.value = email;
            if (nome && colaboradorInput && !colaboradorInput.value.trim()) {
                colaboradorInput.value = nome;
            }
        });
        emailInput.addEventListener("input", () => {
            // E-mail digitado manualmente: nao fica vinculado a uma conta.
            select.value = "";
        });
    }

    wireEmailPair("ramalEmailSelect", "ramalEmailInput", "ramalColaborador");
    wireEmailPair("editRamalEmailSelect", "editRamalEmailInput", "editRamalColaborador");

    // ---------------- Cadastro ----------------
    const createModalEl = document.getElementById("createRamalModal");
    const createModal = createModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(createModalEl) : null;
    document.getElementById("createRamalButton")?.addEventListener("click", () => createModal?.show());

    // ---------------- Edicao / exclusao ----------------
    const editModalEl = document.getElementById("editRamalModal");
    const editModal = editModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(editModalEl) : null;
    const editForm = document.getElementById("editRamalForm");
    const deleteForm = document.getElementById("deleteRamalForm");
    const deleteConfirm = document.getElementById("ramalDeleteConfirm");

    function setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value || "";
    }

    function openEdit(row) {
        if (!editModal) return;
        const d = row.dataset;
        if (editForm) editForm.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("editRamalColaborador", d.colaborador);
        setVal("editRamalSetor", d.setor);
        setVal("editRamalTelefone", d.telefone);
        setVal("editRamalRamal", d.ramal);
        setVal("editRamalEmailInput", d.email);
        setVal("editRamalEmailSelect", d.contaId || "");
        const checkKaspersky = document.getElementById("editRamalKaspersky");
        if (checkKaspersky) checkKaspersky.checked = d.kaspersky === "sim";
        deleteConfirm?.classList.add("is-hidden");
        editForm?.classList.remove("is-hidden");
        editModal.show();
    }

    document.getElementById("editRamalDeleteBtn")?.addEventListener("click", () => {
        editForm?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("ramalDeleteCancel")?.addEventListener("click", () => {
        deleteConfirm?.classList.add("is-hidden");
        editForm?.classList.remove("is-hidden");
    });

    // ---------------- Lista: linhas clicaveis + busca + ordenacao ----------------
    const searchInput = document.getElementById("ramalSearch");
    const statusEl = document.getElementById("ramalSearchStatus");
    const noResults = document.getElementById("ramaisNoResults");
    const tbody = document.getElementById("ramaisTableBody");
    let rows = Array.from(document.querySelectorAll(".ramais-row"));

    rows.forEach((row) => {
        row.addEventListener("click", (event) => {
            // Nao abrir o modal ao clicar no link de e-mail (mailto) nem no
            // tique do Kaspersky - a linha inteira e clicavel para editar.
            if (event.target.closest(".ramais-mail-link")) return;
            if (event.target.closest(".ramais-check")) return;
            openEdit(row);
        });
        row.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                if (event.target.closest(".ramais-check")) return;  // espaco marca o tique
                event.preventDefault();
                openEdit(row);
            }
        });
    });

    // ------------------------------------------------------------------
    // Tique do Kaspersky direto na lista
    // ------------------------------------------------------------------
    // Salva na hora (sem recarregar) e atualiza os cartoes de resumo. Se o POST
    // falhar, o tique volta ao estado anterior para a tela nao mentir.
    const kasperskyTpl = appElement.dataset.ramalKasperskyUrl;

    function atualizarResumoKaspersky(com, sem) {
        const elCom = document.querySelector("[data-stat-com-kaspersky]");
        const elSem = document.querySelector("[data-stat-sem-kaspersky]");
        if (elCom && typeof com === "number") elCom.textContent = com;
        if (elSem && typeof sem === "number") elSem.textContent = sem;
    }

    function textoDoTique(check) {
        const rotulo = check.closest(".ramais-check")?.querySelector(".ramais-check__texto");
        if (rotulo) rotulo.textContent = check.checked ? "instalado" : "nao";
    }

    if (kasperskyTpl) {
        document.querySelectorAll("[data-kaspersky-toggle]").forEach((check) => {
            check.addEventListener("click", (event) => event.stopPropagation());
            check.addEventListener("change", async () => {
                const row = check.closest(".ramais-row");
                const desejado = check.checked;
                check.disabled = true;
                try {
                    const resposta = await fetch(buildUrl(kasperskyTpl, row.dataset.id), {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-CSRFToken": getCookie("csrftoken"),
                            "X-Requested-With": "XMLHttpRequest",
                        },
                        body: JSON.stringify({ instalado: desejado }),
                    });
                    const dados = await resposta.json();
                    if (!resposta.ok || dados.ok === false) throw dados;

                    check.checked = dados.instalado;
                    row.dataset.kaspersky = dados.instalado ? "sim" : "nao";
                    // mantem a busca coerente com o novo estado
                    row.dataset.search = (row.dataset.search || "")
                        .replace(/(com kaspersky instalado antivirus|sem kaspersky sem antivirus)/, "")
                        .trim()
                        + (dados.instalado ? " com kaspersky instalado antivirus" : " sem kaspersky sem antivirus");
                    textoDoTique(check);
                    atualizarResumoKaspersky(dados.com_kaspersky, dados.sem_kaspersky);
                    if (typeof window.showAppToast === "function") {
                        window.showAppToast(dados.message, "success");
                    }
                } catch (erro) {
                    check.checked = !desejado;  // desfaz: o servidor nao aceitou
                    textoDoTique(check);
                    if (typeof window.showAppToast === "function") {
                        window.showAppToast(erro.message || "Nao foi possivel salvar o tique.", "error");
                    }
                } finally {
                    check.disabled = false;
                }
            });
        });
    }

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        if (!searchInput || !searchInput.value.trim()) {
            statusEl.textContent = `${total} ramal(is) no total.`;
        } else {
            statusEl.textContent = `${visible} de ${total} ramal(is) encontrado(s).`;
        }
    }

    function filterRows() {
        const term = (searchInput?.value || "").trim().toLowerCase();
        let visible = 0;
        rows.forEach((row) => {
            const match = !term || (row.dataset.search || "").indexOf(term) !== -1;
            row.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterRows);
    updateStatus(rows.length);

    // Ordenacao ao clicar nos cabecalhos.
    const headers = Array.from(document.querySelectorAll(".ramais-th"));
    let sortState = { index: -1, dir: 1 };

    function cellText(row, index) {
        const cell = row.children[index];
        return cell ? cell.textContent.trim() : "";
    }

    function sortBy(index, numeric) {
        const dir = sortState.index === index ? -sortState.dir : 1;
        sortState = { index, dir };
        const ordered = rows.slice().sort((a, b) => {
            let va = cellText(a, index);
            let vb = cellText(b, index);
            if (numeric) {
                const na = parseFloat(va.replace(/\D/g, "")) || 0;
                const nb = parseFloat(vb.replace(/\D/g, "")) || 0;
                return (na - nb) * dir;
            }
            return va.localeCompare(vb, "pt", { sensitivity: "base" }) * dir;
        });
        ordered.forEach((row) => tbody.appendChild(row));
        headers.forEach((h) => {
            const isActive = Number(h.dataset.sortIndex) === index;
            h.setAttribute("aria-sort", isActive ? (dir === 1 ? "ascending" : "descending") : "none");
            const ind = h.querySelector(".ramais-sort-ind");
            if (ind) ind.textContent = isActive ? (dir === 1 ? "↑" : "↓") : "";
        });
    }

    headers.forEach((h) => {
        h.addEventListener("click", () => {
            sortBy(Number(h.dataset.sortIndex), h.dataset.sortNumeric === "1");
        });
    });
})();
