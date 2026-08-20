import Link from 'next/link'
import { login, signInWithGoogle } from '../auth/actions'

export default function LoginPage({
    searchParams,
  }: {
    searchParams: { message: string }
  }) {
  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-4">
      <Link href="/" className="absolute top-8 left-8 text-neutral-400 hover:text-white transition-colors">
        ← Back to home
      </Link>
      
      <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 p-8 rounded-2xl shadow-xl">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xl shadow-lg mb-4">
            A
          </div>
          <h2 className="text-2xl font-bold text-white">Welcome back</h2>
          <p className="text-neutral-400 text-sm mt-2">Continue to your workspace</p>
        </div>

        {/* Google Sign-In */}
        <form className="mb-6">
          <button
            formAction={signInWithGoogle}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-neutral-100 text-neutral-800 font-medium py-3 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        </form>

        {/* Divider */}
        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-neutral-800"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-neutral-900 text-neutral-500">or continue with email</span>
          </div>
        </div>

        <form className="flex flex-col gap-4">
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
              required
            />
          </div>

          <div className="flex flex-col gap-2">
            <label className="text-sm text-neutral-300 font-medium" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              name="password"
              className="px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="••••••••"
              type="password"
              required
            />
          </div>

          {searchParams?.message && (
            <p className="text-sm text-red-400 bg-red-400/10 p-3 rounded text-center">
              {searchParams.message}
            </p>
          )}

          <button
            formAction={login}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-lg mt-4 transition-colors"
          >
            Sign In
          </button>
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
