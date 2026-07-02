(function () {
    const appElement = document.querySelector(".documentos-app");
    if (!appElement || typeof bootstrap === "undefined") {
        return;
    }

    const createUrl = appElement.dataset.documentoCreateUrl;
    const detailTpl = appElement.dataset.documentoDetailUrl;
    const list = document.getElementById("documentosList");

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

    // ---------------- Lista ----------------
    function buildListItem(doc) {
        const li = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.className = "documento-item";
        button.dataset.documentoId = doc.id;

        const main = document.createElement("span");
        main.className = "documento-item__main";
        const name = document.createElement("span");
        name.className = "documento-item__name";
        name.textContent = doc.nome;
        const obs = document.createElement("span");
        obs.className = "documento-item__obs";
        obs.textContent = doc.observacao ? doc.observacao : "Sem observacao.";
        main.appendChild(name);
        main.appendChild(obs);

        const meta = document.createElement("span");
        meta.className = "documento-item__meta";
        const badge = document.createElement("span");
        badge.className = "documento-item__badge";
        badge.textContent = `${doc.anexos_count} anexo(s)`;
        const sub = document.createElement("span");
        sub.className = "documento-item__sub";
        sub.textContent = `${doc.criado_em} - ${doc.criado_por}`;
        meta.appendChild(badge);
        meta.appendChild(sub);

        button.appendChild(main);
        button.appendChild(meta);
        button.addEventListener("click", () => openDetail(doc.id));
        li.appendChild(button);
        return li;
    }

    function bindItem(button) {
        button.addEventListener("click", () => openDetail(button.dataset.documentoId));
    }

    // ---------------- Cadastro ----------------
    const createModalEl = document.getElementById("createDocumentoModal");
    const createModal = createModalEl ? bootstrap.Modal.getOrCreateInstance(createModalEl) : null;
    const createForm = document.getElementById("createDocumentoForm");

    document.getElementById("createDocumentoButton")?.addEventListener("click", () => {
        createForm?.reset();
        createModal?.show();
    });

    createForm?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const submit = document.getElementById("createDocumentoSubmit");
        if (submit) submit.disabled = true;
        try {
            const data = await sendForm(createUrl, new FormData(createForm));
            const empty = list.querySelector(".documentos-empty");
            if (empty) empty.remove();
            list.insertBefore(buildListItem(data.documento), list.firstChild);
            createModal?.hide();
            createForm.reset();
            showToast(data.message || "Documento cadastrado.", "success");
        } catch (error) {
            showToast(error.message || "Nao foi possivel cadastrar o documento.", "error");
        } finally {
            if (submit) submit.disabled = false;
        }
    });

    // ---------------- Detalhe ----------------
    const detailModalEl = document.getElementById("documentoDetailModal");
    const detailModal = detailModalEl ? bootstrap.Modal.getOrCreateInstance(detailModalEl) : null;

    function setField(key, value) {
        const el = detailModalEl.querySelector(`[data-doc-detail="${key}"]`);
        if (el) el.textContent = value || "-";
    }

    function renderAnexos(anexos) {
        const container = detailModalEl.querySelector("[data-doc-anexos]");
        const empty = detailModalEl.querySelector("[data-doc-anexos-empty]");
        container.innerHTML = "";
        if (!anexos || !anexos.length) {
            empty.classList.remove("is-hidden");
            return;
        }
        empty.classList.add("is-hidden");
        anexos.forEach((anexo) => {
            const li = document.createElement("li");
            const link = document.createElement("a");
            link.href = anexo.url;
            link.textContent = anexo.nome;
            link.target = "_blank";
            link.rel = "noopener";
            li.appendChild(link);
            container.appendChild(li);
        });
    }

    async function openDetail(id) {
        try {
            const data = await sendGet(buildUrl(detailTpl, id));
            setField("nome", data.nome);
            setField("criado_por", data.criado_por);
            setField("criado_em", data.criado_em);
            setField("observacao", data.observacao || "Sem observacao.");
            renderAnexos(data.anexos);
            detailModal?.show();
        } catch (error) {
            showToast(error.message || "Nao foi possivel abrir o documento.", "error");
        }
    }

    // liga os itens ja renderizados no servidor
    list?.querySelectorAll(".documento-item").forEach(bindItem);
})();
