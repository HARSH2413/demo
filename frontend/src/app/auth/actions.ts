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

  // After signup, check if we have an active session
  // If email confirmation is enabled, session will be null until confirmed
  if (data.session) {
    redirect('/boxes')
  } else {
    redirect('/signup?message=Please check your email to confirm your account')
  }
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

export async function createBox(formData: FormData) {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session || !session.access_token) {
      redirect('/login')
  }

  const boxName = formData.get('boxName') as string

  // Use the backend API to create the box
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const res = await fetch(`${API_URL}/api/v1/boxes/`, {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify({ name: boxName.trim() })
  });

  if (!res.ok) {
      const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
      redirect(`/onboarding?message=${encodeURIComponent(errorData.detail || 'Could not create box')}`)
  }

  const json = await res.json();
  const box = json.data;

  redirect(`/boxes/${box.id}`)
}

export async function logout() {
    const supabase = await createClient()
    await supabase.auth.signOut()
    redirect('/login')
}
