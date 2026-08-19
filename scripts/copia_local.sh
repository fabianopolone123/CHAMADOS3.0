#!/usr/bin/env bash
# Traz uma copia dos dados de producao para a maquina local.
#
# Para desenvolver contra dados de verdade (o sistema novo que le o Chamados,
# um relatorio, um teste de importacao) sem tocar no servidor.
#
# O banco NAO e copiado com `cp`: com o sistema rodando, o arquivo pode ser
# pego no meio de uma escrita e chegar corrompido. O snapshot sai pela API de
# backup do proprio SQLite, que devolve um arquivo consistente sem travar
# ninguem.
#
# O que NAO vem junto, de proposito: a `VAULT_ENCRYPTION_KEY`. As credenciais do
# cofre e a senha do SMTP viajam cifradas e **nao abrem** fora do servidor - e
# assim que tem de ser. A copia carrega dado pessoal (CPF, e-mail, telefone):
# trate a pasta como o banco que ela e.
#
#   ./scripts/copia_local.sh [destino]        # padrao: ../copia-producao-AAAAMMDD
#   SEM_MEDIA=1 ./scripts/copia_local.sh      # so o banco (rapido)
set -euo pipefail

SERVIDOR="${CHAMADOS_SSH:-ti@192.168.22.17}"
CHAVE="${CHAMADOS_SSH_KEY:-$HOME/.ssh/chamados_vps}"
REMOTO="${CHAMADOS_DIR:-/opt/chamados}"
DESTINO="${1:-$(dirname "$0")/../../copia-producao-$(date +%Y%m%d)}"

ssh_() { ssh -i "$CHAVE" -o BatchMode=yes "$SERVIDOR" "$@"; }
log() { printf '\033[1;36m==> %s\033[0m\n' "$1"; }

mkdir -p "$DESTINO/media"

log "Snapshot consistente do banco (no servidor)"
ssh_ "cd $REMOTO && .venv/bin/python -c \"
import sqlite3
origem = sqlite3.connect('db.sqlite3')
destino = sqlite3.connect('/tmp/copia_chamados.sqlite3')
with destino:
    origem.backup(destino)
destino.close(); origem.close()
\""

log "Trazendo o banco"
scp -q -i "$CHAVE" -o BatchMode=yes "$SERVIDOR:/tmp/copia_chamados.sqlite3" "$DESTINO/db.sqlite3"
ssh_ "rm -f /tmp/copia_chamados.sqlite3"

if [ "${SEM_MEDIA:-0}" != "1" ]; then
    log "Trazendo os arquivos (media)"
    scp -q -C -r -i "$CHAVE" -o BatchMode=yes "$SERVIDOR:$REMOTO/media/." "$DESTINO/media/"
fi

log "Conferindo"
python -c "
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
estado = con.execute('PRAGMA integrity_check').fetchone()[0]
chamados = con.execute('SELECT COUNT(*) FROM core_chamado').fetchone()[0]
con.close()
print(f'  integridade: {estado} | chamados: {chamados}')
sys.exit(0 if estado == 'ok' else 1)
" "$DESTINO/db.sqlite3"

printf '\033[1;36m==> Pronto: %s\033[0m\n' "$(cd "$DESTINO" && pwd)"
