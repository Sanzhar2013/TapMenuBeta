import io, os, time, uuid, functools
import qrcode, requests
from PIL import Image
from flask import session, redirect, url_for, g, current_app
from models import db, User, Media

Image.MAX_IMAGE_PIXELS = 30_000_000


def tg_send(token, chat_id, text):
    token = token or os.getenv("BOT_TOKEN")
    if not token or not chat_id:
        return False
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=8)
        if not r.ok:
            current_app.logger.warning("Telegram HTTP %s", r.status_code)
        return r.ok
    except requests.RequestException as e:   # не логируем текст ошибки: в нём может быть токен
        current_app.logger.warning("Telegram failed: %s", type(e).__name__)
        return False


def save_image(file, cafe_id, max_side=1200):
    """Проверяет, что это реальная картинка, перекодирует в WebP (метаданные и скрытый код удаляются)."""
    try:
        img = Image.open(file.stream)
        if img.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError
        img = img.convert("RGB")
        img.thumbnail((max_side, max_side))
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=82)
    except Exception:
        raise ValueError("Допустимы только изображения JPG, PNG, WEBP")
    name = uuid.uuid4().hex
    db.session.add(Media(name=name, cafe_id=cafe_id, data=buf.getvalue()))
    return name


def delete_image(name, cafe_id):
    if name:
        Media.query.filter_by(name=name, cafe_id=cafe_id).delete()


def qr_png(url):
    img = qrcode.QRCode(box_size=10, border=3, error_correction=qrcode.constants.ERROR_CORRECT_M)
    img.add_data(url); img.make(fit=True)
    buf = io.BytesIO()
    img.make_image(fill_color="black", back_color="white").save(buf, "PNG")
    return buf.getvalue()


# --- авторизация ---
def login_user(u):
    session.clear(); session["uid"] = u.id


def current_user():
    uid = session.get("uid")
    return db.session.get(User, uid) if uid else None


def admin_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        u = current_user()
        if not u or u.is_owner or not u.cafe or not u.cafe.active:
            return redirect(url_for("admin.login"))
        g.user, g.cafe = u, u.cafe          # ВСЕ запросы админки фильтруются по g.cafe.id
        return f(*a, **k)
    return w


def owner_required(f):
    @functools.wraps(f)
    def w(*a, **k):
        u = current_user()
        if not u or not u.is_owner:
            return redirect(url_for("admin.login"))
        g.user = u
        return f(*a, **k)
    return w


_fails = {}
def too_many_fails(ip):
    _fails[ip] = [t for t in _fails.get(ip, []) if t > time.time() - 300]
    return len(_fails[ip]) >= 8

def register_fail(ip):
    _fails.setdefault(ip, []).append(time.time())
