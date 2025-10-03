# Dashboard Authentication Setup

This guide explains how to set up Supabase authentication for the Operations Dashboard.

## Prerequisites

1. Supabase project with Auth enabled
2. User created in Supabase Auth dashboard
3. Database migration applied (see `migrations/001_add_user_roles.sql`)

## Setup Steps

### 1. Environment Variables

Ensure these environment variables are set:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
DASHBOARD_SECRET_KEY=your-secret-key-for-flask-sessions
```

### 2. Database Migration

Run the migration to create user roles table:

```sql
-- Apply the migration from migrations/001_add_user_roles.sql
-- This creates the user_roles table and RPC functions
```

### 3. Create First User

1. Go to your Supabase project dashboard
2. Navigate to Authentication > Users
3. Click "Add user" and create a user with email/password
4. Note the User ID (UUID) from the user details

### 4. Assign Admin Role

Run the setup script to make the first user an admin:

```bash
cd src/dashboard
python setup_admin.py
```

Enter the User ID when prompted.

### 5. Test Authentication

1. Start the dashboard:
   ```bash
   python app.py
   ```

2. Navigate to `http://localhost:5000`
3. You should be redirected to the login page
4. Login with the user credentials
5. You should see the dashboard with admin privileges

## User Roles

### Admin
- Full access to all features
- Can manage other users
- Can add/edit/delete roasters
- Can trigger scraping jobs

### Operator
- Can view all dashboard data
- Can trigger scraping jobs
- Cannot manage users or roasters

### User
- **Default role for new users** - Used for frontend directory users
- **BLOCKED from operations dashboard** - This dashboard is for operations staff only
- Users with "user" role will be redirected to login with access denied message

### Viewer
- Can view dashboard data only
- Cannot trigger actions
- Cannot manage users or roasters

## API Endpoints

### Public Endpoints
- `GET /login` - Login page
- `POST /login` - Login handler
- `GET /signup` - Signup page
- `POST /signup` - Signup handler
- `GET /logout` - Logout handler

### Protected Endpoints (Require Authentication)
- `GET /` - Dashboard
- `GET /api/dashboard/*` - All dashboard API endpoints

### Admin-Only Endpoints
- `GET /api/dashboard/users` - List all users
- `PUT /api/dashboard/users/<user_id>/role` - Update user role
- `POST /api/dashboard/roasters` - Add roaster
- `PUT /api/dashboard/roasters/<roaster_id>` - Update roaster
- `DELETE /api/dashboard/roasters/<roaster_id>` - Delete roaster

### Operator-Only Endpoints
- `POST /api/dashboard/trigger-scraping` - Trigger scraping jobs

## Security Features

1. **Row Level Security (RLS)** - Database policies ensure users can only access their own data
2. **Role-based Access Control** - Different permission levels for different user types
3. **Session Management** - Flask sessions with Supabase JWT tokens
4. **Audit Logging** - All role changes are logged in `role_audit_log` table

## Troubleshooting

### "Authentication required" error
- Make sure you're logged in
- Check if the session is valid
- Try logging out and logging back in

### "Insufficient permissions" error
- Check your user role in the database
- Contact an admin to update your role
- Ensure you have the required role for the action

### Database connection errors
- Verify SUPABASE_URL and SUPABASE_KEY are correct
- Check if the migration has been applied
- Ensure the RPC functions exist in your database

## Development

To add new protected endpoints:

```python
@app.route('/api/dashboard/new-endpoint')
@require_auth  # Requires any authenticated user
def new_endpoint():
    pass

@app.route('/api/dashboard/admin-endpoint')
@require_role('admin')  # Requires admin role
def admin_endpoint():
    pass
```

## Production Deployment

1. Set strong `DASHBOARD_SECRET_KEY`
2. Use HTTPS in production
3. Configure proper CORS settings
4. Set up proper logging for security events
5. Consider rate limiting for authentication endpoints
