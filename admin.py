import os, re
from flask import (Blueprint, render_template, request, redirect, url_for, flash, g, session, abort, Response)
from models import db, Cafe, Category, Dish, WaiterCall, now
from utils import (admin_required, login_user, too_many_fails, register_fail, save_image, delete_image,
                   qr_png, tg_send, User)
from datetime import datetime

bp = Blueprint("admin", __name__, url_prefix="/admin")


def own(model, id_):
    """Единственный способ получить объект в админке: только из СВОЕГО кафе."""
    return model.query.filter_by(id=id_, cafe_id=g.cafe.id).first_or_404()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.remote_addr or ""
        if too_many_fails(ip):
            flash("Слишком много попыток. Подождите 5 минут.", "err")
        else:
            u = User.query.filter_by(username=request.form.get("username", "").strip().lower()).first()
            if u and u.check(request.form.get("password", "")) and (u.is_owner or (u.cafe and u.cafe.active)):
                login_user(u)
                return redirect(url_for("owner.dashboard" if u.is_owner else "admin.calls"))
            register_fail(ip)
            flash("Неверный логин или пароль", "err")
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@bp.route("/")
@admin_required
def calls():
    active = (WaiterCall.query.filter(WaiterCall.cafe_id == g.cafe.id, WaiterCall.status.in_(["new", "accepted"]))
              .order_by(WaiterCall.created_at).all())
    start = datetime.combine(now().date(), datetime.min.time())
    today = WaiterCall.query.filter(WaiterCall.cafe_id == g.cafe.id, WaiterCall.created_at >= start).count()
    return render_template("admin_calls.html", calls=active, today=today)


@bp.route("/history")
@admin_required
def history():
    rows = (WaiterCall.query.filter(WaiterCall.cafe_id == g.cafe.id, WaiterCall.status.in_(["done", "cancelled"]))
            .order_by(WaiterCall.created_at.desc()).limit(200).all())
    return render_template("admin_history.html", calls=rows)


@bp.post("/calls/<int:id>/<status>")
@admin_required
def call_status(id, status):
    if status not in ("accepted", "done", "cancelled"):
        abort(400)
    own(WaiterCall, id).status = status
    db.session.commit()
    return redirect(url_for("admin.calls"))


# ---------- блюда ----------
@bp.route("/dishes")
@admin_required
def dishes():
    rows = Dish.query.filter_by(cafe_id=g.cafe.id).order_by(Dish.category_id, Dish.id).all()
    return render_template("admin_dishes.html", dishes=rows)


def fill_dish(d):
    f = request.form
    name = f.get("name", "").strip()[:120]
    if not name:
        raise ValueError("Укажите название блюда")
    try:
        price = int(f.get("price", ""))
        assert 0 <= price <= 10_000_000
    except Exception:
        raise ValueError("Некорректная цена")
    cat = Category.query.filter_by(id=f.get("category_id", type=int), cafe_id=g.cafe.id).first()
    if not cat:
        raise ValueError("Выберите категорию")
    d.category_id, d.name, d.price = cat.id, name, price
    d.name_kk = f.get("name_kk", "").strip()[:120] or None
    d.description = f.get("description", "").strip()[:500]
    d.description_kk = f.get("description_kk", "").strip()[:500] or None
    d.badge = f.get("badge") if f.get("badge") in ("hit", "new", "spicy") else None
    d.hidden = bool(f.get("hidden"))
    photo = request.files.get("photo")
    if photo and photo.filename:
        new = save_image(photo, g.cafe.id)
        delete_image(d.photo, g.cafe.id)
        d.photo = new


@bp.route("/dishes/new", methods=["GET", "POST"], defaults={"id": None})
@bp.route("/dishes/<int:id>", methods=["GET", "POST"])
@admin_required
def dish_edit(id):
    d = own(Dish, id) if id else Dish(cafe_id=g.cafe.id)
    if request.method == "POST":
        try:
            fill_dish(d)
            db.session.add(d); db.session.commit()
            flash("Сохранено", "ok")
            return redirect(url_for("admin.dishes"))
        except ValueError as e:
            db.session.rollback(); flash(str(e), "err")
    return render_template("admin_dish.html", d=d, cats=g.cafe.categories)


