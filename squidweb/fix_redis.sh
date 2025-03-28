#!/bin/bash
echo "Исправление проблемы с Redis..."

# Устанавливаем правильную версию Redis
pip3 uninstall -y redis
pip3 install redis==4.6.0

# Удаляем проблемную опцию из settings.py
sed -i "/'PARSER_CLASS': 'redis.connection.HiredisParser',/d" squid_monitor/settings.py

# Перезапускаем сервисы
if systemctl is-active --quiet squid-monitor.service; then
    echo "Перезапуск systemd сервисов..."
    sudo systemctl restart squid-monitor-celery.service
    sudo systemctl restart squid-monitor-celerybeat.service
    sudo systemctl restart squid-monitor.service
else
    echo "Перезапуск приложения вручную..."
    # Останавливаем текущие процессы
    pkill -f "celery -A squid_monitor" || true
    pkill -f "gunicorn squid_monitor.wsgi" || true
    
    # Запускаем заново
    ./start_celery.sh
    ./start_server.sh
fi

echo "Исправление завершено!"
