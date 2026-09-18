import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import BoxesClient from './BoxesClient'

export default async function BoxesPage() {
  const supabase = await createClient()
  
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
      redirect('/login')
  }

  return (
    <BoxesClient />
  )
}
