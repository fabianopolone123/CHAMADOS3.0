/* Painel do Titular — terminal de administracao do sistema.

   Navegacao no estilo dos terminais de banco: a tecla executa na hora, sem
   ENTER e sem setas; ESC volta um nivel de cada vez; a ultima linha da janela e
   a barra de status, que mostra o que esta sendo digitado e o aviso da ultima
   acao. O ENTER so aparece em campo de texto livre (busca, rotulo, valor de
   campo), onde nao ha como adivinhar o fim do que se digita.

   O clique do mouse funciona como atalho de cortesia (mesma acao da tecla),
   mas nada aqui depende dele.

   Telas: principal -> interface | usuarios | dados (tabelas -> tabela ->
   registro) | operacao. Cada tela carrega os proprios dados de `/painel/api/`.
*/
"use strict";

(function () {
    const raiz = document.querySelector(".pnl");
    if (!raiz) {
        return;
    }

    const URLS = {
        estado: raiz.dataset.urlEstado,
        interface: raiz.dataset.urlInterface,
        interfaceSalvar: raiz.dataset.urlInterfaceSalvar,
        usuarios: raiz.dataset.urlUsuarios,
        usuarioAcao: raiz.dataset.urlUsuarioAcao,
        modulos: raiz.dataset.urlModulos,
        modulo: raiz.dataset.urlModulo,
        tabelas: raiz.dataset.urlTabelas,
        registroCamposNovos: raiz.dataset.urlRegistroCamposNovos,
        registroCriar: raiz.dataset.urlRegistroCriar,
        tabela: raiz.dataset.urlTabela,
        registro: raiz.dataset.urlRegistro,
        registroAlterar: raiz.dataset.urlRegistroAlterar,
        registroExcluir: raiz.dataset.urlRegistroExcluir,
        operacao: raiz.dataset.urlOperacao,
        operacaoAcao: raiz.dataset.urlOperacaoAcao,
        saida: raiz.dataset.urlSaida,
    };
    const OPERADOR = (raiz.dataset.operador || "").toUpperCase();

    const $tela = document.getElementById("pnl-tela");
    const $status = document.getElementById("pnl-status");
    const $cabecalho = document.getElementById("pnl-cabecalho");

    /* ------------------------------------------------------------ apoio -- */

    const esc = (valor) =>
        String(valor == null ? "" : valor).replace(/[&<>"]/g, (c) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
        }[c]));

    function csrfToken() {
        const campo = raiz.querySelector("input[name=csrfmiddlewaretoken]");
        if (campo && campo.value) {
            return campo.value;
        }
        const parte = document.cookie.split("; ").find((c) => c.startsWith("csrftoken="));
        return parte ? decodeURIComponent(parte.split("=")[1]) : "";
    }

    function url(molde, chave, pk) {
        return molde.replace("__CHAVE__", encodeURIComponent(chave)).replace("__PK__", encodeURIComponent(pk));
    }

    async function obter(endereco) {
        const resposta = await fetch(endereco, { headers: { "X-Requested-With": "XMLHttpRequest" } });
        const dados = await resposta.json().catch(() => ({ ok: false, message: "Resposta ilegivel do servidor." }));
        if (!resposta.ok || !dados.ok) {
            throw new Error(dados.message || "Falha ao consultar o servidor.");
        }
        return dados;
    }

    async function enviar(endereco, corpo) {
        const resposta = await fetch(endereco, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken(),
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify(corpo || {}),
        });
        const dados = await resposta.json().catch(() => ({ ok: false, message: "Resposta ilegivel do servidor." }));
        if (!resposta.ok || !dados.ok) {
            throw new Error(dados.message || "Falha ao gravar.");
        }
        return dados;
    }

    /* ------------------------------------------------------------ estado -- */

    const estado = {
        tela: "principal",
        aviso: "",
        avisoTipo: "info",
        buffer: "",
        selecionado: null,
        entrada: null, // {rotulo, valor, livre, aoConfirmar}
        confirma: null, // {texto, aoSim}
        dados: {},
        contexto: { modulo: null, rotuloModulo: "", tabela: null, rotuloTabela: "", pk: null, saida: [], voltaDaTabela: "tabelas" },
        // Busca e pagina sao por tela: entrar em DADOS nao herda a busca feita
        // em USUARIOS, e voltar do registro para a lista preserva o filtro.
        buscas: { usuarios: { termo: "", pagina: 0 }, tabela: { termo: "", pagina: 0 } },
        temporizadorLinha: null,
        ocupado: false,
    };

    function busca(tela) {
        return estado.buscas[tela || estado.tela] || { termo: "", pagina: 0 };
    }

    function avisar(texto, tipo = "info") {
        estado.aviso = texto || "";
        estado.avisoTipo = tipo;
    }

    function falhar(erro) {
        avisar(String(erro && erro.message ? erro.message : erro).toUpperCase(), "erro");
        desenhar();
    }

    /* ---------------------------------------------------------- desenho --- */

    function relogio() {
        const agora = new Date();
        const data = agora.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }).toUpperCase();
        $cabecalho.textContent = `TERMINAL 01   OPERADOR: ${OPERADOR}   ${data}`;
    }

    function linhaMenu(tecla, texto) {
        return `<div class="pnl-op" data-tecla="${esc(tecla)}"><span class="pnl-tecla">[${esc(tecla)}]</span> ${esc(texto)}</div>`;
    }

    function blocoMenu(titulo, linhas, rodape) {
        return [
            `<div class="pnl-titulo">${esc(titulo)}</div>`,
            '<div class="pnl-regua"></div>',
            `<div class="pnl-atalhos">${linhas.join("")}</div>`,
            rodape ? `<div class="pnl-rot">${rodape}</div>` : "",
        ].join("");
    }

    function tabelaHTML(colunas, linhas, opcoes = {}) {
        if (!linhas.length) {
            return `<div class="pnl-vazio">${esc(opcoes.vazio || "NADA A MOSTRAR.")}</div>`;
        }
        const cabecalho = colunas.map((c) => `<th data-col="${esc(c)}">${esc(c)}</th>`).join("");
        const corpo = linhas
            .map((linha, indice) => {
                const selecionada = estado.selecionado === indice + 1 ? " sel" : "";
                const celulas = linha
                    .map((valor, coluna) => `<td data-col="${esc(colunas[coluna] || "")}">${valor}</td>`)
                    .join("");
                return `<tr class="pnl-item${selecionada}" data-linha="${indice + 1}"><td class="pnl-num">${indice + 1}</td>${celulas}</tr>`;
            })
            .join("");
        return `<table><thead><tr><th>N</th>${cabecalho}</tr></thead><tbody>${corpo}</tbody></table>`;
    }

    function desenhar() {
        relogio();
        const tela = TELAS[estado.tela];
        const conteudo = tela.desenhar();
        $tela.innerHTML = `<div class="pnl-lista">${conteudo.lista}</div><div class="pnl-menu">${conteudo.menu}</div>`;
        desenharStatus();
        ligarCliques();
    }

    function desenharStatus() {
        if (estado.entrada) {
            $status.innerHTML =
                `<span class="pnl-tecla">${esc(estado.entrada.rotulo)}:</span>` +
                `<input type="${estado.entrada.mascara ? "password" : "text"}" id="pnl-entrada" class="${estado.entrada.livre ? "pnl-livre" : ""}" autocomplete="off" spellcheck="false">` +
                (estado.entrada.dica ? `<span class="pnl-info">${esc(estado.entrada.dica)}</span>` : "") +
                '<span class="pnl-fraco">ENTER CONFIRMA &nbsp; ESC CANCELA</span>';
            const campo = document.getElementById("pnl-entrada");
            campo.value = estado.entrada.valor || "";
            campo.focus();
            campo.select();
            campo.addEventListener("keydown", teclaNaEntrada);
            return;
        }

        if (estado.confirma) {
            $status.innerHTML = `<span class="pnl-erro">${esc(estado.confirma.texto)} &nbsp; [S] SIM &nbsp; [N] NAO</span>`;
            return;
        }

        const partes = [];
        if (estado.buffer) {
            partes.push(`<span class="pnl-buffer">LINHA: ${esc(estado.buffer)}_ &nbsp; ABRE SOZINHO &nbsp; ESC LIMPA</span>`);
        } else if (estado.aviso) {
            partes.push(`<span class="pnl-${esc(estado.avisoTipo)}">${esc(estado.aviso)}</span>`);
        } else {
            partes.push('<span class="pnl-fraco">PRONTO. DIGITE O NUMERO DA LINHA OU A TECLA DA ACAO.</span>');
        }
        $status.innerHTML = partes.join(" ");
    }

    function ligarCliques() {
        $tela.querySelectorAll("[data-tecla]").forEach((elemento) => {
            elemento.addEventListener("click", () => tratarTecla(elemento.dataset.tecla));
        });
        $tela.querySelectorAll("[data-linha]").forEach((elemento) => {
            elemento.addEventListener("click", () => {
                cancelarAberturaAutomatica();
                estado.buffer = "";
                TELAS[estado.tela].escolher(parseInt(elemento.dataset.linha, 10));
            });
        });
    }

    /* --------------------------------------------------------- entradas --- */

    function pedirTexto(rotulo, valorAtual, aoConfirmar, livre = false, dica = "", mascara = false) {
        estado.entrada = { rotulo: rotulo.toUpperCase(), valor: valorAtual || "", aoConfirmar, livre, dica, mascara };
        desenharStatus();
    }

    const ESPERA_CONFIRMACAO = 400; // ms

    /* Quando o numero digitado ainda pode ser o comeco de outro da lista (o "1"
       de uma pagina que tem linha 10), o terminal espera um instante pelo
       segundo digito e abre sozinho se ele nao vier. Assim nao existe ENTER
       para abrir registro: numero sem continuacao possivel abre na hora. */
    const ESPERA_LINHA = 350; // ms

    function cancelarAberturaAutomatica() {
        if (estado.temporizadorLinha) {
            clearTimeout(estado.temporizadorLinha);
            estado.temporizadorLinha = null;
        }
    }

    function pedirConfirmacao(texto, aoSim) {
        estado.confirma = { texto: texto.toUpperCase(), aoSim, desde: Date.now() };
        desenharStatus();
    }

    function teclaNaEntrada(evento) {
        if (evento.key === "Enter") {
            evento.preventDefault();
            const valor = evento.target.value;
            const acao = estado.entrada.aoConfirmar;
            estado.entrada = null;
            evento.stopPropagation();
            acao(valor);
            return;
        }
        if (evento.key === "Escape") {
            evento.preventDefault();
            estado.entrada = null;
            avisar("CANCELADO.", "fraco");
            desenharStatus();
        }
        evento.stopPropagation();

    }

    /* ----------------------------------------------------------- teclado -- */

    function tratarTecla(bruta) {
        cancelarAberturaAutomatica();
        if (estado.ocupado) {
            // Requisicao em curso: a tecla e ignorada de proposito (enfileirar
            // acabaria executando comando fora de contexto), mas o operador ve
            // por que nada aconteceu.
            avisar("PROCESSANDO... AGUARDE.", "info");
            desenharStatus();
            return;
        }
        const tecla = String(bruta || "").toUpperCase();

        if (estado.confirma) {
            if (Date.now() - estado.confirma.desde < ESPERA_CONFIRMACAO) {
                return; // tecla que ja vinha sendo digitada nao confirma nada
            }
            if (tecla === "S") {
                const acao = estado.confirma.aoSim;
                estado.confirma = null;
                acao();
            } else if (tecla === "N" || tecla === "ESCAPE") {
                estado.confirma = null;
                avisar("CANCELADO.", "fraco");
                desenhar();
            }
            return;
        }

        if (tecla === "ESCAPE") {
            voltarUmNivel();
            return;
        }

        if (/^[0-9]$/.test(tecla) && TELAS[estado.tela].totalLinhas) {
            digitar(tecla);
            return;
        }

        if (tecla === "ENTER") {
            if (estado.buffer) {
                const escolhido = parseInt(estado.buffer, 10);
                estado.buffer = "";
                TELAS[estado.tela].escolher(escolhido);
            }
            return;
        }

        TELAS[estado.tela].tecla(tecla);
    }

    function digitar(digito) {
        const total = TELAS[estado.tela].totalLinhas();
        const candidato = estado.buffer + digito;
        const valor = parseInt(candidato, 10);

        if (!valor || valor > total) {
            // Numero fora da lista: nao acumula lixo no buffer.
            if (estado.buffer === "" && TELAS[estado.tela].tecla(digito) !== false) {
                return;
            }
            estado.buffer = "";
            avisar("LINHA INEXISTENTE.", "erro");
            desenharStatus();
            return;
        }

        estado.buffer = candidato;
        // Se nenhum outro numero da lista comeca por este, abre na hora.
        if (valor * 10 > total) {
            estado.buffer = "";
            TELAS[estado.tela].escolher(valor);
            return;
        }
        // Ainda pode virar um numero maior (1 -> 10..14): da um instante para o
        // proximo digito e, se ele nao vier, abre o que foi digitado.
        estado.temporizadorLinha = setTimeout(() => {
            estado.temporizadorLinha = null;
            if (estado.buffer !== candidato) return;
            estado.buffer = "";
            TELAS[estado.tela].escolher(valor);
        }, ESPERA_LINHA);
        desenharStatus();
    }

    function voltarUmNivel() {
        if (estado.entrada) {
            estado.entrada = null;
            avisar("CANCELADO.", "fraco");
            desenhar();
            return;
        }
        if (estado.buffer) {
            estado.buffer = "";
            desenharStatus();
            return;
        }
        if (estado.selecionado !== null) {
            estado.selecionado = null;
            avisar("SELECAO LIMPA.", "fraco");
            desenhar();
            return;
        }
        const filtro = estado.buscas[estado.tela];
        if (filtro && filtro.termo) {
            filtro.termo = "";
            filtro.pagina = 0;
            recarregar();
            return;
        }

        const anterior = TELAS[estado.tela].voltarPara;
        if (!anterior) {
            avisar("VOCE JA ESTA NA TELA INICIAL. USE 0 PARA ENCERRAR.", "erro");
            desenharStatus();
            return;
        }
        irPara(anterior);
    }

    function irPara(nome) {
        estado.tela = nome;
        estado.buffer = "";
        estado.selecionado = null;
        avisar("");
        estado.ocupado = true;
        TELAS[nome]
            .carregar()
            .then(() => {
                estado.ocupado = false;
                desenhar();
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    function recarregar() {
        return TELAS[estado.tela].carregar().then(desenhar).catch(falhar);
    }

    /* ------------------------------------------------------- tela: principal */

    const TELAS = {};

    TELAS.principal = {
        voltarPara: null,
        carregar: async () => {
            estado.dados = await obter(URLS.estado);
        },
        totalLinhas: () => 0,
        escolher: () => {},
        desenhar() {
            const linhas = (estado.dados.linhas || [])
                .map((l) => `<tr><td class="pnl-fraco">${esc(l.rotulo)}</td><td class="pnl-forte">${esc(l.valor)}</td></tr>`)
                .join("");
            const lista = [
                '<div class="pnl-titulo">SITUACAO DO SISTEMA</div>',
                '<div class="pnl-regua"></div>',
                `<table>${linhas}</table>`,
                '<div class="pnl-regua"></div>',
                '<div class="pnl-fraco">ESCOLHA UMA AREA PELA TECLA CORRESPONDENTE.</div>',
                '<div class="pnl-fraco">[5] ABRE OS MODULOS DO MENU PARA TRABALHAR POR AQUI MESMO.</div>',
            ].join("");
            const menu = blocoMenu(
                "AREAS",
                [
                    linhaMenu("1", "INTERFACE DO SISTEMA"),
                    linhaMenu("2", "USUARIOS E ACESSOS"),
                    linhaMenu("3", "DADOS DOS MODULOS"),
                    linhaMenu("4", "OPERACAO E MANUTENCAO"),
                    linhaMenu("5", "MODULOS DO SISTEMA"),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "SAIR DO PAINEL"),
                ],
                "TITULAR: " + esc(OPERADOR)
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "1") return irPara("interface");
            if (tecla === "2") return irPara("usuarios");
            if (tecla === "3") return irPara("tabelas");
            if (tecla === "4") return irPara("operacao");
            if (tecla === "5") return irPara("modulos");
            if (tecla === "A") return recarregar();
            if (tecla === "0") {
                window.location.href = URLS.saida;
                return;
            }
            return false;
        },
    };

    /* ------------------------------------------------------- tela: interface */

    TELAS.interface = {
        voltarPara: "principal",
        carregar: async () => {
            estado.dados = await obter(URLS.interface);
        },
        totalLinhas: () => (estado.dados.itens || []).length,
        escolher(linha) {
            estado.selecionado = linha;
            const item = estado.dados.itens[linha - 1];
            avisar(`SELECIONADO: ${item.rotulo.toUpperCase()} — ESCOLHA A ACAO.`, "info");
            desenhar();
        },
        desenhar() {
            const linhas = (estado.dados.itens || []).map((item) => {
                const rotulo = item.visivel
                    ? `<span class="pnl-forte">${esc(item.rotulo)}</span>`
                    : `<span class="pnl-oculto">${esc(item.rotulo)}</span>`;
                const situacao = item.visivel ? "NO MENU" : '<span class="pnl-fraco">ESCONDIDO</span>';
                const marca = item.alterado ? '<span class="pnl-alterado">ALTERADO</span>' : '<span class="pnl-fraco">PADRAO</span>';
                return [rotulo, esc(item.chave), situacao, marca];
            });
            const lista = [
                '<div class="pnl-titulo">INTERFACE — MENU LATERAL DE TI</div>',
                '<div class="pnl-regua"></div>',
                tabelaHTML(["ITEM", "CHAVE", "SITUACAO", "ESTADO"], linhas, { vazio: "SEM ITENS." }),
                '<div class="pnl-regua"></div>',
                '<div class="pnl-fraco">O QUE VOCE MUDAR AQUI VALE PARA TODA A EQUIPE, NA HORA.</div>',
                '<div class="pnl-fraco">ESTA TELA AJUSTA O MENU. PARA TRABALHAR NO MODULO, USE [I] OU A AREA [5].</div>',
            ].join("");
            const selecionado = estado.selecionado ? (estado.dados.itens || [])[estado.selecionado - 1] : null;
            const acoes = selecionado
                ? [
                      `<div class="pnl-forte">${esc(selecionado.rotulo.toUpperCase())}</div>`,
                      '<div class="pnl-regua"></div>',
                      linhaMenu("V", selecionado.visivel ? "ESCONDER DO MENU" : "MOSTRAR NO MENU"),
                      linhaMenu("+", "SUBIR NA LISTA"),
                      linhaMenu("-", "DESCER NA LISTA"),
                      linhaMenu("E", "EDITAR O ROTULO"),
                      linhaMenu("R", "VOLTAR AO PADRAO"),
                      linhaMenu("I", "ENTRAR NO MODULO"),
                  ]
                : ['<div class="pnl-fraco">DIGITE O NUMERO DE UM ITEM PARA AGIR SOBRE ELE.</div>'];
            const menu = blocoMenu("ACOES", acoes.concat(['<div class="pnl-regua"></div>', linhaMenu("T", "RESTAURAR TUDO"), linhaMenu("A", "ATUALIZAR"), linhaMenu("0", "VOLTAR")]));
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("principal");
            if (tecla === "A") return recarregar();
            if (tecla === "T") {
                pedirConfirmacao("RESTAURAR TODO O MENU PARA O PADRAO?", () => acaoInterface({ acao: "restaurar_tudo" }));
                return;
            }
            if (estado.selecionado === null) {
                return false;
            }
            const item = estado.dados.itens[estado.selecionado - 1];
            if (tecla === "V") return acaoInterface({ acao: "visivel", chave: item.chave });
            if (tecla === "+") return acaoInterface({ acao: "subir", chave: item.chave });
            if (tecla === "-") return acaoInterface({ acao: "descer", chave: item.chave });
            if (tecla === "R") return acaoInterface({ acao: "restaurar", chave: item.chave });
            if (tecla === "I") {
                estado.contexto.modulo = item.chave;
                return irPara("modulo");
            }
            if (tecla === "E") {
                pedirTexto(
                    "NOVO ROTULO",
                    item.rotulo,
                    (valor) => acaoInterface({ acao: "rotulo", chave: item.chave, valor }),
                    true
                );
                return;
            }
            return false;
        },
    };

    function acaoInterface(corpo) {
        estado.ocupado = true;
        enviar(URLS.interfaceSalvar, corpo)
            .then((dados) => {
                estado.ocupado = false;
                estado.dados = dados;
                if (corpo.acao === "restaurar_tudo") {
                    estado.selecionado = null;
                } else if (corpo.acao === "subir" || corpo.acao === "descer") {
                    // A linha selecionada acompanha o item que se moveu.
                    const posicao = (dados.itens || []).findIndex((i) => i.chave === corpo.chave);
                    estado.selecionado = posicao >= 0 ? posicao + 1 : null;
                }
                avisar((dados.message || "SALVO.").toUpperCase(), "ok");
                desenhar();
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    /* -------------------------------------------------------- tela: usuarios */

    TELAS.usuarios = {
        voltarPara: "principal",
        carregar: async () => {
            const filtro = busca("usuarios");
            const endereco = `${URLS.usuarios}?q=${encodeURIComponent(filtro.termo || "")}&pagina=${filtro.pagina || 0}`;
            estado.dados = await obter(endereco);
            filtro.pagina = estado.dados.pagina;
        },
        totalLinhas: () => (estado.dados.usuarios || []).length,
        escolher(linha) {
            estado.selecionado = linha;
            const usuario = estado.dados.usuarios[linha - 1];
            avisar(`SELECIONADO: ${usuario.usuario.toUpperCase()} — ESCOLHA A ACAO.`, "info");
            desenhar();
        },
        desenhar() {
            const linhas = (estado.dados.usuarios || []).map((u) => [
                `<span class="pnl-forte">${esc(u.usuario)}</span>${u.titular ? ' <span class="pnl-alterado">(TITULAR)</span>' : ""}`,
                esc(u.nome),
                u.perfil === "COMUM" ? `<span class="pnl-fraco">COMUM</span>` : esc(u.perfil),
                u.ativo ? "ATIVO" : '<span class="pnl-erro">INATIVO</span>',
                esc(u.ultimo_acesso),
            ]);
            const lista = [
                '<div class="pnl-titulo">USUARIOS E ACESSOS</div>',
                '<div class="pnl-regua"></div>',
                tabelaHTML(["USUARIO", "NOME", "PERFIL", "SITUACAO", "ULTIMO ACESSO"], linhas, { vazio: "NENHUM USUARIO ENCONTRADO." }),
                '<div class="pnl-regua"></div>',
                `<div class="pnl-fraco">${esc(estado.dados.total || 0)} CONTA(S) &nbsp; PAGINA ${(estado.dados.pagina || 0) + 1} DE ${estado.dados.paginas || 1}${busca("usuarios").termo ? " &nbsp; BUSCA: " + esc(busca("usuarios").termo.toUpperCase()) : ""}</div>`,
            ].join("");
            const selecionado = estado.selecionado ? (estado.dados.usuarios || [])[estado.selecionado - 1] : null;
            const acoes = selecionado
                ? [
                      `<div class="pnl-forte">${esc(selecionado.usuario.toUpperCase())}</div>`,
                      '<div class="pnl-regua"></div>',
                      linhaMenu("M", selecionado.admin ? "TIRAR DE ADMINISTRADOR" : "TORNAR ADMINISTRADOR"),
                      linhaMenu("T", selecionado.atendente ? "TIRAR DE ATENDENTE TI" : "TORNAR ATENDENTE TI"),
                      linhaMenu("D", selecionado.ativo ? "DESATIVAR A CONTA" : "ATIVAR A CONTA"),
                  ]
                : ['<div class="pnl-fraco">DIGITE O NUMERO DE UMA LINHA PARA AGIR SOBRE A CONTA.</div>'];
            const menu = blocoMenu(
                "ACOES",
                acoes.concat([
                    '<div class="pnl-regua"></div>',
                    linhaMenu("B", "BUSCAR"),
                    linhaMenu(".", "PROXIMA PAGINA"),
                    linhaMenu(",", "PAGINA ANTERIOR"),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "VOLTAR"),
                ]),
                "A CONTA DO TITULAR NAO PODE SER ALTERADA AQUI."
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("principal");
            if (tecla === "A") return recarregar();
            if (tecla === "B") {
                const filtro = busca("usuarios");
                pedirTexto("BUSCAR USUARIO", filtro.termo, (valor) => {
                    filtro.termo = valor.trim();
                    filtro.pagina = 0;
                    estado.selecionado = null;
                    recarregar();
                }, true);
                return;
            }
            if (tecla === "." || tecla === ",") return paginar(tecla === ".");
            if (estado.selecionado === null) {
                return false;
            }
            const usuario = estado.dados.usuarios[estado.selecionado - 1];
            const acoes = { M: "admin", T: "atendente", D: "ativo" };
            if (!acoes[tecla]) {
                return false;
            }
            const alvo = URLS.usuarioAcao.replace(/\/0\/$/, `/${usuario.pk}/`);
            estado.ocupado = true;
            enviar(alvo, { acao: acoes[tecla] })
                .then((dados) => {
                    estado.ocupado = false;
                    avisar((dados.message || "SALVO.").toUpperCase(), "ok");
                    return TELAS.usuarios.carregar();
                })
                .then(desenhar)
                .catch((erro) => {
                    estado.ocupado = false;
                    falhar(erro);
                });
        },
    };

    function paginar(avancar) {
        const paginas = estado.dados.paginas || 1;
        const filtro = busca();
        const destino = (filtro.pagina || 0) + (avancar ? 1 : -1);
        if (destino < 0 || destino >= paginas) {
            avisar(avancar ? "ULTIMA PAGINA." : "PRIMEIRA PAGINA.", "fraco");
            desenharStatus();
            return;
        }
        filtro.pagina = destino;
        estado.selecionado = null;
        recarregar();
    }

    /* ------------------------------------------------------- tela: modulos -- */

    TELAS.modulos = {
        voltarPara: "principal",
        carregar: async () => {
            estado.dados = await obter(URLS.modulos);
        },
        totalLinhas: () => (estado.dados.modulos || []).length,
        escolher(linha) {
            const modulo = estado.dados.modulos[linha - 1];
            estado.contexto.modulo = modulo.chave;
            estado.contexto.rotuloModulo = modulo.rotulo;
            irPara("modulo");
        },
        desenhar() {
            const linhas = (estado.dados.modulos || []).map((m) => [
                `<span class="pnl-forte">${esc(m.rotulo)}</span>`,
                esc(m.tabelas || "-"),
                esc(m.registros),
                m.no_menu ? "NO MENU" : '<span class="pnl-fraco">ESCONDIDO</span>',
            ]);
            const lista = [
                '<div class="pnl-titulo">MODULOS DO SISTEMA</div>',
                '<div class="pnl-regua"></div>',
                tabelaHTML(["MODULO", "TABELAS", "REGISTROS", "MENU"], linhas),
                '<div class="pnl-regua"></div>',
                '<div class="pnl-fraco">DIGITE O NUMERO DO MODULO PARA ENTRAR E TRABALHAR NELE POR AQUI.</div>',
            ].join("");
            const menu = blocoMenu("NAVEGACAO", [linhaMenu("A", "ATUALIZAR"), linhaMenu("0", "VOLTAR")], "OS MESMOS BOTOES DO MENU LATERAL.");
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("principal");
            if (tecla === "A") return recarregar();
            return false;
        },
    };

    TELAS.modulo = {
        voltarPara: "modulos",
        carregar: async () => {
            estado.dados = await obter(url(URLS.modulo, estado.contexto.modulo, ""));
            estado.contexto.rotuloModulo = estado.dados.rotulo;
        },
        totalLinhas: () => (estado.dados.tabelas || []).length,
        escolher(linha) {
            const tabela = estado.dados.tabelas[linha - 1];
            estado.contexto.tabela = tabela.chave;
            estado.contexto.rotuloTabela = tabela.rotulo;
            estado.contexto.voltaDaTabela = "modulo";
            estado.buscas.tabela = { termo: "", pagina: 0 };
            irPara("tabela");
        },
        desenhar() {
            const linhas = (estado.dados.tabelas || []).map((t) => [
                `<span class="pnl-forte">${esc(t.rotulo)}</span>${t.principal ? ' <span class="pnl-fraco">(PRINCIPAL)</span>' : ""}`,
                esc(t.total),
                t.somente_leitura ? '<span class="pnl-fraco">SO LEITURA</span>' : "CRIA / ALTERA / EXCLUI",
            ]);
            const corpo = (estado.dados.tabelas || []).length
                ? tabelaHTML(["TABELA", "REGISTROS", "ACESSO"], linhas)
                : `<div class="pnl-vazio">ESTE MODULO NAO TEM TABELA PROPRIA. VEJA A AREA ${esc((estado.dados.area || "").toUpperCase())} DO PAINEL.</div>`;
            const lista = [
                `<div class="pnl-titulo">MODULO ${esc((estado.dados.rotulo || "").toUpperCase())}</div>`,
                '<div class="pnl-regua"></div>',
                corpo,
                '<div class="pnl-regua"></div>',
                estado.dados.nota ? `<div class="pnl-info">${esc(estado.dados.nota.toUpperCase())}</div>` : "",
            ].join("");
            const menu = blocoMenu(
                "NAVEGACAO",
                [
                    linhaMenu("T", "ABRIR A TELA CLASSICA"),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "VOLTAR"),
                ],
                "DIGITE O NUMERO DA TABELA PARA LISTAR, CRIAR E ALTERAR."
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("modulos");
            if (tecla === "A") return recarregar();
            if (tecla === "T") {
                if (estado.dados.url) {
                    window.location.href = estado.dados.url;
                }
                return;
            }
            return false;
        },
    };

    /* --------------------------------------------------------- tela: dados -- */

    TELAS.tabelas = {
        voltarPara: "principal",
        carregar: async () => {
            estado.dados = await obter(URLS.tabelas);
        },
        totalLinhas: () => (estado.dados.tabelas || []).length,
        escolher(linha) {
            const tabela = estado.dados.tabelas[linha - 1];
            estado.contexto.tabela = tabela.chave;
            estado.contexto.rotuloTabela = tabela.rotulo;
            estado.contexto.voltaDaTabela = "tabelas";
            estado.buscas.tabela = { termo: "", pagina: 0 };
            irPara("tabela");
        },
        desenhar() {
            const linhas = (estado.dados.tabelas || []).map((t) => [
                `<span class="pnl-forte">${esc(t.rotulo)}</span>`,
                esc(t.total),
                t.somente_leitura ? '<span class="pnl-fraco">SO LEITURA</span>' : "EDITAVEL",
            ]);
            const lista = [
                '<div class="pnl-titulo">DADOS DOS MODULOS</div>',
                '<div class="pnl-regua"></div>',
                tabelaHTML(["TABELA", "REGISTROS", "ACESSO"], linhas),
                '<div class="pnl-regua"></div>',
                '<div class="pnl-fraco">SENHAS, HASHES E TEXTOS CIFRADOS NAO APARECEM AQUI, EM NENHUMA TABELA.</div>',
            ].join("");
            const menu = blocoMenu("NAVEGACAO", [linhaMenu("A", "ATUALIZAR"), linhaMenu("0", "VOLTAR")], "DIGITE O NUMERO DA TABELA.");
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("principal");
            if (tecla === "A") return recarregar();
            return false;
        },
    };

    TELAS.tabela = {
        get voltarPara() {
            return estado.contexto.voltaDaTabela || "tabelas";
        },
        carregar: async () => {
            const filtro = busca("tabela");
            const endereco = `${url(URLS.tabela, estado.contexto.tabela, "")}?q=${encodeURIComponent(filtro.termo || "")}&pagina=${filtro.pagina || 0}`;
            estado.dados = await obter(endereco);
            filtro.pagina = estado.dados.pagina;
        },
        totalLinhas: () => (estado.dados.linhas || []).length,
        escolher(linha) {
            const registro = estado.dados.linhas[linha - 1];
            estado.contexto.pk = registro.pk;
            irPara("registro");
        },
        desenhar() {
            const linhas = (estado.dados.linhas || []).map((l) => [`<span class="pnl-fraco">#${esc(l.pk)}</span>`].concat(l.valores.map(esc)));
            const lista = [
                `<div class="pnl-titulo">${esc(estado.dados.rotulo || "")}</div>`,
                '<div class="pnl-regua"></div>',
                tabelaHTML(["ID"].concat(estado.dados.colunas || []), linhas, { vazio: "NENHUM REGISTRO." }),
                '<div class="pnl-regua"></div>',
                `<div class="pnl-fraco">${esc(estado.dados.total || 0)} REGISTRO(S) &nbsp; PAGINA ${(estado.dados.pagina || 0) + 1} DE ${estado.dados.paginas || 1}${busca("tabela").termo ? " &nbsp; BUSCA: " + esc(busca("tabela").termo.toUpperCase()) : ""}</div>`,
                estado.dados.nota ? `<div class="pnl-info">${esc(estado.dados.nota.toUpperCase())}</div>` : "",
            ].join("");
            const menu = blocoMenu(
                "NAVEGACAO",
                [
                    ...(estado.dados.acoes || []).map((a) => linhaMenu(a.tecla, a.rotulo)),
                    ...((estado.dados.acoes || []).some((a) => a.tecla === "N")
                        ? []
                        : [
                              estado.dados.somente_leitura
                                  ? '<div class="pnl-fraco">[N] TABELA SO DE LEITURA</div>'
                                  : linhaMenu("N", "NOVO REGISTRO"),
                          ]),
                    linhaMenu("B", "BUSCAR"),
                    linhaMenu(".", "PROXIMA PAGINA"),
                    linhaMenu(",", "PAGINA ANTERIOR"),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "VOLTAR"),
                ],
                "DIGITE O NUMERO DA LINHA PARA ABRIR O REGISTRO."
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara(estado.contexto.voltaDaTabela || "tabelas");
            if (tecla === "A") return recarregar();
            const acaoTabela = acaoDisponivel(tecla);
            if (acaoTabela) return executarAcao(acaoTabela);
            if (tecla === "N") return criarRegistro();
            if (tecla === "B") {
                const filtro = busca("tabela");
                pedirTexto("BUSCAR", filtro.termo, (valor) => {
                    filtro.termo = valor.trim();
                    filtro.pagina = 0;
                    recarregar();
                }, true);
                return;
            }
            if (tecla === "." || tecla === ",") return paginar(tecla === ".");
            return false;
        },
    };

    TELAS.registro = {
        voltarPara: "tabela",
        // criado agora: a tela avisa que os campos opcionais podem ser
        // preenchidos ali mesmo, um a um.
        novo: false,
        carregar: async () => {
            estado.dados = await obter(url(URLS.registro, estado.contexto.tabela, estado.contexto.pk));
        },
        totalLinhas: () => (estado.dados.campos || []).length,
        escolher(linha) {
            const campo = estado.dados.campos[linha - 1];
            estado.selecionado = linha;
            if (!campo.editavel) {
                avisar(`${campo.rotulo}: CAMPO SO DE LEITURA.`, "erro");
                desenhar();
                return;
            }
            const dica = campo.opcoes.length
                ? `OPCOES: ${campo.opcoes.join(" / ").toUpperCase()}`
                : campo.tipo.toUpperCase();
            avisar(`${campo.rotulo} — ${campo.tipo.toUpperCase()}`, "info");
            desenhar();
            pedirTexto(
                campo.rotulo,
                campo.valor === "-" ? "" : campo.valor,
                (valor) => {
                    estado.ocupado = true;
                    enviar(url(URLS.registroAlterar, estado.contexto.tabela, estado.contexto.pk), {
                        campo: campo.nome,
                        valor,
                    })
                        .then((dados) => {
                            estado.ocupado = false;
                            estado.dados = dados;
                            avisar((dados.message || "SALVO.").toUpperCase(), "ok");
                            desenhar();
                        })
                        .catch((erro) => {
                            estado.ocupado = false;
                            falhar(erro);
                        });
                },
                true,
                dica
            );
        },
        desenhar() {
            const linhas = (estado.dados.campos || []).map((campo) => [
                campo.editavel ? esc(campo.rotulo) : `<span class="pnl-fraco">${esc(campo.rotulo)}</span>`,
                esc(campo.valor),
                campo.editavel ? '<span class="pnl-fraco">EDITAVEL</span>' : '<span class="pnl-fraco">SO LEITURA</span>',
            ]);
            const lista = [
                `<div class="pnl-titulo">${esc(estado.dados.rotulo || "")} &middot; REGISTRO #${esc(estado.dados.pk)}</div>`,
                `<div class="pnl-forte">${esc(estado.dados.titulo || "")}</div>`,
                '<div class="pnl-regua"></div>',
                `<div class="pnl-campos">${tabelaHTML(["CAMPO", "VALOR", "ACESSO"], linhas)}</div>`,
                estado.dados.nota ? `<div class="pnl-info">${esc(estado.dados.nota.toUpperCase())}</div>` : "",
            ].join("");
            const acoes = estado.dados.acoes || [];
            const menu = blocoMenu(
                "ACOES",
                [
                    ...(acoes.length
                        ? acoes.map((a) => linhaMenu(a.tecla, a.rotulo)).concat(['<div class="pnl-regua"></div>'])
                        : []),
                    '<div class="pnl-fraco">DIGITE O NUMERO DO CAMPO</div>',
                    '<div class="pnl-fraco">PARA ALTERAR O VALOR.</div>',
                    '<div class="pnl-regua"></div>',
                    // Quando ha acao de fluxo no X (excluir credencial do Cofre,
                    // que a camada generica nao pode fazer), ela manda na tecla.
                    ...(acoes.some((a) => a.tecla === "X")
                        ? []
                        : [
                              estado.dados.pode_excluir
                                  ? linhaMenu("X", "EXCLUIR O REGISTRO")
                                  : '<div class="pnl-fraco">[X] EXCLUSAO BLOQUEADA</div>',
                          ]),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "VOLTAR"),
                ],
                "DATAS: DD/MM/AAAA &nbsp; SIM/NAO: S OU N &nbsp; VINCULO: ID"
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("tabela");
            if (tecla === "A") return recarregar();
            const acao = acaoDisponivel(tecla);
            if (acao) return executarAcao(acao);
            if (tecla === "X") {
                if (!estado.dados.pode_excluir) {
                    avisar("ESTA TABELA NAO PERMITE EXCLUSAO PELO PAINEL.", "erro");
                    desenharStatus();
                    return;
                }
                pedirConfirmacao(`EXCLUIR ${String(estado.dados.titulo || "").toUpperCase()}? NAO TEM VOLTA.`, () => {
                    estado.ocupado = true;
                    enviar(url(URLS.registroExcluir, estado.contexto.tabela, estado.contexto.pk), {})
                        .then((dados) => {
                            estado.ocupado = false;
                            avisar((dados.message || "EXCLUIDO.").toUpperCase(), "ok");
                            irPara("tabela");
                        })
                        .catch((erro) => {
                            estado.ocupado = false;
                            falhar(erro);
                        });
                });
                return;
            }
            return false;
        },
    };



    /* --------------------------------------------------- acoes de fluxo ---- */

    /* Acoes que a tela classica ja tem (abrir chamado, Play/Pause/Stop,
       converter pendencia, aprovar orcamento...). O terminal NAO repete a
       regra: pergunta o que falta e chama a mesma rota, mostrando a resposta.
       Assim o chamado aberto por aqui nasce com evento na timeline e com a
       notificacao por e-mail, igual ao Kanban. */

    function acaoDisponivel(tecla) {
        return (estado.dados.acoes || []).find((a) => a.tecla === String(tecla).toUpperCase());
    }

    function executarAcao(acao) {
        const campos = acao.campos || [];
        const seguir = () => {
            if (acao.formato === "arquivo") {
                escolherArquivo(acao, campos);
                return;
            }
            coletarCampos(acao, campos, 0, {});
        };
        if (acao.confirma) {
            pedirConfirmacao(acao.confirma, seguir);
            return;
        }
        seguir();
    }

    /* O terminal e uma pagina de navegador: para mandar arquivo, quem escolhe e
       o seletor do proprio computador. A tecla dispara o `input file` escondido
       e o arquivo sobe pela mesma rota da tela classica. */

    function escolherArquivo(acao, campos) {
        const entrada = document.createElement("input");
        entrada.type = "file";
        entrada.style.display = "none";
        document.body.appendChild(entrada);

        entrada.addEventListener("change", () => {
            const arquivo = entrada.files && entrada.files[0];
            if (entrada.parentNode) {
                document.body.removeChild(entrada);
            }
            if (!arquivo) {
                semArquivo(acao, campos);
                return;
            }
            avisar(`ARQUIVO: ${arquivo.name.toUpperCase()}`, "info");
            desenhar();
            coletarCampos(acao, campos, 0, {}, arquivo);
        });

        // Fechar a janela sem escolher nada nao dispara `change`: sem isso o
        // terminal ficaria parado no "escolha o arquivo" e o input pendurado.
        entrada.addEventListener("cancel", () => {
            if (entrada.parentNode) {
                document.body.removeChild(entrada);
            }
            semArquivo(acao, campos);
        });

        avisar("ESCOLHA O ARQUIVO NA JANELA DO COMPUTADOR...", "info");
        desenharStatus();
        entrada.click();
    }

    /* Fechar a janela sem escolher: quando o arquivo e opcional (cadastrar um
       documento que ainda nao tem anexo, por exemplo) a acao segue sem ele. */

    function semArquivo(acao, campos) {
        if (acao.arquivo_opcional) {
            avisar("SEGUINDO SEM ARQUIVO.", "info");
            desenhar();
            coletarCampos(acao, campos, 0, {});
            return;
        }
        avisar("NENHUM ARQUIVO ESCOLHIDO. ACAO CANCELADA.", "fraco");
        desenharStatus();
    }

    function coletarCampos(acao, campos, indice, valores, arquivo) {
        if (indice >= campos.length) {
            enviarAcao(acao, valores, arquivo);
            return;
        }
        const campo = campos[indice];
        const dica = campo.mascara
            ? "NAO APARECE ENQUANTO DIGITA"
            : campo.tipo === "DATA"
              ? "DD/MM/AAAA"
              : campo.opcoes.length
                ? `OPCOES: ${campo.opcoes.join(" / ").toUpperCase()}`
                : campo.tipo;
        avisar(`${acao.rotulo} — ${campo.rotulo}${campo.obrigatorio ? "" : " (OPCIONAL)"}`, "info");
        desenhar();
        pedirTexto(
            campo.rotulo,
            "",
            (valor) => {
                const texto = String(valor).trim();
                if (campo.obrigatorio && !texto) {
                    avisar(`${campo.rotulo} E OBRIGATORIO. ACAO CANCELADA.`, "erro");
                    desenhar();
                    return;
                }
                if (texto) {
                    valores[campo.nome] = campo.tipo === "DATA" ? dataParaISO(texto) : texto;
                }
                coletarCampos(acao, campos, indice + 1, valores, arquivo);
            },
            true,
            dica,
            campo.mascara
        );
    }

    /* No painel a data se digita como em todo lugar do sistema (DD/MM/AAAA); as
       rotas dos modulos leem ISO. A conversao fica aqui para o operador nao ter
       de lembrar de dois formatos. Texto que nao for data passa como veio, e o
       proprio backend recusa. */

    function dataParaISO(texto) {
        const partes = String(texto).match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
        return partes ? `${partes[3]}-${partes[2]}-${partes[1]}` : texto;
    }

    /* Copiar usa o MESMO codigo da tela (`requisicao_texto.js`) para montar a
       mensagem: o terminal so busca o JSON do modulo, monta e joga na area de
       transferencia. Nenhuma formatacao e reescrita aqui. */

    const MONTADORES = {
        requisicao_whatsapp: (dados) => window.RequisicaoTexto.whatsapp(dados),
        requisicao_email: (dados) => window.RequisicaoTexto.emailTexto(dados),
    };

    function copiarDaRota(acao) {
        const montar = MONTADORES[acao.montador];
        if (!montar || !window.RequisicaoTexto) {
            avisar("ESTA COPIA NAO ESTA DISPONIVEL NESTA TELA.", "erro");
            desenharStatus();
            return;
        }
        estado.ocupado = true;
        avisar("MONTANDO O TEXTO...", "info");
        desenharStatus();

        fetch(acao.url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(async (resposta) => {
                const dados = await resposta.json().catch(() => ({}));
                if (!resposta.ok || dados.ok === false) {
                    throw new Error(dados.message || "Nao foi possivel ler o registro.");
                }
                return dados;
            })
            .then((dados) => {
                const texto = montar(dados);
                return window.RequisicaoTexto.copiar(texto).then(() => texto);
            })
            .then((texto) => {
                estado.ocupado = false;
                avisar(`COPIADO: ${texto.split("\n").length} LINHAS. E SO COLAR.`, "ok");
                desenharStatus();
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    function enviarAcao(acao, valores, arquivo) {
        const corpo = Object.assign({}, acao.payload || {}, valores);

        if (acao.formato === "copiar") {
            copiarDaRota(acao);
            return;
        }

        // Abrir nao envia nada: o navegador ja sabe o que fazer com PDF,
        // planilha e imagem. O que foi perguntado (o mes da planilha, por
        // exemplo) vai na propria URL, como a tela faz.
        if (acao.formato === "abrir") {
            const parametros = new URLSearchParams(corpo).toString();
            window.open(parametros ? `${acao.url}?${parametros}` : acao.url, "_blank", "noopener");
            avisar(`${acao.rotulo}: ABERTO EM OUTRA ABA.`, "ok");
            desenharStatus();
            return;
        }

        estado.ocupado = true;
        avisar(arquivo ? "ENVIANDO O ARQUIVO..." : "EXECUTANDO...", "info");
        desenharStatus();

        // O `Content-Type` do FormData e do formulario tem de ser montado pelo
        // navegador (o multipart leva um separador que ele mesmo gera), entao so
        // o envio em JSON declara o cabecalho.
        let opcoes;
        if (acao.formato === "arquivo") {
            const dados = new FormData();
            Object.keys(corpo).forEach((chave) => dados.append(chave, corpo[chave]));
            if (arquivo) {
                dados.append(acao.campo_arquivo, arquivo, arquivo.name);
            }
            opcoes = {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
                body: dados,
            };
        } else if (acao.formato === "form") {
            opcoes = {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken(), "X-Requested-With": "XMLHttpRequest" },
                body: new URLSearchParams(corpo),
            };
        } else {
            opcoes = {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfToken(),
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: JSON.stringify(corpo),
            };
        }

        fetch(acao.url, opcoes)
            .then(async (resposta) => {
                const dados = await resposta.json().catch(() => ({}));
                if (!resposta.ok || dados.ok === false) {
                    throw new Error(dados.message || "A acao nao pode ser concluida.");
                }
                return dados;
            })
            .then((dados) => {
                estado.ocupado = false;
                if (acao.revela_resposta && dados[acao.revela_resposta]) {
                    // Sem caixa alta e sem recarregar: senha so serve exatamente
                    // como foi guardada, e some na proxima tecla.
                    avisar(String(dados[acao.revela_resposta]), "ok");
                    desenharStatus();
                    return null;
                }
                avisar((dados.message || `${acao.rotulo}: CONCLUIDO.`).toUpperCase(), "ok");
                // Criou algo? o terminal ja filtra a lista pelo registro novo,
                // que fica na primeira linha, pronto para abrir.
                const identificador = acao.busca_resposta ? dados[acao.busca_resposta] : "";
                if (identificador) {
                    estado.buscas.tabela = { termo: String(identificador), pagina: 0 };
                }
                return recarregar();
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    /* ----------------------------------------------------- criar registro --- */

    /* O terminal pergunta um campo por vez (so os obrigatorios), como uma ficha
       de cadastro: preencheu todos, o registro e criado e abre na tela do
       registro, onde o resto dos campos se completa a vontade. */
    function criarRegistro() {
        if (estado.dados.somente_leitura) {
            avisar("ESTA TABELA E SOMENTE LEITURA.", "erro");
            desenharStatus();
            return;
        }
        estado.ocupado = true;
        obter(url(URLS.registroCamposNovos, estado.contexto.tabela, ""))
            .then((dados) => {
                estado.ocupado = false;
                const obrigatorios = (dados.campos || []).filter((c) => c.obrigatorio);
                perguntarCampo(obrigatorios, 0, {});
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    function perguntarCampo(campos, indice, valores) {
        if (indice >= campos.length) {
            gravarNovo(valores);
            return;
        }
        const campo = campos[indice];
        const dica = campo.opcoes.length
            ? `OPCOES: ${campo.opcoes.join(" / ").toUpperCase()}`
            : campo.tipo.toUpperCase();
        avisar(`NOVO REGISTRO ${indice + 1}/${campos.length} — ${campo.rotulo}`, "info");
        desenhar();
        pedirTexto(
            `${campo.rotulo} (${indice + 1}/${campos.length})`,
            "",
            (valor) => {
                if (!String(valor).trim()) {
                    avisar(`${campo.rotulo} E OBRIGATORIO. CADASTRO CANCELADO.`, "erro");
                    desenhar();
                    return;
                }
                valores[campo.nome] = valor;
                perguntarCampo(campos, indice + 1, valores);
            },
            true,
            dica
        );
    }

    function gravarNovo(valores) {
        estado.ocupado = true;
        avisar("GRAVANDO...", "info");
        desenharStatus();
        enviar(url(URLS.registroCriar, estado.contexto.tabela, ""), { valores })
            .then((dados) => {
                estado.ocupado = false;
                estado.contexto.pk = dados.pk;
                estado.dados = dados;
                estado.tela = "registro";
                estado.selecionado = null;
                avisar((dados.message || "CRIADO.").toUpperCase() + " — COMPLETE OS DEMAIS CAMPOS PELO NUMERO.", "ok");
                desenhar();
            })
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    /* ------------------------------------------------------ tela: operacao -- */

    TELAS.operacao = {
        voltarPara: "principal",
        carregar: async () => {
            estado.dados = await obter(URLS.operacao);
        },
        totalLinhas: () => 0,
        escolher: () => {},
        desenhar() {
            const sistema = (estado.dados.sistema || [])
                .map((l) => `<tr><td class="pnl-fraco">${esc(l.rotulo)}</td><td class="pnl-forte">${esc(l.valor)}</td></tr>`)
                .join("");
            const abertos = (estado.dados.abertos || []).length
                ? `<table><thead><tr><th>CHAMADO</th><th>ATENDENTE</th><th>DESDE</th><th>HORAS</th></tr></thead><tbody>${(estado.dados.abertos || [])
                      .map(
                          (a) =>
                              `<tr><td>${esc(a.chamado)}</td><td>${esc(a.atendente)}</td><td>${esc(a.desde)}</td><td class="${a.horas > 12 ? "pnl-erro" : ""}">${esc(a.horas)}</td></tr>`
                      )
                      .join("")}</tbody></table>`
                : '<div class="pnl-vazio">NENHUM PLAY ABERTO.</div>';
            const auditoria = (estado.dados.auditoria || []).length
                ? `<table><thead><tr><th>QUANDO</th><th>AREA</th><th>ACAO</th><th>ALVO</th></tr></thead><tbody>${(estado.dados.auditoria || [])
                      .map((l) => `<tr><td>${esc(l.quando)}</td><td class="pnl-fraco">${esc(l.area)}</td><td>${esc(l.acao)}</td><td class="pnl-fraco">${esc(l.alvo)}</td></tr>`)
                      .join("")}</tbody></table>`
                : '<div class="pnl-vazio">NADA REGISTRADO AINDA.</div>';

            const saida = (estado.contexto.saida || []).length
                ? [
                      '<div class="pnl-regua"></div>',
                      '<div class="pnl-titulo">SAIDA DO ULTIMO COMANDO</div>',
                      `<div class="pnl-pre pnl-fraco">${esc((estado.contexto.saida || []).join("\n"))}</div>`,
                  ].join("")
                : "";

            const lista = [
                '<div class="pnl-titulo">OPERACAO E MANUTENCAO</div>',
                '<div class="pnl-regua"></div>',
                `<div class="pnl-bloco"><table>${sistema}</table></div>`,
                '<div class="pnl-regua"></div>',
                `<div class="pnl-titulo">ATENDIMENTOS COM PLAY ABERTO &nbsp;<span class="pnl-fraco">(PAUSAS SEM COMPLEMENTO: ${esc(estado.dados.pausas_pendentes || 0)})</span></div>`,
                abertos,
                '<div class="pnl-regua"></div>',
                '<div class="pnl-titulo">ULTIMAS ACOES NO PAINEL</div>',
                auditoria,
                saida,
            ].join("");
            const menu = blocoMenu(
                "COMANDOS",
                [
                    linhaMenu("P", "PAUSAR O EXPEDIENTE"),
                    linhaMenu("S", "SIMULAR A PAUSA"),
                    linhaMenu("L", "LIMPAR SESSOES"),
                    linhaMenu("V", "VERIFICAR O SISTEMA"),
                    linhaMenu("A", "ATUALIZAR"),
                    linhaMenu("0", "VOLTAR"),
                ],
                "PAUSAR FECHA TODO PLAY ABERTO E ABRE A PENDENCIA DE COMPLEMENTO."
            );
            return { lista, menu };
        },
        tecla(tecla) {
            if (tecla === "0") return irPara("principal");
            if (tecla === "A") {
                estado.contexto.saida = [];
                return recarregar();
            }
            const comandos = { S: "pausar_expediente_simulacao", L: "limpar_sessoes", V: "verificar" };
            if (tecla === "P") {
                pedirConfirmacao("PAUSAR AGORA TODOS OS ATENDIMENTOS COM PLAY ABERTO?", () => comandoOperacao("pausar_expediente"));
                return;
            }
            if (comandos[tecla]) {
                return comandoOperacao(comandos[tecla]);
            }
            return false;
        },
    };

    function comandoOperacao(acao) {
        estado.ocupado = true;
        avisar("EXECUTANDO...", "info");
        desenharStatus();
        enviar(URLS.operacaoAcao, { acao })
            .then((dados) => {
                estado.ocupado = false;
                estado.contexto.saida = dados.saida || [];
                avisar((dados.message || "CONCLUIDO.").toUpperCase(), "ok");
                return TELAS.operacao.carregar();
            })
            .then(desenhar)
            .catch((erro) => {
                estado.ocupado = false;
                falhar(erro);
            });
    }

    /* ---------------------------------------------------------- inicio ----- */

    document.addEventListener("keydown", (evento) => {
        if (estado.entrada) {
            return; // o proprio campo trata (ENTER confirma, ESC cancela)
        }
        if (evento.ctrlKey || evento.altKey || evento.metaKey) {
            return; // atalhos do navegador seguem funcionando
        }
        const tecla = evento.key;
        if (tecla === "Tab") {
            return;
        }
        if (tecla.length === 1 || tecla === "Escape" || tecla === "Enter") {
            evento.preventDefault();
            tratarTecla(tecla === "Escape" ? "ESCAPE" : tecla === "Enter" ? "ENTER" : tecla);
        }
    });

    setInterval(relogio, 30000);
    irPara("principal");
})();
