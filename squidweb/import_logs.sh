#!/bin/bash
cd /squidweb
source venv/bin/activate

# Импорт новых логов
python3 manage.py import_squid_logs

# Очистка старых логов каждые 6 часов
current_hour=$(date +%H)
if [ $((current_hour % 6)) -eq 0 ]; then
    python3 manage.py cleanup_logs
fi

# Проверка размера базы данных
DB_FILE="/squidweb/db.sqlite3"
MAX_SIZE=$((800*1024))  # 800 MB в килобайтах
DB_SIZE=$(du -k "$DB_FILE" | cut -f1)

if [ $DB_SIZE -gt $MAX_SIZE ]; then
    echo "База данных превышает $MAX_SIZE KB. Запуск очистки..."
    python3 manage.py cleanup_database
fi
