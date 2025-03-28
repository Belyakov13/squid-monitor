from django.db import models
from django.core.validators import MaxValueValidator
from datetime import timedelta
from django.utils import timezone

class SquidLog(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    client_address = models.GenericIPAddressField(db_index=True)
    result_code = models.CharField(max_length=50)
    bytes = models.IntegerField()
    request_method = models.CharField(max_length=20)
    url = models.URLField(max_length=2048)
    user_ident = models.CharField(max_length=50, blank=True)
    hierarchy_code = models.CharField(max_length=50)
    content_type = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'client_address']),
            models.Index(fields=['client_address', 'timestamp']),
            models.Index(fields=['timestamp', 'bytes']),
            models.Index(fields=['client_address', 'bytes']),
        ]
        ordering = ['-timestamp']
        
        # Ограничение на 2 дня
        constraints = [
            models.CheckConstraint(
                check=models.Q(timestamp__gte=timezone.now() - timedelta(days=2)),
                name='log_date_constraint'
            )
        ]

    def __str__(self):
        return f"{self.timestamp} - {self.client_address} - {self.url}"

    @classmethod
    def cleanup_old_logs(cls):
        """Удаляет логи старше 2 дней"""
        two_days_ago = timezone.now() - timedelta(days=2)
        cls.objects.filter(timestamp__lt=two_days_ago).delete()
