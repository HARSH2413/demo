"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, FolderOpen, Sparkles, Settings, User, Plus, Menu, X, LogOut, PanelLeftClose, PanelRightClose, PanelLeftOpen } from 'lucide-react';

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
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Load collapsed state from local storage on mount
  React.useEffect(() => {
    try {
      const saved = localStorage.getItem('docintel.shell.collapsed');
      if (saved !== null) setIsCollapsed(JSON.parse(saved));
    } catch {}
  }, []);

  const toggleCollapsed = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    try { localStorage.setItem('docintel.shell.collapsed', JSON.stringify(newState)); } catch {}
  };

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

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 bg-white border-r border-slate-200 flex flex-col p-4 transition-all duration-300 ease-in-out md:static md:translate-x-0
        ${isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        ${isCollapsed ? 'w-20 items-center' : 'w-64'}
      `}>
        {/* Brand Header */}
        <div className={`flex items-center py-3 mb-6 ${isCollapsed ? 'justify-center' : 'justify-between px-2 w-full'}`}>
          {!isCollapsed && (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex shrink-0 items-center justify-center">
                <Sparkles className="w-[18px] h-[18px] text-indigo-600" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-headline text-base font-semibold tracking-tight text-slate-900 truncate">DocIntel</div>
                <div className="text-xs text-slate-500 leading-tight tracking-tight truncate">Precision AI</div>
              </div>
            </div>
          )}
          <button className="hidden md:flex text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors shrink-0" onClick={toggleCollapsed} title={isCollapsed ? "Open Sidebar" : "Close Sidebar"}>
            {isCollapsed ? <PanelLeftOpen size={20} /> : <PanelLeftClose size={20} />}
          </button>
          <button className="ml-auto md:hidden text-slate-400 hover:text-slate-700" onClick={closeMobileMenu}>
            <X size={20} />
          </button>
        </div>

        {/* New Box CTA */}
        <div className="mb-6 px-1 w-full">
          <button
            onClick={() => {
              closeMobileMenu();
              window.dispatchEvent(new CustomEvent('docintel:create-box'));
              if (!pathname.startsWith('/boxes')) router.push('/boxes');
            }}
            title={isCollapsed ? "New Box" : undefined}
            className={`flex items-center justify-center py-2 rounded-lg bg-slate-50 border border-slate-200 hover:border-indigo-400 hover:bg-indigo-50/50 text-slate-700 hover:text-indigo-600 text-sm font-medium transition-all duration-150 ${isCollapsed ? 'w-10 h-10 px-0 mx-auto' : 'w-full gap-2 px-3'}`}
          >
            <Plus size={16} className="text-indigo-600 shrink-0" />
            {!isCollapsed && <span>New Box</span>}
          </button>
        </div>

        {/* Navigation */}
        <nav className="space-y-1 flex-1 text-sm font-medium tracking-tight w-full">
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
                title={isCollapsed ? item.name : undefined}
                className={`
                  flex items-center justify-between py-2 rounded-lg transition-colors duration-150
                  ${isCollapsed ? 'justify-center px-0 w-10 mx-auto' : 'px-3'}
                  ${active
                    ? 'bg-indigo-50 text-indigo-600 font-semibold'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                  }
                `}
              >
                <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
                  <Icon size={20} className={`shrink-0 ${active ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {!isCollapsed && <span>{item.name}</span>}
                </div>
                {!isCollapsed && item.badge && (
                  <span className="text-[10px] tracking-wide uppercase px-1.5 py-0.5 rounded font-mono font-semibold bg-indigo-100 text-indigo-600">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Footer Profile */}
        <div className="pt-4 border-t border-slate-200 space-y-1 w-full">
          <div className={`flex items-center ${isCollapsed ? 'justify-center px-0' : 'gap-3 px-3'} py-2 rounded-lg text-slate-600 text-sm font-medium`}>
            <div className="w-7 h-7 shrink-0 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-xs font-semibold text-indigo-600">
              {userName ? userName.charAt(0).toUpperCase() : userEmail?.charAt(0).toUpperCase() || 'U'}
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate">{userName || userEmail || 'User'}</p>
              </div>
            )}
          </div>
          <button
            onClick={handleSignOut}
            title={isCollapsed ? "Sign Out" : undefined}
            className={`w-full flex items-center ${isCollapsed ? 'justify-center px-0 w-10 mx-auto' : 'gap-3 px-3'} py-2 rounded-lg text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors text-sm font-medium`}
          >
            <LogOut size={20} className="text-slate-400 shrink-0" />
            {!isCollapsed && <span>Sign Out</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0">
        {/* Top Nav Bar — matches Stitch */}
        <header className="flex items-center h-14 px-4 md:px-6 w-full bg-white border-b border-slate-200 sticky top-0 z-30 shrink-0 gap-3">
          {/* Mobile menu button */}
          <button className="md:hidden text-slate-400 hover:text-slate-700 shrink-0" onClick={() => setIsMobileMenuOpen(true)}>
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
