import json
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, Response, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import desc, or_
from . import db
from .storage import save_tool_image, delete_stored_image, storage_backend
from .models import Admin, Link, Category, AuditLog, PortalSetting

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def snapshot_link(link):
    return {
        "title": link.title,
        "description": link.description,
        "url": link.url,
        "category_id": link.category_id,
        "icon": link.icon,
        "image_url": link.image_url,
        "is_active": link.is_active,
        "is_beta": link.is_beta,
        "sort_order": link.sort_order,
    }


def snapshot_category(category):
    return {"name": category.name, "icon": category.icon, "sort_order": category.sort_order}


def snapshot_admin(admin):
    return {"name": admin.name, "email": admin.email, "is_active": admin.is_active}

def snapshot_portal(setting):
    return {"gamma_url": setting.gamma_url, "gamma_embed_url": setting.gamma_embed_url}


def extract_iframe_src(value):
    value = (value or "").strip()
    if not value:
        return ""
    if "<iframe" in value.lower():
        import re
        match = re.search(r"src\s*=\s*[\"']([^\"']+)[\"']", value, flags=re.I)
        return match.group(1).strip() if match else ""
    return value


def valid_gamma_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and (host == "gamma.app" or host.endswith(".gamma.app"))



def audit(action, entity_type, entity_id, entity_name, before=None, after=None):
    db.session.add(AuditLog(
        admin_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        before_data=before,
        after_data=after,
    ))


def valid_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def valid_image_reference(value):
    if not value:
        return True
    return value.startswith("/static/") or valid_url(value)


def is_safe_redirect(target):
    if not target:
        return False
    base = urlparse(request.host_url)
    destination = urlparse(urljoin(request.host_url, target))
    return destination.scheme in ("http", "https") and base.netloc == destination.netloc


def valid_password(password):
    return len(password) >= 12


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        admin = Admin.query.filter_by(email=email, is_active=True).first()
        if admin and check_password_hash(admin.password_hash, password):
            session.clear()
            session.permanent = True
            login_user(admin, remember=False)
            next_url = request.args.get("next")
            return redirect(next_url if is_safe_redirect(next_url) else url_for("admin.dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("admin/login.html")


@admin_bp.post("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Você saiu do painel administrativo.", "success")
    return redirect(url_for("public.index"))


@admin_bp.route("/")
@login_required
def dashboard():
    return render_template(
        "admin/dashboard.html",
        link_count=Link.query.count(),
        active_count=Link.query.filter_by(is_active=True).count(),
        inactive_count=Link.query.filter_by(is_active=False).count(),
        category_count=Category.query.count(),
        admin_count=Admin.query.filter_by(is_active=True).count(),
        recent=AuditLog.query.order_by(desc(AuditLog.created_at)).limit(8).all(),
        database_backend=db.engine.url.get_backend_name(),
        storage_backend=storage_backend(),
    )


@admin_bp.route("/links")
@login_required
def links():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("categoria", type=int)
    status = request.args.get("status", "").strip()
    query = Link.query.join(Category)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Link.title.ilike(like), Link.description.ilike(like), Link.url.ilike(like)))
    if category_id:
        query = query.filter(Link.category_id == category_id)
    if status == "ativo":
        query = query.filter(Link.is_active.is_(True))
    elif status == "inativo":
        query = query.filter(Link.is_active.is_(False))
    elif status == "beta":
        query = query.filter(Link.is_beta.is_(True))
    return render_template(
        "admin/links.html",
        links=query.order_by(Category.sort_order, Link.sort_order, Link.title).all(),
        categories=Category.query.order_by(Category.sort_order, Category.name).all(),
        search=q,
        selected_category=category_id,
        selected_status=status,
    )


