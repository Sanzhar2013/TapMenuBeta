import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
from models import db, Cafe, User, Category, Dish

csrf = CSRFProtect()

DEMO = [
    ("Завтраки", "Таңғы ас", [
        ("Сырники со сметаной", "Қаймақпен сырники", "Нежные творожные сырники, ягодный соус", "Жұмсақ ірімшік сырники, жидек тұздығы", 2200, None),
        ("Омлет с лососем", "Лосось қосылған омлет", "Яйца, слабосолёный лосось, зелень", "Жұмыртқа, тұздалған лосось, көкөніс", 2900, "new")]),
    ("Основные блюда", "Негізгі тағамдар", [
        ("Бешбармак", "Бешбармақ", "Классический, конина, домашняя лапша, шорпа", "Классикалық, жылқы еті, үй кеспесі, сорпа", 5900, "hit"),
        ("Стейк рибай", "Рибай стейк", "Мраморная говядина, овощи гриль", "Мәрмәр сиыр еті, грильдегі көкөністер", 9800, None)]),
    ("Салаты", "Салаттар", [
        ("Цезарь с курицей", "Тауық етті Цезарь", "Романо, пармезан, соус цезарь", "Романо, пармезан, цезарь тұздығы", 3200, None),
        ("Тёплый салат с говядиной", "Ыстық сиыр еті салаты", "Говядина, болгарский перец, кунжут", "Сиыр еті, болгар бұрышы, күнжіт", 3800, "spicy")]),
    ("Напитки", "Сусындар", [
        ("Чай с чабрецом", "Жебіршөп шайы", "Чёрный чай, чабрец, мёд", "Қара шай, жебіршөп, бал", 1200, None),
        ("Капучино", "Капучино", "Двойной эспрессо, молоко", "Қос эспрессо, сүт", 1500, None)]),
    ("Десерты", "Десерттер", [
        ("Чак-чак", "Шәкшәк", "Медовый десерт по домашнему рецепту", "Үй рецепті бойынша балды десерт", 1800, "hit"),
        ("Тирамису", "Тирамису", "Маскарпоне, кофе, какао", "Маскарпоне, кофе, какао", 2400, None)]),
]


def ensure_owner():
    pw = os.getenv("OWNER_PASSWORD")
    if pw and not User.query.filter_by(is_owner=True).first():
        u = User(username=os.getenv("OWNER_USERNAME", "owner").lower(), is_owner=True)
        u.set_password(pw); db.session.add(u); db.session.commit()


def create_app():
    app = Flask(__name__)
    prod = os.getenv("APP_ENV") == "production"
    secret = os.getenv("SECRET_KEY")
    if prod and not secret:
        raise RuntimeError("В production обязателен SECRET_KEY")
    uri = os.getenv("DATABASE_URL", "sqlite:///tapmenu.db")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config.update(SECRET_KEY=secret or "dev-secret-change-me", SQLALCHEMY_DATABASE_URI=uri,
                      SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}, MAX_CONTENT_LENGTH=6 * 1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=prod,
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    db.init_app(app); csrf.init_app(app)

    from public import bp as p; from admin import bp as a; from owner import bp as o
    for b in (p, a, o):
        app.register_blueprint(b)

    off = int(os.getenv("TZ_OFFSET", "5"))
    app.jinja_env.filters["local"] = lambda d: (d + timedelta(hours=off)).strftime("%d.%m %H:%M")
    app.jinja_env.filters["money"] = lambda n: f"{n:,}".replace(",", "\u00a0")

    @app.after_request
    def headers(r):
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["Referrer-Policy"] = "same-origin"
        if prod:
            r.headers["Strict-Transport-Security"] = "max-age=31536000"
        return r

    with app.app_context():
        db.create_all()
        ensure_owner()

    @app.cli.command("seed")
    def seed():
        """Создаёт владельца и демо-кафе с блюдами."""
        if not User.query.filter_by(is_owner=True).first():
            u = User(username=os.getenv("OWNER_USERNAME", "owner").lower(), is_owner=True)
            u.set_password(os.getenv("OWNER_PASSWORD", "owner12345")); db.session.add(u)
        if not Cafe.query.filter_by(slug="demo").first():
            c = Cafe(slug="demo", name="Кафе «Алтын»", name_kk="«Алтын» кафесі", tables_count=12,
                     description="Казахская и европейская кухня в центре города",
                     description_kk="Қала орталығындағы қазақ және еуропа асханасы")
            db.session.add(c); db.session.flush()
            a = User(username="demo", cafe_id=c.id); a.set_password("demo12345"); db.session.add(a)
            for i, (n, nk, dishes) in enumerate(DEMO):
                cat = Category(cafe_id=c.id, name=n, name_kk=nk, position=i); db.session.add(cat); db.session.flush()
                for dn, dk, dd, ddk, pr, bd in dishes:
                    db.session.add(Dish(cafe_id=c.id, category_id=cat.id, name=dn, name_kk=dk, description=dd,
                                        description_kk=ddk, price=pr, badge=bd))
        db.session.commit()
        print("Владелец: owner / owner12345 (или из .env) -> /owner\nДемо-кафе: demo / demo12345 -> /admin  | меню: /c/demo?t=5")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=not os.getenv("APP_ENV") == "production")
