@echo off
echo Запуск сервера с Gunicorn...
start cmd /k "cd /d %~dp0 && python -m gunicorn squid_monitor.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:8000"
echo Сервер запущен на http://localhost:8000
