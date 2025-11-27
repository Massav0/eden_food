1. Créer .env à partir de .env.example et remplir SECRET_KEY + DATABASE_URL
   - Générer SECRET_KEY: python -c "import secrets; print(secrets.token_hex(64))"

2. Installer dépendances:
   pip install -r requirements.txt

3a. Déploiement Docker (local test):
   docker compose up --build

3b. Déploiement VPS:
   - créer virtualenv, pip install -r requirements.txt
   - config systemd unit (app.service)
   - sudo systemctl daemon-reload
   - sudo systemctl enable --now app.service

4. Migrations DB si tu utilises Alembic/Flask-Migrate.

5. En prod, configurer un reverse-proxy (nginx) pour SSL + forward to gunicorn 127.0.0.1:8000
