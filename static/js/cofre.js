(function () {
    const app = document.querySelector(".cofre-app");
    if (!app) {
        return;
    }

    const revealTpl = app.dataset.revealUrl;
    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const estado = app.dataset.estado;
    const hasBootstrap = typeof bootstrap !== "undefined";
    const csrf = (app.querySelector("[name=csrfmiddlewaretoken]") || {}).value || "";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };

    async function copyText(text, btn) {
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
        } catch (e) {
            const ta = document.createElement("textarea");
            ta.value = text; document.body.appendChild(ta); ta.select();
            try { document.execCommand("copy"); } catch (err) {}
            document.body.removeChild(ta);
        }
        if (btn) { btn.classList.add("is-copied"); setTimeout(() => btn.classList.remove("is-copied"), 1200); }
    }

    // Olho de mostrar/ocultar em campos de senha (destrave + modais).
    function wireEye(eyeId, inputId) {
        const eye = document.getElementById(eyeId);
        const inp = document.getElementById(inputId);
        eye?.addEventListener("click", () => { if (inp) inp.type = inp.type === "password" ? "text" : "password"; });
    }
    wireEye("cofreUnlockEye", "cofreUnlockInput");
    wireEye("credSenhaEye", "credSenha");

    // Bloqueio: contagem regressiva e reload quando zerar.
    const bloqueio = document.getElementById("cofreBloqueio");
    if (bloqueio) {
        let rest = parseInt(bloqueio.dataset.restante || "0", 10);
        const tick = () => {
            rest -= 1;
            if (rest <= 0) { window.location.reload(); return; }
            bloqueio.textContent = rest + "s";
        };
        setInterval(tick, 1000);
    }

    if (estado !== "aberto") {
        return; // nas telas de portao nao ha lista/modal
    }

    // ------------------------------------------------------------------
    // Revelar / copiar senha sob demanda (fetch por credencial, auditado)
    // ------------------------------------------------------------------
    async function fetchSenha(card) {
        const passEl = card.querySelector(".cred-pass");
        if (passEl.dataset.loaded === "1") return passEl.dataset.real || "";
        const id = card.dataset.id;
        const resp = await fetch(buildUrl(revealTpl, id), {
            method: "POST",
            headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
        });
        if (resp.status === 403) { window.location.reload(); return ""; }
        const data = await resp.json().catch(() => null);
        if (!data || !data.ok) return "";
        passEl.dataset.real = data.senha || "";
        passEl.dataset.loaded = "1";
        return passEl.dataset.real;
    }

    document.querySelectorAll(".js-reveal-pass").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const card = btn.closest(".cred-card");
            const passEl = card.querySelector(".cred-pass");
            if (passEl.dataset.shown === "1") {
                passEl.textContent = "••••••••";
                passEl.dataset.shown = "0";
                return;
            }
            const senha = await fetchSenha(card);
            passEl.textContent = senha || "(vazia)";
            passEl.dataset.shown = "1";
        });
    });

    document.querySelectorAll(".js-copy-pass").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const card = btn.closest(".cred-card");
            const senha = await fetchSenha(card);
            copyText(senha, btn);
        });
    });

    document.querySelectorAll(".js-copy-user").forEach((btn) => {
        btn.addEventListener("click", () => {
            const card = btn.closest(".cred-card");
            copyText(card.dataset.usuario || "", btn);
        });
    });

    // ------------------------------------------------------------------
    // Travar manualmente
    // ------------------------------------------------------------------
    document.getElementById("cofreLockBtn")?.addEventListener("click", () => {
        const f = document.createElement("form");
        f.method = "post"; f.action = "/cofre/travar/";
        f.innerHTML = `<input type="hidden" name="csrfmiddlewaretoken" value="${csrf}">`;
        document.body.appendChild(f); f.submit();
    });

    // ------------------------------------------------------------------
    // Modal cadastro / edicao
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("credModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("credForm");
    const deleteForm = document.getElementById("credDeleteForm");
    const deleteConfirm = document.getElementById("credDeleteConfirm");
    const deleteBtn = document.getElementById("credDeleteBtn");
    const senhaHelp = document.getElementById("credSenhaHelp");
    const createAction = form ? form.getAttribute("action") : "";

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("credModalLabel").textContent = "Nova credencial";
        document.getElementById("credSubmit").textContent = "Adicionar credencial";
        form.action = createAction;
        setVal("credRotulo", "");
        setVal("credUsuario", "");
        setVal("credSenha", "");
        setVal("credNotas", "");
        if (senhaHelp) senhaHelp.textContent = "";
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        modal?.show();
    }

    function openEdit(card) {
        if (!form || !card) return;
        const d = card.dataset;
        document.getElementById("credModalLabel").textContent = "Editar credencial";
        document.getElementById("credSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("credRotulo", d.rotulo);
        setVal("credUsuario", d.usuario);
        setVal("credSenha", "");
        setVal("credNotas", d.notas);
        if (senhaHelp) senhaHelp.textContent = "Deixe a senha em branco para manter a atual.";
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        modal?.show();
    }

    document.getElementById("createCredButton")?.addEventListener("click", openCreate);
    document.querySelectorAll(".js-edit-cred").forEach((btn) => {
        btn.addEventListener("click", () => openEdit(btn.closest(".cred-card")));
    });
    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("credDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Busca
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("credSearch");
    const statusEl = document.getElementById("credSearchStatus");
    const noResults = document.getElementById("credNoResults");
    const cards = Array.from(document.querySelectorAll(".cred-card"));

    const normalize = (v) => (v || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = cards.length;
        statusEl.textContent = (searchInput && searchInput.value.trim())
            ? `${visible} de ${total} credencial(is) encontrada(s).`
            : `${total} credencial(is) no cofre.`;
    }

    function filterCards() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        cards.forEach((card) => {
            const match = !term || normalize(card.dataset.search).includes(term);
            card.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || cards.length === 0);
        updateStatus(visible);
    }
    searchInput?.addEventListener("input", filterCards);
    updateStatus(cards.length);

    // ------------------------------------------------------------------
    // Auto-lock: contagem regressiva do tempo de sessao do cofre
    // ------------------------------------------------------------------
    const timerEl = document.getElementById("cofreTimer");
    const openEl = document.querySelector(".cofre-open");
    let restante = parseInt((openEl && openEl.dataset.unlockSegundos) || app.dataset.unlockSegundos || "0", 10);
    function fmt(s) {
        const m = Math.floor(s / 60), ss = s % 60;
        return `${m}:${ss.toString().padStart(2, "0")}`;
    }
    if (timerEl && restante > 0) {
        timerEl.textContent = "Trava em " + fmt(restante);
        setInterval(() => {
            restante -= 1;
            if (restante <= 0) { window.location.reload(); return; }
            timerEl.textContent = "Trava em " + fmt(restante);
        }, 1000);
    }
})();
