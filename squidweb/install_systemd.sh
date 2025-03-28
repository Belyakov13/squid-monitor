#!/bin/bash
echo "Установка systemd сервисов для Squid Monitor..."

# Определяем путь к приложению
APP_PATH=$(pwd)

# Заменяем путь в файлах сервисов
sed -i "s|/path/to/squidweb|$APP_PATH|g" systemd/squid-monitor.service
sed -i "s|/path/to/squidweb|$APP_PATH|g" systemd/squid-monitor-celery.service
sed -i "s|/path/to/squidweb|$APP_PATH|g" systemd/squid-monitor-celerybeat.service

# Копируем файлы сервисов в systemd
sudo cp systemd/squid-monitor.service /etc/systemd/system/
sudo cp systemd/squid-monitor-celery.service /etc/systemd/system/
sudo cp systemd/squid-monitor-celerybeat.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем и запускаем сервисы
sudo systemctl enable squid-monitor.service
sudo systemctl enable squid-monitor-celery.service
sudo systemctl enable squid-monitor-celerybeat.service

sudo systemctl start squid-monitor-celery.service
sudo systemctl start squid-monitor-celerybeat.service
sudo systemctl start squid-monitor.service

echo "Сервисы установлены и запущены!"
echo "Для проверки статуса выполните:"
echo "sudo systemctl status squid-monitor.service"
echo "sudo systemctl status squid-monitor-celery.service"
echo "sudo systemctl status squid-monitor-celerybeat.service"
