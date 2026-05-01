# LendingStore (Django)

Интернет-магазин крепежа на Django с витриной, корзиной, заказами, личным кабинетом, отзывами/вопросами, избранным и расширенной админкой (включая импорт/экспорт товаров CSV/Excel).

## 1) Технологии

- Python 3.12+
- Django 6
- SQLite (по умолчанию) или PostgreSQL
- Gunicorn + WhiteNoise (для Docker/prod-like запуска)
- Pillow (изображения), OpenPyXL (Excel импорт/экспорт)

## 2) Структура проекта

- `django_store/` — настройки, URL root, WSGI/ASGI
- `shop/` — основное приложение (модели, views, urls, admin, формы)
- `templates/` — HTML шаблоны витрины и админки
- `static/` — статические ресурсы приложения
- `media/` — пользовательские загрузки (изображения товаров, категорий, отзывы)
- `docker/entrypoint.sh` — стартовый скрипт контейнера
- `docker-compose.yml` — базовый запуск с SQLite
- `docker-compose.postgres.yml` — оверлей для запуска с PostgreSQL

## 3) Быстрый запуск (локально, SQLite)

### 3.1 Подготовка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3.2 Миграции и суперпользователь

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 3.3 Старт

```bash
python manage.py runserver
```

- Витрина: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Админка: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

## 4) Переменные окружения

Настройки читаются из переменных окружения в `django_store/settings.py`.

Основные:

- `DJANGO_SECRET_KEY` — секретный ключ Django
- `DJANGO_DEBUG` — `1/0`, `true/false`
- `DJANGO_ALLOWED_HOSTS` — список через запятую, например `localhost,127.0.0.1,web`
- `DJANGO_CSRF_TRUSTED_ORIGINS` — список URL через запятую для HTTPS-прокси
- `DJANGO_SERVE_MEDIA` — раздача `media` через Django (`1` удобно в контейнере без nginx)
- `DJANGO_COLLECTSTATIC` — запуск `collectstatic` в entrypoint (`1` по умолчанию)
- `DJANGO_USE_POSTGRES` — переключатель БД (`1` = PostgreSQL, `0` = SQLite)
- `SQLITE_PATH` — путь к SQLite-файлу (для Docker задан как `/data/db.sqlite3`)

Для PostgreSQL:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

Пример см. в `env.example`.

## 5) Docker

## 5.1 Базовый запуск в Docker (SQLite)

```bash
docker compose up --build
```

Что происходит автоматически:

- выполняются миграции;
- собирается статика (`collectstatic`, если `DJANGO_COLLECTSTATIC=1`);
- приложение стартует через Gunicorn на `0.0.0.0:8000`.

Открыть:

