# import os
# import sys
# import traceback

# # Tell Django where your settings are
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# try:
#     print("1. Importing Django...")
#     import django
#     print("2. Running django.setup()...")
#     django.setup()
#     print("3. Setup successful! Loading apps...")
    
#     from django.core.management import call_command
#     print("4. Running 'showmigrations'...")
#     call_command('showmigrations')
#     print("5. Done.")
    
# except Exception as e:
#     print("=" * 60)
#     print("❌ CRASH DETECTED! Here is the full error:")
#     print("=" * 60)
#     traceback.print_exc()


import os
import sys
import traceback

# Tell Django where your settings are
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    print("1. Importing Django...")
    import django
    print("2. Running django.setup()...")
    django.setup()
    print("3. Setup successful! Loading apps...")

    from django.core.management import call_command
    print("4. Running 'makemigrations' for users and chat...")
    call_command('makemigrations', 'users', 'chat', verbosity=3)
    print("5. Done.")

except Exception as e:
    print("=" * 60)
    print("❌ CRASH DETECTED! Here is the full error:")
    print("=" * 60)
    traceback.print_exc()