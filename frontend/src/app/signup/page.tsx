'use client'

import React, { useState } from 'react'
import Link from 'next/link'
import { signup } from '../auth/actions'
import { Eye, EyeOff } from 'lucide-react'
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
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-4 selection:bg-indigo-500/30">
      <Link href="/" className="absolute top-8 left-8 text-neutral-400 hover:text-white transition-colors animate-fade-in">
        ← Back to home
      </Link>
      
      <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 p-8 rounded-2xl shadow-2xl animate-fade-in-up">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xl shadow-lg shadow-indigo-500/20 mb-4">
            D
          </div>
          <h2 className="text-2xl font-bold text-white">Create your account</h2>
          <p className="text-neutral-400 text-sm mt-2">Start your private AI knowledge base</p>
        </div>

        {/* Google Sign-Up */}
        <GoogleSignInButton />

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-neutral-800"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-neutral-900 text-neutral-500">or sign up with email</span>
          </div>
        </div>

        <form action={signup} onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-neutral-300 font-medium" htmlFor="fullName">
              Full Name
            </label>
            <input
              id="fullName"
              name="fullName"
              className="px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="John Doe"
              type="text"
              autoComplete="name"
              required
            />
          </div>

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
            <label className="text-sm text-neutral-300 font-medium" htmlFor="password">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                className={`w-full px-4 py-3 bg-neutral-950 border ${showMismatchError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500' : showMatchSuccess ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500' : 'border-neutral-800 focus:border-indigo-500 focus:ring-indigo-500'} rounded-lg text-white focus:outline-none focus:ring-1 transition-all pr-12`}
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
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-200"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-neutral-500">Must be at least 6 characters</p>
          </div>

          <div className="flex flex-col gap-2 relative">
            <label className="text-sm text-neutral-300 font-medium" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                name="confirmPassword"
                className={`w-full px-4 py-3 bg-neutral-950 border ${showMismatchError ? 'border-red-500/50 focus:border-red-500 focus:ring-red-500' : showMatchSuccess ? 'border-emerald-500/50 focus:border-emerald-500 focus:ring-emerald-500' : 'border-neutral-800 focus:border-indigo-500 focus:ring-indigo-500'} rounded-lg text-white focus:outline-none focus:ring-1 transition-all pr-12`}
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
              <p className="text-xs text-red-400 mt-1" role="alert">Passwords do not match</p>
            )}
            {showMatchSuccess && (
              <p className="text-xs text-emerald-400 mt-1" role="status">Passwords match</p>
            )}
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

          <SubmitButton 
            text="Create Account" 
            loadingText="Creating account..." 
            disabled={showMismatchError} 
          />
        </form>

        <div className="mt-8 text-center text-sm text-neutral-400">
          Already have an account?{' '}
          <Link href="/login" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
            Log in
          </Link>
        </div>
      </div>
    </div>
  )
}
