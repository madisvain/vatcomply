"""
ASGI config for VATcomply project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from vatcomply.middleware import BackgroundTasksMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vatcomply.settings")

application = BackgroundTasksMiddleware(get_asgi_application())
