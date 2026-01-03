# Production Deployment Script

# Install production dependencies
pip install -r requirements.txt

# Option 1: Run with Gunicorn (Event-driven, non-blocking I/O)
gunicorn -w 4 -k gevent --worker-connections 1000 --bind 0.0.0.0:5000 app:app

# Option 2: Run with uWSGI (Thread pool)
# uwsgi --http :5000 --wsgi-file app.py --callable app --threads 4 --processes 2

# Option 3: Development mode
# python app.py
