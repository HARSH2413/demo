
import Link from 'next/link'
import { ArrowRight, Database, Search, Shield, Zap, UploadCloud, MessageSquare, FileText, CheckCircle2 } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-indigo-500/30 relative overflow-hidden">
      
      {/* Animated Background Grid & Glows */}
      <div className="absolute inset-0 z-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f46e510_1px,transparent_1px),linear-gradient(to_bottom,#4f46e510_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] animate-grid" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-600/20 blur-[120px] rounded-full mix-blend-screen" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-6 max-w-7xl w-full mx-auto animate-fade-in-up" style={{ animationDelay: '0.1s', opacity: 0 }}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20" aria-hidden="true">
            D
          </div>
          <span className="text-xl font-bold tracking-tight">DocIntel</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/login" className="text-neutral-400 hover:text-white transition-colors hidden sm:block focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 outline-none rounded-md px-2 py-1">
            Log In
          </Link>
          <Link 
            href="/signup" 
            className="bg-white text-black px-5 py-2.5 rounded-full hover:bg-neutral-200 transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 outline-none"
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
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-medium text-indigo-300 mb-8 backdrop-blur-sm animate-fade-in-up"
            style={{ animationDelay: '0.1s', opacity: 0 }}
          >
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" aria-hidden="true"></span>
            The intelligent document assistant
          </div>
          
          <h1 
            className="text-5xl md:text-7xl font-bold tracking-tight mb-6 text-white leading-tight animate-fade-in-up"
            style={{ animationDelay: '0.2s', opacity: 0 }}
          >
            Understand any document <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">in seconds.</span>
          </h1>
          
          <p 
            className="text-lg md:text-xl text-neutral-400 mb-10 leading-relaxed max-w-2xl mx-auto animate-fade-in-up"
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
              className="flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-full font-medium transition-all duration-300 hover:scale-105 active:scale-95 w-full sm:w-auto shadow-[0_0_30px_-5px_rgba(79,70,229,0.4)] hover:shadow-[0_0_40px_-5px_rgba(79,70,229,0.6)] focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 outline-none"
            >
              Get Started for Free <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <Link 
              href="/login" 
              className="flex items-center justify-center gap-2 bg-neutral-900 hover:bg-neutral-800 hover:-translate-y-0.5 text-white px-8 py-4 rounded-full font-medium transition-all duration-300 border border-neutral-800 hover:border-neutral-700 w-full sm:w-auto focus-visible:ring-2 focus-visible:ring-neutral-500 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 outline-none"
            >
              Log In
            </Link>
          </div>
        </div>

        {/* Visual Demonstration Mockup */}
        <div className="mt-20 w-full animate-fade-in-up" style={{ animationDelay: '0.5s', opacity: 0 }} aria-hidden="true">
          <div className="relative rounded-2xl bg-neutral-900/50 border border-neutral-800/80 p-2 md:p-4 shadow-2xl backdrop-blur-xl overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-t from-neutral-950 via-transparent to-transparent z-10 pointer-events-none" />
            
            <div className="bg-neutral-950 rounded-xl border border-neutral-800 flex flex-col md:flex-row h-auto md:h-[500px] overflow-hidden relative z-0">
              {/* Sidebar / Upload Demo */}
              <div className="w-full md:w-1/3 border-b md:border-b-0 md:border-r border-neutral-800 bg-neutral-900/20 p-4 md:p-6 flex flex-col gap-3 md:gap-4">
                <div className="flex items-center justify-between mb-2 md:mb-4">
                  <h3 className="font-semibold text-neutral-200">Sources</h3>
                  <div className="p-1.5 bg-neutral-800 rounded-md"><UploadCloud className="w-4 h-4 text-neutral-400" /></div>
                </div>
                
                <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-900 border border-neutral-800">
                  <div className="p-2 bg-indigo-500/20 rounded text-indigo-400"><FileText className="w-5 h-5" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-200 truncate">Q3_Financial_Report.pdf</p>
                    <p className="text-xs text-neutral-500">1.2 MB • Processed</p>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                </div>
                <div className="hidden sm:flex items-center gap-3 p-3 rounded-lg bg-neutral-900/50 border border-neutral-800/50">
                  <div className="p-2 bg-neutral-800 rounded text-neutral-500"><FileText className="w-5 h-5" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-400 truncate">Market_Analysis_2024.pdf</p>
                    <p className="text-xs text-neutral-600">3.4 MB • Processed</p>
                  </div>
                </div>
              </div>
              
              {/* Chat Demo */}
              <div className="flex-1 flex flex-col p-4 md:p-6 relative min-h-[350px] md:min-h-0">
                <div className="flex-1 space-y-6 overflow-hidden">
                  <div className="flex gap-4 items-start max-w-[85%] ml-auto justify-end">
                    <div className="bg-neutral-800 text-neutral-200 p-3.5 rounded-2xl rounded-tr-sm text-sm">
                      What were the primary revenue drivers in Q3?
                    </div>
                  </div>
                  
                  <div className="flex gap-4 items-start max-w-[90%]">
                    <div className="w-8 h-8 shrink-0 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-xs">
                      D
                    </div>
                    <div className="bg-indigo-500/10 border border-indigo-500/20 text-neutral-200 p-4 rounded-2xl rounded-tl-sm text-sm leading-relaxed">
                      Based on the <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs font-mono">Q3_Financial_Report.pdf</span>, the primary revenue drivers were:
                      <ul className="list-disc pl-5 mt-2 space-y-1">
                        <li>Cloud Infrastructure Services (up 24% YoY)</li>
                        <li>Enterprise Software Subscriptions (up 18% YoY)</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div className="mt-4 relative">
                  <div className="w-full bg-neutral-900 border border-neutral-800 rounded-xl p-3 pl-4 pr-12 text-sm text-neutral-400">
                    Ask a question about your documents...
                  </div>
                  <div className="absolute right-2 top-2 p-1.5 bg-indigo-600 rounded-lg text-white">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* How It Works Section */}
      <section className="relative z-10 bg-neutral-950 border-t border-neutral-900 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16 animate-fade-in-up" style={{ animationDelay: '0.2s', opacity: 0 }}>
            <h2 className="text-3xl font-bold text-white mb-4">How it works</h2>
            <p className="text-neutral-400 max-w-2xl mx-auto">Get answers from your documents in three simple steps.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 relative">
            {/* Connecting line for desktop */}
            <div className="hidden md:block absolute top-8 left-[16.66%] right-[16.66%] h-[2px] bg-gradient-to-r from-transparent via-neutral-700 to-transparent z-0" />
            
            <StepCard 
              number="1"
              delay="0.3s"
              icon={<UploadCloud className="w-7 h-7 text-indigo-400" />}
              title="Upload Your Documents"
              description="Upload PDFs and other supported documents to your Box."
            />
            <StepCard 
              number="2"
              delay="0.4s"
              icon={<Zap className="w-7 h-7 text-purple-400" />}
              title="Let DocIntel Process Them"
              description="DocIntel extracts and indexes document content so it's ready for searching and asking questions."
            />
            <StepCard 
              number="3"
              delay="0.5s"
              icon={<MessageSquare className="w-7 h-7 text-pink-400" />}
              title="Ask Questions"
              description="Ask questions about your documents and receive answers based on the available information."
            />
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 bg-neutral-950 border-t border-neutral-900 py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16 animate-fade-in-up" style={{ animationDelay: '0.2s', opacity: 0 }}>
            <h2 className="text-3xl font-bold text-white mb-4">Everything you need to work smarter</h2>
            <p className="text-neutral-400 max-w-2xl mx-auto">Upload, index, and query your knowledge base effortlessly.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard 
              delay="0.3s"
              icon={<UploadCloud className="w-6 h-6 text-indigo-400" />}
              title="Secure Uploads"
              description="Simply drag and drop your PDFs. We securely process and index them in seconds."
            />
            <FeatureCard 
              delay="0.4s"
              icon={<Search className="w-6 h-6 text-purple-400" />}
              title="Semantic Search"
              description="Find relevant information instantly. Our AI understands context, not just keywords."
            />
            <FeatureCard 
              delay="0.5s"
              icon={<MessageSquare className="w-6 h-6 text-pink-400" />}
              title="Conversational AI"
              description="Ask natural questions and get synthesized answers with direct source citations."
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-neutral-900 bg-neutral-950 py-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-8 text-sm text-neutral-500">
          <div className="flex flex-col gap-3 max-w-md">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-neutral-800 flex items-center justify-center font-bold text-neutral-400 text-xs" aria-hidden="true">
                D
              </div>
              <span className="font-semibold text-neutral-300">DocIntel</span>
            </div>
            <p className="leading-relaxed text-neutral-400">
              Your files are strictly isolated to your personal Box. Original files are deleted immediately after secure vector processing.
            </p>
            <span>© {new Date().getFullYear()} DocIntel. All rights reserved.</span>
          </div>
          <div className="flex gap-6">
            <Link href="/login" className="hover:text-neutral-300 transition-colors focus-visible:ring-2 focus-visible:ring-neutral-500 outline-none rounded px-1">Log In</Link>
            <Link href="/signup" className="text-indigo-400 hover:text-indigo-300 transition-colors focus-visible:ring-2 focus-visible:ring-indigo-500 outline-none rounded px-1">Sign Up</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

