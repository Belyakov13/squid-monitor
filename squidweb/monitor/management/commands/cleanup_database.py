from django.core.management.base import BaseCommand
from monitor.models import SquidLog
from django.utils import timezone
from datetime import timedelta
import os
from django.conf import settings
from django.db.models import Min, Max, Count

class Command(BaseCommand):
    help = 'Очистка базы данных при превышении размера'

    def handle(self, *args, **options):
        db_path = settings.DATABASES['default']['NAME']
        
        # Проверяем размер базы данных
        db_size = os.path.getsize(db_path)
        max_size = 800 * 1024 * 1024  # 800 MB в байтах
        
        if db_size > max_size:
            self.stdout.write(f'Размер базы данных ({db_size / 1024 / 1024:.2f} MB) превышает лимит')
            
            # Получаем временной диапазон всех записей
            stats = SquidLog.objects.aggregate(
                min_date=Min('timestamp'),
                max_date=Max('timestamp'),
                total_count=Count('id')
            )
            
            if not stats['total_count']:
                self.stdout.write('База данных пуста')
                return
                
            total_records = stats['total_count']
            time_range = stats['max_date'] - stats['min_date']
            
            # Вычисляем дату, до которой удалим записи (50% самых старых)
            cutoff_date = stats['min_date'] + (time_range * 0.5)  # удаляем первые 50% по времени
            
            # Удаляем записи старше cutoff_date
            deleted_count = SquidLog.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()[0]
            
            self.stdout.write(
                f'Удалено {deleted_count} записей старше {cutoff_date}'
            )
            
            # Выполняем VACUUM для освобождения места
            from django.db import connection
            cursor = connection.cursor()
            cursor.execute('VACUUM;')
            
            # Проверяем новый размер
            new_size = os.path.getsize(db_path)
            self.stdout.write(
                f'Новый размер базы данных: {new_size / 1024 / 1024:.2f} MB'
            )
            
            # Если размер всё ещё слишком большой, удаляем ещё записи
            if new_size > max_size:
                self.stdout.write('Размер всё ещё превышает лимит, удаляем ещё записи...')
                
                # Получаем новую статистику
                new_stats = SquidLog.objects.aggregate(
                    min_date=Min('timestamp'),
                    max_date=Max('timestamp')
                )
                
                if new_stats['min_date'] and new_stats['max_date']:
                    new_time_range = new_stats['max_date'] - new_stats['min_date']
                    new_cutoff_date = new_stats['min_date'] + (new_time_range * 0.5)
                    
                    # Удаляем ещё 50% оставшихся старых записей
                    additional_deleted = SquidLog.objects.filter(
                        timestamp__lt=new_cutoff_date
                    ).delete()[0]
                    
                    self.stdout.write(
                        f'Дополнительно удалено {additional_deleted} записей'
                    )
                    
                    # Снова выполняем VACUUM
                    cursor.execute('VACUUM;')
                    final_size = os.path.getsize(db_path)
                    self.stdout.write(
                        f'Финальный размер базы данных: {final_size / 1024 / 1024:.2f} MB'
                    )
        else:
            self.stdout.write(
                f'Размер базы данных ({db_size / 1024 / 1024:.2f} MB) в пределах нормы'
            )
