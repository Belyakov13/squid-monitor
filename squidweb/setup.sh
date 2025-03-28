#!/bin/bash
echo "Настройка приложения Squid Monitor..."

# Установка зависимостей
echo "Установка зависимостей..."
pip3 install -r requirements.txt

# Проверка версии Redis
REDIS_VERSION=$(pip3 show redis | grep Version | awk '{print $2}')
if [[ "$REDIS_VERSION" != "4.6.0" ]]; then
    echo "Установка правильной версии Redis..."
    pip3 uninstall -y redis
    pip3 install redis==4.6.0
fi

# Установка Redis, если его нет
if ! command -v redis-server &> /dev/null; then
    echo "Установка Redis..."
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
fi

# Сбор статических файлов
echo "Сбор статических файлов..."
python3 manage.py collectstatic --noinput

# Предварительное заполнение кэша
echo "Заполнение кэша..."
python3 manage.py update_cache

# Установка прав на запуск скриптов
echo "Установка прав на запуск скриптов..."
chmod +x start_celery.sh
chmod +x start_server.sh
chmod +x update_cache.sh
chmod +x fix_redis.sh

echo "Настройка завершена!"
echo "Для запуска приложения выполните:"
echo "1. ./start_celery.sh - для запуска Celery"
echo "2. ./start_server.sh - для запуска веб-сервера"