- [http://127.0.0.1:8000](http://127.0.0.1:8000)

Остановить:

```bash
docker compose down
```

Удалить тома (SQLite/медиа):

```bash
docker compose down -v
```

## 5.2 Запуск в Docker с PostgreSQL

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

Здесь:

- добавляется сервис `db` (`postgres:16-alpine`);
- `web` переключается на `DJANGO_USE_POSTGRES=1`;
- подключение к БД идёт на `db:5432`.

Остановить:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down
```

Удалить и том PostgreSQL:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml down -v
```

## 5.3 Использование .env с Docker Compose

```bash
cp env.example .env
```

Дальше отредактируйте значения в `.env` и запускайте compose-команды как обычно.

## 6) Как переключить проект на PostgreSQL

Есть 2 типичных сценария.

## 6.1 Локально (без Docker)

1. Поднимите PostgreSQL.
2. Создайте БД/пользователя.
3. Экспортируйте переменные:

```bash
export DJANGO_USE_POSTGRES=1
export POSTGRES_DB=lending
export POSTGRES_USER=lending
export POSTGRES_PASSWORD=lending
export POSTGRES_HOST=127.0.0.1
export POSTGRES_PORT=5432
```

4. Примените миграции:

```bash
python manage.py migrate
```

5. Запустите сервер:

```bash
python manage.py runserver
```

## 6.2 В Docker

Используйте оверлей:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up --build
```

## 7) Бизнес-функции проекта

## 7.1 Витрина каталога

- Главная страница с категориями и промо-товарами.
- Страница категорий и подкатегорий.
- Товары в подкатегории с пагинацией.
- Поиск товаров (`name`, `sku`, `description`) с пагинацией.

## 7.2 Карточка товара

- Основное изображение + галерея миниатюр.
- Клик по основному изображению открывает модальное увеличенное фото.
- Характеристики товара из реляционной схемы `ProductSpecValue`.
- Отзывы пользователей с рейтингом и фото.
- Вопросы по товару.
- Кнопки: добавить в корзину, избранное, быстрый заказ.

## 7.3 Корзина и заказы

- Добавление/изменение/удаление позиций из корзины.
- Оформление заказа из корзины.
- Быстрый заказ с карточки товара.
- Страница успешного оформления.

## 7.4 Аккаунт пользователя

- Авторизация/регистрация.
- Подтверждение email через токен.
- Личные данные и редактирование профиля.
- Смена пароля.
- Избранные товары.
- Просмотр заказов.
- Организации пользователя.

## 7.5 Демо-данные

- При первом обращении к витрине срабатывает сидинг демо-каталога и отзывов/вопросов.
- Сидинг идемпотентный: недостающие демо-товары добавляются без дублей.

## 8) Админка: возможности

## 8.1 Категории

- SEO поля (`meta_title`, `meta_description`)
- загрузка изображения с ПК (`image`) + fallback `image_url`
- предпросмотр изображения
- управление характеристиками категории (`CategorySpecAttribute`, inline)

## 8.2 Товары

- загрузка основного изображения с ПК (`image`) + fallback `image_url`
- до 10 изображений галереи (`ProductGalleryImage`, inline)
- значения характеристик товара (`ProductSpecValue`, inline)
- предпросмотр изображения в админке

## 8.3 Импорт/экспорт товаров (CSV/Excel)

В списке товаров:

- кнопка **Импорт CSV/Excel**
- action **Экспорт выбранных товаров**
- чекбокс формата (**по умолчанию Excel**, можно CSV)

Экспорт включает:

- базовые поля товара;
- динамические колонки характеристик в виде `spec__<название>`.

Импорт:

- создание/обновление по `sku`;
- валидация числовых/булевых полей и существования категории по `category_slug`;
- итоговый отчёт об ошибках в сообщениях админки.

## 9) Работа со статикой и медиа

- Статика:
  - исходники в `static/`
  - для контейнера/production-like: `STATIC_ROOT=staticfiles`, WhiteNoise
- Медиа:
  - хранение в `media/`
  - в dev и docker-сценариях может раздаваться Django (`DJANGO_SERVE_MEDIA=1`)

## 10) Полезные команды

```bash
# Проверка проекта
python manage.py check

# Миграции
python manage.py makemigrations
python manage.py migrate

# Сбор статики вручную
python manage.py collectstatic --noinput

# Создание админа
python manage.py createsuperuser
```

## 11) Troubleshooting

- `ModuleNotFoundError: No module named 'django'`
  - убедитесь, что активировано `.venv` и установлены зависимости.

- Ошибки подключения к PostgreSQL
  - проверьте `DJANGO_USE_POSTGRES=1` и все `POSTGRES_*`.
  - в Docker убедитесь, что запуск с `docker-compose.postgres.yml`.

- Не грузятся media-файлы в контейнере
  - оставьте `DJANGO_SERVE_MEDIA=1` (или настройте внешний nginx).

- Изменения шаблонов/статики не видны
  - перезапустите контейнер/сервер, очистите кеш браузера.

## 12) Деплой на VPS (Nginx + Docker + HTTPS)

Ниже production-подход для одного сервера (Ubuntu), когда:

- приложение работает в Docker (Gunicorn + Django),
- PostgreSQL в Docker,
- наружу смотрит Nginx на хосте,
- HTTPS выдаёт Let’s Encrypt.

## 12.1 Подготовка сервера

Подключитесь по SSH и выполните:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release nginx
```

Установите Docker Engine + Compose plugin (официальный репозиторий Docker):

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Опционально, чтобы запускать Docker без `sudo`:

```bash
sudo usermod -aG docker $USER
newgrp docker
```

## 12.2 Размещение проекта

Пример:

```bash
sudo mkdir -p /opt/lendingstore
sudo chown -R $USER:$USER /opt/lendingstore
cd /opt/lendingstore
# git clone <repo-url> .
```

Создайте `.env` рядом с `docker-compose.yml`:

```bash
cp env.example .env
```

Минимально поменяйте в `.env`:

- `DJANGO_SECRET_KEY` — длинный уникальный ключ;
- `DJANGO_DEBUG=0`;
- `DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com`;
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com`;
- `POSTGRES_PASSWORD` — сложный пароль.

## 12.3 Старт контейнеров (с PostgreSQL)

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
```

Проверьте статус:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml ps
docker compose -f docker-compose.yml -f docker-compose.postgres.yml logs -f web
```

Создайте суперпользователя:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec web python manage.py createsuperuser
```

## 12.4 Nginx reverse proxy (HTTP)

Создайте конфиг `/etc/nginx/sites-available/lendingstore`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Активируйте и проверьте:

```bash
sudo ln -s /etc/nginx/sites-available/lendingstore /etc/nginx/sites-enabled/lendingstore
sudo nginx -t
sudo systemctl reload nginx
```

Убедитесь, что DNS A-записи домена указывают на ваш VPS.

## 12.5 HTTPS (Let’s Encrypt)

Установите certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Получите сертификат:

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Проверьте автопродление:

```bash
sudo certbot renew --dry-run
```

## 12.6 Рекомендуемые прод-переменные Django

В `.env`:

- `DJANGO_DEBUG=0`
- `DJANGO_SERVE_MEDIA=1` (если media отдаёт Django через Nginx прокси)
- `DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com`

Если позже вынесете `media/static` в отдельный Nginx location или S3 — `DJANGO_SERVE_MEDIA` можно выключить.

## 12.7 Обновление приложения (релизный цикл)

```bash
cd /opt/lendingstore
git pull
docker compose -f docker-compose.yml -f docker-compose.postgres.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.postgres.yml logs -f web
```

Миграции и `collectstatic` выполняются автоматически в `docker/entrypoint.sh`.

## 12.8 Резервные копии PostgreSQL

Бэкап:

```bash
docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup_$(date +%F).sql
```

Восстановление:

```bash
cat backup_YYYY-MM-DD.sql | docker compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Делайте бэкапы регулярно и храните копии вне VPS.

## 12.9 Мини-чеклист перед продом

- `DJANGO_DEBUG=0`
- секреты не захардкожены, а лежат в `.env`
- домен и SSL работают
- создан `superuser`
- проверены загрузка изображений и оформление заказа
- настроены бэкапы БД
- включен мониторинг логов (`docker compose logs`, journald/nginx logs)

