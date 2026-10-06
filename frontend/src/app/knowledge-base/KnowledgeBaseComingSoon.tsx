"use client";

import React from 'react';
import { Sparkles } from 'lucide-react';

export default function KnowledgeBaseComingSoon() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center p-8 -mt-6">
      <div className="max-w-md w-full flex flex-col items-center text-center">
        {/* Icon with glow */}
        <div className="relative mb-6">
          <div className="w-16 h-16 rounded-2xl bg-white border border-slate-200 shadow-[0_8px_30px_rgb(79,70,229,0.08)] ring-4 ring-indigo-50 flex items-center justify-center text-indigo-600 transition-transform duration-300 hover:scale-105">
            <Sparkles size={32} />
          </div>
          {/* Tiny green accent dot */}
          <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-white" />
        </div>

        {/* Coming Soon Badge */}
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#eef2ff] border border-indigo-100 mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-pulse" />
          <span className="text-xs font-medium text-indigo-600 tracking-tight">Coming Soon</span>
        </div>

        {/* Headline */}
        <h2 className="text-2xl font-semibold tracking-[-0.02em] text-[#0f172a] mb-3 font-headline">
          Global Knowledge Base
        </h2>

        {/* Description */}
        <p className="text-sm text-[#64748b] leading-relaxed mb-8 max-w-sm">
          Cross-Box search and synthesis across all your workspaces will be available soon. For now, document intelligence remains strictly isolated within each individual Box.
        </p>

        {/* Notify form */}
        <form className="w-full max-w-sm" onSubmit={e => { e.preventDefault(); }}>
          <div className="flex items-center gap-2 p-1.5 bg-white border border-[#e2e8f0] rounded-xl shadow-xs focus-within:border-indigo-600 focus-within:ring-2 focus-within:ring-indigo-600/15 transition-all">
            <input
              className="flex-1 bg-transparent border-none px-3 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:ring-0 focus:outline-none"
              placeholder="Enter your work email"
              type="email"
            />
            <button
              className="px-4 py-2 bg-[#4f46e5] text-white hover:bg-indigo-700 active:scale-[0.98] font-medium text-xs rounded-lg transition-all shadow-xs whitespace-nowrap"
              type="submit"
            >
              Notify me
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
