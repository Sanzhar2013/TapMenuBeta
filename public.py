import html, re
from datetime import timedelta
from flask import Blueprint, render_template, request, jsonify, Response, abort, url_for
from models import db, Cafe, Category, Dish, WaiterCall, Media, now
from utils import tg_send

bp = Blueprint("public", __name__)
TABLE_RE = re.compile(r"^[0-9A-Za-zА-Яа-яЁё\-]{1,10}$")


@bp.route("/")
def index():
    return render_template("landing.html")


@bp.route("/healthz")
def healthz():
    return "ok"


@bp.route("/media/<name>")
def media(name):
    m = db.session.get(Media, name) or abort(404)
    return Response(m.data, mimetype="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})


@bp.route("/c/<slug>")
def menu(slug):
    cafe = Cafe.query.filter_by(slug=slug, active=True).first_or_404()
    table = request.args.get("t", "").strip()
    table = table if TABLE_RE.match(table) else ""
    sections = []
    for c in cafe.categories:
        dishes = Dish.query.filter_by(cafe_id=cafe.id, category_id=c.id, hidden=False).order_by(Dish.id).all()
        if dishes:
            sections.append((c, dishes))
    return render_template("menu.html", cafe=cafe, table=table, sections=sections)


@bp.route("/c/<slug>/call", methods=["POST"])
def call(slug):
    cafe = Cafe.query.filter_by(slug=slug, active=True).first_or_404()
    data = request.get_json(silent=True) or {}
    table = str(data.get("table", "")).strip()
    comment = str(data.get("comment", "")).strip()[:300]
    if not TABLE_RE.match(table):
        return jsonify(error="table"), 400
    ip = request.remote_addr or ""
    t = now()
    if WaiterCall.query.filter(WaiterCall.cafe_id == cafe.id, WaiterCall.table == table,
                               WaiterCall.created_at > t - timedelta(seconds=60)).count():
        return jsonify(error="wait"), 429
    if WaiterCall.query.filter(WaiterCall.cafe_id == cafe.id, WaiterCall.ip == ip,
                               WaiterCall.created_at > t - timedelta(minutes=10)).count() >= 5:
        return jsonify(error="limit"), 429
    c = WaiterCall(cafe_id=cafe.id, table=table, comment=comment, ip=ip)
    db.session.add(c); db.session.commit()
    esc = html.escape
    text = (f"🔔 <b>НОВЫЙ ВЫЗОВ ОФИЦИАНТА</b>\n\n🏠 Кафе: {esc(cafe.name)}\n"
            f"🪑 Столик: №{esc(table)}\n💬 Комментарий: {esc(comment or '—')}")
    c.notified = tg_send(cafe.tg_token, cafe.tg_chat_id, text)
    db.session.commit()
    return jsonify(ok=True)
