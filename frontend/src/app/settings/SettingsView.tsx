"use client";

import React from 'react';

export default function SettingsView({ userEmail, userName }: { userEmail: string; userName: string }) {
  return (
    <div className="flex-1 px-6 md:px-10 py-8 md:py-12 max-w-4xl w-full mx-auto">
      {/* Header */}
      <div className="mb-8">
        <p className="text-[10px] font-semibold text-indigo-600 uppercase tracking-widest mb-1 font-mono">Configuration & Governance</p>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 font-headline mb-2">Settings</h1>
        <p className="text-sm text-slate-500">Manage your account settings and preferences.</p>
      </div>

      {/* Account Section */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 font-headline">Account</h2>
            <p className="text-xs text-slate-500">Your personal account information.</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-900 block mb-1.5">Display Name</label>
            <input
              className="w-full max-w-md bg-white border border-slate-300 rounded-lg px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15 transition-all"
              defaultValue={userName}
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-900 block mb-1.5">Email</label>
            <input
              className="w-full max-w-md bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 text-sm text-slate-500 cursor-not-allowed"
              defaultValue={userEmail}
              disabled
            />
            <p className="text-[11px] text-slate-400 mt-1">Email is managed by your authentication provider.</p>
          </div>
        </div>
      </section>

      {/* AI Preferences */}
      <section className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 font-headline">AI Model Preferences</h2>
            <p className="text-xs text-slate-500">Configure inference parameters and citation sensitivity for Box queries.</p>
          </div>
        </div>

        <div className="space-y-5">
          {/* Strict Citation Grounding */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">Strict Citation Grounding</p>
              <p className="text-xs text-slate-500 mt-0.5">Only synthesize statements directly backed by cited passages.</p>
            </div>
            <div className="w-11 h-6 bg-indigo-600 rounded-full relative cursor-pointer">
              <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm" />
            </div>
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 font-headline">Security & Privacy</h2>
            <p className="text-xs text-slate-500">Enforce perimeter isolation and data retention constraints.</p>
          </div>
        </div>

        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">Zero-Retention File Ingestion</p>
              <p className="text-xs text-slate-500 mt-0.5">Immediately purge raw document files after processing.</p>
            </div>
            <div className="w-11 h-6 bg-indigo-600 rounded-full relative cursor-pointer">
              <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm" />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-900">Strict Box Isolation</p>
              <p className="text-xs text-slate-500 mt-0.5">Forbid any cross-pollination of data between distinct Boxes.</p>
            </div>
            <div className="w-11 h-6 bg-indigo-600 rounded-full relative cursor-pointer">
              <div className="w-4 h-4 bg-white rounded-full absolute right-1 top-1 shadow-sm" />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
