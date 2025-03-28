from celery import shared_task
from .utils import SquidLogReader
import pandas as pd
import plotly.express as px
from urllib.parse import urlparse
from datetime import timedelta
from django.utils import timezone
from zoneinfo import ZoneInfo
from django.core.cache import cache

@shared_task
def update_log_cache():
    """Задача для обновления кэша логов"""
    reader = SquidLogReader()
    entries = reader.get_last_lines(n=0)
    
    # Кэшируем на 5 минут
    cache.set('squid_log_entries_all', entries, 300)
    
    # Фильтруем записи для дневной и месячной статистики
    now = timezone.now().astimezone(ZoneInfo('Europe/Moscow'))
    day_limit = now - timedelta(hours=24)
    month_limit = now - timedelta(days=30)
    
    day_entries = [entry for entry in entries if entry['timestamp'] >= day_limit]
    month_entries = [entry for entry in entries if entry['timestamp'] >= month_limit]
    
    cache.set('squid_log_entries_day', day_entries, 300)
    cache.set('squid_log_entries_month', month_entries, 300)
    
    return len(entries)

@shared_task
def generate_traffic_charts():
    """Задача для генерации графиков трафика"""
    # Получаем записи из кэша
    day_entries = cache.get('squid_log_entries_day')
    month_entries = cache.get('squid_log_entries_month')
    
    if not day_entries or not month_entries:
        # Если кэш пуст, запускаем обновление и выходим
        update_log_cache.delay()
        return False
    
    # Статистика по времени для дня
    hourly_stats = {}
    for entry in day_entries:
        hour = entry['timestamp'].replace(minute=0, second=0, microsecond=0)
        if hour not in hourly_stats:
            hourly_stats[hour] = {'traffic': 0, 'requests': 0}
        hourly_stats[hour]['traffic'] += entry['bytes']
        hourly_stats[hour]['requests'] += 1
    
    # Создаем график для дня
    if hourly_stats:
        df = pd.DataFrame([
            {'time': hour.strftime('%H:%M'), 'traffic': stats['traffic']}
            for hour, stats in sorted(hourly_stats.items())
        ])
        if not df.empty:
            fig = px.line(df, x='time', y='traffic',
                        title='Объем трафика за последние 24 часа')
            fig.update_layout(
                xaxis_title='Время',
                yaxis_title='Трафик',
                template='plotly_white',
                yaxis=dict(tickformat='.2s')
            )
            chart_html = fig.to_html(full_html=False)
            cache.set('traffic_chart_day', chart_html, 300)
    
    # Статистика по времени для месяца
    daily_stats = {}
    for entry in month_entries:
        day = entry['timestamp'].date()
        if day not in daily_stats:
            daily_stats[day] = {'traffic': 0, 'requests': 0}
        daily_stats[day]['traffic'] += entry['bytes']
        daily_stats[day]['requests'] += 1
    
    # Создаем график для месяца
    if daily_stats:
        df = pd.DataFrame([
            {'date': day.strftime('%d.%m'), 'traffic': stats['traffic']}
            for day, stats in sorted(daily_stats.items())
        ])
        if not df.empty:
            fig = px.line(df, x='date', y='traffic',
                        title='Объем трафика за последние 30 дней')
            fig.update_layout(
                xaxis_title='Дата',
                yaxis_title='Трафик',
                template='plotly_white',
                xaxis=dict(
                    tickmode='array',
                    ticktext=df['date'].tolist(),
                    tickvals=list(range(len(df))),
                    tickangle=45
                ),
                yaxis=dict(tickformat='.2s'),
                margin=dict(b=80)
            )
            chart_html = fig.to_html(full_html=False)
            cache.set('traffic_chart_month', chart_html, 300)
    
    return True

