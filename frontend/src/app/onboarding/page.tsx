import { createWorkspace } from '../auth/actions'

export default async function OnboardingPage(props: {
  searchParams: Promise<{ message?: string }>
}) {
  const searchParams = await props.searchParams;
  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-neutral-900 border border-neutral-800 p-8 rounded-2xl shadow-xl">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xl shadow-lg mb-4">
            A
          </div>
          <h2 className="text-2xl font-bold text-white text-center">Create your workspace</h2>
          <p className="text-neutral-400 text-sm mt-2 text-center">Let&apos;s set up your AI workspace.</p>
        </div>

        <form className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-neutral-300 font-medium" htmlFor="workspaceName">
              Workspace Name
            </label>
            <input
              id="workspaceName"
              name="workspaceName"
              className="px-4 py-3 bg-neutral-950 border border-neutral-800 rounded-lg text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
              placeholder="Acme Technologies"
              type="text"
              required
            />
          </div>

          {searchParams?.message && (
            <p className="text-sm text-red-400 bg-red-400/10 p-3 rounded text-center">
              {searchParams.message}
            </p>
          )}

          <button
            formAction={createWorkspace}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-lg mt-6 transition-colors"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  )
}
