"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, FolderOpen, Sparkles, Settings, User, Plus, Menu, X, LogOut } from 'lucide-react';

interface ShellLayoutProps {
  children: React.ReactNode;
  userEmail?: string;
  userName?: string;
}

export default function ShellLayout({ children, userEmail, userName }: ShellLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [showCreateBox, setShowCreateBox] = useState(false);

  const navItems = [
    { name: 'Dashboard', href: '/boxes', icon: LayoutDashboard },
    { name: 'My Boxes', href: '/boxes/all', icon: FolderOpen },
    { name: 'Knowledge Base', href: '/knowledge-base', icon: Sparkles, badge: 'Soon' },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  const handleSignOut = async () => {
    await fetch('/auth/logout', { method: 'POST' });
    window.location.href = '/login';
  };

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  const isActive = (href: string, name: string) => {
    if (name === 'Dashboard') return pathname === '/boxes';
    if (name === 'My Boxes') return pathname.startsWith('/boxes/');
    return pathname === href;
  };

  return (
    <div className="flex h-screen bg-[#f8fafc] text-[#0f172a] font-sans overflow-hidden">
      {/* Mobile Overlay */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 bg-[#0f172a]/30 backdrop-blur-[3px] z-40 md:hidden" onClick={closeMobileMenu} />
      )}

      {/* Sidebar — matches Stitch exactly */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col p-4 transition-transform duration-300 ease-in-out md:static md:translate-x-0
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Brand Header */}
        <div className="flex items-center gap-3 px-2 py-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center">
            <Sparkles className="w-[18px] h-[18px] text-indigo-600" />
          </div>
          <div>
            <div className="font-headline text-base font-semibold tracking-tight text-slate-900">DocIntel</div>
            <div className="text-xs text-slate-500 leading-tight tracking-tight">Precision AI</div>
          </div>
          <button className="ml-auto md:hidden text-slate-400 hover:text-slate-700" onClick={closeMobileMenu}>
            <X size={20} />
          </button>
        </div>

        {/* New Box CTA */}
        <div className="mb-6 px-1">
          <button
            onClick={() => {
              closeMobileMenu();
              // Dispatch custom event so BoxesClient can open its modal
              window.dispatchEvent(new CustomEvent('docintel:create-box'));
              if (!pathname.startsWith('/boxes')) router.push('/boxes');
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-slate-700 hover:text-indigo-600 text-sm font-medium transition-all duration-150"
          >
            <Plus size={16} className="text-indigo-600" />
            New Box
          </button>
        </div>

        {/* Navigation */}
        <nav className="space-y-1 flex-1 text-sm font-medium tracking-tight">
          {navItems.map((item) => {
            const active = isActive(item.href, item.name);
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.badge ? '#' : item.href}
                onClick={(e) => {
                  if (item.badge) { e.preventDefault(); return; }
                  closeMobileMenu();
                }}
                className={`
                  flex items-center justify-between px-3 py-2 rounded-lg transition-colors duration-150
                  ${active
                    ? 'bg-indigo-50 text-indigo-600 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <Icon size={20} className={active ? 'text-indigo-600' : 'text-slate-400'} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] tracking-wide uppercase px-1.5 py-0.5 rounded font-mono font-semibold bg-indigo-100 text-indigo-600">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer Profile */}
        <div className="pt-4 border-t border-slate-200 space-y-1">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 text-sm font-medium">
            <div className="w-7 h-7 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-xs font-semibold text-indigo-600">
              {userName ? userName.charAt(0).toUpperCase() : userEmail?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700 truncate">{userName || userEmail || 'User'}</p>
            </div>
          </div>
          <button
            onClick={handleSignOut}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors text-sm font-medium"
          >
            <LogOut size={20} className="text-slate-400" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Top Nav Bar — matches Stitch */}
        <header className="flex justify-between items-center h-14 px-4 md:px-8 w-full bg-white border-b border-slate-200 sticky top-0 z-30 shrink-0">
          {/* Mobile menu button */}
          <button className="mr-3 md:hidden text-slate-400 hover:text-slate-700" onClick={() => setIsMobileMenuOpen(true)}>
            <Menu size={22} />
          </button>

          {/* Search (desktop) */}
          <div className="relative w-72 hidden md:block">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:bg-white focus:ring-1 focus:ring-indigo-600 focus:border-indigo-600 focus:outline-none transition-all"
              placeholder="Search..."
              type="text"
            />
          </div>

          {/* Trailing cluster */}
          <div className="flex items-center gap-3 ml-auto">
            <div className="w-px h-4 bg-slate-200 mx-1 hidden md:block" />
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-xs font-semibold text-indigo-600">
                {userName ? userName.charAt(0).toUpperCase() : userEmail?.charAt(0).toUpperCase() || 'U'}
              </div>
              <span className="text-xs font-medium text-slate-700 hidden sm:block">
                {userName || userEmail || 'User'}
              </span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
