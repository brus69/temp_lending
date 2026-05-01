#!/bin/sh
set -e
cd /app

python manage.py migrate --noinput

if [ "${DJANGO_COLLECTSTATIC:-1}" != "0" ]; then
  python manage.py collectstatic --noinput --clear
fi

exec "$@"
