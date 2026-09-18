"use client";

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Loader2, Plus, Database, ChevronRight, AlertCircle, Trash2 } from 'lucide-react';
import { API_URL } from '@/lib/config';
import { createClient } from '@/lib/supabase/client';

interface Box {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export default function BoxesClient() {
  const router = useRouter();
  const [boxes, setBoxes] = useState<Box[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newBoxName, setNewBoxName] = useState('');

  const apiFetch = useCallback(async (path: string, options?: RequestInit) => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    
    const fetchHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options?.headers as Record<string, string>),
    };
    
    if (session?.access_token) {
      fetchHeaders['Authorization'] = `Bearer ${session.access_token}`;
    }

    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: fetchHeaders
    });
    
    if (!res.ok) {
      const data = await res.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  }, []);

  const fetchBoxes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiFetch('/api/v1/boxes/');
      setBoxes(res.data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load boxes.");
    } finally {
      setLoading(false);
    }
  }, [apiFetch]);

  useEffect(() => {
    fetchBoxes();
  }, [fetchBoxes]);

  const handleCreateBox = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newBoxName.trim() || isCreating) return;

    try {
      setIsCreating(true);
      setError(null);
      const res = await apiFetch('/api/v1/boxes/', {
        method: 'POST',
        body: JSON.stringify({ name: newBoxName.trim() })
      });
      setBoxes([res.data, ...boxes]);
      setNewBoxName('');
      router.push(`/boxes/${res.data.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create box.");
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteBox = async (boxId: string, boxName: string) => {
    if (!window.confirm(`Delete box "${boxName}"? This cannot be undone.`)) return;
    try {
      await apiFetch(`/api/v1/boxes/${boxId}`, { method: 'DELETE' });
      setBoxes(boxes.filter(b => b.id !== boxId));
    } catch (err: any) {
      setError(err.message || "Failed to delete box.");
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans text-slate-900 p-8 flex justify-center">
      <div className="max-w-4xl w-full">
        <header className="mb-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600 p-2 rounded-xl shadow-lg shadow-indigo-100">
              <Database className="text-white w-6 h-6" />
            </div>
            <h1 className="font-bold text-3xl tracking-tight text-slate-800">Your Boxes</h1>
          </div>
          <form onSubmit={handleCreateBox} className="flex gap-2">
            <input 
              type="text" 
              placeholder="New Box Name" 
              value={newBoxName}
              onChange={(e) => setNewBoxName(e.target.value)}
              className="px-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              required
            />
            <button 
              type="submit" 
              disabled={isCreating || !newBoxName.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-all disabled:opacity-50"
            >
              {isCreating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              Create
            </button>
          </form>
        </header>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-center gap-3">
            <AlertCircle size={20} />
            <span className="font-semibold">{error}</span>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center p-20">
            <Loader2 className="w-10 h-10 animate-spin text-indigo-600" />
          </div>
        ) : boxes.length === 0 ? (
          <div className="text-center p-20 border-2 border-dashed border-slate-200 rounded-3xl bg-white text-slate-500">
            <Database size={48} className="mx-auto mb-4 text-indigo-200" />
            <h2 className="text-xl font-bold text-slate-700 mb-2">No Boxes Yet</h2>
            <p>Create your first Box to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {boxes.map(box => (
              <div key={box.id} className="group flex flex-col justify-between bg-white border border-slate-200 p-6 rounded-3xl hover:border-indigo-500 hover:shadow-xl transition-all relative">
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-bold text-lg text-slate-800 line-clamp-2">{box.name}</h3>
                    <button 
                      onClick={(e) => { e.preventDefault(); handleDeleteBox(box.id, box.name); }} 
                      className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-600 p-1 rounded-lg hover:bg-red-50 transition-all"
                      title="Delete Box"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                  {box.description && <p className="text-sm text-slate-500 line-clamp-2 mb-4">{box.description}</p>}
                  <p className="text-xs text-slate-400">Created {new Date(box.created_at).toLocaleDateString()}</p>
                </div>
                <Link href={`/boxes/${box.id}`} className="mt-6 flex items-center justify-center gap-2 w-full py-2.5 bg-slate-50 text-indigo-600 font-bold rounded-xl group-hover:bg-indigo-50 transition-colors">
                  Open Box <ChevronRight size={16} />
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
