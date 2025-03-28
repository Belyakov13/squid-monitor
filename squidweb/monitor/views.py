from django.views.generic import TemplateView
from django.core.paginator import Paginator
from .utils import SquidLogReader
import pandas as pd
import plotly.express as px
from urllib.parse import urlparse
import socket
from django.utils import timezone
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from functools import lru_cache
from .tasks import update_log_cache, generate_traffic_charts, generate_domain_charts, update_users_cache

class DashboardView(TemplateView):
    template_name = 'monitor/dashboard.html'
    
    def _format_size(self, size_bytes):
        """Форматирует размер в байтах в человекочитаемый формат"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} ПБ"

    @method_decorator(cache_page(60))  # Кэшируем на 1 минуту
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _get_cached_entries(self, period='day'):
        """Получает записи из кэша или читает их из файла"""
        cache_key = f'squid_log_entries_{period}'
        entries = cache.get(cache_key)
        
        if entries is None:
            # Запускаем задачу обновления кэша
            update_log_cache.delay()
            
            # Пока кэш не готов, получаем данные напрямую
            reader = SquidLogReader()
            entries = reader.get_last_lines(n=10000)  # Ограничиваем количество записей для быстрого ответа
            
            # Фильтруем по периоду
            now = timezone.now().astimezone(ZoneInfo('Europe/Moscow'))
            if period == 'day':
                period_limit = now - timedelta(hours=24)
            elif period == 'month':
                period_limit = now - timedelta(days=30)
            else:
                period_limit = now - timedelta(days=365)
                
            entries = [entry for entry in entries if entry['timestamp'] >= period_limit]
        
        return entries

    def _get_cached_chart(self, df, chart_type, period):
        """Получает график из кэша или создает новый"""
        cache_key = f'chart_{chart_type}_{period}_{df.shape[0]}'
        chart_html = cache.get(cache_key)
        
        if chart_html is None:
            if chart_type == 'traffic':
                if period == 'day':
                    fig = px.line(df, x='time', y='traffic',
                                title='Объем трафика за последние 24 часа')
                    fig.update_layout(
                        xaxis_title='Время',
                        yaxis_title='Трафик',
                        template='plotly_white',
                        yaxis=dict(tickformat='.2s')
                    )
                else:
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
            elif chart_type == 'domains':
                fig = px.bar(
                    df,
                    x='requests',
                    y='domain',
                    title='Топ 10 посещаемых доменов',
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
            # Кэшируем на 1 минуту
            cache.set(cache_key, chart_html, 60)
        
        return chart_html

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Получаем период из параметров запроса (день или месяц)
        period = self.request.GET.get('period', 'day')
        hours = 24 if period == 'day' else 720  # 720 часов = 30 дней
        
        # Получаем временную границу
        time_limit = timezone.now().astimezone(ZoneInfo('Europe/Moscow')) - timedelta(hours=hours)
        
        # Получаем записи из кэша или файла
        entries = self._get_cached_entries(period)
        
        # Фильтруем записи по времени
        filtered_entries = [entry for entry in entries if entry['timestamp'] >= time_limit]
        
        # Статистика по времени
        hourly_stats = {}
        daily_stats = {}
        domain_stats = {}  # Статистика по доменам
        total_traffic = 0
        total_requests = 0
        active_users = set()
        
        # Используем LRU-кэш для разрешения доменных имен
        @lru_cache(maxsize=1000)
        def get_domain(url, method):
            try:
                if method == 'CONNECT':
                    return url.split(':')[0]
                return urlparse(url).netloc
            except:
                return 'Неизвестно'
        
        for entry in filtered_entries:
            # Обработка временной статистики
            if period == 'day':
                hour = entry['timestamp'].replace(minute=0, second=0, microsecond=0)
                if hour not in hourly_stats:
                    hourly_stats[hour] = {'traffic': 0, 'requests': 0}
                hourly_stats[hour]['traffic'] += entry['bytes']
                hourly_stats[hour]['requests'] += 1
            else:
                day = entry['timestamp'].date()
                if day not in daily_stats:
                    daily_stats[day] = {'traffic': 0, 'requests': 0}
                daily_stats[day]['traffic'] += entry['bytes']
                daily_stats[day]['requests'] += 1
            
            # Статистика по доменам
            domain = get_domain(entry['url'], entry['request_method'])
            if domain not in domain_stats:
                domain_stats[domain] = {'requests': 0, 'traffic': 0}
            domain_stats[domain]['requests'] += 1
            domain_stats[domain]['traffic'] += entry['bytes']
            
            total_traffic += entry['bytes']
            total_requests += 1
            active_users.add(entry['client_address'])
        
        # График трафика
        if period == 'day' and hourly_stats:
            df = pd.DataFrame([
                {'time': hour.strftime('%H:%M'), 'traffic': stats['traffic']}
                for hour, stats in sorted(hourly_stats.items())
            ])
            if not df.empty:
                context['traffic_chart'] = self._get_cached_chart(df, 'traffic', 'day')
        
        elif period == 'month' and daily_stats:
            df = pd.DataFrame([
                {'date': day.strftime('%d.%m'), 'traffic': stats['traffic']}
                for day, stats in sorted(daily_stats.items())
            ])
            if not df.empty:
                context['traffic_chart'] = self._get_cached_chart(df, 'traffic', 'month')

        # График топ доменов
        if domain_stats:
            df_domains = pd.DataFrame([
                {'domain': domain, 'requests': stats['requests'], 'traffic': stats['traffic']}
                for domain, stats in domain_stats.items()
            ]).sort_values('requests', ascending=True).tail(10)
            
            if not df_domains.empty:
                context['domains_chart'] = self._get_cached_chart(df_domains, 'domains', period)
        
        context.update({
            'total_traffic': self._format_size(total_traffic),
            'total_requests': total_requests,
            'active_users': len(active_users),
            'period': period
        })
        
        return context

@method_decorator(cache_page(60), name='dispatch')  # Кэшируем на 1 минуту
class UsersListView(TemplateView):
    template_name = 'monitor/users_list.html'
    
    def _format_size(self, size_bytes):
        """Форматирует размер в байтах в человекочитаемый формат"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} ПБ"

    # Кэшируем разрешение имен хостов
    @lru_cache(maxsize=1000)
    def _get_hostname(self, ip):
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return 'Неизвестно'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Пытаемся получить данные из кэша
        cache_key = 'users_list_data'
        users_data = cache.get(cache_key)
        
        if users_data is None:
            # Запускаем задачу обновления кэша
            update_users_cache.delay()
            
            # Пока кэш не готов, получаем данные напрямую
            reader = SquidLogReader()
            
            # Получаем все записи
            entries = reader.get_last_lines(n=10000)  # Ограничиваем количество записей для быстрого ответа
            
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
            
            # Формируем список пользователей
            users_data = []
            for ip, stats in users_stats.items():
                # Добавляем пользователя только если у него была активность за последние 30 дней
                if stats['month_requests'] > 0:
                    users_data.append({
                        'ip': ip,
                        'hostname': self._get_hostname(ip),
                        'day_traffic': self._format_size(stats['day_traffic']),
                        'month_traffic': self._format_size(stats['month_traffic']),
                        'day_requests': stats['day_requests'],
                        'month_requests': stats['month_requests'],
                        'last_activity': stats['last_activity']
                    })
            
            # Сортируем по количеству запросов за месяц (по убыванию)
            users_data.sort(key=lambda x: x['month_requests'], reverse=True)
            
            # Кэшируем результат на 1 минуту
            cache.set(cache_key, users_data, 60)
        
        context['users'] = users_data
        return context

