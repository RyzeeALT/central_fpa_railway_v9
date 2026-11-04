# Deploy da Central FP&A na Railway

## Arquitetura
- Serviço web: Flask + Gunicorn
- Banco: PostgreSQL da própria Railway
- Imagens: Volume persistente anexado ao serviço web

## 1. Subir o projeto
1. Coloque este projeto em um repositório GitHub.
2. Na Railway, crie um projeto e adicione o repositório como serviço.
3. Adicione um serviço PostgreSQL no mesmo projeto em `+ New > Database > PostgreSQL`.

## 2. Variáveis do serviço web
No serviço Flask, em `Variables`, configure:

- `SECRET_KEY`: uma chave longa e aleatória.
- `FLASK_DEBUG=0`
- `DATABASE_URL=${{Postgres.DATABASE_URL}}`

O nome `Postgres` pode variar conforme o nome do seu serviço de banco. Use a opção de referência de variável da Railway, em vez de copiar usuário/senha manualmente.

Para gerar `SECRET_KEY` localmente:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## 3. Inicialização automática do banco
No serviço web, em Settings > Deploy, defina o **Pre-Deploy Command**:

```bash
python -m flask --app app.py init-db && python -m flask --app app.py bootstrap-admin
```

Esse comando roda dentro da infraestrutura Railway, com acesso à rede privada do PostgreSQL.

Para o PRIMEIRO deploy, crie temporariamente no serviço web:
- `BOOTSTRAP_ADMIN_NAME`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD` (mínimo 12 caracteres)

Após o primeiro deploy confirmar que o admin foi criado, remova `BOOTSTRAP_ADMIN_PASSWORD` (e, se quiser, as outras duas variáveis). Nos próximos deploys, o bootstrap será ignorado.

## 4. Start Command
Se a Railway não detectar o Procfile automaticamente, use em Settings > Deploy > Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

## 5. Healthcheck
Defina o Healthcheck Path como:

```text
/health
```

## 6. Uploads persistentes
Anexe um **Volume** ao serviço web e escolha o mount path:

```text
/data
```

A Railway injeta `RAILWAY_VOLUME_MOUNT_PATH` automaticamente. O portal detecta essa variável e salva uploads em `/data/uploads/tools`.

Sem Volume, o upload ainda funciona, mas os arquivos podem ser perdidos em um redeploy.

## 7. Domínio
Em Settings > Networking, gere um domínio Railway. Depois, se quiser, conecte o domínio próprio.

## 8. Gamma
Depois do deploy, abra `/admin/portal` e cole o URL normal do Gamma e o URL/código de incorporação gerado em Compartilhar > Incorporar.

## Checklist rápido
- [ ] Serviço web criado a partir do GitHub
- [ ] PostgreSQL no mesmo projeto
- [ ] `DATABASE_URL` referenciando o PostgreSQL
- [ ] `SECRET_KEY` criada
- [ ] `FLASK_DEBUG=0`
- [ ] Pre-Deploy Command configurado
- [ ] Primeiro admin criado
- [ ] Volume anexado em `/data`
- [ ] Healthcheck `/health`
- [ ] Domínio Railway ativo
