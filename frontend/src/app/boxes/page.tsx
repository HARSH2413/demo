import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import BoxesClient from './BoxesClient'

export default async function BoxesPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
      redirect('/login')
  }

  const meta = (user.user_metadata || {}) as Record<string, string | undefined>
  const fullName = meta.full_name || meta.name || user.email?.split('@')[0] || ''
  const userName = fullName.split(' ')[0]

  return (
    <BoxesClient userName={userName} />
  )
}
