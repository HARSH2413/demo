'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { login } from '../auth/actions'
import { Eye, EyeOff } from 'lucide-react'
import { SubmitButton } from '@/components/auth/SubmitButton'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'

export default function LoginPage({
    searchParams,
  }: {
    searchParams: Promise<{ error?: string, success?: string }>
  }) {
  const params = React.use(searchParams);
  const [showPassword, setShowPassword] = useState(false);
  
  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-4 selection:bg-indigo-500/30">
      <Link href="/" className="absolute top-8 left-8 text-neutral-400 hover:text-white transition-colors animate-fade-in">
        ← Back to home
      </Link>
      
      <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 p-8 rounded-2xl shadow-2xl animate-fade-in-up">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-indigo-500/20 mb-4">
            D
          </div>
          <h2 className="text-2xl font-bold text-white">Welcome back</h2>
          <p className="text-neutral-400 text-sm mt-2">Log in to your workspace</p>
        </div>

        {/* Google Sign-In */}
        <GoogleSignInButton />

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-neutral-800"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-neutral-900 text-neutral-500">or continue with email</span>
          </div>
        </div>

        <form action={login} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-neutral-300 font-medium" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              className="px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="you@example.com"
              type="email"
              autoComplete="email"
              required
            />
          </div>

          <div className="flex flex-col gap-2 relative">
            <div className="flex justify-between items-center">
              <label className="text-sm text-neutral-300 font-medium" htmlFor="password">
                Password
              </label>
              {/* If password recovery is supported in actions.ts, we can add a link here, but it's not currently implemented in auth actions. */}
            </div>
            
            <div className="relative">
              <input
                id="password"
                name="password"
                className="w-full px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all pr-12"
                placeholder="••••••••"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
              />
              <button 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-200"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {params?.error && (
            <div className="text-sm text-red-400 bg-red-400/10 p-3 rounded-lg text-center border border-red-500/20 animate-fade-in">
              {params.error}
            </div>
          )}

          {params?.success && (
            <div className="text-sm text-emerald-400 bg-emerald-400/10 p-3 rounded-lg text-center border border-emerald-500/20 animate-fade-in">
              {params.success}
            </div>
          )}

          <SubmitButton text="Log In" loadingText="Logging in..." />
        </form>

        <div className="mt-8 text-center text-sm text-neutral-400">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
            Create account
          </Link>
        </div>
      </div>
    </div>
  )
}