@admin_bp.route("/links/new", methods=["GET", "POST"])
@admin_bp.route("/links/<int:link_id>/edit", methods=["GET", "POST"])
@login_required
def edit_link(link_id=None):
    link = db.session.get(Link, link_id) if link_id else Link()
    if link_id and not link:
        abort(404)
    before = snapshot_link(link) if link_id else None
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    if not categories:
        flash("Crie pelo menos uma categoria antes de cadastrar um acesso.", "warning")
        return redirect(url_for("admin.categories"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()
        image_url = request.form.get("image_url", "").strip()
        image_file = request.files.get("image_file")
        category_id = request.form.get("category_id", type=int)
        if not title:
            flash("Informe o nome do acesso.", "danger")
        elif not db.session.get(Category, category_id):
            flash("Selecione uma categoria válida.", "danger")
        elif not valid_url(url) or not valid_image_reference(image_url):
            flash("A URL do acesso deve começar com https:// ou http://. A imagem pode ser uma URL externa ou um arquivo local do portal.", "danger")
        else:
            try:
                uploaded_image = save_tool_image(image_file)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("admin/link_form.html", link=link, categories=categories, storage_backend=storage_backend())
            old_image = link.image_url if link_id else ""
            link.title = title
            link.description = request.form.get("description", "").strip()
            link.url = url
            link.category_id = category_id
            link.icon = request.form.get("icon", "external-link").strip() or "external-link"
            new_image = uploaded_image or image_url
            link.image_url = new_image
            if old_image and old_image != new_image:
                delete_stored_image(old_image)
            link.is_active = request.form.get("is_active") == "on" and bool(url)
            link.is_beta = request.form.get("is_beta") == "on"
            link.sort_order = request.form.get("sort_order", 0, type=int) or 0
            link.updated_by_id = current_user.id
            if not link_id:
                db.session.add(link)
            db.session.flush()
            audit("atualização" if link_id else "criação", "link", link.id, link.title, before, snapshot_link(link))
            db.session.commit()
            flash("Acesso salvo. O portal público já reflete a alteração.", "success")
            return redirect(url_for("admin.links"))
    return render_template("admin/link_form.html", link=link, categories=categories, storage_backend=storage_backend())


@admin_bp.post("/links/<int:link_id>/toggle")
@login_required
def toggle_link(link_id):
    link = db.get_or_404(Link, link_id)
    before = snapshot_link(link)
    if not link.is_active and not link.url:
        flash("Cadastre um endereço antes de ativar o acesso.", "warning")
        return redirect(url_for("admin.links"))
    link.is_active = not link.is_active
    link.updated_by_id = current_user.id
    audit("ativação/desativação", "link", link.id, link.title, before, snapshot_link(link))
    db.session.commit()
    flash("Status atualizado.", "success")
    return redirect(url_for("admin.links"))


@admin_bp.post("/links/<int:link_id>/delete")
@login_required
def delete_link(link_id):
    link = db.get_or_404(Link, link_id)
    before = snapshot_link(link)
    audit("exclusão", "link", link.id, link.title, before, None)
    delete_stored_image(link.image_url)
    db.session.delete(link)
    db.session.commit()
    flash("Acesso removido.", "success")
    return redirect(url_for("admin.links"))


@admin_bp.route("/categorias", methods=["GET", "POST"])
@login_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "folder").strip() or "folder"
        sort_order = request.form.get("sort_order", 0, type=int) or 0
        exists = Category.query.filter(db.func.lower(Category.name) == name.lower()).first() if name else None
        if name and not exists:
            category = Category(name=name, icon=icon, sort_order=sort_order)
            db.session.add(category)
            db.session.flush()
            audit("criação", "categoria", category.id, category.name, None, snapshot_category(category))
            db.session.commit()
            flash("Categoria criada.", "success")
        else:
            flash("Informe um nome válido e ainda não utilizado.", "danger")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html", categories=Category.query.order_by(Category.sort_order, Category.name).all())


@admin_bp.post("/categorias/<int:category_id>/edit")
@login_required
def edit_category(category_id):
    category = db.get_or_404(Category, category_id)
    before = snapshot_category(category)
    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", "folder").strip() or "folder"
    sort_order = request.form.get("sort_order", 0, type=int) or 0
    duplicate = Category.query.filter(db.func.lower(Category.name) == name.lower(), Category.id != category.id).first() if name else None
    if not name or duplicate:
        flash("Use um nome de categoria válido e único.", "danger")
    else:
        category.name = name
        category.icon = icon
        category.sort_order = sort_order
        audit("atualização", "categoria", category.id, category.name, before, snapshot_category(category))
        db.session.commit()
        flash("Categoria atualizada.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.post("/categorias/<int:category_id>/delete")
@login_required
def delete_category(category_id):
    category = db.get_or_404(Category, category_id)
    if category.links:
        flash("Esta categoria ainda possui ferramentas. Mova ou remova os links antes.", "warning")
    else:
        audit("exclusão", "categoria", category.id, category.name, snapshot_category(category), None)
        db.session.delete(category)
        db.session.commit()
        flash("Categoria removida.", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/administradores", methods=["GET", "POST"])
@login_required
def admins():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or "@" not in email or not valid_password(password) or Admin.query.filter_by(email=email).first():
            flash("Confira os dados. Use um e-mail único e senha com pelo menos 12 caracteres.", "danger")
        else:
            admin = Admin(name=name, email=email, password_hash=generate_password_hash(password, method="scrypt"))
            db.session.add(admin)
            db.session.flush()
            audit("criação", "administrador", admin.id, admin.email, None, snapshot_admin(admin))
            db.session.commit()
            flash("Administrador cadastrado.", "success")
        return redirect(url_for("admin.admins"))
    return render_template("admin/admins.html", admins=Admin.query.order_by(Admin.name).all())


@admin_bp.post("/administradores/<int:admin_id>/toggle")
@login_required
def toggle_admin(admin_id):
    admin = db.get_or_404(Admin, admin_id)
    if admin.id == current_user.id:
        flash("Você não pode desativar a própria conta.", "warning")
    else:
        before = snapshot_admin(admin)
        admin.is_active = not admin.is_active
        audit("alteração de acesso", "administrador", admin.id, admin.email, before, snapshot_admin(admin))
        db.session.commit()
        flash("Acesso administrativo atualizado.", "success")
    return redirect(url_for("admin.admins"))


@admin_bp.post("/administradores/<int:admin_id>/reset-password")
@login_required
def reset_admin_password(admin_id):
    admin = db.get_or_404(Admin, admin_id)
    password = request.form.get("password", "")
    if not valid_password(password):
        flash("A nova senha deve ter pelo menos 12 caracteres.", "danger")
    else:
        admin.password_hash = generate_password_hash(password, method="scrypt")
        audit("redefinição de senha", "administrador", admin.id, admin.email, None, {"password": "alterada"})
        db.session.commit()
        flash("Senha do administrador redefinida.", "success")
    return redirect(url_for("admin.admins"))


@admin_bp.route("/minha-conta", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Informe seu nome.", "danger")
            else:
                before = snapshot_admin(current_user)
                current_user.name = name
                audit("atualização de perfil", "administrador", current_user.id, current_user.email, before, snapshot_admin(current_user))
                db.session.commit()
                flash("Perfil atualizado.", "success")
        elif action == "password":
            current_password = request.form.get("current_password", "")
            new_password = request.form.get("new_password", "")
            confirm_password = request.form.get("confirm_password", "")
            if not check_password_hash(current_user.password_hash, current_password):
                flash("A senha atual está incorreta.", "danger")
            elif new_password != confirm_password:
                flash("A confirmação da nova senha não confere.", "danger")
            elif not valid_password(new_password):
                flash("A nova senha deve ter pelo menos 12 caracteres.", "danger")
            else:
                current_user.password_hash = generate_password_hash(new_password, method="scrypt")
                audit("alteração de senha", "administrador", current_user.id, current_user.email, None, {"password": "alterada"})
                db.session.commit()
                flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("admin.account"))
    return render_template("admin/account.html")


@admin_bp.route("/portal", methods=["GET", "POST"])
@login_required
def portal_settings():
    setting = db.session.get(PortalSetting, 1)
    if not setting:
        setting = PortalSetting(id=1, gamma_url="", gamma_embed_url="")
        db.session.add(setting)
        db.session.commit()
    if request.method == "POST":
        gamma_url = request.form.get("gamma_url", "").strip()
        embed_raw = request.form.get("gamma_embed_url", "").strip()
        gamma_embed_url = extract_iframe_src(embed_raw)
        if not valid_gamma_url(gamma_url):
            flash("O link principal precisa ser uma URL HTTPS do Gamma.", "danger")
        elif gamma_embed_url and not valid_gamma_url(gamma_embed_url):
            flash("O embed precisa ser uma URL HTTPS do Gamma ou o código iframe copiado do Gamma.", "danger")
        else:
            before = snapshot_portal(setting)
            setting.gamma_url = gamma_url
            setting.gamma_embed_url = gamma_embed_url
            setting.updated_by_id = current_user.id
            audit("atualização", "portal", setting.id, "Configurações do portal", before, snapshot_portal(setting))
            db.session.commit()
            flash("Configurações do portal atualizadas.", "success")
            return redirect(url_for("admin.portal_settings"))
    return render_template("admin/portal.html", setting=setting, storage_backend=storage_backend())


@admin_bp.route("/historico")
@login_required
def history():
    q = request.args.get("q", "").strip()
    entity_type = request.args.get("tipo", "").strip()
    query = AuditLog.query.join(Admin)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(AuditLog.entity_name.ilike(like), AuditLog.action.ilike(like), Admin.name.ilike(like), Admin.email.ilike(like)))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    logs = query.order_by(desc(AuditLog.created_at)).limit(500).all()
    return render_template("admin/history.html", logs=logs, search=q, selected_type=entity_type)


@admin_bp.get("/backup.json")
@login_required
def backup_json():
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": [snapshot_category(c) | {"id": c.id} for c in Category.query.order_by(Category.sort_order, Category.name).all()],
        "links": [snapshot_link(link) | {"id": link.id} for link in Link.query.order_by(Link.id).all()],
        "portal": snapshot_portal(db.session.get(PortalSetting, 1)) if db.session.get(PortalSetting, 1) else None,
    }
    return Response(
        json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=central-fpa-backup.json"},
    )
