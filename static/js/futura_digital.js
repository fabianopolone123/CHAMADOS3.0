(function () {
    const app = document.querySelector(".futura-app");
    if (!app) {
        return;
    }

    const updateTpl = app.dataset.updateUrl;
    const deleteTpl = app.dataset.deleteUrl;
    const hasBootstrap = typeof bootstrap !== "undefined";

    const buildUrl = (t, id) => (t ? t.replace("/0/", `/${id}/`) : "");
    const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v == null ? "" : v; };

    const nfInt = new Intl.NumberFormat("pt-BR");
    const nfBRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

    // Converte "1.234,56" ou "1234.56" em Number.
    function parseNum(v) {
        v = (v || "").toString().trim();
        if (!v) return 0;
        if (v.indexOf(",") !== -1) v = v.replace(/\./g, "").replace(",", ".");
        const n = parseFloat(v);
        return Number.isNaN(n) ? 0 : n;
    }

    // ------------------------------------------------------------------
    // Grafico mes a mes
    // ------------------------------------------------------------------
    const chartEl = document.getElementById("fdChart");
    const chartSub = document.getElementById("fdChartSub");
    const chartLegend = document.getElementById("fdChartLegend");
    let serie = [];
    try {
        const raw = document.getElementById("fdSerie");
        if (raw) serie = JSON.parse(raw.textContent) || [];
    } catch (e) { serie = []; }

    const METRICS = {
        valor: { label: "Valor pago", fmt: (v) => nfBRL.format(v), cls: "fd-bar--valor" },
        copias: { label: "Copias", fmt: (v) => nfInt.format(v), cls: "fd-bar--copias" },
        excedentes: { label: "Copias excedentes", fmt: (v) => nfInt.format(v), cls: "fd-bar--excedentes" },
    };
    let metric = "valor";

    function renderChart() {
        if (!chartEl || !serie.length) return;
        const m = METRICS[metric];
        const vals = serie.map((d) => Number(d[metric]) || 0);
        const max = Math.max(...vals, 1);
        chartEl.innerHTML = "";
        serie.forEach((d) => {
            const v = Number(d[metric]) || 0;
            const bar = document.createElement("div");
            bar.className = "fd-bar " + m.cls;
            bar.title = `${d.mes}: ${m.fmt(v)}`;
            const val = document.createElement("span");
            val.className = "fd-bar__val";
            val.textContent = metric === "valor" ? nfInt.format(Math.round(v)) : m.fmt(v);
            const col = document.createElement("div");
            col.className = "fd-bar__col";
            col.style.height = `${Math.max((v / max) * 100, 2)}%`;
            const lbl = document.createElement("span");
            lbl.className = "fd-bar__label";
            lbl.textContent = d.mes;
            bar.appendChild(val); bar.appendChild(col); bar.appendChild(lbl);
            chartEl.appendChild(bar);
        });
        if (chartSub) chartSub.textContent = `${m.label} por mes (${serie.length} meses)`;
        if (chartLegend) {
            const total = vals.reduce((a, b) => a + b, 0);
            const media = total / vals.length;
            chartLegend.textContent = metric === "valor"
                ? `Media mensal: ${nfBRL.format(media)} · Maior: ${nfBRL.format(Math.max(...vals))}`
                : `Media mensal: ${nfInt.format(Math.round(media))} · Maior: ${nfInt.format(Math.max(...vals))}`;
        }
    }

    document.querySelectorAll(".fd-toggle").forEach((btn) => {
        btn.addEventListener("click", () => {
            metric = btn.dataset.metric || "valor";
            document.querySelectorAll(".fd-toggle").forEach((b) => {
                const active = b === btn;
                b.classList.toggle("is-active", active);
                b.setAttribute("aria-selected", active ? "true" : "false");
            });
            renderChart();
        });
    });
    renderChart();

    // ------------------------------------------------------------------
    // Modal cadastro / edicao + calculo ao vivo
    // ------------------------------------------------------------------
    const modalEl = document.getElementById("faturaModal");
    const modal = modalEl && hasBootstrap ? bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    const form = document.getElementById("faturaForm");
    const deleteForm = document.getElementById("faturaDeleteForm");
    const deleteConfirm = document.getElementById("faturaDeleteConfirm");
    const deleteBtn = document.getElementById("faturaDeleteBtn");
    const createAction = form ? form.getAttribute("action") : "";
    const docInput = document.getElementById("faturaDocumento");

    const def = {
        franquiaCopias: form ? form.dataset.franquiaCopias : "23000",
        franquiaValor: form ? form.dataset.franquiaValor : "1610.00",
        rateExc: form ? form.dataset.rateExc : "0.07",
        rateCor: form ? form.dataset.rateCor : "0.75",
    };

    function recalc() {
        const total = parseNum(document.getElementById("faturaTotal")?.value);
        const cor = parseNum(document.getElementById("faturaCor")?.value);
        const franqC = parseNum(document.getElementById("faturaFranquiaCopias")?.value);
        const franqV = parseNum(document.getElementById("faturaFranquiaValor")?.value);
        const rExc = parseNum(document.getElementById("faturaRateExc")?.value);
        const rCor = parseNum(document.getElementById("faturaRateCor")?.value);
        const exc = Math.max(total - cor - franqC, 0);
        const vExc = exc * rExc;
        const vCor = cor * rCor;
        const totalPagar = franqV + vExc + vCor;
        const set = (id, txt) => { const el = document.getElementById(id); if (el) el.textContent = txt; };
        set("calcExcedentes", nfInt.format(exc));
        set("calcFranquia", nfBRL.format(franqV));
        set("calcExcValor", nfBRL.format(vExc));
        set("calcCorValor", nfBRL.format(vCor));
        set("calcTotal", nfBRL.format(totalPagar));
        const ei = document.getElementById("calcExcInfo");
        if (ei) ei.textContent = `(${nfInt.format(exc)} x ${nfBRL.format(rExc)})`;
        const ci = document.getElementById("calcCorInfo");
        if (ci) ci.textContent = `(${nfInt.format(cor)} x ${nfBRL.format(rCor)})`;
    }

    ["faturaTotal","faturaCor","faturaFranquiaCopias","faturaFranquiaValor","faturaRateExc","faturaRateCor"].forEach((id) => {
        document.getElementById(id)?.addEventListener("input", recalc);
    });

    function resetDelete() {
        deleteConfirm?.classList.add("is-hidden");
        form?.classList.remove("is-hidden");
    }

    function openCreate() {
        if (!form) return;
        document.getElementById("faturaModalLabel").textContent = "Nova fatura mensal";
        document.getElementById("faturaSubmit").textContent = "Cadastrar fatura";
        form.action = createAction;
        setVal("faturaMes", "");
        setVal("faturaNota", "");
        setVal("faturaTotal", "0");
        setVal("faturaCor", "0");
        setVal("faturaFranquiaCopias", def.franquiaCopias);
        setVal("faturaFranquiaValor", String(def.franquiaValor).replace(".", ","));
        setVal("faturaRateExc", String(def.rateExc).replace(".", ","));
        setVal("faturaRateCor", String(def.rateCor).replace(".", ","));
        if (docInput) docInput.value = "";
        deleteBtn?.classList.add("is-hidden");
        resetDelete();
        recalc();
        modal?.show();
    }

    function openEdit(row) {
        if (!form || !row) return;
        const d = row.dataset;
        document.getElementById("faturaModalLabel").textContent = "Editar fatura";
        document.getElementById("faturaSubmit").textContent = "Salvar alteracoes";
        form.action = buildUrl(updateTpl, d.id);
        if (deleteForm) deleteForm.action = buildUrl(deleteTpl, d.id);
        setVal("faturaMes", (d.mes || "").slice(0, 7)); // YYYY-MM
        setVal("faturaNota", d.nota);
        setVal("faturaTotal", d.total);
        setVal("faturaCor", d.cor);
        setVal("faturaFranquiaCopias", d.franquiaCopias);
        setVal("faturaFranquiaValor", String(d.franquiaValor || "").replace(".", ","));
        setVal("faturaRateExc", String(d.rateExc || "").replace(".", ","));
        setVal("faturaRateCor", String(d.rateCor || "").replace(".", ","));
        if (docInput) docInput.value = "";
        deleteBtn?.classList.remove("is-hidden");
        resetDelete();
        recalc();
        modal?.show();
    }

    document.getElementById("createFaturaButton")?.addEventListener("click", openCreate);
    document.querySelectorAll(".js-edit-fatura").forEach((btn) => {
        btn.addEventListener("click", (e) => { e.stopPropagation(); openEdit(btn.closest(".fd-row")); });
    });
    deleteBtn?.addEventListener("click", () => {
        form?.classList.add("is-hidden");
        deleteConfirm?.classList.remove("is-hidden");
    });
    document.getElementById("faturaDeleteCancel")?.addEventListener("click", resetDelete);

    // ------------------------------------------------------------------
    // Busca
    // ------------------------------------------------------------------
    const searchInput = document.getElementById("faturaSearch");
    const statusEl = document.getElementById("faturaSearchStatus");
    const noResults = document.getElementById("faturasNoResults");
    const tbody = document.getElementById("faturasTableBody");
    const rows = Array.from(document.querySelectorAll(".fd-row"));

    const normalize = (v) => (v || "").toString().normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

    function updateStatus(visible) {
        if (!statusEl) return;
        const total = rows.length;
        statusEl.textContent = (searchInput && searchInput.value.trim())
            ? `${visible} de ${total} mes(es) encontrado(s).`
            : `${total} mes(es) registrado(s).`;
    }

    function filterRows() {
        const term = normalize(searchInput?.value).trim();
        let visible = 0;
        rows.forEach((row) => {
            const match = !term || normalize(row.dataset.search).includes(term);
            row.classList.toggle("is-hidden", !match);
            if (match) visible += 1;
        });
        if (noResults) noResults.classList.toggle("is-hidden", visible !== 0 || rows.length === 0);
        updateStatus(visible);
    }

    searchInput?.addEventListener("input", filterRows);
    updateStatus(rows.length);

    // ------------------------------------------------------------------
    // Ordenacao por cabecalho
    // ------------------------------------------------------------------
    const headers = Array.from(document.querySelectorAll(".fd-th"));
    let sortState = { index: -1, dir: 1 };

    function cellValue(row, index, type) {
        const cell = row.children[index];
        if (!cell) return "";
        if (type === "num") {
            const raw = cell.dataset.sortValue != null ? cell.dataset.sortValue : cell.textContent;
            return parseFloat(String(raw).replace(/[^0-9.\-]/g, "")) || 0;
        }
        if (type === "month") return (row.dataset.mes || ""); // ISO yyyy-mm-dd
        return cell.textContent.trim();
    }

    function sortBy(index, type) {
        const dir = sortState.index === index ? -sortState.dir : 1;
        sortState = { index, dir };
        const ordered = rows.slice().sort((a, b) => {
            const va = cellValue(a, index, type);
            const vb = cellValue(b, index, type);
            if (type === "num") return (va - vb) * dir;
            return String(va).localeCompare(String(vb), "pt", { sensitivity: "base", numeric: true }) * dir;
        });
        ordered.forEach((row) => tbody.appendChild(row));
        headers.forEach((h) => {
            const isActive = Number(h.dataset.sortIndex) === index;
            h.setAttribute("aria-sort", isActive ? (dir === 1 ? "ascending" : "descending") : "none");
            const ind = h.querySelector(".fd-sort-ind");
            if (ind) ind.textContent = isActive ? (dir === 1 ? "↑" : "↓") : "";
        });
    }

    headers.forEach((h) => {
        h.addEventListener("click", () => sortBy(Number(h.dataset.sortIndex), h.dataset.sortType || "text"));
    });
})();
