#!/bin/bash
echo "Запуск Celery Worker..."
celery -A squid_monitor worker -l info --detach
echo "Запуск Celery Beat..."
celery -A squid_monitor beat -l info --detach
echo "Celery запущен!"
