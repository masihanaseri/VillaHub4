"""
تنظیمات Celery برای پروژه VillaHub.

این فایل طبق الگوی استاندارد ادغام Celery با Django نوشته شده است:
https://docs.celeryq.org/en/stable/django/first-steps-with-django.html

اجرای Worker (از داخل پوشه backend/، هم‌سطح با manage.py):
    celery -A config worker --loglevel=info

اجرای Beat (در صورت نیاز به تسک‌های دوره‌ای):
    celery -A config beat --loglevel=info
"""

import os

from celery import Celery

# تنظیم پیش‌فرض ماژول Settings جنگو برای برنامه 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# استفاده از تنظیمات Django به‌عنوان منبع تنظیمات Celery.
# namespace='CELERY' یعنی تمام کلیدهای مرتبط با Celery در settings.py
# باید با پیشوند `CELERY_` نوشته شوند (که در این پروژه همین‌طور است).
app.config_from_object('django.conf:settings', namespace='CELERY')

# کشف خودکار ماژول‌های tasks.py در تمام اپ‌های ثبت‌شده در INSTALLED_APPS.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """تسک آزمایشی داخلی Celery برای بررسی سریع اتصال Worker."""
    print(f'Request: {self.request!r}')