@bp.post("/dishes/<int:id>/toggle")
@admin_required
def dish_toggle(id):
    d = own(Dish, id); d.hidden = not d.hidden
    db.session.commit()
    return redirect(url_for("admin.dishes"))


@bp.post("/dishes/<int:id>/delete")
@admin_required
def dish_delete(id):
    d = own(Dish, id); delete_image(d.photo, g.cafe.id)
    db.session.delete(d); db.session.commit()
    flash("Блюдо удалено", "ok")
    return redirect(url_for("admin.dishes"))


# ---------- категории ----------
@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()[:80]
        if name:
            pos = len(g.cafe.categories)
            db.session.add(Category(cafe_id=g.cafe.id, name=name, position=pos,
                                    name_kk=request.form.get("name_kk", "").strip()[:80] or None))
            db.session.commit()
        return redirect(url_for("admin.categories"))
    return render_template("admin_cats.html", cats=g.cafe.categories)


@bp.post("/categories/<int:id>")
@admin_required
def category_update(id):
    c = own(Category, id)
    name = request.form.get("name", "").strip()[:80]
    if name:
        c.name = name
        c.name_kk = request.form.get("name_kk", "").strip()[:80] or None
        c.position = request.form.get("position", type=int) or 0
        db.session.commit()
    return redirect(url_for("admin.categories"))


@bp.post("/categories/<int:id>/delete")
@admin_required
def category_delete(id):
    c = own(Category, id)
    if c.dishes:
        flash("Сначала удалите или перенесите блюда этой категории", "err")
    else:
        db.session.delete(c); db.session.commit()
    return redirect(url_for("admin.categories"))


# ---------- настройки ----------
@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings():
    c = g.cafe
    if request.method == "POST":
        f = request.form
        c.name = f.get("name", "").strip()[:120] or c.name
        c.name_kk = f.get("name_kk", "").strip()[:120] or None
        c.description = f.get("description", "").strip()[:500]
        c.description_kk = f.get("description_kk", "").strip()[:500] or None
        chat = f.get("tg_chat_id", "").strip()
        c.tg_chat_id = chat if re.fullmatch(r"-?\d{3,20}|@\w{4,40}", chat) else None
        if f.get("tg_token", "").strip():
            c.tg_token = f["tg_token"].strip()[:120]
        c.tables_count = min(max(f.get("tables_count", type=int) or 1, 1), 200)
        try:
            logo = request.files.get("logo")
            if logo and logo.filename:
                new = save_image(logo, c.id, 400); delete_image(c.logo, c.id); c.logo = new
            db.session.commit(); flash("Настройки сохранены", "ok")
        except ValueError as e:
            db.session.rollback(); flash(str(e), "err")
        return redirect(url_for("admin.settings"))
    return render_template("admin_settings.html", c=c, shared_bot=bool(os.getenv("BOT_TOKEN")))


@bp.post("/settings/test-telegram")
@admin_required
def test_tg():
    ok = tg_send(g.cafe.tg_token, g.cafe.tg_chat_id, f"✅ TapMenu: связь с Telegram работает.\n🏠 {g.cafe.name}")
    flash("Тестовое сообщение отправлено" if ok else "Не удалось отправить. Проверьте токен бота и Chat ID "
          "(и что вы нажали Start у бота).", "ok" if ok else "err")
    return redirect(url_for("admin.settings"))


# ---------- QR ----------
def base_url():
    return (os.getenv("BASE_URL") or request.host_url).rstrip("/")


@bp.route("/qr")
@admin_required
def qr():
    root = f"{base_url()}/c/{g.cafe.slug}"
    return render_template("admin_qr.html", root=root, n=g.cafe.tables_count)


@bp.route("/qr/<int:n>.png")
@admin_required
def qr_img(n):
    if not 0 <= n <= 200:
        abort(404)
    url = f"{base_url()}/c/{g.cafe.slug}" + (f"?t={n}" if n else "")
    return Response(qr_png(url), mimetype="image/png",
                    headers={"Content-Disposition": f'inline; filename="{g.cafe.slug}-{n or "cafe"}.png"'})
