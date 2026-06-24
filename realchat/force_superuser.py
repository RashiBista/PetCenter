import os
import sys
import traceback

# Tell Django where your settings are
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    print("1. Setting up Django...")
    import django
    django.setup()
    print("2. Creating superuser non-interactively...")

    from django.core.management import call_command

    # Set the password via environment variable
    os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'admin123'

    call_command(
        'createsuperuser',
        username='admin',
        email='admin@example.com',
        interactive=False,
        verbosity=3
    )
    print("3. ✅ Superuser 'admin' created successfully! Password: admin123")

except Exception as e:
    print("=" * 60)
    print(" CRASH DETECTED! Here is the full error:")
    print("=" * 60)
    traceback.print_exc()