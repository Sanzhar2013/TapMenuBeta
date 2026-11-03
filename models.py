from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    name_kk = db.Column(db.String(120))
    description = db.Column(db.String(500), default="")
    description_kk = db.Column(db.String(500))
    logo = db.Column(db.String(40))
    tg_chat_id = db.Column(db.String(40))
    tg_token = db.Column(db.String(120))      # необязательно: свой бот кафе
    tables_count = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now)
    categories = db.relationship("Category", order_by="Category.position", cascade="all, delete-orphan")
    users = db.relationship("User", backref="cafe")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafe.id"), nullable=True, index=True)
    username = db.Column(db.String(60), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_owner = db.Column(db.Boolean, default=False)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check(self, pw):
        return check_password_hash(self.password_hash, pw)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafe.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    name_kk = db.Column(db.String(80))
    position = db.Column(db.Integer, default=0)


class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafe.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    name_kk = db.Column(db.String(120))
    description = db.Column(db.String(500), default="")
    description_kk = db.Column(db.String(500))
    price = db.Column(db.Integer, nullable=False, default=0)
    photo = db.Column(db.String(40))
    badge = db.Column(db.String(10))          # hit | new | spicy
    hidden = db.Column(db.Boolean, default=False)
    category = db.relationship("Category", backref="dishes")


class WaiterCall(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafe.id"), nullable=False, index=True)
    table = db.Column(db.String(10), nullable=False)
    comment = db.Column(db.String(300), default="")
    status = db.Column(db.String(12), default="new")   # new | accepted | done | cancelled
    notified = db.Column(db.Boolean, default=False)
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=now, index=True)


class Media(db.Model):
    """Фото хранятся в БД (PostgreSQL) — переживают перезапуски бесплатного хостинга."""
    name = db.Column(db.String(40), primary_key=True)
    cafe_id = db.Column(db.Integer, db.ForeignKey("cafe.id"), nullable=False, index=True)
    data = db.Column(db.LargeBinary, nullable=False)
