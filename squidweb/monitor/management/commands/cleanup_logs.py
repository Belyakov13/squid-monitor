from django.core.management.base import BaseCommand
from monitor.models import SquidLog

class Command(BaseCommand):
    help = 'Очистка старых логов'

    def handle(self, *args, **options):
        SquidLog.cleanup_old_logs()
        self.stdout.write(self.style.SUCCESS('Старые логи успешно удалены'))
