import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import SecureBrainDashboard from './ChatDashboard'

export default async function WorkspaceChatPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
      redirect('/login')
  }

  // Get user's first workspace
  const { data: members, error } = await supabase
      .from('workspace_members')
      .select('workspace_id')
      .eq('user_id', user.id)
      .limit(1)

  if (error || !members || members.length === 0) {
      // User has no workspace, send to onboarding
      redirect('/onboarding')
  }

  const tenantId = members[0].workspace_id

  return (
    <SecureBrainDashboard tenantId={tenantId} />
  )
}
