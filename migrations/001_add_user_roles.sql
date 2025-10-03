-- Migration: Add user roles and authentication
-- Description: Creates user roles table and RLS policies for dashboard authentication
-- Create role enum
-- Note: 'user' role is for frontend directory users only, not operations dashboard
DO $$ BEGIN
    CREATE TYPE user_role_enum AS ENUM ('admin', 'operator', 'user', 'viewer');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create user_roles table
CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role user_role_enum NOT NULL DEFAULT 'user'::user_role_enum,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),
    UNIQUE(user_id)
);



-- Update user_roles table to use enum
ALTER TABLE user_roles ALTER COLUMN role TYPE user_role_enum USING role::user_role_enum;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles(role);

-- Enable RLS
ALTER TABLE user_roles ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own role" ON user_roles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all roles" ON user_roles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_roles ur 
            WHERE ur.user_id = auth.uid() 
            AND ur.role = 'admin'
        )
    );

CREATE POLICY "Admins can manage all roles" ON user_roles
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM user_roles ur 
            WHERE ur.user_id = auth.uid() 
            AND ur.role = 'admin'
        )
    );

-- Create function to get user role
CREATE OR REPLACE FUNCTION get_user_role(user_uuid UUID DEFAULT auth.uid())
RETURNS user_role_enum AS $$
BEGIN
    RETURN (
        SELECT role 
        FROM user_roles 
        WHERE user_id = user_uuid
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to check if user has permission
CREATE OR REPLACE FUNCTION has_permission(required_role user_role_enum)
RETURNS BOOLEAN AS $$
DECLARE
    user_role user_role_enum;
BEGIN
    user_role := get_user_role();
    
    -- Admin has all permissions
    IF user_role = 'admin' THEN
        RETURN TRUE;
    END IF;
    
    -- Check role hierarchy: admin > operator > user > viewer
    CASE required_role
        WHEN 'admin' THEN
            RETURN user_role = 'admin';
        WHEN 'operator' THEN
            RETURN user_role IN ('admin', 'operator');
        WHEN 'user' THEN
            RETURN user_role IN ('admin', 'operator', 'user');
        WHEN 'viewer' THEN
            RETURN user_role IN ('admin', 'operator', 'user', 'viewer');
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to assign role to user
CREATE OR REPLACE FUNCTION assign_user_role(
    target_user_id UUID,
    new_role user_role_enum,
    assigned_by UUID DEFAULT auth.uid()
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Check if the assigner has admin permissions
    IF NOT has_permission('admin') THEN
        RAISE EXCEPTION 'Insufficient permissions to assign roles';
    END IF;
    
    -- Insert or update user role
    INSERT INTO user_roles (user_id, role, created_by)
    VALUES (target_user_id, new_role, assigned_by)
    ON CONFLICT (user_id) 
    DO UPDATE SET 
        role = new_role,
        updated_at = NOW(),
        created_by = assigned_by;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create function to get all users with their roles
CREATE OR REPLACE FUNCTION get_users_with_roles()
RETURNS TABLE (
    user_id UUID,
    email TEXT,
    role user_role_enum,
    created_at TIMESTAMP WITH TIME ZONE,
    last_sign_in TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    -- Check if user has admin permissions
    IF NOT has_permission('admin') THEN
        RAISE EXCEPTION 'Insufficient permissions to view user roles';
    END IF;
    
    RETURN QUERY
    SELECT 
        u.id,
        u.email,
        COALESCE(ur.role, 'user'::user_role_enum) as role,
        u.created_at,
        u.last_sign_in_at
    FROM auth.users u
    LEFT JOIN user_roles ur ON u.id = ur.user_id
    ORDER BY u.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Insert default admin role for the first user (you'll need to update this with your actual user ID)
-- This is a placeholder - you'll need to replace 'your-user-id-here' with the actual UUID from Supabase Auth
-- INSERT INTO user_roles (user_id, role) VALUES ('your-user-id-here', 'admin');

-- Create audit log table for role changes
CREATE TABLE IF NOT EXISTS role_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    old_role user_role_enum,
    new_role user_role_enum NOT NULL,
    changed_by UUID NOT NULL REFERENCES auth.users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason TEXT
);

-- Enable RLS on audit log
ALTER TABLE role_audit_log ENABLE ROW LEVEL SECURITY;

-- Create policy for audit log
CREATE POLICY "Admins can view audit log" ON role_audit_log
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_roles ur 
            WHERE ur.user_id = auth.uid() 
            AND ur.role = 'admin'
        )
    );

-- Create trigger to log role changes
CREATE OR REPLACE FUNCTION log_role_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND OLD.role != NEW.role THEN
        INSERT INTO role_audit_log (user_id, old_role, new_role, changed_by)
        VALUES (NEW.user_id, OLD.role, NEW.role, auth.uid());
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO role_audit_log (user_id, old_role, new_role, changed_by)
        VALUES (NEW.user_id, NULL, NEW.role, auth.uid());
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER role_change_audit
    AFTER INSERT OR UPDATE ON user_roles
    FOR EACH ROW
    EXECUTE FUNCTION log_role_change();

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_roles TO authenticated;
GRANT SELECT ON role_audit_log TO authenticated;
GRANT EXECUTE ON FUNCTION get_user_role(UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION has_permission(user_role_enum) TO authenticated;
GRANT EXECUTE ON FUNCTION assign_user_role(UUID, user_role_enum, UUID) TO authenticated;
GRANT EXECUTE ON FUNCTION get_users_with_roles() TO authenticated;
