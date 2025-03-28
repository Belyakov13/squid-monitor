from django.core.management.base import BaseCommand
from monitor.tasks import update_log_cache, generate_traffic_charts, generate_domain_charts, update_users_cache

class Command(BaseCommand):
    help = 'Обновляет кэш для ускорения работы приложения'

    def handle(self, *args, **options):
        self.stdout.write('Обновление кэша логов...')
        entries_count = update_log_cache()
        self.stdout.write(self.style.SUCCESS(f'Кэш логов обновлен, обработано {entries_count} записей'))
        
        self.stdout.write('Генерация графиков трафика...')
        generate_traffic_charts()
        self.stdout.write(self.style.SUCCESS('Графики трафика сгенерированы'))
        
        self.stdout.write('Генерация графиков доменов...')
        generate_domain_charts()
        self.stdout.write(self.style.SUCCESS('Графики доменов сгенерированы'))
        
        self.stdout.write('Обновление кэша пользователей...')
        users_count = update_users_cache()
        self.stdout.write(self.style.SUCCESS(f'Кэш пользователей обновлен, обработано {users_count} пользователей'))
        
        self.stdout.write(self.style.SUCCESS('Все задачи выполнены успешно'))
