import { createBox } from '../auth/actions'
import { Sparkles } from 'lucide-react'

export default async function OnboardingPage(props: {
  searchParams: Promise<{ message?: string }>
}) {
  const searchParams = await props.searchParams;
  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col items-center justify-center p-4 selection:bg-indigo-100 selection:text-indigo-900">
      <div className="w-full max-w-md bg-white border border-slate-200 p-8 rounded-2xl shadow-xl shadow-slate-200/50">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-4">
            <Sparkles className="w-6 h-6 text-indigo-600" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 font-headline tracking-tight text-center">Create your Box</h2>
          <p className="text-slate-500 text-sm mt-1.5 text-center">Let&apos;s set up your AI workspace.</p>
        </div>

        <form className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-slate-700 font-semibold tracking-tight" htmlFor="boxName">
              Box Name
            </label>
            <input
              id="boxName"
              name="boxName"
              className="px-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-1 focus:ring-indigo-600 transition-all text-sm shadow-sm"
              placeholder="e.g., Q4 Acquisition Due Diligence"
              type="text"
              required
            />
          </div>

          {searchParams?.message && (
            <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg text-center border border-red-200">
              {searchParams.message}
            </p>
          )}

          <button
            formAction={createBox}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg mt-4 transition-colors text-sm shadow-sm"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  )
}
