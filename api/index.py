# api/index.py
import os
from asgiref.wsgi import WsgiToAsgi  # only if you still use WSGI
from asgiref.compatibility import guarantee_single_callable
from django.core.wsgi import get_wsgi_application

# REQUIRED: point to your production settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vhinternational.settings")

# Ensure DEBUG is off at runtime unless explicitly set
os.environ.setdefault("DEBUG", "0")

# If you have ASGI:
# from django.core.asgi import get_asgi_application
# app = get_asgi_application()

# If your project is WSGI-only, wrap it:
wsgi_app = get_wsgi_application()
app = guarantee_single_callable(WsgiToAsgi(wsgi_app))

# Vercel looks for "app" callable
