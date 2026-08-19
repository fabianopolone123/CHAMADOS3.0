/* Texto da requisicao para WhatsApp e para e-mail, e a copia para a area de
 * transferencia.
 *
 * Isto morava dentro de `contratos.js`, que so carrega na tela de Requisicoes.
 * Como o terminal do Painel do Titular precisa da **mesma** mensagem, o codigo
 * saiu de la para ca em vez de ser copiado: a formatacao mora num lugar so, e
 * mudar o texto aqui muda nos dois.
 *
 * Consome o JSON de `requisicao_detail` como ele vem: `{requisicao, orcamentos}`.
 */
window.RequisicaoTexto = (function () {
    "use strict";

    function fmtRawMoney(raw, moeda) {
        const symbol = moeda === "USD" ? "US$" : "R$";
        const n = Number(raw);
        if (!isFinite(n)) {
            return `${symbol} ${raw}`;
        }
        const txt = n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        return `${symbol} ${txt}`;
    }

    function buildWhatsappMessage(data) {
        const req = data.requisicao;
        const orcs = data.orcamentos || [];
        const L = [];
        const codigo = req.codigo ? `${req.codigo} — ` : "";
        L.push(`*${codigo}${req.titulo}*`);
        // Tipo e status sao controle interno: nao entram na mensagem enviada.
        L.push(`Solicitado por ${req.criado_por} em ${req.criado_em}`);
        if (req.entregue_em) {
            L.push(`Entregue em ${req.entregue_em}${req.entregue_por ? ` por ${req.entregue_por}` : ""}`);
        }
        if (req.texto && req.texto.trim()) {
            L.push("");
            L.push("📝 *Descrição*");
            L.push(req.texto.trim());
        }

        if (orcs.length) {
            L.push("");
            L.push("━━━━━━━━━━━━━━━");
            L.push(`💼 *Orçamentos (${orcs.length})*`);
            orcs.forEach((orc, index) => {
                L.push("");
                const aprovado = orc.aprovado ? " ✅ Aprovado" : "";
                L.push(`*${index + 1}. ${orc.titulo}*${aprovado}`);
                if (orc.loja && orc.loja !== "-") {
                    L.push(`🏪 ${orc.loja}`);
                }
                L.push(`Valor: ${fmtRawMoney(orc.valor, orc.moeda)}  ·  Qtd: ${orc.quantidade}`);
                const extras = [];
                if (Number(orc.frete)) extras.push(`Frete: ${fmtRawMoney(orc.frete, orc.moeda)}`);
                if (Number(orc.desconto)) extras.push(`Desconto: ${fmtRawMoney(orc.desconto, orc.moeda)}`);
                if (extras.length) L.push(extras.join("  ·  "));
                L.push(`*Total: ${orc.total_display}*`);
                const subs = orc.suborcamentos || [];
                if (subs.length) {
                    L.push(`_Total + suborçamentos: ${orc.total_com_suborcamentos_display}_`);
                    subs.forEach((sub) => {
                        L.push("");
                        L.push(`   *↳ ${sub.titulo}*`);
                        if (sub.loja && sub.loja !== "-") {
                            L.push(`   🏪 ${sub.loja}`);
                        }
                        L.push(`   Valor: ${fmtRawMoney(sub.valor, sub.moeda)}  ·  Qtd: ${sub.quantidade}`);
                        const se = [];
                        if (Number(sub.frete)) se.push(`Frete: ${fmtRawMoney(sub.frete, sub.moeda)}`);
                        if (Number(sub.desconto)) se.push(`Desconto: ${fmtRawMoney(sub.desconto, sub.moeda)}`);
                        if (se.length) L.push(`   ${se.join("  ·  ")}`);
                        L.push(`   *Total: ${sub.total_display}*`);
                    });
                }
            });
        } else {
            L.push("");
            L.push("_Sem orçamentos cadastrados._");
        }

        return L.join("\n");
    }

    function buildEmailPlainText(data) {
        const req = data.requisicao;
        const orcs = data.orcamentos || [];
        const L = [];
        L.push(`${req.codigo ? `${req.codigo} - ` : ""}${req.titulo}`);
        L.push(`Solicitado por ${req.criado_por} em ${req.criado_em}`);
        if (req.entregue_em) {
            L.push(`Entregue em ${req.entregue_em}${req.entregue_por ? ` por ${req.entregue_por}` : ""}`);
        }
        if (req.texto && req.texto.trim()) {
            L.push("", "DESCRIÇÃO", req.texto.trim());
        }
        L.push("", `ORÇAMENTOS (${orcs.length})`);
        if (!orcs.length) {
            L.push("Sem orçamentos cadastrados.");
        }
        const item = (it, prefixo) => {
            if (it.loja && it.loja !== "-") L.push(`${prefixo}Loja: ${it.loja}`);
            L.push(`${prefixo}Valor unitário: ${fmtRawMoney(it.valor, it.moeda)} | Quantidade: ${it.quantidade}`);
            if (Number(it.frete)) L.push(`${prefixo}Frete: ${fmtRawMoney(it.frete, it.moeda)}`);
            if (Number(it.desconto)) L.push(`${prefixo}Desconto: ${fmtRawMoney(it.desconto, it.moeda)}`);
            if (it.link) L.push(`${prefixo}Link: ${it.link}`);
            L.push(`${prefixo}Total: ${it.total_display}`);
            (it.documentos || []).forEach((doc) => L.push(`${prefixo}Documento: ${doc.nome}`));
        };
        orcs.forEach((orc, index) => {
            L.push("", `${index + 1}. ${orc.titulo}${orc.aprovado ? " [APROVADO]" : ""}`);
            item(orc, "   ");
            (orc.suborcamentos || []).forEach((sub) => {
                L.push("", `   + ${sub.titulo}`);
                item(sub, "      ");
            });
            if ((orc.suborcamentos || []).length) {
                L.push(`   Total do orçamento + suborçamentos: ${orc.total_com_suborcamentos_display}`);
            }
        });
        return L.join("\n");
    }

    async function copyText(text) {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
            return;
        }
        // Fallback para contexto inseguro (HTTP) ou navegadores antigos.
        const area = document.createElement("textarea");
        area.value = text;
        area.style.position = "fixed";
        area.style.top = "-1000px";
        area.style.opacity = "0";
        document.body.appendChild(area);
        area.focus();
        area.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(area);
        if (!ok) {
            throw new Error("copy-failed");
        }
    }

    return {
        moeda: fmtRawMoney,
        whatsapp: buildWhatsappMessage,
        emailTexto: buildEmailPlainText,
        copiar: copyText,
    };
})();
