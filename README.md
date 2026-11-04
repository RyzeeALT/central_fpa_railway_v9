# Central de Links - FP&A

Portal Flask para centralizar ferramentas, documentos, sistemas e apresentações do Planejamento Financeiro.

## Desenvolvimento local

```powershell
python -m pip install -r requirements.txt
python -m flask --app run.py init-db
python -m flask --app run.py create-admin
python run.py
```

Acesse `http://127.0.0.1:5000`.

## Produção
A versão atual está preparada para Railway + PostgreSQL + Volume persistente.

Leia `DEPLOY_RAILWAY.md` para o passo a passo.