class ConnectionsView(TemplateView):
    template_name = 'monitor/connections.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reader = SquidLogReader()
        
        # Получаем последние соединения
        connections = []
        entries = reader.get_last_lines(n=100)
        
        for entry in entries:
            try:
                hostname = socket.gethostbyaddr(entry['client_address'])[0]
            except:
                hostname = 'Неизвестно'

            url = entry['url']
            try:
                domain = urlparse(url).netloc
            except:
                domain = 'Неизвестно'

            connections.append({
                'timestamp': entry['timestamp'],
                'ip': entry['client_address'],
                'hostname': hostname,
                'domain': domain,
                'url': url,
                'method': entry['request_method'],
                'status': entry['result_code'],
                'size': entry['bytes']
            })
        
        context['connections'] = connections
        return context

class UserDetailView(TemplateView):
    template_name = 'monitor/user_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reader = SquidLogReader()
        user_ip = kwargs.get('ip')
        
        # Получаем период из параметров запроса (день или месяц)
        period = self.request.GET.get('period', 'day')
        hours = 24 if period == 'day' else 720  # 720 часов = 30 дней
        
        # Получаем временную границу
        time_limit = timezone.now().astimezone(ZoneInfo('Europe/Moscow')) - timedelta(hours=hours)
        
        # Получаем все подключения пользователя
        user_connections = []
        entries = reader.get_last_lines(n=50000)  # Увеличиваем для большей истории
        
        total_traffic = 0
        total_requests = 0
        domain_stats = {}
        hourly_stats = {}
        daily_stats = {}
        
        for entry in entries:
            if entry['client_address'] == user_ip:
                # Добавляем все подключения в историю
                try:
                    domain = urlparse(entry['url']).netloc
                except:
                    domain = 'Неизвестно'
                    
                user_connections.append({
                    'timestamp': entry['timestamp'],
                    'url': entry['url'],
                    'domain': domain,
                    'method': entry['request_method'],
                    'status': entry['result_code'],
                    'size': entry['bytes']
                })
                
                # Собираем статистику только за выбранный период
                if entry['timestamp'] >= time_limit:
                    # Статистика по доменам
                    if domain not in domain_stats:
                        domain_stats[domain] = {'requests': 0, 'traffic': 0}
                    domain_stats[domain]['requests'] += 1
                    domain_stats[domain]['traffic'] += entry['bytes']
                    
                    # Почасовая статистика
                    hour = entry['timestamp'].replace(minute=0, second=0, microsecond=0)
                    if hour not in hourly_stats:
                        hourly_stats[hour] = {'requests': 0, 'traffic': 0}
                    hourly_stats[hour]['requests'] += 1
                    hourly_stats[hour]['traffic'] += entry['bytes']
                    
                    # Ежедневная статистика
                    day = entry['timestamp'].date()
                    if day not in daily_stats:
                        daily_stats[day] = {'requests': 0, 'traffic': 0}
                    daily_stats[day]['requests'] += 1
                    daily_stats[day]['traffic'] += entry['bytes']
                    
                    total_traffic += entry['bytes']
                    total_requests += 1
        
        # Сортируем подключения по времени (новые сверху)
        user_connections.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Пагинация
        paginator = Paginator(user_connections, 25)  # 25 записей на страницу
        page = self.request.GET.get('page', 1)
        connections = paginator.get_page(page)
        
        # График активности
        if period == 'day' and hourly_stats:
            df_traffic = pd.DataFrame([
                {'time': hour.strftime('%H:%M'), 'traffic': data['traffic']}
                for hour, data in sorted(hourly_stats.items())
            ])
            if not df_traffic.empty:
                fig_traffic = px.line(
                    df_traffic,
                    x='time',
                    y='traffic',
                    title='Объем трафика за последние 24 часа'
                )
                fig_traffic.update_layout(
                    xaxis_title='Время',
                    yaxis_title='Трафик',
                    template='plotly_white',
                    yaxis=dict(tickformat='.2s'),
                    margin=dict(b=50)
                )
                context['traffic_chart'] = fig_traffic.to_html(full_html=False)
        
        elif period == 'month' and daily_stats:
            df_traffic = pd.DataFrame([
                {'date': day.strftime('%d.%m'), 'traffic': data['traffic']}
                for day, data in sorted(daily_stats.items())
            ])
            if not df_traffic.empty:
                fig_traffic = px.line(
                    df_traffic,
                    x='date',
                    y='traffic',
                    title='Объем трафика за последние 30 дней'
                )
                fig_traffic.update_layout(
                    xaxis_title='Дата',
                    yaxis_title='Трафик',
                    template='plotly_white',
                    xaxis=dict(
                        tickmode='array',
                        ticktext=df_traffic['date'].tolist(),
                        tickvals=list(range(len(df_traffic))),
                        tickangle=45
                    ),
                    yaxis=dict(tickformat='.2s'),
                    margin=dict(b=80)
                )
                context['traffic_chart'] = fig_traffic.to_html(full_html=False)
        
        # График доменов
        if domain_stats:
            df_domains = pd.DataFrame([
                {'domain': domain, 'requests': stats['requests'], 'traffic': stats['traffic']}
                for domain, stats in domain_stats.items()
            ]).sort_values('requests', ascending=True).tail(10)
            
            if not df_domains.empty:
                fig_domains = px.bar(
                    df_domains,
                    x='requests',
                    y='domain',
                    title='Топ 10 посещаемых доменов',
                    orientation='h',
                    hover_data=['traffic']
                )
                fig_domains.update_layout(
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
                fig_domains.update_traces(
                    hovertemplate="<br>".join([
                        "Домен: %{y}",
                        "Запросов: %{x}",
                        "Трафик: %{customdata[0]:.2s}B"
                    ])
                )
                context['domains_chart'] = fig_domains.to_html(full_html=False)
        
        try:
            hostname = socket.gethostbyaddr(user_ip)[0]
        except:
            hostname = 'Неизвестно'
        
        context.update({
            'user_ip': user_ip,
            'hostname': hostname,
            'connections': connections,
            'total_traffic': total_traffic,
            'total_requests': total_requests,
            'domain_stats': sorted(domain_stats.items(), key=lambda x: x[1]['requests'], reverse=True)[:10],
            'period': period
        })
        
        return context
