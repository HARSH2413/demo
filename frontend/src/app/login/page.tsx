'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { login } from '../auth/actions'
import { Eye, EyeOff, Sparkles } from 'lucide-react'
import { SubmitButton } from '@/components/auth/SubmitButton'
export default function LoginPage({
    searchParams,
  }: {
    searchParams: Promise<{ error?: string, success?: string }>
  }) {
  const params = React.use(searchParams);
  const [showPassword, setShowPassword] = useState(false);
  
  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col items-center justify-center p-4 selection:bg-indigo-100 selection:text-indigo-900">
      <Link href="/" className="absolute top-8 left-8 text-slate-500 hover:text-slate-900 transition-colors font-medium text-sm">
        ← Back to home
      </Link>
      
      <div className="w-full max-w-md bg-white border border-slate-200 p-8 rounded-2xl shadow-xl shadow-slate-200/50">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-4">
            <Sparkles className="w-6 h-6 text-indigo-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 font-headline tracking-tight">Welcome back</h2>
          <p className="text-slate-500 text-sm mt-1.5">Log in to your workspace</p>
        </div>



        <form action={login} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              name="email"
              className="px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all text-sm shadow-sm"
              placeholder="you@example.com"
              type="email"
              autoComplete="email"
              required
            />
          </div>

          <div className="flex flex-col gap-2 relative">
            <div className="flex justify-between items-center">
              <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="password">
                Password
              </label>
            </div>
            
            <div className="relative">
              <input
                id="password"
                name="password"
                className="w-full px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all pr-12 text-sm shadow-sm"
                placeholder="••••••••"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
              />
              <button 
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {params?.error && (
            <div className="text-sm text-red-600 bg-red-50 p-3 rounded-lg text-center border border-red-200">
              {params.error}
            </div>
          )}

          {params?.success && (
            <div className="text-sm text-emerald-700 bg-emerald-50 p-3 rounded-lg text-center border border-emerald-200">
              {params.success}
            </div>
          )}

          <div className="mt-2">
            <SubmitButton text="Log In" loadingText="Logging in..." />
          </div>
        </form>

        <div className="mt-8 text-center text-sm text-slate-500">
          Don&apos;t have an account?{' '}
          <Link href="/signup" className="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
            Create account
          </Link>
        </div>
      </div>
    </div>
  )
}
