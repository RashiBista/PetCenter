import os
import sys
import traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    import django
    django.setup()
    from django.core.management import call_command
    print("Generating migrations for chat...")
    call_command('makemigrations', 'chat', verbosity=3)
    print("Done.")
except Exception as e:
    traceback.print_exc()