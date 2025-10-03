#!/usr/bin/env python3
"""
Setup script to assign admin role to the first user
Run this after creating the first user in Supabase Auth
"""

import os
import sys
from supabase import create_client, Client

def setup_admin_user():
    """Set up the first user as admin"""
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY environment variables are required")
        sys.exit(1)
    
    # Initialize Supabase client
    supabase: Client = create_client(supabase_url, supabase_key)
    
    print("Setting up admin user...")
    print("Please provide the user ID of the user you want to make admin.")
    print("You can find this in the Supabase Auth dashboard under Users.")
    
    user_id = input("Enter the user ID (UUID): ").strip()
    
    if not user_id:
        print("Error: User ID is required")
        sys.exit(1)
    
    try:
        # Assign admin role to the user
        result = supabase.rpc('assign_user_role', {
            'target_user_id': user_id,
            'new_role': 'admin'
        }).execute()
        
        print(f"✅ Successfully assigned admin role to user {user_id}")
        print("The user can now access all dashboard features and manage other users.")
        
    except Exception as e:
        print(f"❌ Error assigning admin role: {e}")
        print("\nMake sure:")
        print("1. The user ID is correct")
        print("2. The migration has been run in Supabase")
        print("3. The user exists in the auth.users table")
        sys.exit(1)

if __name__ == "__main__":
    setup_admin_user()
