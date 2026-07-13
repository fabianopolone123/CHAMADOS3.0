(function () {
    const appElement = document.querySelector(".ramais-app");
    if (!appElement) {
        return;
    }

    // ---------------- Cadastro (modal) ----------------
    const createBtn = document.getElementById("createRamalButton");
    const createModalEl = document.getElementById("createRamalModal");
    if (createBtn && createModalEl && typeof bootstrap !== "undefined") {
        const createModal = bootstrap.Modal.getOrCreateInstance(createModalEl);
        createBtn.addEventListener("click", () => createModal.show());
    }

    // Ao escolher um e-mail, preenche o colaborador automaticamente (se vazio).
    const emailSelect = document.getElementById("ramalEmailSelect");
    const colaboradorInput = document.getElementById("ramalColaborador");
    emailSelect?.addEventListener("change", () => {
        const opt = emailSelect.options[emailSelect.selectedIndex];
        const nome = opt ? opt.getAttribute("data-nome") : "";
        if (nome && colaboradorInput && !colaboradorInput.value.trim()) {
            colaboradorInput.value = nome;
        }
    });

    // ---------------- Busca (client-side, instantanea) ----------------
    const searchInput = document.getElementById("ramalSearch");
    const statusEl = document.getElementById("ramalSearchStatus");
    const noResults = document.getElementById("ramaisNoResults");
    const rows = Array.from(document.querySelectorAll(".ramais-row"));

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
            const haystack = row.dataset.search || "";
            const match = !term || haystack.indexOf(term) !== -1;
            row.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterRows);
    updateStatus(rows.length);
})();
