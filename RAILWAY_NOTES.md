# O que mudou na versão Railway

- Removida a dependência do Vercel Blob.
- Produção agora detecta o ambiente Railway.
- PostgreSQL continua via `DATABASE_URL`.
- Uploads usam Volume Railway quando `RAILWAY_VOLUME_MOUNT_PATH` existe.
- Nova rota `/media/tools/...` serve imagens persistidas no Volume.
- Novo comando `bootstrap-admin` permite criar o primeiro admin sem prompt interativo.
- `init-db` pode ser executado como Pre-Deploy Command dentro da rede privada Railway.
- Procfile atualizado para Gunicorn na porta `$PORT`.
- Documentação reescrita para Railway.
