"""
Authentication module for the Operations Dashboard
Handles Supabase authentication with Flask session storage
"""

import os
from typing import Optional, Dict, Any
from flask import session, request, redirect, url_for, flash, jsonify
from gotrue import SyncSupportedStorage
from supabase import create_client, Client
from werkzeug.local import LocalProxy
from flask import g

class FlaskSessionStorage(SyncSupportedStorage):
    """Custom storage class that integrates Flask sessions with Supabase auth"""
    
    def __init__(self):
        self.storage = session

    def get_item(self, key: str) -> Optional[str]:
        if key in self.storage:
            return self.storage[key]
        return None

    def set_item(self, key: str, value: str) -> None:
        self.storage[key] = value

    def remove_item(self, key: str) -> None:
        if key in self.storage:
            self.storage.pop(key, None)

def get_supabase() -> Client:
    """Get Supabase client with Flask session storage"""
    if "supabase" not in g:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_KEY", "")
        
        g.supabase = create_client(
            url,
            key,
            options={
                "storage": FlaskSessionStorage(),
                "flow_type": "pkce"
            }
        )
    return g.supabase

# Create a proxy for easy access
supabase: Client = LocalProxy(get_supabase)

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user"""
    try:
        response = supabase.auth.get_user()
        if response and hasattr(response, 'user') and response.user:
            return {
                'id': response.user.id,
                'email': response.user.email,
                'role': get_user_role(response.user.id)
            }
    except Exception as e:
        print(f"Error getting current user: {e}")
    return None

def get_user_role(user_id: str) -> str:
    """Get user role from database"""
    try:
        response = supabase.table('user_roles').select('role').eq('user_id', user_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0]['role']
    except Exception as e:
        print(f"Error getting user role: {e}")
    return 'user'  # Default role for new users

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        
        # Deny access to 'user' role - this is an operations dashboard
        user_role = user.get('role', 'viewer')
        if user_role == 'user':
            if request.is_json:
                return jsonify({'error': 'Access denied. This is an operations dashboard for admin, operator, and viewer roles only.'}), 403
            flash('Access denied. This dashboard is for operations staff only.', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_role(required_role: str):
    """Decorator to require specific role"""
    def decorator(f):
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login'))
            
            user_role = user.get('role', 'user')
            role_hierarchy = {'admin': 3, 'operator': 2, 'viewer': 1}
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                if request.is_json:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                flash('Insufficient permissions', 'error')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

def login_user(email: str, password: str) -> Dict[str, Any]:
    """Login user with email and password"""
    try:
        response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        if response.user:
            return {
                'success': True,
                'user': {
                    'id': response.user.id,
                    'email': response.user.email,
                    'role': get_user_role(response.user.id)
                }
            }
        else:
            return {
                'success': False,
                'error': 'Invalid credentials'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def logout_user():
    """Logout current user"""
    try:
        supabase.auth.sign_out()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def signup_user(email: str, password: str) -> Dict[str, Any]:
    """Sign up new user"""
    try:
        response = supabase.auth.sign_up({
            'email': email,
            'password': password
        })
        
        if response.user:
            return {
                'success': True,
                'user': {
                    'id': response.user.id,
                    'email': response.user.email
                }
            }
        else:
            return {
                'success': False,
                'error': 'Signup failed'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_users_with_roles() -> Dict[str, Any]:
    """Get all users with their roles (admin only)"""
    try:
        response = supabase.rpc('get_users_with_roles').execute()
        return {
            'success': True,
            'users': response.data if response.data else []
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def assign_user_role(user_id: str, role: str) -> Dict[str, Any]:
    """Assign role to user (admin only)"""
    try:
        response = supabase.rpc('assign_user_role', {
            'target_user_id': user_id,
            'new_role': role
        }).execute()
        return {
            'success': True,
            'message': f'Role {role} assigned successfully'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
