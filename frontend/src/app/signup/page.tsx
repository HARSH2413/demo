'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { signup } from '../auth/actions'
import { Eye, EyeOff, Sparkles } from 'lucide-react'
import { SubmitButton } from '@/components/auth/SubmitButton'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'

export default function SignupPage({
    searchParams,
  }: {
    searchParams: Promise<{ error?: string, success?: string }>
  }) {
  const params = React.use(searchParams);
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const hasBothPasswords = password.length > 0 && confirmPassword.length > 0;
  const passwordsMatch = password === confirmPassword;
  const showMismatchError = hasBothPasswords && !passwordsMatch;
  const showMatchSuccess = hasBothPasswords && passwordsMatch;
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    if (showMismatchError) {
      e.preventDefault();
    }
  };
  
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
          <h2 className="text-2xl font-bold text-slate-900 font-headline tracking-tight">Create your account</h2>
          <p className="text-slate-500 text-sm mt-1.5">Start your private AI knowledge base</p>
        </div>

        {/* Google Sign-Up */}
        <GoogleSignInButton />

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-white text-slate-500 font-medium">or sign up with email</span>
          </div>
        </div>

        <form action={signup} onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="fullName">
              Full Name
            </label>
            <input
              id="fullName"
              name="fullName"
              className="px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all text-sm shadow-sm"
              placeholder="John Doe"
              type="text"
              autoComplete="name"
              required
            />
          </div>

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
            <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                className={`w-full px-4 py-2.5 bg-white border ${showMismatchError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500' : showMatchSuccess ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500' : 'border-slate-300 focus:border-indigo-600 focus:ring-indigo-600'} rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 transition-all pr-12 text-sm shadow-sm`}
                placeholder="••••••••"
                type={showPassword ? "text" : "password"}
                minLength={6}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
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
            <p className="text-xs text-slate-500">Must be at least 6 characters</p>
          </div>

          <div className="flex flex-col gap-2 relative">
            <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                name="confirmPassword"
                className={`w-full px-4 py-2.5 bg-white border ${showMismatchError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500' : showMatchSuccess ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500' : 'border-slate-300 focus:border-indigo-600 focus:ring-indigo-600'} rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 transition-all pr-12 text-sm shadow-sm`}
                placeholder="••••••••"
                type={showPassword ? "text" : "password"}
                minLength={6}
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>
            {showMismatchError && (
              <p className="text-xs text-red-500 mt-1" role="alert">Passwords do not match</p>
            )}
            {showMatchSuccess && (
              <p className="text-xs text-emerald-600 mt-1" role="status">Passwords match</p>
            )}
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
            <SubmitButton 
              text="Create Account" 
              loadingText="Creating account..." 
              disabled={showMismatchError} 
            />
          </div>
        </form>

        <div className="mt-8 text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link href="/login" className="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
            Log in
          </Link>
        </div>
      </div>
    </div>
  )
}
