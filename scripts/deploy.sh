#!/usr/bin/env bash
#
# Deploy do CHAMADOS3.0 no Ubuntu Server.
#
# Faz o ciclo completo de qualquer alteracao: atualiza o codigo (git pull),
# instala as dependencias, aplica as migrations, coleta os arquivos estaticos e
# reinicia o servico do gunicorn (systemd). Serve para qualquer tipo de deploy.
#
# Uso (depois de instalar o atalho global - ver docs/08_deploy_seguro.md):
#   chamados-deploy
#
# Variaveis de ambiente para ajustar o ambiente (todas opcionais):
#   CHAMADOS_DIR      diretorio do projeto        (default: /opt/chamados)
#   CHAMADOS_VENV     virtualenv                  (default: $CHAMADOS_DIR/.venv)
#   CHAMADOS_ENV      arquivo de env de producao  (default: /etc/chamados/app.env)
#   CHAMADOS_SERVICE  nome do servico systemd     (default: chamados)
#   CHAMADOS_BRANCH   branch para o deploy        (default: main)
#
set -euo pipefail

# --- Configuracao (defaults batem com docs/08_deploy_seguro.md) --------------
APP_DIR="${CHAMADOS_DIR:-/opt/chamados}"
VENV_DIR="${CHAMADOS_VENV:-$APP_DIR/.venv}"
ENV_FILE="${CHAMADOS_ENV:-/etc/chamados/app.env}"
SERVICE="${CHAMADOS_SERVICE:-chamados}"
BRANCH="${CHAMADOS_BRANCH:-main}"

PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
err()  { printf '\n\033[1;31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }

# --- Re-exec a partir de uma copia estavel -----------------------------------
# Como o proprio script vive no repositorio, um "git pull" durante o deploy
# poderia reescrever este arquivo enquanto o bash ainda o le linha a linha e
# corromper a execucao. Copiamos o script para um arquivo temporario e seguimos
# a partir dele; assim o git pull nunca mexe no que esta rodando.
if [ "${CHAMADOS_DEPLOY_REEXEC:-}" != "1" ]; then
    tmp_self="$(mktemp)"
    cp "$0" "$tmp_self"
    CHAMADOS_DEPLOY_REEXEC=1 exec bash "$tmp_self" "$@"
fi
trap 'rm -f "$0"' EXIT  # aqui $0 ja e a copia temporaria

# --- sudo so quando nao for root ---------------------------------------------
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    SUDO="sudo"
fi

# --- Validacoes basicas ------------------------------------------------------
[ -d "$APP_DIR" ]  || err "Diretorio do projeto nao existe: $APP_DIR (defina CHAMADOS_DIR)"
[ -x "$PYTHON" ]   || err "Python do venv nao encontrado: $PYTHON (defina CHAMADOS_VENV)"
cd "$APP_DIR"

# --- Carrega a env de producao (VAULT_ENCRYPTION_KEY, SECRET_KEY, etc.) -------
# Necessario para migrate/collectstatic rodarem com as mesmas variaveis do
# servico systemd.
if [ -f "$ENV_FILE" ]; then
    log "Carregando variaveis de $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    . "$ENV_FILE"
    set +a
else
    log "Aviso: $ENV_FILE nao encontrado; usando o ambiente atual"
fi

# --- 1. Codigo ---------------------------------------------------------------
log "Atualizando codigo (branch $BRANCH)"
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"
echo "Commit atual: $(git rev-parse --short HEAD) - $(git log -1 --pretty=%s)"

# --- 2. Dependencias ---------------------------------------------------------
log "Instalando dependencias (requirements.txt)"
"$PIP" install --upgrade pip >/dev/null
"$PIP" install -r requirements.txt

# --- 3. Banco ----------------------------------------------------------------
log "Aplicando migrations"
"$PYTHON" manage.py migrate --noinput

# --- 4. Estaticos ------------------------------------------------------------
log "Coletando arquivos estaticos"
"$PYTHON" manage.py collectstatic --noinput

# --- 5. Checagem de deploy (nao aborta) --------------------------------------
log "Checando configuracao (manage.py check --deploy)"
"$PYTHON" manage.py check --deploy || true

# --- 6. Reinicia o servico ---------------------------------------------------
log "Reiniciando o servico ($SERVICE)"
$SUDO systemctl restart "$SERVICE"
sleep 1
if $SUDO systemctl is-active --quiet "$SERVICE"; then
    log "Servico ativo. Deploy concluido com sucesso."
    $SUDO systemctl --no-pager --full status "$SERVICE" | head -n 8 || true
else
    err "O servico $SERVICE nao subiu. Veja: journalctl -u $SERVICE -n 50 --no-pager"
fi
