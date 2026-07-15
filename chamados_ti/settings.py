import json
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8-sig").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _env_json_dict(name: str, default: dict[str, str]) -> dict[str, str]:
    raw = (os.environ.get(name, "") or "").strip()
    if not raw:
        return default

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ImproperlyConfigured(f"{name} must be a JSON object.")

    return {str(key): str(value) for key, value in parsed.items()}


def _normalize_ca_cert_file(raw_path: str) -> str:
    path_value = (raw_path or "").strip()
    if not path_value:
        return ""

    candidate = Path(path_value)
    if candidate.exists():
        return str(candidate)

    if sys.platform.startswith("win"):
        return path_value

    if len(path_value) >= 3 and path_value[1:3] == ":\\":
        drive = path_value[0].lower()
        suffix = path_value[3:].replace("\\", "/")
        mount_root = (os.environ.get("WINDOWS_DRIVE_MOUNT_ROOT", "/mnt") or "/mnt").rstrip("/")
        converted = Path(f"{mount_root}/{drive}/{suffix}")
        if converted.exists():
            return str(converted)

    return path_value


DEBUG = _env_bool("DEBUG", True)

SECRET_KEY = (os.environ.get("DJANGO_SECRET_KEY", "") or "").strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-dev-insecure-key-change-in-production"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required when DEBUG=False.")

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
extra_hosts = (os.environ.get("EXTRA_ALLOWED_HOSTS", "") or "").strip()
if extra_hosts:
    for host in extra_hosts.split(","):
        normalized = host.strip()
        if normalized and normalized not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(normalized)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chamados_ti.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "chamados_ti.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
SERVE_STATIC_WITH_DJANGO = _env_bool("SERVE_STATIC_WITH_DJANGO", True)

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tickets_dashboard"
LOGOUT_REDIRECT_URL = "login"

AUTHENTICATION_BACKENDS = [
    "core.auth_backend.ActiveDirectoryBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AD_LDAP_SERVER_URI = (os.environ.get("AD_LDAP_SERVER_URI", "") or "").strip()
AD_LDAP_BASE_DN = (os.environ.get("AD_LDAP_BASE_DN", "") or "").strip()
AD_LDAP_BIND_DN = (os.environ.get("AD_LDAP_BIND_DN", "") or "").strip()
AD_LDAP_BIND_PASSWORD = (os.environ.get("AD_LDAP_BIND_PASSWORD", "") or "").strip()
AD_LDAP_USER_FILTER = (
    os.environ.get("AD_LDAP_USER_FILTER", "(&(objectClass=user)(sAMAccountName=%(user)s))") or ""
).strip()
AD_LDAP_VALIDATE_CERT = _env_bool("AD_LDAP_VALIDATE_CERT", True)
AD_LDAP_CA_CERT_FILE = _normalize_ca_cert_file(os.environ.get("AD_LDAP_CA_CERT_FILE", ""))
AD_LDAP_CONNECT_TIMEOUT = _env_int("AD_LDAP_CONNECT_TIMEOUT", 5)
AD_LDAP_USER_ATTR_MAP = _env_json_dict(
    "AD_LDAP_USER_ATTR_MAP",
    {
        "username": "sAMAccountName",
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
    },
)

# ---------------------------------------------------------------------------
# Cofre de senhas (modulo Cofre)
# ---------------------------------------------------------------------------
# Chave Fernet usada para cifrar as credenciais em repouso. Em PRODUCAO defina
# VAULT_ENCRYPTION_KEY no ambiente (nunca no codigo/Git). Gere com:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
VAULT_ENCRYPTION_KEY = (os.environ.get("VAULT_ENCRYPTION_KEY", "") or "").strip()
# Em dev (DEBUG), permite derivar uma chave da SECRET_KEY quando a chave real
# nao esta configurada. Em producao (DEBUG=False) o padrao e NAO permitir.
VAULT_ALLOW_INSECURE_KEY_DERIVATION = _env_bool("VAULT_ALLOW_INSECURE_KEY_DERIVATION", DEBUG)
# Tempo (segundos) que o cofre fica destravado na sessao antes de re-travar.
VAULT_UNLOCK_SECONDS = _env_int("VAULT_UNLOCK_SECONDS", 900)
# Anti-brute-force da senha-mestra.
VAULT_MAX_FAILED_ATTEMPTS = _env_int("VAULT_MAX_FAILED_ATTEMPTS", 5)
VAULT_LOCKOUT_SECONDS = _env_int("VAULT_LOCKOUT_SECONDS", 300)

# ---------------------------------------------------------------------------
# Endurecimento para producao (HTTPS). Deixe SECURE_COOKIES=1 no ambiente
# quando o servidor estiver atras de HTTPS (nginx + TLS). Em dev fica desligado
# para nao quebrar o acesso por http.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Notificacoes por e-mail (modulo E-mail)
# ---------------------------------------------------------------------------
# A configuracao SMTP fica no banco (EmailConfig, tela /email-config/), com a
# senha (senha de app do Google) cifrada em repouso. Estas settings sao apenas
# de suporte: EMAIL_BACKEND_OVERRIDE forca um backend (usado nos testes para
# capturar em memoria); em branco, o envio monta a conexao SMTP a partir da
# EmailConfig.
EMAIL_BACKEND_OVERRIDE = (os.environ.get("EMAIL_BACKEND_OVERRIDE", "") or "").strip()

# ---------------------------------------------------------------------------
_secure_cookies = _env_bool("SECURE_COOKIES", False)
SESSION_COOKIE_SECURE = _secure_cookies
CSRF_COOKIE_SECURE = _secure_cookies
SESSION_COOKIE_HTTPONLY = True
if _secure_cookies:
    SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
