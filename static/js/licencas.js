(function () {
    const app = document.querySelector(".licencas-app");
    if (!app) {
        return;
    }

    const softwareUpdateTpl = app.dataset.softwareUpdateUrl;
    const softwareDeleteTpl = app.dataset.softwareDeleteUrl;
    const licencaUpdateTpl = app.dataset.licencaUpdateUrl;
    const licencaDeleteTpl = app.dataset.licencaDeleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    function buildUrl(template, id) {
        return template ? template.replace("/0/", `/${id}/`) : "";
    }

    function setVal(id, value) {
        const el = document.getElementById(id);
        if (el) el.value = value == null ? "" : value;
    }

    // ------------------------------------------------------------------
    // Modais Bootstrap
    // ------------------------------------------------------------------
    const softwareModalEl = document.getElementById("softwareModal");
    const licencaModalEl = document.getElementById("licencaModal");
    const softwareModal = softwareModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(softwareModalEl) : null;
    const licencaModal = licencaModalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(licencaModalEl) : null;

    const softwareForm = document.getElementById("softwareForm");
    const softwareDeleteForm = document.getElementById("softwareDeleteForm");
    const softwareDeleteConfirm = document.getElementById("softwareDeleteConfirm");
    const softwareDeleteBtn = document.getElementById("softwareDeleteBtn");

    const licencaForm = document.getElementById("licencaForm");
    const licencaDeleteForm = document.getElementById("licencaDeleteForm");
    const licencaDeleteConfirm = document.getElementById("licencaDeleteConfirm");
    const licencaDeleteBtn = document.getElementById("licencaDeleteBtn");

    // ------------------------------------------------------------------
    // Software: cadastrar / editar / excluir
    // ------------------------------------------------------------------
    function resetSoftwareDelete() {
        softwareDeleteConfirm?.classList.add("is-hidden");
        softwareForm?.classList.remove("is-hidden");
    }

    // Guarda o action de criacao original (antes de qualquer edicao trocar).
    const createSoftwareAction = softwareForm ? softwareForm.getAttribute("action") : "";

    function openSoftwareCreate() {
        if (!softwareForm) return;
        document.getElementById("softwareModalLabel").textContent = "Cadastrar novo software";
        document.getElementById("softwareSubmit").textContent = "Cadastrar software";
        softwareForm.action = createSoftwareAction;
        setVal("softwareNome", "");
        setVal("softwareQuantidade", "1");
        setVal("softwareObservacoes", "");
        softwareDeleteBtn?.classList.add("is-hidden");
        resetSoftwareDelete();
        softwareModal?.show();
    }

    function openSoftwareEdit(d) {
        if (!softwareForm) return;
        document.getElementById("softwareModalLabel").textContent = "Editar software";
        document.getElementById("softwareSubmit").textContent = "Salvar alteracoes";
        softwareForm.action = buildUrl(softwareUpdateTpl, d.id);
        if (softwareDeleteForm) softwareDeleteForm.action = buildUrl(softwareDeleteTpl, d.id);
        setVal("softwareNome", d.nome);
        setVal("softwareQuantidade", d.quantidade);
        setVal("softwareObservacoes", d.observacoes);
        softwareDeleteBtn?.classList.remove("is-hidden");
        resetSoftwareDelete();
        softwareModal?.show();
    }

    document.getElementById("createSoftwareButton")?.addEventListener("click", openSoftwareCreate);

    document.querySelectorAll(".js-edit-software").forEach((btn) => {
        btn.addEventListener("click", () => openSoftwareEdit(btn.dataset));
    });

    softwareDeleteBtn?.addEventListener("click", () => {
        softwareForm?.classList.add("is-hidden");
        softwareDeleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("softwareDeleteCancel")?.addEventListener("click", resetSoftwareDelete);

    // ------------------------------------------------------------------
    // Licenca: cadastrar / editar / excluir
    // ------------------------------------------------------------------
    const createLicencaAction = licencaForm ? licencaForm.getAttribute("action") : "";
    const licencaTipo = document.getElementById("licencaTipo");
    const licencaExpiraWrap = document.getElementById("licencaExpiraWrap");

    function toggleExpira() {
        const show = licencaTipo && licencaTipo.value === "expira_em";
        licencaExpiraWrap?.classList.toggle("is-hidden", !show);
    }
    licencaTipo?.addEventListener("change", toggleExpira);

    function resetLicencaDelete() {
        licencaDeleteConfirm?.classList.add("is-hidden");
        licencaForm?.classList.remove("is-hidden");
    }

    function openLicencaCreate(softwareId) {
        if (!licencaForm) return;
        document.getElementById("licencaModalLabel").textContent = "Cadastrar nova licenca";
        document.getElementById("licencaSubmit").textContent = "Cadastrar licenca";
        licencaForm.action = createLicencaAction;
        setVal("licencaSoftware", softwareId || "");
        setVal("licencaUsuario", "");
        setVal("licencaSerial", "");
        setVal("licencaEmail", "");
        setVal("licencaTipo", "indeterminado");
        setVal("licencaExpira", "");
        setVal("licencaPagamento", "");
        setVal("licencaCartao", "");
        setVal("licencaObservacoes", "");
        toggleExpira();
        licencaDeleteBtn?.classList.add("is-hidden");
        resetLicencaDelete();
        licencaModal?.show();
    }

    function openLicencaEdit(d) {
        if (!licencaForm) return;
        document.getElementById("licencaModalLabel").textContent = "Editar licenca";
        document.getElementById("licencaSubmit").textContent = "Salvar alteracoes";
        licencaForm.action = buildUrl(licencaUpdateTpl, d.id);
        if (licencaDeleteForm) licencaDeleteForm.action = buildUrl(licencaDeleteTpl, d.id);
        setVal("licencaSoftware", d.software);
        setVal("licencaUsuario", d.usuario);
        setVal("licencaSerial", d.serial);
        setVal("licencaEmail", d.email);
        setVal("licencaTipo", d.tipo || "indeterminado");
        setVal("licencaExpira", d.expira);
        setVal("licencaPagamento", d.pagamento);
        setVal("licencaCartao", d.cartao);
        setVal("licencaObservacoes", d.observacoes);
        toggleExpira();
        licencaDeleteBtn?.classList.remove("is-hidden");
        resetLicencaDelete();
        licencaModal?.show();
    }

    document.getElementById("createLicencaButton")?.addEventListener("click", () => openLicencaCreate(""));

    document.querySelectorAll(".js-add-licenca").forEach((btn) => {
        btn.addEventListener("click", () => openLicencaCreate(btn.dataset.softwareId));
    });

    document.querySelectorAll(".js-edit-licenca").forEach((btn) => {
        btn.addEventListener("click", () => {
            const row = btn.closest(".lic-row");
            if (row) openLicencaEdit(row.dataset);
        });
    });

    licencaDeleteBtn?.addEventListener("click", () => {
        licencaForm?.classList.add("is-hidden");
        licencaDeleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("licencaDeleteCancel")?.addEventListener("click", resetLicencaDelete);

    // ------------------------------------------------------------------
    // Colapsar / expandir cada software
    // ------------------------------------------------------------------
    document.querySelectorAll(".lic-software__toggle").forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const card = toggle.closest(".lic-software");
            const collapsed = card.classList.toggle("is-collapsed");
            toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
        });
    });

    // ------------------------------------------------------------------
    // Busca client-side (filtra os softwares)
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("licencaSearch");
    const statusEl = document.getElementById("licencaSearchStatus");
    const noResults = document.getElementById("licencasNoResults");
    const cards = Array.from(document.querySelectorAll(".lic-software"));

    function normalize(value) {
        return (value || "")
            .toString()
            .normalize("NFD")
            .replace(/[̀-ͯ]/g, "")
            .toLowerCase();
    }

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = cards.length;
        if (!searchInput || !searchInput.value.trim()) {
            statusEl.textContent = `${total} software(s) cadastrado(s).`;
        } else {
            statusEl.textContent = `${visible} de ${total} software(s) encontrado(s).`;
        }
    }

    function filterCards() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        cards.forEach((card) => {
            const match = !term || normalize(card.dataset.search).includes(term);
            card.classList.toggle("is-hidden", !match);
            if (match) {
                visible += 1;
                if (term) card.classList.remove("is-collapsed");
            }
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || cards.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterCards);
    updateStatus(cards.length);
})();
