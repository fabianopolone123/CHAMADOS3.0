(function () {
    const app = document.querySelector(".dicas-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const anexoTpl = app.dataset.anexoUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };

    function escapeHtml(s) {
        return (s || "").replace(/[&<>"']/g, (c) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        }[c]));
    }
    // Escapa e transforma URLs em links clicaveis (conteudo vem de TI, mas escapamos por seguranca).
    function linkify(s) {
        return escapeHtml(s).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    }

    // ------------------------------------------------------------------
    // Modal de detalhe
    // ------------------------------------------------------------------
    const detailEl = document.getElementById("dicaDetailModal");
    const detailModal = detailEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(detailEl) : null;
    const detailBadge = document.getElementById("dicaDetailBadge");
    const detailContent = document.getElementById("dicaDetailContent");
    const detailAnexoWrap = document.getElementById("dicaDetailAnexoWrap");
    const detailAnexo = document.getElementById("dicaDetailAnexo");
    let lastCard = null;

    function openDetail(card) {
        if (!detailModal || !card) return;
        lastCard = card;
        const d = card.dataset;
        document.getElementById("dicaDetailLabel").textContent = d.titulo || "Detalhe da dica";
        if (detailBadge) {
            detailBadge.textContent = d.categoriaLabel || "Dica";
            detailBadge.className = "dica-badge dica-badge--" + (d.categoria || "geral");
        }
        const full = card.querySelector(".dica-content-full");
        const texto = full ? full.textContent : "";
        if (detailContent) detailContent.innerHTML = texto.trim() ? linkify(texto) : "<em>Sem conteudo.</em>";
        if (detailAnexoWrap && detailAnexo) {
            if (d.temAnexo === "1") {
                detailAnexo.href = buildUrl(anexoTpl, d.id);
                detailAnexoWrap.classList.remove("is-hidden");
            } else {
                detailAnexoWrap.classList.add("is-hidden");
            }
        }
        detailModal.show();
    }

    document.querySelectorAll(".dica-card").forEach((card) => {
        card.addEventListener("click", (e) => {
            if (e.target.closest(".js-edit-dica")) return;
            openDetail(card);
        });
        card.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openDetail(card); }
        });
    });

    // ------------------------------------------------------------------
    // Modal de cadastro / edicao
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("dicaModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("dicaForm");
    const deleteForm = document.getElementById("dicaDeleteForm");
    const deleteConfirm = document.getElementById("dicaDeleteConfirm");
    const deleteBtn = document.getElementById("dicaDeleteBtn");
    const anexoInput = document.getElementById("dicaAnexo");
    const anexoAtual = document.getElementById("dicaAnexoAtual");
    const removeAnexoWrap = document.getElementById("dicaRemoveAnexoWrap");
    const removeAnexo = document.getElementById("dicaRemoveAnexo");
    const createAction = form ? form.getAttribute("action") : "";

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("dicaModalLabel").textContent = "Nova dica";
        document.getElementById("dicaSubmit").textContent = "Cadastrar dica";
        form.action = createAction;
        setVal("dicaCategoria", "geral");
        setVal("dicaTitulo", "");
        setVal("dicaConteudo", "");
        if (anexoInput) anexoInput.value = "";
        if (anexoAtual) anexoAtual.textContent = "";
        if (removeAnexo) removeAnexo.checked = false;
        removeAnexoWrap?.classList.add("is-hidden");
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(card) {
        if (!form || !card) return;
        const d = card.dataset;
        document.getElementById("dicaModalLabel").textContent = "Editar dica";
        document.getElementById("dicaSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("dicaCategoria", d.categoria || "geral");
        setVal("dicaTitulo", d.titulo);
        const full = card.querySelector(".dica-content-full");
        setVal("dicaConteudo", full ? full.textContent : "");
        if (anexoInput) anexoInput.value = "";
        if (removeAnexo) removeAnexo.checked = false;
        if (d.temAnexo === "1") {
            if (anexoAtual) anexoAtual.textContent = "Ha um anexo atual. Envie um novo para substituir.";
            removeAnexoWrap?.classList.remove("is-hidden");
        } else {
            if (anexoAtual) anexoAtual.textContent = "";
            removeAnexoWrap?.classList.add("is-hidden");
        }
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
    }

    document.getElementById("createDicaButton")?.addEventListener("click", openCreate);
    document.querySelectorAll(".js-edit-dica").forEach((btn) => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); openEdit(btn.closest(".dica-card")); });
    });
    document.getElementById("dicaDetailEditBtn")?.addEventListener("click", () => {
        detailModal?.hide();
        if (lastCard) openEdit(lastCard);
    });
    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("dicaDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Busca + filtro por categoria
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("dicaSearch");
    const statusEl = document.getElementById("dicaSearchStatus");
    const noResults = document.getElementById("dicasNoResults");
    const chips = Array.from(document.querySelectorAll(".dicas-chip"));
    const cards = Array.from(document.querySelectorAll(".dica-card"));
    let activeCategory = "";

    const normalize = (v) => (v || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = cards.length;
        const filtering = (searchInput && searchInput.value.trim()) || activeCategory;
        statusEl.textContent = filtering
            ? `${visible} de ${total} dica(s) encontrada(s).`
            : `${total} dica(s) no total.`;
    }

    function applyFilters() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        cards.forEach((card) => {
            const matchText = !term || normalize(card.dataset.search).includes(term);
            const matchCat = !activeCategory || card.dataset.categoria === activeCategory;
            const show = matchText && matchCat;
            card.classList.toggle("is-hidden", !show);
            if (show) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || cards.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", applyFilters);
    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeCategory = chip.dataset.category || "";
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