function FeatureCard({ icon, title, description, delay }: { icon: React.ReactNode, title: string, description: string, delay: string }) {
  return (
    <div 
      className="p-8 rounded-2xl bg-neutral-900/30 border border-neutral-800 hover:border-neutral-700 hover:bg-neutral-900/60 transition-all duration-300 hover:-translate-y-1 group animate-fade-in-up"
      style={{ animationDelay: delay, opacity: 0 }}
    >
      <div className="w-12 h-12 rounded-xl bg-neutral-900 border border-neutral-800 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-neutral-400 leading-relaxed">{description}</p>
    </div>
  )
}

function StepCard({ number, icon, title, description, delay }: { number: string, icon: React.ReactNode, title: string, description: string, delay: string }) {
  return (
    <div 
      className="flex flex-col items-center text-center group animate-fade-in-up relative"
      style={{ animationDelay: delay, opacity: 0 }}
    >
      <div className="w-16 h-16 rounded-2xl bg-neutral-900/50 border border-neutral-800 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-neutral-800 group-hover:border-neutral-700 transition-all duration-300 relative z-10 backdrop-blur-sm shadow-lg">
        <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-neutral-950 text-neutral-300 text-sm font-bold flex items-center justify-center border border-neutral-800 shadow-sm">
          {number}
        </div>
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-white mb-3 transition-colors duration-300 group-hover:text-indigo-300">{title}</h3>
      <p className="text-neutral-400 leading-relaxed max-w-sm">{description}</p>
    </div>
  )
}
