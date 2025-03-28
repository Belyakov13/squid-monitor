# Squid Proxy Monitor

A web application for monitoring Squid proxy server logs with a beautiful and intuitive interface.

## Features
- Real-time log monitoring
- Interactive charts and statistics
- Traffic analysis
- User activity monitoring
- Response code distribution
- Bandwidth usage tracking
- High performance with Redis caching and Celery background tasks

## Installation on Ubuntu

### Quick Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/squid-monitor.git
cd squid-monitor
```

2. Run the setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Start the application:
```bash
./start_celery.sh
./start_server.sh
```

4. Access the application at http://your-server-ip:8000

### Manual Installation

1. Install requirements:
```bash
pip3 install -r requirements.txt
```

2. Install and start Redis:
```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

3. Collect static files:
```bash
python3 manage.py collectstatic --noinput
```

4. Start Celery worker and beat:
```bash
celery -A squid_monitor worker -l info --detach
celery -A squid_monitor beat -l info --detach
```

5. Start the Gunicorn server:
```bash
gunicorn squid_monitor.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:8000
```

### Installation as systemd services

1. Run the systemd installation script:
```bash
chmod +x install_systemd.sh
./install_systemd.sh
```

2. Check service status:
```bash
sudo systemctl status squid-monitor.service
sudo systemctl status squid-monitor-celery.service
sudo systemctl status squid-monitor-celerybeat.service
```

## Configuration
Make sure to set the correct path to your Squid access log file in settings.py:

```python
SQUID_LOG_DIR = '/var/log/squid'  # Директория с логами
SQUID_LOG_PATH = os.path.join(SQUID_LOG_DIR, 'access.log')  # Путь к текущему логу
```

## Performance Optimization

The application uses several techniques to optimize performance:

1. **Redis Caching**: All heavy operations are cached in Redis
2. **Celery Background Tasks**: Log processing and chart generation run in background
3. **Gunicorn Multi-worker**: Multiple workers handle requests in parallel
4. **Static Files Compression**: Static files are compressed for faster delivery
5. **Optimized Database Access**: Minimized database hits through caching

## Updating Cache Manually

If you need to manually update the cache:

```bash
./update_cache.sh
```

## Troubleshooting

If the application is slow:
1. Make sure Redis server is running
2. Check that Celery workers are active
3. Verify that log file path is correct
4. Run the update_cache.sh script to pre-populate cache

### Common Errors

#### Redis HiredisParser Error

If you encounter this error:
```
ImportError: Module "redis.connection" does not define a "HiredisParser" attribute/class
```

Run the fix script:
```bash
chmod +x fix_redis.sh
./fix_redis.sh
```

Or manually fix:
1. Install the correct Redis version: `pip3 install redis==4.6.0`
2. Remove the HiredisParser line from settings.py
3. Restart the application

#### Checking Application Status

To check the status of all components:
```bash
chmod +x check_status.sh
./check_status.sh
