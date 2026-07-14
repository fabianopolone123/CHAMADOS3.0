"""Criptografia simetrica do Cofre de senhas.

As credenciais do cofre sao cifradas em repouso com Fernet (AES-128 CBC + HMAC).
A chave vem de `settings.VAULT_ENCRYPTION_KEY` (variavel de ambiente, NUNCA no
codigo/Git). Em desenvolvimento, se a chave nao estiver configurada e o fallback
estiver liberado, deriva-se uma chave estavel a partir da SECRET_KEY (apenas para
testes locais; em producao a chave real e obrigatoria).
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def _build_fernet() -> Fernet:
    configured_key = (getattr(settings, "VAULT_ENCRYPTION_KEY", "") or "").strip()
    if configured_key:
        try:
            return Fernet(configured_key.encode("utf-8"))
        except Exception as exc:  # chave malformada
            raise ImproperlyConfigured(
                "VAULT_ENCRYPTION_KEY invalida. Gere uma chave Fernet valida "
                "(python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")."
            ) from exc

    if not getattr(settings, "VAULT_ALLOW_INSECURE_KEY_DERIVATION", False):
        raise ImproperlyConfigured(
            "VAULT_ENCRYPTION_KEY nao configurada e o fallback inseguro esta desativado. "
            "Defina VAULT_ENCRYPTION_KEY no ambiente."
        )

    # Fallback SOMENTE para desenvolvimento: chave estavel derivada da SECRET_KEY.
    logger.warning("Cofre usando derivacao insegura de chave a partir da SECRET_KEY (apenas dev).")
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_text(value: str) -> str:
    """Cifra um texto e retorna o token (str)."""
    if value is None:
        value = ""
    token = _build_fernet().encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(token: str) -> str:
    """Decifra um token; retorna '' se vazio. Levanta erro se a chave nao bater."""
    if not token:
        return ""
    try:
        value = _build_fernet().decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise ImproperlyConfigured(
            "Nao foi possivel decifrar a credencial do cofre. Verifique a VAULT_ENCRYPTION_KEY."
        ) from exc
    return value.decode("utf-8")
