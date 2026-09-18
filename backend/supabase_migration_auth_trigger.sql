-- supabase_migration_auth_trigger.sql
-- Automatically creates a Personal Workspace for every new user.

-- 1. Create the trigger function
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
DECLARE
  workspace_id uuid;
BEGIN
  -- Insert default workspace
  INSERT INTO public.workspaces (name, owner_id)
  VALUES ('Personal Workspace', NEW.id)
  RETURNING id INTO workspace_id;
  
  -- Add user as owner to the workspace
  INSERT INTO public.workspace_members (workspace_id, user_id, role)
  VALUES (workspace_id, NEW.id, 'owner');
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Attach the trigger to auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
