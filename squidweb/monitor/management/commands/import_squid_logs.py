from django.core.management.base import BaseCommand
from django.conf import settings
from monitor.models import SquidLog
from datetime import datetime
import re
from django.db import transaction
from django.utils import timezone
import os

class Command(BaseCommand):
    help = 'Импорт логов из Squid access.log'

    def handle(self, *args, **options):
        self.stdout.write(f'Начинаем импорт логов из {settings.SQUID_LOG_PATH}')
        
        # Проверяем существование файла
        if not os.path.exists(settings.SQUID_LOG_PATH):
            self.stdout.write(self.style.ERROR(f'Файл лога не найден: {settings.SQUID_LOG_PATH}'))
            return
            
        # Проверяем права доступа
        if not os.access(settings.SQUID_LOG_PATH, os.R_OK):
            self.stdout.write(self.style.ERROR(f'Нет прав на чтение файла: {settings.SQUID_LOG_PATH}'))
            return
            
        # Проверяем размер файла
        file_size = os.path.getsize(settings.SQUID_LOG_PATH)
        self.stdout.write(f'Размер файла лога: {file_size} байт')
        
        # Паттерн для формата лога Squid
        log_pattern = re.compile(
            r'(\d+\.\d+)\s+(\d+)\s+(\S+)\s+(\S+)\/(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
        )
        
        # Читаем последнюю запись из базы
        last_log = SquidLog.objects.order_by('-timestamp').first()
        last_timestamp = last_log.timestamp if last_log else None
        self.stdout.write(f'Последняя запись в базе: {last_timestamp}')

        new_logs = []
        processed_lines = 0
        matched_lines = 0
        skipped_lines = 0
        
        with open(settings.SQUID_LOG_PATH, 'r') as file:
            for line in file:
                processed_lines += 1
                try:
                    # Пропускаем пустые строки
                    if not line.strip():
                        continue
                        
                    parts = line.strip().split()
                    if len(parts) < 10:
                        continue
                        
                    timestamp = float(parts[0])
                    log_time = timezone.make_aware(datetime.fromtimestamp(timestamp))
                    
                    # Пропускаем старые записи
                    if last_timestamp and log_time <= last_timestamp:
                        skipped_lines += 1
                        continue
                        
                    matched_lines += 1
                    
                    # Разбираем строку лога
                    result_code_parts = parts[3].split('/')
                    result_code = parts[3]  # Оставляем как есть, если не удастся разделить
                    if len(result_code_parts) == 2:
                        result_code = f"{result_code_parts[0]}/{result_code_parts[1]}"
                    
                    new_logs.append(SquidLog(
                        timestamp=log_time,
                        client_address=parts[2],
                        result_code=result_code,
                        bytes=int(parts[4]),
                        request_method=parts[5],
                        url=parts[6],
                        user_ident=parts[7],
                        hierarchy_code=parts[8],
                        content_type=parts[9]
                    ))
                    
                    # Пакетная вставка каждые 1000 записей
                    if len(new_logs) >= 1000:
                        with transaction.atomic():
                            SquidLog.objects.bulk_create(new_logs)
                        self.stdout.write(f'Импортировано 1000 записей (всего обработано: {processed_lines})')
                        new_logs = []
                except Exception as e:
                    if processed_lines <= 5:
                        self.stdout.write(self.style.WARNING(f'Ошибка при обработке строки: {line.strip()}\nОшибка: {str(e)}'))
                    continue

        # Вставляем оставшиеся записи
        if new_logs:
            with transaction.atomic():
                SquidLog.objects.bulk_create(new_logs)
            self.stdout.write(f'Импортировано последние {len(new_logs)} записей')

        # Выводим статистику
        self.stdout.write(f'''
Статистика импорта:
- Всего обработано строк: {processed_lines}
- Успешно распознано: {matched_lines}
- Пропущено старых записей: {skipped_lines}
- Добавлено новых записей: {matched_lines - skipped_lines}
''')

        # Очищаем старые логи
        SquidLog.cleanup_old_logs()

        self.stdout.write(self.style.SUCCESS('Импорт логов успешно завершен'))
