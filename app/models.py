from datetime import datetime, timezone
from flask_login import UserMixin
from . import db


def utcnow():
    return datetime.now(timezone.utc)


class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(60), default="folder", nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    links = db.relationship("Link", backref="category", lazy=True)


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.String(400), default="", nullable=False)
    url = db.Column(db.String(1000), default="", nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    icon = db.Column(db.String(60), default="external-link", nullable=False)
    image_url = db.Column(db.String(1000), default="", nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    is_beta = db.Column(db.Boolean, default=False, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=True)
    updated_by = db.relationship("Admin", foreign_keys=[updated_by_id])


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=False)
    admin = db.relationship("Admin")
    action = db.Column(db.String(40), nullable=False)
    entity_type = db.Column(db.String(40), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    entity_name = db.Column(db.String(180), nullable=False)
    before_data = db.Column(db.JSON, nullable=True)
    after_data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class PortalSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True, default=1)
    gamma_url = db.Column(db.String(1000), default="", nullable=False)
    gamma_embed_url = db.Column(db.String(1000), default="", nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("admin.id"), nullable=True)
    updated_by = db.relationship("Admin", foreign_keys=[updated_by_id])
