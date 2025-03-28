#!/bin/bash
echo "Проверка состояния Squid Monitor..."

# Проверка Redis
echo -n "Redis: "
if systemctl is-active --quiet redis-server; then
    echo "РАБОТАЕТ"
else
    echo "НЕ РАБОТАЕТ"
fi

# Проверка Celery
echo -n "Celery Worker: "
if pgrep -f "celery -A squid_monitor worker" > /dev/null; then
    echo "РАБОТАЕТ"
else
    echo "НЕ РАБОТАЕТ"
fi

echo -n "Celery Beat: "
if pgrep -f "celery -A squid_monitor beat" > /dev/null; then
    echo "РАБОТАЕТ"
else
    echo "НЕ РАБОТАЕТ"
fi

# Проверка Gunicorn
echo -n "Gunicorn: "
if pgrep -f "gunicorn squid_monitor.wsgi" > /dev/null; then
    echo "РАБОТАЕТ"
else
    echo "НЕ РАБОТАЕТ"
fi

# Проверка доступности веб-интерфейса
echo -n "Веб-интерфейс: "
if curl -s --head http://localhost:8000 | grep "200 OK" > /dev/null; then
    echo "ДОСТУПЕН"
else
    echo "НЕДОСТУПЕН"
fi

# Проверка кэша
echo -n "Кэш: "
if python3 -c "from django.core.cache import cache; print('OK' if cache.get('squid_log_entries_day') else 'ПУСТО')" 2>/dev/null | grep "OK" > /dev/null; then
    echo "ЗАПОЛНЕН"
else
    echo "ПУСТ (запустите ./update_cache.sh)"
fi

echo "Проверка завершена!"
