#!/bin/bash

# Путь к проекту
PROJECT_DIR="/squidweb"
DB_FILE="$PROJECT_DIR/db.sqlite3"
MAX_SIZE=$((800*1024))  # 800 MB в килобайтах

cd $PROJECT_DIR
source venv/bin/activate

# Получаем размер базы в килобайтах
DB_SIZE=$(du -k "$DB_FILE" | cut -f1)

echo "Текущий размер базы: $DB_SIZE KB"
echo "Максимальный размер: $MAX_SIZE KB"

# Проверяем размер базы
if [ $DB_SIZE -gt $MAX_SIZE ]; then
    echo "База данных превышает максимальный размер. Запуск очистки..."
    python3 manage.py cleanup_database
    
    # Проверяем новый размер
    NEW_SIZE=$(du -k "$DB_FILE" | cut -f1)
    echo "Размер базы после очистки: $NEW_SIZE KB"
else
    echo "Размер базы данных в пределах нормы"
fi
