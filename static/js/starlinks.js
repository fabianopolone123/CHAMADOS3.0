(function () {
    const app = document.querySelector(".star-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };

    // ------------------------------------------------------------------
    // Senha nos cards: mostrar/ocultar e copiar
    // ------------------------------------------------------------------
    document.querySelectorAll(".js-toggle-pass").forEach((btn) => {
        btn.addEventListener("click", () => {
            const val = btn.parentElement.querySelector(".star-pass__value");
            if (!val) return;
            const real = val.dataset.real || "";
            if (val.dataset.shown === "1") {
                val.textContent = "••••••••";
                val.dataset.shown = "0";
            } else {
                val.textContent = real || "-";
                val.dataset.shown = "1";
            }
        });
    });

    document.querySelectorAll(".js-copy-pass").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const val = btn.parentElement.querySelector(".star-pass__value");
            const real = val ? (val.dataset.real || "") : "";
            if (!real) return;
            try {
                await navigator.clipboard.writeText(real);
            } catch (e) {
                const ta = document.createElement("textarea");
                ta.value = real; document.body.appendChild(ta); ta.select();
                try { document.execCommand("copy"); } catch (err) {}
                document.body.removeChild(ta);
            }
            btn.classList.add("is-copied");
            setTimeout(() => btn.classList.remove("is-copied"), 1200);
        });
    });

    // ------------------------------------------------------------------
    // Modal cadastro / edicao
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("starModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("starForm");
    const deleteForm = document.getElementById("starDeleteForm");
    const deleteConfirm = document.getElementById("starDeleteConfirm");
    const deleteBtn = document.getElementById("starDeleteBtn");
    const senhaInput = document.getElementById("starSenha");
    const senhaHelp = document.getElementById("starSenhaHelp");
    const createAction = form ? form.getAttribute("action") : "";

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("starModalLabel").textContent = "Nova Starlink";
        document.getElementById("starSubmit").textContent = "Cadastrar Starlink";
        form.action = createAction;
        ["starNome","starLocal","starEmail","starSenha","starCartao","starIdent","starVersao","starSerie","starKit"].forEach((id) => setVal(id, ""));
        setVal("starForma", "cartao");
        const ativo = document.getElementById("starAtivo"); if (ativo) ativo.checked = true;
        if (senhaInput) senhaInput.type = "password";
        if (senhaHelp) senhaHelp.textContent = "";
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(card) {
        if (!form || !card) return;
        const d = card.dataset;
        document.getElementById("starModalLabel").textContent = "Editar Starlink";
        document.getElementById("starSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("starNome", d.nome);
        setVal("starLocal", d.local);
        setVal("starEmail", d.email);
        setVal("starSenha", "");
        setVal("starForma", d.forma || "cartao");
        setVal("starCartao", d.cartao);
        setVal("starIdent", d.identificador);
        setVal("starVersao", d.versao);
        setVal("starSerie", d.serie);
        setVal("starKit", d.kit);
        const ativo = document.getElementById("starAtivo"); if (ativo) ativo.checked = d.ativo === "1";
        if (senhaInput) senhaInput.type = "password";
        if (senhaHelp) senhaHelp.textContent = d.senha ? "Deixe em branco para manter a senha atual." : "";
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
    }

    document.getElementById("createStarButton")?.addEventListener("click", openCreate);
    document.querySelectorAll(".js-edit-star").forEach((btn) => {
        btn.addEventListener("click", () => openEdit(btn.closest(".star-card")));
    });
    document.getElementById("starSenhaToggle")?.addEventListener("click", () => {
        if (senhaInput) senhaInput.type = senhaInput.type === "password" ? "text" : "password";
    });
    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("starDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Busca + filtro por status
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("starSearch");
    const statusEl = document.getElementById("starSearchStatus");
    const noResults = document.getElementById("starNoResults");
    const chips = Array.from(document.querySelectorAll(".star-chip"));
    const cards = Array.from(document.querySelectorAll(".star-card"));
    let activeStatus = "";

    const normalize = (v) => (v || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = cards.length;
        const filtering = (searchInput && searchInput.value.trim()) || activeStatus;
        statusEl.textContent = filtering
            ? `${visible} de ${total} Starlink(s) encontrada(s).`
            : `${total} Starlink(s) no total.`;
    }

    function applyFilters() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        cards.forEach((card) => {
            const matchText = !term || normalize(card.dataset.search).includes(term);
            const matchStatus = !activeStatus || card.dataset.status === activeStatus;
            const show = matchText && matchStatus;
            card.classList.toggle("is-hidden", !show);
            if (show) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || cards.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", applyFilters);
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeStatus = chip.dataset.status || "";
            chips.forEach((c) => {
                const active = c === chip;
                c.classList.toggle("is-active", active);
                c.setAttribute("aria-selected", active ? "true" : "false");
            });
            applyFilters();
        });
    });
    updateStatus(cards.length);
})();
