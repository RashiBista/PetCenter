import os
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    print("1. Setting up Django...")
    import django
    django.setup()
    print("2. Running migrate...")
    from django.core.management import call_command
    call_command('migrate', verbosity=3)
    print("3.  Done.")
except Exception as e:
    print("=" * 60)
    print("ERROR:")
    traceback.print_exc()