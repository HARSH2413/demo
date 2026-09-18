'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { headers } from 'next/headers'
import { createClient } from '@/lib/supabase/server'

export async function login(formData: FormData) {
  const supabase = await createClient()

  const data = {
    email: formData.get('email') as string,
    password: formData.get('password') as string,
  }

  const { error } = await supabase.auth.signInWithPassword(data)

  if (error) {
    redirect('/login?message=Could not authenticate user')
  }

  revalidatePath('/', 'layout')
  
  // After login, go straight to boxes
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
      redirect('/boxes')
  } else {
      redirect('/login?message=Authentication failed')
  }
}

export async function signup(formData: FormData) {
  const supabase = await createClient()

  const email = formData.get('email') as string
  const password = formData.get('password') as string
  const confirmPassword = formData.get('confirmPassword') as string
  const fullName = formData.get('fullName') as string

  // Validate passwords match
  if (password !== confirmPassword) {
    redirect('/signup?message=Passwords do not match')
  }

  // Validate password strength
  if (password.length < 6) {
    redirect('/signup?message=Password must be at least 6 characters')
  }

  const { error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      data: {
        full_name: fullName,
      },
    },
  })

  if (error) {
    redirect(`/signup?message=${encodeURIComponent(error.message)}`)
  }

  // After signup, go straight to boxes
  redirect('/boxes')
}

export async function signInWithGoogle() {
  const supabase = await createClient()
  const headersList = await headers()
  const origin = headersList.get('origin') || headersList.get('x-forwarded-host') || 'http://localhost:3000'

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${origin}/auth/callback`,
    },
  })

  if (error) {
    redirect('/login?message=Could not connect to Google')
  }

  if (data.url) {
    redirect(data.url)
  }
}

export async function createWorkspace(formData: FormData) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
      redirect('/login')
  }

  const workspaceName = formData.get('workspaceName') as string

  // Insert box (RLS allows user_id = auth.uid())
  const { data: box, error: boxError } = await supabase
      .from('boxes')
      .insert({ name: workspaceName, user_id: user.id })
      .select('id')
      .single()

  if (boxError || !box) {
      redirect(`/onboarding?message=Could not create box: ${boxError?.message}`)
  }

  redirect(`/boxes/${box.id}`)
}

export async function logout() {
    const supabase = await createClient()
    await supabase.auth.signOut()
    redirect('/login')
}
