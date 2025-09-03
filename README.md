# N8N · Clientes (Flask + Bootstrap) — EasyPanel Docker

## Deploy rápido (EasyPanel)
1. Crie um app **Dockerfile** e aponte para este repositório/ZIP.
2. Porta interna: **8000**.
3. Variables:
   - `SECRET_KEY` (obrigatória)
   - `DATABASE_URL` (ex.: `postgresql+psycopg2://zaza:SENHA@HOST:5432/DB`)
   - `PAGE_SIZE` (opcional, padrão 10)
4. Build & Deploy.

> O app usa Gunicorn em Python 3.11 slim, usuário não-root e healthcheck.

## Desenvolvimento local (opcional)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY=dev
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/n8n
flask run -p 5080
```