@shared_task
def generate_domain_charts():
    """Задача для генерации графиков доменов"""
    # Получаем записи из кэша
    day_entries = cache.get('squid_log_entries_day')
    month_entries = cache.get('squid_log_entries_month')
    
    if not day_entries or not month_entries:
        # Если кэш пуст, запускаем обновление и выходим
        update_log_cache.delay()
        return False
    
    # Статистика по доменам для дня
    day_domain_stats = {}
    for entry in day_entries:
        try:
            if entry['request_method'] == 'CONNECT':
                domain = entry['url'].split(':')[0]
            else:
                domain = urlparse(entry['url']).netloc
            if not domain:
                domain = 'Неизвестно'
        except:
            domain = 'Неизвестно'
        
        if domain not in day_domain_stats:
            day_domain_stats[domain] = {'requests': 0, 'traffic': 0}
        day_domain_stats[domain]['requests'] += 1
        day_domain_stats[domain]['traffic'] += entry['bytes']
    
    # Создаем график доменов для дня
    if day_domain_stats:
        df = pd.DataFrame([
            {'domain': domain, 'requests': stats['requests'], 'traffic': stats['traffic']}
            for domain, stats in day_domain_stats.items()
        ]).sort_values('requests', ascending=True).tail(10)
        
        if not df.empty:
            fig = px.bar(
                df,
                x='requests',
                y='domain',
                title='Топ 10 посещаемых доменов (за сутки)',
                orientation='h',
                hover_data=['traffic']
            )
            fig.update_layout(
                xaxis_title='Количество запросов',
                yaxis_title='Домен',
                template='plotly_white',
                yaxis={'categoryorder': 'total ascending'},
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Rockwell"
                ),
                margin=dict(l=200)
            )
            fig.update_traces(
                hovertemplate="<br>".join([
                    "Домен: %{y}",
                    "Запросов: %{x}",
                    "Трафик: %{customdata[0]:.2s}B"
                ])
            )
            chart_html = fig.to_html(full_html=False)
            cache.set('domains_chart_day', chart_html, 300)
    
    # Статистика по доменам для месяца
    month_domain_stats = {}
    for entry in month_entries:
        try:
            if entry['request_method'] == 'CONNECT':
                domain = entry['url'].split(':')[0]
            else:
                domain = urlparse(entry['url']).netloc
            if not domain:
                domain = 'Неизвестно'
        except:
            domain = 'Неизвестно'
        
        if domain not in month_domain_stats:
            month_domain_stats[domain] = {'requests': 0, 'traffic': 0}
        month_domain_stats[domain]['requests'] += 1
        month_domain_stats[domain]['traffic'] += entry['bytes']
    
    # Создаем график доменов для месяца
    if month_domain_stats:
        df = pd.DataFrame([
            {'domain': domain, 'requests': stats['requests'], 'traffic': stats['traffic']}
            for domain, stats in month_domain_stats.items()
        ]).sort_values('requests', ascending=True).tail(10)
        
        if not df.empty:
            fig = px.bar(
                df,
                x='requests',
                y='domain',
                title='Топ 10 посещаемых доменов (за месяц)',
                orientation='h',
                hover_data=['traffic']
            )
            fig.update_layout(
                xaxis_title='Количество запросов',
                yaxis_title='Домен',
                template='plotly_white',
                yaxis={'categoryorder': 'total ascending'},
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=12,
                    font_family="Rockwell"
                ),
                margin=dict(l=200)
            )
            fig.update_traces(
                hovertemplate="<br>".join([
                    "Домен: %{y}",
                    "Запросов: %{x}",
                    "Трафик: %{customdata[0]:.2s}B"
                ])
            )
            chart_html = fig.to_html(full_html=False)
            cache.set('domains_chart_month', chart_html, 300)
    
    return True

@shared_task
def update_users_cache():
    """Задача для обновления кэша пользователей"""
    reader = SquidLogReader()
    entries = cache.get('squid_log_entries_all')
    
    if not entries:
        entries = reader.get_last_lines(n=0)
        cache.set('squid_log_entries_all', entries, 300)
    
    # Определяем временные границы
    now = timezone.now().astimezone(ZoneInfo('Europe/Moscow'))
    day_limit = now - timedelta(hours=24)
    month_limit = now - timedelta(days=30)
    
    # Словарь для хранения статистики пользователей
    users_stats = {}
    
    # Обрабатываем все записи
    for entry in entries:
        ip = entry['client_address']
        if not ip:
            continue
            
        if ip not in users_stats:
            users_stats[ip] = {
                'day_traffic': 0,
                'month_traffic': 0,
                'day_requests': 0,
                'month_requests': 0,
                'last_activity': None
            }
        
        # Обновляем время последней активности
        if not users_stats[ip]['last_activity'] or entry['timestamp'] > users_stats[ip]['last_activity']:
            users_stats[ip]['last_activity'] = entry['timestamp']
        
        # Считаем статистику за сутки
        if entry['timestamp'] >= day_limit:
            users_stats[ip]['day_traffic'] += entry['bytes']
            users_stats[ip]['day_requests'] += 1
        
        # Считаем статистику за месяц
        if entry['timestamp'] >= month_limit:
            users_stats[ip]['month_traffic'] += entry['bytes']
            users_stats[ip]['month_requests'] += 1
    
    # Кэшируем результат
    cache.set('users_stats', users_stats, 300)
    
    return len(users_stats)
