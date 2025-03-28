Squid Proxy Monitor
A web application for monitoring Squid proxy server logs with a beautiful and intuitive interface.

Features
Real-time log monitoring
Interactive charts and statistics
Traffic analysis
User activity monitoring
Response code distribution
Bandwidth usage tracking
High performance with Redis caching and Celery background tasks
Installation on Ubuntu
Quick Setup
Clone the repository:
git clone https://github.com/yourusername/squid-monitor.git
cd squid-monitor
Run the setup script:
chmod +x setup.sh
./setup.sh
Start the application:
./start_celery.sh
./start_server.sh
Access the application at http://your-server-ip:8000
Manual Installation
Install requirements:
pip3 install -r requirements.txt
Install and start Redis:
sudo apt update
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
Collect static files:
python3 manage.py collectstatic --noinput
Start Celery worker and beat:
celery -A squid_monitor worker -l info --detach
celery -A squid_monitor beat -l info --detach
Start the Gunicorn server:
gunicorn squid_monitor.wsgi:application --workers 4 --threads 2 --bind 0.0.0.0:8000
Installation as systemd services
Run the systemd installation script:
chmod +x install_systemd.sh
./install_systemd.sh
Check service status:
sudo systemctl status squid-monitor.service
sudo systemctl status squid-monitor-celery.service
sudo systemctl status squid-monitor-celerybeat.service
Configuration
Make sure to set the correct path to your Squid access log file in settings.py:

SQUID_LOG_DIR = '/var/log/squid'  # Директория с логами
SQUID_LOG_PATH = os.path.join(SQUID_LOG_DIR, 'access.log')  # Путь к текущему логу
Performance Optimization
The application uses several techniques to optimize performance:

Redis Caching: All heavy operations are cached in Redis
Celery Background Tasks: Log processing and chart generation run in background
Gunicorn Multi-worker: Multiple workers handle requests in parallel
Static Files Compression: Static files are compressed for faster delivery
Optimized Database Access: Minimized database hits through caching
Updating Cache Manually
If you need to manually update the cache:

./update_cache.sh
Troubleshooting
If the application is slow:

Make sure Redis server is running
Check that Celery workers are active
Verify that log file path is correct
Run the update_cache.sh script to pre-populate cache
Common Errors
Redis HiredisParser Error
If you encounter this error:

ImportError: Module "redis.connection" does not define a "HiredisParser" attribute/class
Run the fix script:

chmod +x fix_redis.sh
./fix_redis.sh
Or manually fix:

Install the correct Redis version: pip3 install redis==4.6.0
Remove the HiredisParser line from settings.py
Restart the application
Checking Application Status
To check the status of all components:

chmod +x check_status.sh
./check_status.sh
