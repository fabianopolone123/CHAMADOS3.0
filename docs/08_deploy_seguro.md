# 08 - Deploy seguro (Ubuntu Server) e Cofre

Guia pratico para colocar o sistema no Ubuntu Server com foco na seguranca do
**Cofre de senhas**. O modelo de seguranca do cofre e "chave no servidor +
senha-mestra" (duas camadas independentes).

## Modelo de seguranca do Cofre (resumo)

- **Camada 1 - cifra em repouso:** cada senha e cifrada com Fernet usando a
  `VAULT_ENCRYPTION_KEY`, que fica **so na variavel de ambiente do servidor**
  (nunca no codigo/Git). No banco so ha texto cifrado. Protege contra vazamento
  do banco/backup.
- **Camada 2 - senha-mestra:** mesmo sendo TI, o usuario precisa digitar a
  senha-mestra para destravar o cofre na sessao (auto-lock por tempo, bloqueio
  por tentativas). A senha-mestra e guardada so como hash. Protege contra acesso
  curioso interno / sessao aberta.
- Acesso = estar no grupo **Atendente TI/Admin** **e** saber a senha-mestra.
- O unico cenario nao coberto e o servidor 100% comprometido (root lendo env +
  banco). Isso vale para qualquer cofre que decifra sozinho no servidor.

## 1. Gerar a chave de criptografia (no servidor)

Gere uma chave nova, exclusiva de producao (nao reutilize a de dev):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Guarde uma copia dessa chave em local seguro e **separado do servidor** (ex.: um
gerenciador de senhas de um gestor). Sem ela, os dados do cofre nao sao
recuperaveis.

## 2. Variaveis de ambiente (arquivo protegido + systemd)

Crie `/etc/chamados/app.env` (fora do diretorio do projeto), so leitura do
usuario da aplicacao:

```bash
sudo mkdir -p /etc/chamados
sudo tee /etc/chamados/app.env >/dev/null <<'ENV'
DEBUG=False
DJANGO_SECRET_KEY=<gere uma secret key forte>
EXTRA_ALLOWED_HOSTS=chamados.suaempresa.com.br
VAULT_ENCRYPTION_KEY=<a chave gerada no passo 1>
VAULT_ALLOW_INSECURE_KEY_DERIVATION=False
VAULT_UNLOCK_SECONDS=900
VAULT_MAX_FAILED_ATTEMPTS=5
VAULT_LOCKOUT_SECONDS=300
SECURE_COOKIES=1
ENV
sudo chown appuser:appuser /etc/chamados/app.env
sudo chmod 600 /etc/chamados/app.env
```

- `VAULT_ALLOW_INSECURE_KEY_DERIVATION=False` obriga a chave real em producao
  (sem cair no fallback de dev derivado da SECRET_KEY).
- `SECURE_COOKIES=1` liga cookies `Secure`, HSTS e redirect para HTTPS (so use
  com TLS ativo, senao o login quebra).

No servico systemd, aponte para o arquivo:

```ini
# /etc/systemd/system/chamados.service (trecho)
[Service]
User=appuser
Group=appuser
EnvironmentFile=/etc/chamados/app.env
WorkingDirectory=/opt/chamados
ExecStart=/opt/chamados/.venv/bin/gunicorn chamados_ti.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always
```

## 3. HTTPS obrigatorio (nginx + Let's Encrypt)

