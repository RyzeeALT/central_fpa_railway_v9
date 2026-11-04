from flask import Blueprint, render_template, request, abort, send_from_directory
from sqlalchemy import or_
from . import db
from .models import Link, Category, PortalSetting
from .storage import railway_volume_root

public_bp = Blueprint("public", __name__)
GAMMA_TITLES = ["Apresentações de resultados", "Apresentação de Resultados", "Status e Resultados de Projetos"]
GAMMA_FALLBACK_URL = "https://gamma.app/docs/Status-e-Resultados-de-Projetos-Planejamento-Financeiro-e-Control-nf32vtoycjihai5"


@public_bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("categoria", type=int)
    query = Link.query.filter_by(is_active=True).join(Category).filter(~Link.title.in_(GAMMA_TITLES))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(Link.title.ilike(like), Link.description.ilike(like), Category.name.ilike(like)))
    if category_id:
        query = query.filter(Link.category_id == category_id)
    links = query.order_by(Category.sort_order, Link.sort_order, Link.title).all()
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    return render_template("index.html", links=links, categories=categories, selected_category=category_id, search=q)


@public_bp.get("/resultados")
def resultados():
    setting = db.session.get(PortalSetting, 1)
    gamma_url = (setting.gamma_url.strip() if setting and setting.gamma_url else GAMMA_FALLBACK_URL)
    gamma_embed_url = setting.gamma_embed_url.strip() if setting and setting.gamma_embed_url else ""
    return render_template("resultados.html", gamma_url=gamma_url, gamma_embed_url=gamma_embed_url)


@public_bp.get("/ferramenta/<int:link_id>")
def link_detail(link_id):
    link = Link.query.filter_by(id=link_id, is_active=True).first()
    if not link:
        abort(404)
    return render_template("link_detail.html", link=link)


@public_bp.get("/media/tools/<path:filename>")
def media_tool(filename):
    root = railway_volume_root()
    if not root:
        abort(404)
    folder = root / "uploads" / "tools"
    return send_from_directory(folder, filename, max_age=86400)
