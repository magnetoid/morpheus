import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'morph.settings')
django.setup()

from django.test import RequestFactory
from plugins.installed.ai_assistant.views.manifest import generate_openai_tools
req = RequestFactory().get('/')
print(generate_openai_tools(req).content.decode('utf-8'))
