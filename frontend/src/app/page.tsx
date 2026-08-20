'use client'

import Link from 'next/link'
import { ArrowRight, Database, Search, Shield, Zap } from 'lucide-react'

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col font-sans selection:bg-neutral-800 relative overflow-hidden">
      
      {/* Animated Background Grid */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f46e510_1px,transparent_1px),linear-gradient(to_bottom,#4f46e510_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] animate-grid" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl w-full mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-lg">
            A
          </div>
          <span className="text-xl font-bold tracking-tight">Action.ai</span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium">
          <Link href="/login" className="text-neutral-400 hover:text-white transition-colors">
            Sign In
          </Link>
          <Link 
            href="/signup" 
            className="bg-white text-black px-4 py-2 rounded-full hover:bg-neutral-200 transition-colors"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 pt-20 pb-32 max-w-5xl mx-auto text-center pointer-events-auto">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-neutral-900 border border-neutral-800 text-xs font-medium text-neutral-400 mb-8">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          Action.ai Enterprise is now available
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 bg-gradient-to-b from-white to-neutral-400 bg-clip-text text-transparent leading-tight">
          Your knowledge. <br />
          One intelligent assistant.
        </h1>
        
        <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12 leading-relaxed">
          Upload your documents, connect your knowledge sources, and ask questions in natural language. Action.ai finds the exact answers and shows you the sources.
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4">
          <Link 
            href="/signup" 
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-8 py-4 rounded-full font-medium transition-all hover:scale-105 active:scale-95 w-full sm:w-auto justify-center shadow-[0_0_40px_-10px_rgba(79,70,229,0.5)]"
          >
            Get Started Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </main>

      {/* Features Grid */}
      <section className="bg-neutral-900/50 border-t border-neutral-900 py-24">
        <div className="max-w-7xl mx-auto px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            
            <FeatureCard 
              icon={<Database className="w-6 h-6 text-blue-400" />}
              title="Knowledge Base"
              description="Store all your important PDFs, Word docs, and presentations in one secure place."
            />
            <FeatureCard 
              icon={<Search className="w-6 h-6 text-purple-400" />}
              title="Semantic Search"
              description="Find relevant information instantly, even when exact keywords aren't used."
            />
            <FeatureCard 
              icon={<Zap className="w-6 h-6 text-yellow-400" />}
              title="Instant Answers"
              description="Ask natural questions and get synthesized answers with direct source citations."
            />
            <FeatureCard 
              icon={<Shield className="w-6 h-6 text-emerald-400" />}
              title="Private Workspace"
              description="Your data is completely isolated. Enterprise-grade security for your organization's knowledge."
            />

          </div>
        </div>
      </section>

    </div>
  )
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode, title: string, description: string }) {
  return (
    <div className="p-6 rounded-2xl bg-neutral-950 border border-neutral-800 hover:border-neutral-700 transition-colors">
      <div className="w-12 h-12 rounded-xl bg-neutral-900 border border-neutral-800 flex items-center justify-center mb-6">
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-neutral-400 text-sm leading-relaxed">{description}</p>
    </div>
  )
}
