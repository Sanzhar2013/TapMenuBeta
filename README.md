# TapMenu — «Ас мәзірі • Бір қолмен»

Электронное меню для кафе: QR/NFC → меню (RU/KK) → вызов официанта → Telegram.
Мультитенантность: у каждого кафе свой админ, меню, фото, Telegram, QR. Админ кафе видит только свои данные
(все запросы в `admin.py` идут через `own()` / `cafe_id = g.cafe.id`).

## Структура
```
app.py        фабрика приложения, seed-команда, заголовки безопасности
models.py     Cafe, User, Category, Dish, WaiterCall, Media
public.py     меню, вызов официанта, отдача фото, /healthz
admin.py      админка кафе (вызовы, блюда, категории, настройки, QR)
owner.py      панель владельца TapMenu (создание кафе, отключение, сброс пароля)
utils.py      Telegram, обработка фото, QR, авторизация
templates/ static/   интерфейс (чёрный/золотой, орнамент, RU/KK)
requirements.txt  .env.example  render.yaml
```

## Быстрый старт (Windows)
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        (откройте .env и задайте SECRET_KEY)
flask --app app seed
python app.py
```
Откройте http://localhost:5000 · меню: `/c/demo?t=5`

**Тестовые аккаунты** (после `seed`):
- Владелец: `owner` / `owner12345` → `/admin/login` (перенаправит в `/owner`)
- Кафе «Алтын»: `demo` / `demo12345` → `/admin`

## Android (Termux)
```
pkg update && pkg install python libjpeg-turbo libpng clang git
cd tapmenu
python -m venv venv && source venv/bin/activate
grep -v psycopg2 requirements.txt > req-termux.txt
LDFLAGS="-L/system/lib64" CFLAGS="-I/data/data/com.termux/files/usr/include" pip install -r req-termux.txt
cp .env.example .env && flask --app app seed && python app.py
```
Откройте в браузере телефона http://localhost:5000. Для доступа гостей снаружи нужен хостинг (см. ниже).

## Telegram
1. @BotFather → `/newbot` → получите токен → `BOT_TOKEN` в `.env` (один бот на все кафе) —
   либо каждое кафе вводит токен своего бота в «Настройки».
2. Админ кафе (или группа персонала) пишет боту `/start`.
3. Chat ID: напишите боту @userinfobot (личный чат) или добавьте бота в группу и откройте
   `https://api.telegram.org/bot<TOKEN>/getUpdates` — для группы ID начинается с `-`.
4. «Настройки» → Chat ID → «Отправить тест в Telegram».
Если Telegram недоступен, вызов всё равно сохраняется и виден в админке (⚠ пометка).

## Хостинг на Render
1. Создайте PostgreSQL (Render или внешний бесплатный: Neon/Supabase — проверьте актуальные условия тарифов;
   у бесплатных баз бывают ограничения по сроку).
2. Залейте проект в GitHub → Render → New → Blueprint (`render.yaml`) или Web Service:
   Build `pip install -r requirements.txt`, Start `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`.
3. Переменные: `APP_ENV=production`, `SECRET_KEY`, `DATABASE_URL` (строка подключения Postgres),
   `BASE_URL=https://ваш-сервис.onrender.com`, `BOT_TOKEN`, `OWNER_PASSWORD` (владелец создаётся при первом запуске).
4. **HTTPS** Render выдаёт автоматически; для своего домена добавьте его в Settings → Custom Domains
   и пропишите CNAME. В production включены Secure-cookie и HSTS.
5. **Фото** хранятся в PostgreSQL (таблица `media`, WebP до 1200 px) — не пропадают при перезапуске
   бесплатного сервера с временной файловой системой. SQLite на сервере не используйте.
   При росте перенесите фото в S3/Cloudinary: нужно изменить только `save_image`, `delete_image` и `/media/<name>`.

## Безопасность (что сделано)
хеши паролей (werkzeug), CSRF-токены на всех формах и вызове официанта, ORM (нет SQL-инъекций),
проверка и перекодирование фото (метаданные и скрытое содержимое удаляются), лимит вызовов
(1 в минуту на столик, 5 за 10 мин с IP), блок перебора пароля, изоляция кафе, токены только в env/БД и никогда в HTML,
HTML-экранирование в Telegram-сообщениях.

## От себя (дополнительно)
метки блюд «Хит / Новинка / Острое»; быстрые причины вызова (счёт, салфетки, помощь, заказ);
автообновление списка вызовов + статусы «Принять → Готово»; тест-кнопка Telegram;
печать QR-листа; отключение неоплатившего кафе одной кнопкой; `/healthz`.

## Идеи для развития
тарифы и биллинг по кафе, Flask-Migrate (Alembic), webhook с кнопкой «Принято» прямо в Telegram,
статистика по столикам, поддержка английского языка, сброс пароля по e-mail, S3-хранилище.
