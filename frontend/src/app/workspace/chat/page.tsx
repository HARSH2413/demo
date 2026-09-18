import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import SecureBrainDashboard from './ChatDashboard'

export default async function WorkspaceChatPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
      redirect('/login')
  }

  // Get user's workspaces
  const { data: members, error } = await supabase
      .from('workspace_members')
      .select('workspace_id, workspaces(name)')
      .eq('user_id', user.id)

  if (error || !members || members.length === 0) {
      // User has no workspace, send to onboarding
      redirect('/onboarding')
  }

  // Format workspaces for the dashboard
  const workspaces = members.map(m => ({
    id: m.workspace_id,
    name: m.workspaces.name || 'Unknown Workspace'
  }))

  return (
    <SecureBrainDashboard workspaces={workspaces} />
  )
}
