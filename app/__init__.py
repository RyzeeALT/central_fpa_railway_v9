import os
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
    # Railway roda como serviço persistente. Localmente, a pasta instance guarda o SQLite.
    if not is_railway:
        os.makedirs(app.instance_path, exist_ok=True)
    secret = os.getenv("SECRET_KEY", "dev-only-change-this-secret")
    if is_railway and secret == "dev-only-change-this-secret":
        raise RuntimeError("Defina SECRET_KEY nas variáveis do serviço web na Railway antes do deploy.")

    db_uri = os.getenv("DATABASE_URL")
    if is_railway and not db_uri:
        raise RuntimeError("Defina DATABASE_URL no serviço web apontando para o PostgreSQL da Railway.")
    if not db_uri:
        db_uri = "sqlite:///" + os.path.join(app.instance_path, "central_fpa.db")
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_uri.startswith("postgresql://") and not db_uri.startswith("postgresql+psycopg://"):
        db_uri = db_uri.replace("postgresql://", "postgresql+psycopg://", 1)

    app.config.update(
        SECRET_KEY=secret,
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS=(
            {
                "pool_pre_ping": True,
                "pool_recycle": 280,
                "connect_args": {"connect_timeout": 10},
            }
            if db_uri.startswith("postgresql")
            else {}
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_railway or os.getenv("FLASK_DEBUG", "1") != "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_SECURE=is_railway,
        WTF_CSRF_TIME_LIMIT=3600,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "admin.login"
    login_manager.login_message = "Entre com sua conta administrativa para continuar."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    from .models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        try:
            admin = db.session.get(Admin, int(user_id))
            return admin if admin and admin.is_active else None
        except (TypeError, ValueError):
            return None

    from .public import public_bp
    from .admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_globals():
        return {"current_year": datetime.now().year}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'; frame-src 'self' https://gamma.app https://*.gamma.app; "
            "connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
        )
        if request_is_https():
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.cli.command("init-db")
    def init_db():
        """Create tables and seed starter content if empty."""
        from .models import Category, Link, PortalSetting
        from sqlalchemy import text
        print("[1/4] Testando conexão com o banco...", flush=True)
        try:
            db.session.execute(text("SELECT 1"))
            db.session.rollback()
        except Exception as exc:
            db.session.rollback()
            print(f"ERRO AO CONECTAR AO BANCO: {exc}", flush=True)
            raise
        print("[2/4] Conexão OK. Criando/verificando tabelas...", flush=True)
        db.create_all()
        print("[3/4] Tabelas verificadas. Sincronizando dados iniciais...", flush=True)
        if Category.query.count() == 0:
            categories = [
                ("Compras", "shopping-cart", 10),
                ("Pessoas e documentos", "file-text", 20),
                ("Planejamento", "chart", 30),
                ("Sistemas", "monitor", 40),
                ("Planilhas e bancos", "table", 50),
                ("Laboratório / Beta", "flask", 70),
            ]
            for name, icon, order in categories:
                db.session.add(Category(name=name, icon=icon, sort_order=order))
            db.session.commit()
        # Áreas dedicadas do portal (criadas também em bancos já existentes).
        dedicated_categories = [
            ("Vídeos Tutoriais", "play", 60),
            ("Bancos mais utilizados", "database", 55),
        ]
        for name, icon, order in dedicated_categories:
            category = Category.query.filter_by(name=name).first()
            if not category:
                db.session.add(Category(name=name, icon=icon, sort_order=order))
        db.session.commit()

        if Link.query.count() == 0:
            seeds = [
                ("Requisição de Compra", "Compras", "Acesso ao sistema de requisições de compra."),
                ("Solicitação de Contracheque", "Pessoas e documentos", "Solicitação e consulta de contracheques."),
                ("Viabilidade Novos Cursos", "Planejamento", "Ferramenta de análise de viabilidade de novos cursos."),
                ("Repositório de Comprovantes", "Planilhas e bancos", "Repositório de comprovantes e documentos."),
                ("Calculadora de Desconto", "Planejamento", "Ferramenta de cálculo de descontos."),
                ("Unig Conecta", "Sistemas", "Acesso ao Unig Conecta."),
                ("Sistema de Gerenciamento de Projetos", "Sistemas", "Acompanhamento e gestão de projetos."),
                ("Sistema de Agendamento 105", "Sistemas", "Acesso ao sistema de agendamento 105."),
                ("Painel Executivo", "Planejamento", "Painéis e indicadores executivos."),
                ("Vio", "Sistemas", "Acesso à ferramenta Vio."),
                ("Banco de Requisição de Compra", "Bancos mais utilizados", "Planilha vinculada à requisição de compra."),
                ("Repositório de Contas a Pagar", "Planilhas e bancos", "Banco de dados de contas a pagar."),
                ("Banco de Viabilidade de Novos Cursos", "Bancos mais utilizados", "Planilhas de viabilidade."),
                ("Sistema de Atendimento", "Sistemas", "Acesso ao sistema de atendimento."),
                ("Vídeos tutoriais", "Vídeos Tutoriais", "Materiais em vídeo para orientar os usuários."),
                ("Central de Links CRA", "Sistemas", "Acesso à central de links CRA."),
            ]
            cats = {c.name: c.id for c in Category.query.all()}
            for idx, (title, cat, description) in enumerate(seeds, start=1):
                db.session.add(Link(title=title, category_id=cats[cat], description=description, url="", is_active=False, sort_order=idx * 10))
            db.session.commit()

        # Migração leve para instalações já existentes: move links claramente identificados
        # para as novas áreas dedicadas, sem alterar URLs ou conteúdo cadastrado.
        bank_category = Category.query.filter_by(name="Bancos mais utilizados").first()
        tutorial_category = Category.query.filter_by(name="Vídeos Tutoriais").first()
        legacy_tutorial_category = Category.query.filter_by(name="Tutoriais").first()
        moved = False
        if bank_category:
            for item in Link.query.filter(Link.title.ilike("Banco de %")).all():
                if item.category_id != bank_category.id:
                    item.category_id = bank_category.id
                    moved = True
        if tutorial_category and legacy_tutorial_category:
            for item in Link.query.filter_by(category_id=legacy_tutorial_category.id).all():
                if item.category_id != tutorial_category.id:
                    item.category_id = tutorial_category.id
                    moved = True
            db.session.flush()
            if Link.query.filter_by(category_id=legacy_tutorial_category.id).count() == 0:
                db.session.delete(legacy_tutorial_category)
                moved = True
        if moved:
            db.session.commit()

        starter_images = {
            "Requisição de Compra": "/static/img/tools/requisicao-compra.png",
            "Solicitação de Contracheque": "/static/img/tools/solicitacao-contracheque.png",
            "Viabilidade Novos Cursos": "/static/img/tools/viabilidade-cursos.png",
        }
        changed = False
        for title, image_path in starter_images.items():
            item = Link.query.filter_by(title=title).first()
            if item and not item.image_url:
                item.image_url = image_path
                changed = True

        gamma_url = "https://gamma.app/docs/Status-e-Resultados-de-Projetos-Planejamento-Financeiro-e-Control-nf32vtoycjihai5"
        setting = db.session.get(PortalSetting, 1)
        if not setting:
            setting = PortalSetting(id=1, gamma_url=gamma_url, gamma_embed_url="")
            db.session.add(setting)
            changed = True
        elif not setting.gamma_url:
            setting.gamma_url = gamma_url
            changed = True

        legacy_gamma = Link.query.filter(Link.title.in_([
            "Apresentações de resultados", "Apresentação de Resultados", "Status e Resultados de Projetos"
        ])).first()
        if legacy_gamma:
            if legacy_gamma.url and not setting.gamma_url:
                setting.gamma_url = legacy_gamma.url
            legacy_gamma.is_active = False
            changed = True

        if changed:
            db.session.commit()
        print("[4/4] Banco inicializado e configuração do portal sincronizada.", flush=True)


    @app.cli.command("bootstrap-admin")
    def bootstrap_admin():
        """Create the first production admin from temporary environment variables."""
        from werkzeug.security import generate_password_hash
        from .models import Admin
        name = (os.getenv("BOOTSTRAP_ADMIN_NAME") or "").strip()
        email = (os.getenv("BOOTSTRAP_ADMIN_EMAIL") or "").strip().lower()
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or ""
        if not (name and email and password):
            print("Bootstrap ignorado: defina BOOTSTRAP_ADMIN_NAME, BOOTSTRAP_ADMIN_EMAIL e BOOTSTRAP_ADMIN_PASSWORD.", flush=True)
            return
        if "@" not in email or len(password) < 12:
            raise SystemExit("Bootstrap inválido: confira o e-mail e use senha com pelo menos 12 caracteres.")
        existing = Admin.query.filter_by(email=email).first()
        if existing:
            print(f"Bootstrap ignorado: {email} já existe.", flush=True)
            return
        admin = Admin(name=name, email=email, password_hash=generate_password_hash(password, method="scrypt"))
        db.session.add(admin)
        db.session.commit()
        print(f"Administrador inicial {email} criado com sucesso.", flush=True)

    @app.cli.command("create-admin")
    def create_admin():
        import getpass
        from werkzeug.security import generate_password_hash
        from .models import Admin
        name = input("Nome: ").strip()
        email = input("E-mail: ").strip().lower()
        password = getpass.getpass("Senha (mínimo 12 caracteres): ")
        if not name or "@" not in email:
            raise SystemExit("Informe nome e e-mail válidos.")
        if len(password) < 12:
            raise SystemExit("A senha precisa ter pelo menos 12 caracteres.")
        if Admin.query.filter_by(email=email).first():
            raise SystemExit("Já existe um administrador com esse e-mail.")
        admin = Admin(name=name, email=email, password_hash=generate_password_hash(password, method="scrypt"))
        db.session.add(admin)
        db.session.commit()
        print(f"Administrador {email} criado.")

    return app


def request_is_https():
    from flask import request
    return request.is_secure or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