O cofre trafega senhas — **nunca** sirva por HTTP puro. Use nginx como proxy com
TLS (Certbot/Let's Encrypt) na frente do gunicorn (127.0.0.1:8000). Com
`SECURE_COOKIES=1`, o Django ja marca os cookies como `Secure`, envia HSTS e
redireciona HTTP->HTTPS (assumindo o header `X-Forwarded-Proto` do nginx).

## 4. Levar o codigo e os dados para o servidor

- **Codigo:** via Git (`git clone`/`git pull`). Depois: instalar `requirements.txt`,
  `python manage.py migrate`, `python manage.py collectstatic`.
- **Credenciais do cofre (as 20):** o `seed/` e o banco NAO vao pelo Git (de
  proposito). Para popular no servidor:
  1. Gere a `VAULT_ENCRYPTION_KEY` e configure a env ANTES (passos 1-2).
  2. Copie o arquivo `seed/cofre_seed.json` para o servidor com segurança (uma
     vez): `scp seed/cofre_seed.json appuser@servidor:/opt/chamados/seed/`.
  3. Rode as migrations: `python manage.py migrate` — a migration de seed cifra
     as credenciais **com a chave de producao**.
  4. **Apague o `seed/cofre_seed.json` do servidor** (contem senhas em texto):
     `shred -u /opt/chamados/seed/cofre_seed.json` (ou `rm`).
- Observacao: as credenciais que existem no ambiente de DEV foram cifradas com a
  chave de dev (derivada da SECRET_KEY local) e **nao abrem** com a chave de
  producao — por isso o correto e semear no servidor a partir do JSON, que
  re-cifra com a chave de la. Nao copie o `db.sqlite3` de dev para producao.

## 5. Primeiro acesso ao cofre

1. Um usuario **admin** (grupo Administrador ou superusuario) entra em `/cofre/`.
2. A tela pede para **definir a senha-mestra** (min. 6 caracteres). Defina e
   comunique de forma segura a quem for usar o cofre.
3. A partir dai, qualquer Atendente TI/Admin destrava com a senha-mestra.

## 5b. Notificacoes por e-mail (modulo E-mail)

- A configuracao SMTP e feita pela tela `/email-config/` (TI/admin), nao por env.
  A **senha de app do Google** e cifrada em repouso com a **mesma**
  `VAULT_ENCRYPTION_KEY` do cofre — portanto ela ja fica protegida pelos passos
  1-2 e pelas mesmas regras de backup abaixo.
- Recomendado: use uma **senha de app** dedicada (Google, com verificacao em duas
  etapas ligada), servidor `smtp.gmail.com`, porta `587`, TLS. Use o botao
  **"Enviar teste"** apos salvar para validar a configuracao.
- Se a chave for perdida/trocada, a senha de e-mail (como as do cofre) deixa de
  ser decifravel; basta cadastra-la de novo na tela.

## 5c. Deploy automatico (atalho global `chamados-deploy`)

O repositorio traz `scripts/deploy.sh`, que faz o ciclo completo de qualquer
alteracao: `git pull` -> `pip install -r requirements.txt` -> `migrate` ->
`collectstatic` -> `systemctl restart`. Ele carrega o `/etc/chamados/app.env`
antes de rodar o `manage.py` (para migrate/collectstatic terem a
`VAULT_ENCRYPTION_KEY` e demais variaveis) e so declara sucesso se o servico
subir.

Instale o atalho global **uma vez** no servidor (symlink para o script
versionado, entao ele acompanha o codigo):

```bash
sudo chmod +x /opt/chamados/scripts/deploy.sh
sudo ln -sf /opt/chamados/scripts/deploy.sh /usr/local/bin/chamados-deploy
```

A partir dai, para publicar qualquer mudanca (de qualquer diretorio):

```bash
chamados-deploy
```

Ambiente diferente do padrao? Sobrescreva por variaveis (o script tem defaults
que batem com este guia):

```bash
CHAMADOS_DIR=/srv/chamados CHAMADOS_SERVICE=chamados-web chamados-deploy
```

Variaveis suportadas: `CHAMADOS_DIR` (default `/opt/chamados`), `CHAMADOS_VENV`
(default `$CHAMADOS_DIR/.venv`), `CHAMADOS_ENV` (default
`/etc/chamados/app.env`), `CHAMADOS_SERVICE` (default `chamados`) e
`CHAMADOS_BRANCH` (default `main`).

Para o `systemctl restart` funcionar sem senha quando rodar como o usuario da
aplicacao (`appuser`), libere apenas esse comando no sudoers:

```bash
echo 'appuser ALL=(root) NOPASSWD: /bin/systemctl restart chamados, /bin/systemctl status chamados, /bin/systemctl is-active chamados' | sudo tee /etc/sudoers.d/chamados-deploy
sudo chmod 440 /etc/sudoers.d/chamados-deploy
```

Observacao: o script re-executa a si mesmo a partir de uma copia temporaria
antes do `git pull`, para que a atualizacao do proprio `deploy.sh` nunca corrompa
a execucao em andamento.

## 6. Backups

- O backup do banco contem as senhas **cifradas** (inuteis sem a chave), mas
  ainda assim restrinja o acesso ao arquivo.
- Guarde a `VAULT_ENCRYPTION_KEY` **fora** do backup (em local separado). Sem ela
  o backup do cofre nao pode ser restaurado.

## 7. Boas praticas operacionais

- Nunca commite `.env`, `seed/` ou `db.sqlite3` (ja estao no `.gitignore`).
- Rotacione a senha-mestra periodicamente (tela do cofre, so admin).
- A auditoria do cofre (`CofreAuditoria`) registra destrave, falhas, revelacoes e
  alteracoes com IP — revise em caso de suspeita.
- Se precisar trocar a `VAULT_ENCRYPTION_KEY`, e necessario re-cifrar as
  credenciais (decifrar com a chave antiga e cifrar com a nova) — planeje uma
  rotina de rekey antes de trocar a chave em producao.
