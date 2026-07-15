"""Notificacoes por e-mail dos chamados.

O envio usa a configuracao SMTP guardada no banco (`EmailConfig`, singleton),
com defaults do Google. A senha (senha de app) vem cifrada em repouso. Todas as
funcoes de notificacao sao "fail-safe": qualquer falha de envio e apenas
registrada em log e NUNCA interrompe o fluxo do chamado (abrir, mover, mensagem,
fechar continuam funcionando mesmo sem e-mail configurado ou com SMTP fora).

Em testes, defina `settings.EMAIL_BACKEND_OVERRIDE` para o backend locmem para
capturar as mensagens em `django.core.mail.outbox` sem tocar o SMTP real.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils.html import escape

from .models import Chamado, EmailConfig

logger = logging.getLogger(__name__)


def _get_connection(config: EmailConfig):
    """Abre a conexao de e-mail. Em testes usa o backend de override; senao,
    monta uma conexao SMTP a partir da `EmailConfig`."""
    override = (getattr(settings, "EMAIL_BACKEND_OVERRIDE", "") or "").strip()
    if override:
        return get_connection(backend=override)

    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=(config.host or "").strip(),
        port=config.porta,
        username=(config.usuario or "").strip(),
        password=config.obter_senha(),
        use_tls=config.usar_tls,
        use_ssl=config.usar_ssl,
        timeout=config.timeout or 15,
    )


def _solicitante_email(chamado: Chamado) -> str:
    email = (chamado.solicitante_email or "").strip()
    if not email and chamado.solicitante_id and chamado.solicitante:
        email = (chamado.solicitante.email or "").strip()
    return email


def _absolute_url(request, chamado: Chamado) -> str:
    try:
        from django.urls import reverse

        caminho = reverse("ticket_detail", kwargs={"numero": chamado.numero})
        if request is not None:
            return request.build_absolute_uri(caminho)
        return caminho
    except Exception:  # pragma: no cover - construcao de URL nunca deve quebrar envio
        return ""


def _enviar(config: EmailConfig, destinatarios, assunto: str, corpo: str) -> bool:
    """Envio central, fail-safe. Retorna True se ao menos tentou enviar."""
    remetente = config.remetente_efetivo
    destinatarios = [d for d in dict.fromkeys(d.strip() for d in destinatarios if d and d.strip())]

    if not remetente or not destinatarios:
        return False

    corpo_txt = corpo.strip() + "\n"
    corpo_html = "<p>" + corpo_txt.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"

    try:
        conexao = _get_connection(config)
        de = f"{config.remetente_nome} <{remetente}>" if config.remetente_nome else remetente
        msg = EmailMultiAlternatives(assunto, corpo_txt, de, destinatarios, connection=conexao)
        msg.attach_alternative(corpo_html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception:
        logger.warning("Falha ao enviar notificacao de e-mail (assunto=%r).", assunto, exc_info=True)
        return False


def _notificacoes_ativas() -> EmailConfig | None:
    """Retorna a config se as notificacoes estao ligadas e utilizaveis, senao None."""
    try:
        config = EmailConfig.load()
    except Exception:  # pragma: no cover
        return None
    if not config.ativo:
        return None
    if not config.remetente_efetivo:
        return None
    return config


def notificar_novo_chamado(chamado: Chamado, request=None) -> None:
    config = _notificacoes_ativas()
    if not config or not config.notif_novo_chamado:
        return

    link = _absolute_url(request, chamado)
    solicitante = _solicitante_email(chamado)
    nome = chamado.solicitante_nome or "solicitante"

    corpo_base = (
        f"Chamado: {chamado.numero}\n"
        f"Titulo: {chamado.titulo}\n"
        f"Solicitante: {nome}\n"
        f"Status: {chamado.status_label}\n"
    )
    if (chamado.descricao or "").strip():
        corpo_base += f"\nDescricao:\n{chamado.descricao.strip()}\n"
    if link:
        corpo_base += f"\nAcompanhe em: {link}\n"

    assunto = f"[Chamado {chamado.numero}] Novo chamado aberto: {chamado.titulo}"

    # Solicitante (confirmacao de abertura).
    if solicitante:
        _enviar(
            config,
            [solicitante],
            assunto,
            f"Ola, {nome}.\n\nSeu chamado foi aberto com sucesso.\n\n{corpo_base}",
        )

    # Equipe de TI.
    destinatarios_ti = [e for e in config.destinatarios_ti() if e.lower() != solicitante.lower()]
    if destinatarios_ti:
        _enviar(
            config,
            destinatarios_ti,
            assunto,
            f"Um novo chamado foi aberto e aguarda atendimento.\n\n{corpo_base}",
        )


def notificar_nova_mensagem(chamado: Chamado, mensagem, request=None) -> None:
    config = _notificacoes_ativas()
    if not config or not config.notif_nova_mensagem:
        return

    autor = mensagem.autor
    autor_email = (getattr(autor, "email", "") or "").strip()
    autor_nome = ""
    if autor is not None:
        autor_nome = autor.get_full_name() or autor.username

    solicitante = _solicitante_email(chamado)
    eh_solicitante = bool(autor and chamado.solicitante_id == autor.id)

    # Notifica a outra parte + TI, sem notificar quem escreveu.
    destinatarios: list[str] = []
    if eh_solicitante:
        destinatarios.extend(config.destinatarios_ti())
    else:
        if solicitante:
            destinatarios.append(solicitante)
        destinatarios.extend(config.destinatarios_ti())

    if autor_email:
        destinatarios = [d for d in destinatarios if d.lower() != autor_email.lower()]

    if not destinatarios:
        return

    link = _absolute_url(request, chamado)
    texto = (mensagem.texto or "").strip() or "(mensagem sem texto)"
    corpo = (
        f"Nova mensagem no chamado {chamado.numero} - {chamado.titulo}.\n"
        f"De: {autor_nome or 'sistema'}\n\n"
        f"{texto}\n"
    )
    if link:
        corpo += f"\nResponda em: {link}\n"

    _enviar(config, destinatarios, f"[Chamado {chamado.numero}] Nova mensagem", corpo)


def notificar_mudanca_status(chamado: Chamado, status_anterior: str, autor_nome: str, request=None) -> None:
    config = _notificacoes_ativas()
    if not config or not config.notif_mudanca_status:
        return

    solicitante = _solicitante_email(chamado)
    destinatarios = list(config.destinatarios_ti())
    if solicitante:
        destinatarios.append(solicitante)
    if not destinatarios:
        return

    link = _absolute_url(request, chamado)
    corpo = (
        f"O status do chamado {chamado.numero} - {chamado.titulo} foi alterado.\n\n"
        f"De: {status_anterior}\n"
        f"Para: {chamado.status_label}\n"
        f"Por: {autor_nome or 'equipe de TI'}\n"
    )
    if link:
        corpo += f"\nDetalhes em: {link}\n"

    _enviar(config, destinatarios, f"[Chamado {chamado.numero}] Status: {chamado.status_label}", corpo)


def notificar_fechamento(chamado: Chamado, autor_nome: str, descricao: str = "", request=None) -> None:
    config = _notificacoes_ativas()
    if not config or not config.notif_fechamento:
        return

    solicitante = _solicitante_email(chamado)
    destinatarios = list(config.destinatarios_ti())
    if solicitante:
        destinatarios.append(solicitante)
    if not destinatarios:
        return

    link = _absolute_url(request, chamado)
    corpo = (
        f"O chamado {chamado.numero} - {chamado.titulo} foi finalizado.\n\n"
        f"Finalizado por: {autor_nome or 'equipe de TI'}\n"
    )
    if (descricao or "").strip():
        corpo += f"\nO que foi feito:\n{descricao.strip()}\n"
    if link:
        corpo += f"\nConsulte em: {link}\n"

    _enviar(config, destinatarios, f"[Chamado {chamado.numero}] Chamado finalizado", corpo)


def enviar_email_teste(config: EmailConfig, destinatario: str) -> tuple[bool, str]:
    """Envia um e-mail de teste com a configuracao atual. Nao e fail-safe: retorna
    (ok, mensagem) para a tela mostrar o erro real ao usuario."""
    remetente = config.remetente_efetivo
    destinatario = (destinatario or "").strip()
    if not remetente:
        return False, "Configure a conta de envio (usuario/remetente) antes de testar."
    if not destinatario:
        return False, "Informe um e-mail de destino para o teste."

    try:
        conexao = _get_connection(config)
        de = f"{config.remetente_nome} <{remetente}>" if config.remetente_nome else remetente
        msg = EmailMultiAlternatives(
            "[Chamados TI] E-mail de teste",
            "Este e um e-mail de teste do modulo de notificacoes do Chamados TI.\n"
            "Se voce recebeu esta mensagem, a configuracao SMTP esta funcionando.\n",
            de,
            [destinatario],
            connection=conexao,
        )
        msg.send(fail_silently=False)
        return True, f"E-mail de teste enviado para {destinatario}."
    except Exception as exc:
        logger.warning("Falha no e-mail de teste.", exc_info=True)
        return False, f"Falha ao enviar: {escape(str(exc))}"
