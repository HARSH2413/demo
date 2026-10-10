import Link from 'next/link'
import { ArrowRight, Database, Search, Shield, Zap, UploadCloud, MessageSquare, FileText, CheckCircle2, Sparkles } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-900 relative overflow-hidden">

      {/* Background Grid & Glows */}
      <div className="absolute inset-0 z-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f46e510_1px,transparent_1px),linear-gradient(to_bottom,#4f46e510_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] animate-grid" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-200/50 blur-[120px] rounded-full mix-blend-multiply" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-6 max-w-7xl w-full mx-auto animate-fade-in-up" style={{ animationDelay: '0.1s', opacity: 0 }}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center font-bold text-indigo-600 shadow-sm" aria-hidden="true">
            <Sparkles className="w-4 h-4 text-indigo-600" />
          </div>
          <span className="text-xl font-bold tracking-tight font-headline">DocIntel</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/login" className="text-slate-500 hover:text-slate-900 transition-colors hidden sm:block focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white outline-none rounded-md px-2 py-1">
            Log In
          </Link>
          <Link
            href="/signup"
            className="bg-indigo-600 text-white px-5 py-2.5 rounded-full hover:bg-indigo-700 transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white outline-none"
          >
            Sign Up
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex-1 flex flex-col items-center px-4 pt-16 pb-24 max-w-6xl mx-auto w-full">

        {/* Text Content */}
        <div className="text-center max-w-3xl mx-auto">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 border border-indigo-100 text-xs font-medium text-indigo-600 mb-8 animate-fade-in-up shadow-sm"
            style={{ animationDelay: '0.1s', opacity: 0 }}
          >
            <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" aria-hidden="true"></span>
            The intelligent document assistant
          </div>

          <h1
            className="text-5xl md:text-7xl font-bold tracking-tight mb-6 text-slate-900 font-headline leading-tight animate-fade-in-up"
            style={{ animationDelay: '0.2s', opacity: 0 }}
          >
            Understand any document <br className="hidden md:block" />
            <span className="text-indigo-600">in seconds.</span>
          </h1>

          <p
            className="text-lg md:text-xl text-slate-500 mb-10 leading-relaxed max-w-2xl mx-auto animate-fade-in-up"
            style={{ animationDelay: '0.3s', opacity: 0 }}
          >
            DocIntel reads your PDFs, connects the dots, and answers your questions instantly with precise citations. Built for students, researchers, and professionals.
          </p>

          <div
            className="flex flex-col sm:flex-row items-center gap-4 justify-center animate-fade-in-up"
            style={{ animationDelay: '0.4s', opacity: 0 }}
          >
            <Link
              href="/signup"
              className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-4 rounded-full font-medium transition-all duration-300 hover:scale-105 active:scale-95 w-full sm:w-auto shadow-md shadow-indigo-200 focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white outline-none"
            >
              Get Started for Free <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link
              href="/login"
              className="flex items-center justify-center gap-2 bg-white hover:bg-slate-50 hover:-translate-y-0.5 text-slate-700 px-8 py-4 rounded-full font-medium transition-all duration-300 border border-slate-200 hover:border-slate-300 w-full sm:w-auto focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white outline-none shadow-sm"
            >
              Log In
            </Link>
          </div>
        </div>

        {/* Visual Demonstration Mockup */}
        <div className="mt-20 w-full animate-fade-in-up" style={{ animationDelay: '0.5s', opacity: 0 }} aria-hidden="true">
          <div className="relative rounded-2xl bg-white/50 border border-slate-200/80 p-2 md:p-4 shadow-2xl shadow-slate-200/50 overflow-hidden">
            <div className="bg-white rounded-xl border border-slate-200 flex flex-col md:flex-row h-auto md:h-[500px] overflow-hidden relative z-0 shadow-sm">

              {/* Sidebar / Upload Demo */}
              <div className="w-full md:w-1/3 border-b md:border-b-0 md:border-r border-slate-200 bg-slate-50 p-4 md:p-6 flex flex-col gap-3 md:gap-4">
                <div className="flex items-center justify-between mb-2 md:mb-4">
                  <h3 className="font-semibold text-slate-800 font-headline">Sources</h3>
                  <div className="p-1.5 bg-white border border-slate-200 rounded-md shadow-xs"><UploadCloud className="w-4 h-4 text-slate-500" /></div>
                </div>

                <div className="flex items-center gap-3 p-3 rounded-lg bg-white border border-slate-200 shadow-sm">
                  <div className="p-2 bg-indigo-50 rounded text-indigo-600"><FileText className="w-5 h-5" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate font-headline">Q3_Financial_Report.pdf</p>
                    <p className="text-xs text-slate-500">1.2 MB • Processed</p>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                </div>
                <div className="hidden sm:flex items-center gap-3 p-3 rounded-lg bg-white/50 border border-slate-200 border-dashed">
                  <div className="p-2 bg-slate-50 border border-slate-100 rounded text-slate-400"><FileText className="w-5 h-5" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-500 truncate font-headline">Market_Analysis_2024.pdf</p>
                    <p className="text-xs text-slate-400">3.4 MB • Processed</p>
                  </div>
                </div>
              </div>

              {/* Chat Demo */}
              <div className="flex-1 flex flex-col p-4 md:p-6 relative min-h-[350px] md:min-h-0 bg-white">
                <div className="flex-1 space-y-6 overflow-hidden">
                  <div className="flex gap-4 items-start max-w-[85%] ml-auto justify-end">
                    <div className="bg-slate-100 border border-slate-200 text-slate-800 p-3.5 rounded-2xl rounded-tr-sm text-sm shadow-sm">
                      What were the primary revenue drivers in Q3?
                    </div>
                  </div>

                  <div className="flex gap-4 items-start max-w-[90%]">
                    <div className="w-8 h-8 shrink-0 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center">
                      <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
                    </div>
                    <div className="bg-white border border-indigo-100 text-slate-800 p-4 rounded-2xl rounded-tl-sm text-sm leading-relaxed shadow-sm">
                      Based on the <span className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 text-xs font-mono shadow-xs">Q3_Financial_Report.pdf</span>, the primary revenue drivers were:
                      <ul className="list-disc pl-5 mt-2 space-y-1 text-slate-600">
                        <li>Cloud Infrastructure Services (up 24% YoY)</li>
                        <li>Enterprise Software Subscriptions (up 18% YoY)</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="mt-4 relative">
                  <div className="w-full bg-white border border-slate-200 shadow-sm rounded-xl p-3 pl-4 pr-12 text-sm text-slate-400">
                    Ask a question about your documents...
                  </div>
                  <div className="absolute right-2 top-2 p-1.5 bg-indigo-600 hover:bg-indigo-700 transition-colors rounded-lg text-white">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* How It Works Section */}
      <section className="relative z-10 bg-slate-50 border-t border-slate-200 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16 animate-fade-in-up" style={{ animationDelay: '0.2s', opacity: 0 }}>
            <h2 className="text-3xl font-bold text-slate-900 font-headline mb-4">How it works</h2>
            <p className="text-slate-500 max-w-2xl mx-auto">Get answers from your documents in three simple steps.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* Connecting line for desktop */}
            <div className="hidden md:block absolute top-8 left-[16.66%] right-[16.66%] h-[2px] bg-gradient-to-r from-transparent via-slate-200 to-transparent z-0" />

            <StepCard
              number="1"
              delay="0.3s"
              icon={<UploadCloud className="w-6 h-6 text-indigo-600" />}
              title="Upload Your Documents"
              description="Upload PDFs and other supported documents to your Box."
            />
            <StepCard
              number="2"
              delay="0.4s"
              icon={<Zap className="w-6 h-6 text-purple-600" />}
              title="Let DocIntel Process Them"
              description="DocIntel extracts and indexes document content so it's ready for searching and asking questions."
            />
            <StepCard
              number="3"
              delay="0.5s"
              icon={<MessageSquare className="w-6 h-6 text-emerald-600" />}
              title="Ask Questions"
              description="Ask questions about your documents and receive answers based on the available information."
            />
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 bg-white border-t border-slate-200 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16 animate-fade-in-up" style={{ animationDelay: '0.2s', opacity: 0 }}>
            <h2 className="text-3xl font-bold text-slate-900 font-headline mb-4">Everything you need to work smarter</h2>
            <p className="text-slate-500 max-w-2xl mx-auto">Upload, index, and query your knowledge base effortlessly.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              delay="0.3s"
              icon={<UploadCloud className="w-6 h-6 text-indigo-600" />}
              title="Secure Uploads"
              description="Simply drag and drop your PDFs. We securely process and index them in seconds."
            />
            <FeatureCard
              delay="0.4s"
              icon={<Search className="w-6 h-6 text-purple-600" />}
              title="Semantic Search"
              description="Find relevant information instantly. Our AI understands context, not just keywords."
            />
            <FeatureCard
              delay="0.5s"
              icon={<MessageSquare className="w-6 h-6 text-emerald-600" />}
              title="Conversational AI"
              description="Ask natural questions and get synthesized answers with direct source citations."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200 bg-slate-50 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-8 text-sm text-slate-500">
          <div className="flex flex-col gap-3 max-w-md">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-indigo-50 border border-indigo-100 flex items-center justify-center font-bold text-indigo-600" aria-hidden="true">
                <Sparkles className="w-3 h-3 text-indigo-600" />
              </div>
              <span className="font-semibold text-slate-700 font-headline tracking-tight">DocIntel</span>
            </div>
            <p className="leading-relaxed text-slate-500">
              Your files are strictly isolated to your personal Box. Original files are deleted immediately after secure vector processing.
            </p>
            <span>© {new Date().getFullYear()} DocIntel. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <Link href="/login" className="font-medium hover:text-slate-900 transition-colors focus-visible:ring-2 focus-visible:ring-slate-500 outline-none rounded px-1">Log In</Link>
            <Link href="/signup" className="font-semibold text-indigo-600 hover:text-indigo-700 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 outline-none rounded px-1">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description, delay }: { icon: React.ReactNode, title: string, description: string, delay: string }) {
  return (
    <div
      className="p-8 rounded-2xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-1 group animate-fade-in-up"
      style={{ animationDelay: delay, opacity: 0 }}
    >
      <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-indigo-200 group-hover:bg-indigo-50 transition-all duration-300">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-slate-900 font-headline mb-2">{title}</h3>
      <p className="text-slate-500 leading-relaxed">{description}</p>
    </div>
  )
}

function StepCard({ number, icon, title, description, delay }: { number: string, icon: React.ReactNode, title: string, description: string, delay: string }) {
  return (
    <div
      className="flex flex-col items-center text-center group animate-fade-in-up relative"
      style={{ animationDelay: delay, opacity: 0 }}
    >
      <div className="w-16 h-16 rounded-2xl bg-white border border-slate-200 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:border-indigo-200 group-hover:bg-indigo-50 transition-all duration-300 relative z-10 shadow-sm">
        <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-slate-900 text-white text-sm font-bold flex items-center justify-center shadow-md">
          {number}
        </div>
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-slate-900 font-headline mb-3 transition-colors duration-300 group-hover:text-indigo-600">{title}</h3>
      <p className="text-slate-500 leading-relaxed max-w-sm">{description}</p>
    </div>
  )
}
