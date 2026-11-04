# Railway fix v10

Corrige colisão de import entre `app.py` e o pacote `app/`.

## Start Command
```bash
gunicorn run:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120
```

## Pre-Deploy Command
```bash
python -m flask --app run.py init-db && python -m flask --app run.py bootstrap-admin
```
