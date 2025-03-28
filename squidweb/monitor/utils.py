import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import os
from zoneinfo import ZoneInfo

class SquidLogReader:
    def __init__(self, log_path='/var/log/squid/access.log'):
        self.log_path = log_path
        self.log_pattern = re.compile(
            r'(\d+\.\d+)\s+(\d+)\s+(\S+)\s+(\S+)/(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+-\s+(\S+)/(\S+)\s+(.+)'  # Исправленное регулярное выражение
        )
        self.moscow_tz = ZoneInfo('Europe/Moscow')

    def _parse_line(self, line):
        """Парсит строку лога и возвращает словарь с данными"""
        try:
            match = self.log_pattern.match(line.strip())
            if match:
                timestamp, response_time, client_address, cache_result, status_code, bytes_sent, request_method, url, hierarchy, server, mime_type = match.groups()
                
                # Преобразуем timestamp в московское время
                dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).astimezone(self.moscow_tz)
                
                if request_method == 'CONNECT':
                    clean_url = f'https://{url}'
                else:
                    clean_url = url

                return {
                    'timestamp': dt,
                    'response_time': float(response_time),
                    'client_address': client_address,
                    'result_code': int(status_code),
                    'bytes': int(bytes_sent),
                    'request_method': request_method,
                    'url': clean_url,
                    'cache_result': cache_result,
                    'server': server,
                    'mime_type': mime_type
                }
        except Exception as e:
            print(f"Error parsing line: {line[:100]}... Error: {e}")
        return None

    def get_last_lines(self, n=10000):
        """Читает последние n строк из файла"""
        entries = []
        
        try:
            with open(self.log_path, 'rb') as f:
                # Перемещаемся в конец файла
                f.seek(0, 2)
                file_size = f.tell()
                
                # Читаем файл блоками с конца
                chunk_size = 8192  # 8KB блоки
                file_position = file_size
                lines = []
                
                # Продолжаем читать блоки, пока не получим достаточно строк или не дойдем до начала файла
                while file_position > 0 and (n == 0 or len(lines) < n):
                    # Определяем размер следующего блока
                    read_size = min(chunk_size, file_position)
                    file_position -= read_size
                    
                    # Читаем блок
                    f.seek(file_position)
                    chunk = f.read(read_size)
                    
                    # Добавляем строки из текущего блока
                    chunk_lines = chunk.decode('utf-8', errors='ignore').splitlines()
                    
                    # Если это не первый блок и у нас есть строки,
                    # первая строка может быть неполной - соединяем ее с последней строкой предыдущего блока
                    if file_position > 0 and chunk_lines and lines:
                        # Читаем следующий символ для проверки разделителя строк
                        f.seek(file_position - 1)
                        if f.read(1) != b'\n':
                            lines[0] = chunk_lines[-1] + lines[0]
                            chunk_lines = chunk_lines[:-1]
                    
                    lines = chunk_lines + lines
                
                # Обрезаем до нужного количества строк, если указан лимит
                if n > 0:
                    lines = lines[-n:]
                
                # Парсим строки
                for line in lines:
                    if line.strip():  # Пропускаем пустые строки
                        entry = self._parse_line(line)
                        if entry:
                            entries.append(entry)
                
                print(f"Successfully parsed {len(entries)} entries from {self.log_path}")
                
        except Exception as e:
            print(f"Error reading log file: {e}")
        
        # Сортируем по времени (старые записи первые)
        entries.sort(key=lambda x: x['timestamp'])
        return entries

    def get_user_connections(self, ip_address, limit=500):
        """Получает соединения конкретного пользователя"""
        entries = self.get_last_lines(n=0)  # Читаем весь файл
        connections = []
        
        for entry in entries:
            if entry['client_address'] == ip_address:
                connections.append(entry)
                if len(connections) >= limit:
                    break
        
        return connections

    def get_active_users(self, hours=24):
        """Получает список активных пользователей за последние N часов"""
        users = {}
        min_timestamp = datetime.now(self.moscow_tz) - timedelta(hours=hours)
        
        entries = self.get_last_lines(n=0)  # Читаем весь файл
        
        for entry in entries:
            if entry['timestamp'] >= min_timestamp:
                ip = entry['client_address']
                if ip not in users:
                    users[ip] = {'requests': 0, 'bytes': 0, 'last_activity': None}
                
                users[ip]['requests'] += 1
                users[ip]['bytes'] += entry['bytes']
                
                if not users[ip]['last_activity'] or entry['timestamp'] > users[ip]['last_activity']:
                    users[ip]['last_activity'] = entry['timestamp']
        
        return users

    def get_traffic_stats(self, hours=24):
        """Получает статистику трафика за указанное количество часов"""
        stats = {
            'total_requests': 0,
            'total_bytes': 0,
            'hourly_stats': {},
            'daily_stats': {},
            'monthly_stats': {},
            'status_codes': {},
            'users': {},
            'domains': {}
        }
        
        min_timestamp = datetime.now(self.moscow_tz) - timedelta(hours=hours)
        month_limit = datetime.now(self.moscow_tz) - timedelta(days=30)
        
        entries = self.get_last_lines(n=0)  # Читаем весь файл
        
        for entry in entries:
            if entry['timestamp'] >= min_timestamp:
                stats['total_requests'] += 1
                stats['total_bytes'] += entry['bytes']
                
                hour = entry['timestamp'].replace(minute=0, second=0, microsecond=0)
                if hour not in stats['hourly_stats']:
                    stats['hourly_stats'][hour] = {'requests': 0, 'bytes': 0}
                stats['hourly_stats'][hour]['requests'] += 1
                stats['hourly_stats'][hour]['bytes'] += entry['bytes']
                
                status = entry['result_code']
                stats['status_codes'][status] = stats['status_codes'].get(status, 0) + 1
                
                ip = entry['client_address']
                if ip not in stats['users']:
                    stats['users'][ip] = {'requests': 0, 'bytes': 0}
                stats['users'][ip]['requests'] += 1
                stats['users'][ip]['bytes'] += entry['bytes']
                
                try:
                    if entry['request_method'] == 'CONNECT':
                        domain = entry['url'].split(':')[0]
                    else:
                        domain = urlparse(entry['url']).netloc
                    if domain:
                        stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
                except:
                    pass
            
            if entry['timestamp'] >= month_limit:
                day = entry['timestamp'].date()
                if day not in stats['daily_stats']:
                    stats['daily_stats'][day] = {'requests': 0, 'bytes': 0}
                stats['daily_stats'][day]['requests'] += 1
                stats['daily_stats'][day]['bytes'] += entry['bytes']
                
                month = entry['timestamp'].replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if month not in stats['monthly_stats']:
                    stats['monthly_stats'][month] = {'requests': 0, 'bytes': 0}
                stats['monthly_stats'][month]['requests'] += 1
                stats['monthly_stats'][month]['bytes'] += entry['bytes']
        
        # Сортируем статистику по времени
        stats['hourly_stats'] = dict(sorted(stats['hourly_stats'].items()))
        stats['daily_stats'] = dict(sorted(stats['daily_stats'].items()))
        stats['monthly_stats'] = dict(sorted(stats['monthly_stats'].items()))
        
        return stats
