#!/usr/bin/env python
"""
Export all database data to a formatted text file.
Run with: python export_data.py
"""

import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangojwt.settings')
django.setup()

from myapp.models import User, UserProfile, VetProfile

def export_data():
    """Export all data to a formatted file."""
    
    output = []
    output.append("=" * 80)
    output.append("PET CENTRE DATABASE - DATA EXPORT")
    output.append(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("=" * 80)
    output.append("")
    
    # Users Data
    output.append("📋 USERS DATA")
    output.append("-" * 80)
    users = User.objects.all()
    
    if users.exists():
        for user in users:
            output.append(f"ID: {user.id}")
            output.append(f"  Username: {user.username}")
            output.append(f"  Email: {user.email}")
            output.append(f"  Phone: {user.phone_number}")
            output.append(f"  Role: {user.get_role_display()}")
            output.append(f"  Joined: {user.date_joined}")
            output.append(f"  Active: {user.is_active}")
            output.append("")
    else:
        output.append("No users found.")
        output.append("")
    
    # User Profiles Data
    output.append("\n👤 USER PROFILES (Pet Owners)")
    output.append("-" * 80)
    user_profiles = UserProfile.objects.select_related('user').all()
    
    if user_profiles.exists():
        for profile in user_profiles:
            output.append(f"ID: {profile.id}")
            output.append(f"  User: {profile.user.username}")
            output.append(f"  Address: {profile.address or 'Not set'}")
            output.append(f"  Created: {profile.created_at}")
            output.append(f"  Updated: {profile.updated_at}")
            output.append("")
    else:
        output.append("No user profiles found.")
        output.append("")
    
    # Vet Profiles Data
    output.append("\n🩺 VET PROFILES (Veterinarians)")
    output.append("-" * 80)
    vet_profiles = VetProfile.objects.select_related('user').all()
    
    if vet_profiles.exists():
        for profile in vet_profiles:
            output.append(f"ID: {profile.id}")
            output.append(f"  Vet: {profile.user.username}")
            output.append(f"  Email: {profile.user.email}")
            output.append(f"  Created: {profile.created_at}")
            output.append(f"  Updated: {profile.updated_at}")
            output.append("")
    else:
        output.append("No vet profiles found.")
        output.append("")
    
    # Summary Statistics
    output.append("\n📊 SUMMARY")
    output.append("-" * 80)
    output.append(f"Total Users: {users.count()}")
    output.append(f"Total Pet Owners: {user_profiles.count()}")
    output.append(f"Total Vets: {vet_profiles.count()}")
    output.append("")
    output.append("=" * 80)
    
    # Write to file
    content = "\n".join(output)
    
    with open('DATABASE_DATA.txt', 'w') as f:
        f.write(content)
    
    print("✅ Data exported to DATABASE_DATA.txt")
    print(content)

if __name__ == '__main__':
    export_data()
