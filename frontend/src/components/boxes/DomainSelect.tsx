"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Search } from 'lucide-react';

export const BOX_DOMAINS = [
  'General / Other',
  'Business & Management',
  'Finance & Accounting',
  'Legal & Compliance',
  'Human Resources',
  'Sales & Marketing',
  'Technology & IT',
  'Engineering',
  'Healthcare & Medical',
  'Education & Training',
  'Research & Science',
  'Government & Public Sector',
  'Real Estate & Property',
  'Manufacturing & Operations',
  'Construction & Infrastructure',
  'Media & Communications',
  'Retail & E-commerce',
  'Customer Support & Service',
  'Nonprofit & Organizations',
  'Personal / General Documents',
  'Other',
];

interface Props {
  id?: string;
  value: string;
  onChange: (value: string) => void;
}

export default function DomainSelect({ id = 'box-domain', value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(
    () => BOX_DOMAINS.filter(d => d.toLowerCase().includes(query.toLowerCase())),
    [query]
  );

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    setTimeout(() => inputRef.current?.focus(), 0);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  useEffect(() => { setActive(0); }, [query]);

  const select = (d: string) => {
    onChange(d);
    setOpen(false);
    setQuery('');
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a + 1, filtered.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)); }
    else if (e.key === 'Enter') { e.preventDefault(); if (filtered[active]) select(filtered[active]); }
    else if (e.key === 'Escape') { e.preventDefault(); setOpen(false); }
  };

  return (
    <div ref={wrapRef} className="relative">
      <button
        id={id}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center justify-between bg-white border rounded-lg px-3.5 py-2.5 text-sm text-left transition-all focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/15 ${open ? 'border-indigo-600 ring-2 ring-indigo-600/15' : 'border-slate-300'}`}
      >
        <span className={value ? 'text-slate-900' : 'text-slate-400'}>{value || 'Select a domain...'}</span>
        <ChevronDown size={16} className={`text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-20 mt-1.5 w-full bg-white border border-slate-200 rounded-lg shadow-lg overflow-hidden">
          <div className="relative border-b border-slate-100">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              ref={inputRef}
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Search domains..."
              className="w-full pl-9 pr-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none"
            />
          </div>
          <ul role="listbox" className="max-h-56 overflow-y-auto py-1">
            {filtered.length === 0 && (
              <li className="px-3.5 py-2 text-xs text-slate-400">No matching domain</li>
            )}
            {filtered.map((d, i) => (
              <li
                key={d}
                role="option"
                aria-selected={value === d}
                onMouseEnter={() => setActive(i)}
                onMouseDown={e => { e.preventDefault(); select(d); }}
                className={`flex items-center justify-between px-3.5 py-2 text-sm cursor-pointer ${i === active ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700'}`}
              >
                <span>{d}</span>
                {value === d && <Check size={14} className="text-indigo-600" />}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
