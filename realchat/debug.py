import os
import sys
import traceback

print("1. Current directory:", os.getcwd())
print("2. Files in current dir:", os.listdir('.'))

try:
    print("3. Attempting to import config.settings...")
    import config.settings
    print("4. ✅ SUCCESS! Settings imported without errors.")
except Exception as e:
    print("5. ❌ FAILED! Here is the error:")
    traceback.print_exc()