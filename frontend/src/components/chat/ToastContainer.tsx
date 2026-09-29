import React from 'react';
import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react';

export interface Toast {
  id: number;
  message: string;
  type: 'success' | 'error' | 'warning';
}

export function ToastContainer({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="fixed top-6 right-6 z-50 space-y-3">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl text-sm font-semibold backdrop-blur-md animate-slide-in max-w-sm ${toast.type === 'success' ? 'bg-emerald-600/95 text-white' :
            toast.type === 'error' ? 'bg-red-600/95 text-white' :
              'bg-amber-500/95 text-white'
            }`}
        >
          {toast.type === 'success' && <CheckCircle2 size={16} />}
          {toast.type === 'error' && <XCircle size={16} />}
          {toast.type === 'warning' && <AlertCircle size={16} />}
          <span className="flex-1">{toast.message}</span>
          <button onClick={() => onDismiss(toast.id)} className="opacity-70 hover:opacity-100">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
