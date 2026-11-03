import re
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, Cafe, User, Category, Dish, WaiterCall
from utils import owner_required

bp = Blueprint("owner", __name__, url_prefix="/owner")


@bp.route("/", methods=["GET", "POST"])
@owner_required
def dashboard():
    if request.method == "POST":
        f = request.form
        slug = f.get("slug", "").strip().lower()
        username = f.get("username", "").strip().lower()
        pw = f.get("password", "")
        if not f.get("name", "").strip() or not re.fullmatch(r"[a-z0-9-]{3,40}", slug):
            flash("Название обязательно; адрес — латиница, цифры, дефис (3–40 символов)", "err")
        elif len(pw) < 8 or not re.fullmatch(r"[a-z0-9_.-]{3,40}", username):
            flash("Логин: латиница/цифры (3–40), пароль от 8 символов", "err")
        elif Cafe.query.filter_by(slug=slug).first() or User.query.filter_by(username=username).first():
            flash("Такой адрес или логин уже занят", "err")
        else:
            c = Cafe(slug=slug, name=f["name"].strip()[:120])
            db.session.add(c); db.session.flush()
            u = User(username=username, cafe_id=c.id); u.set_password(pw)
            db.session.add(u)
            for i, n in enumerate(["Завтраки", "Основные блюда", "Салаты", "Напитки", "Десерты"]):
                db.session.add(Category(cafe_id=c.id, name=n, position=i))
            db.session.commit(); flash(f"Кафе «{c.name}» создано", "ok")
        return redirect(url_for("owner.dashboard"))
    rows = []
    for c in Cafe.query.order_by(Cafe.id).all():
        rows.append((c, Dish.query.filter_by(cafe_id=c.id).count(), WaiterCall.query.filter_by(cafe_id=c.id).count(),
                     User.query.filter_by(cafe_id=c.id).first()))
    return render_template("owner.html", rows=rows)


@bp.post("/<int:id>/toggle")
@owner_required
def toggle(id):
    c = db.get_or_404(Cafe, id); c.active = not c.active
    db.session.commit()
    return redirect(url_for("owner.dashboard"))


@bp.post("/<int:id>/password")
@owner_required
def password(id):
    u = User.query.filter_by(cafe_id=id).first_or_404()
    pw = request.form.get("password", "")
    if len(pw) < 8:
        flash("Пароль от 8 символов", "err")
    else:
        u.set_password(pw); db.session.commit(); flash("Пароль изменён", "ok")
    return redirect(url_for("owner.dashboard"))
