"use client";

import React from 'react';
import { X, FileText, Loader2, Check, Clock, ArrowRight, Info, Lock, CloudUpload } from 'lucide-react';

export type UploadFileStatus = 'queued' | 'processing' | 'indexing' | 'ready' | 'failed';

export interface UploadFileItem {
  filename: string;
  size: number;
  status: UploadFileStatus;
  progress: number; // 0-100
  statusMessage?: string;
}

interface UploadProgressModalProps {
  isOpen: boolean;
  boxName: string;
  files: UploadFileItem[];
  onClose: () => void;
  onCancelAll: () => void;
  onRemoveFile: (filename: string) => void;
}

function CircularProgress({ progress, color }: { progress: number; color: string }) {
  const circumference = 2 * Math.PI * 14; // r=14
  const offset = circumference - (progress / 100) * circumference;
  return (
    <div className="relative w-7 h-7 flex items-center justify-center">
      <svg className="w-7 h-7 transform -rotate-90" viewBox="0 0 36 36">
        <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeWidth="3" className="text-slate-200" />
        <circle cx="18" cy="18" r="14" fill="none" stroke="currentColor" strokeWidth="3"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          className={`${color} transition-all duration-300`} />
      </svg>
      <span className={`absolute text-[10px] font-semibold font-mono ${color.replace('text-', 'text-')}`}>
        {progress}%
      </span>
    </div>
  );
}

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return 'pdf';
  if (ext === 'docx' || ext === 'doc') return 'docx';
  if (ext === 'csv' || ext === 'xlsx') return 'spreadsheet';
  return 'file';
}

export default function UploadProgressModal({
  isOpen,
  boxName,
  files,
  onClose,
  onCancelAll,
  onRemoveFile,
}: UploadProgressModalProps) {
  if (!isOpen || files.length === 0) return null;

  const completedCount = files.filter(f => f.status === 'ready').length;
  const totalCount = files.length;
  const overallProgress = totalCount > 0
    ? Math.round(files.reduce((sum, f) => sum + f.progress, 0) / totalCount)
    : 0;

  const allDone = completedCount === totalCount;
  const hasFailed = files.some(f => f.status === 'failed');

  const statusMessages: Record<UploadFileStatus, string> = {
    queued: 'Waiting for slot...',
    processing: 'Extracting content',
    indexing: 'Generating vectors',
    ready: 'Indexed and ready',
    failed: 'Processing failed',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-900/30 backdrop-blur-sm transition-all" role="dialog" aria-modal="true" aria-labelledby="upload-modal-title">
      {/* Modal Card */}
      <div className="w-full max-w-2xl bg-white rounded-xl border border-slate-200 shadow-2xl overflow-hidden flex flex-col transition-all">

        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-100 bg-white flex items-start justify-between">
          <div className="flex items-start gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
              <CloudUpload className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold tracking-tight text-slate-900 font-headline" id="upload-modal-title">
                  Uploading & Processing Files
                </h2>
                <span className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
                  allDone
                    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    : 'text-indigo-600 bg-indigo-50 border-indigo-100'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${allDone ? 'bg-emerald-500' : 'bg-indigo-600 animate-pulse'}`} />
                  {allDone ? 'Complete' : 'Active'}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Adding {totalCount} document{totalCount !== 1 ? 's' : ''} to <span className="font-medium text-slate-700">{boxName}</span>. Files will be ready for querying once indexed.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-900 hover:bg-slate-100 p-1.5 rounded-lg transition-colors" aria-label="Close dialog">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 bg-white max-h-[calc(85vh-150px)] overflow-y-auto">
          {/* Batch Progress Summary */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-3">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium text-slate-700">Overall Batch Progress:</span>
                <span className="font-semibold text-indigo-600">{completedCount} of {totalCount} files complete</span>
                <span className="text-[11px] font-mono text-slate-500">({overallProgress}%)</span>
              </div>
              {!allDone && (
                <div className="flex items-center gap-1.5 text-slate-500 text-xs font-mono">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Processing...</span>
                </div>
              )}
            </div>
            {/* Progress Bar */}
            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ease-out ${allDone ? 'bg-emerald-500' : 'bg-indigo-600'}`}
                style={{ width: `${overallProgress}%` }}
              />
            </div>
            {/* Privacy Badge */}
            <div className="flex items-center gap-2 pt-0.5">
              <Lock className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-xs text-slate-500">
                Documents are processed securely with zero-retention privacy and AES-256 vector encryption.
              </span>
            </div>
          </div>

          {/* File Processing List */}
          <div className="space-y-3" role="list">
            {files.map((file) => (
              <div
                key={file.filename}
                className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-colors flex items-center justify-between gap-4"
                role="listitem"
              >
                {/* File Info */}
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 border ${
                    file.status === 'ready' ? 'bg-emerald-50 border-emerald-200 text-emerald-600' :
                    file.status === 'failed' ? 'bg-red-50 border-red-200 text-red-500' :
                    file.status === 'queued' ? 'bg-slate-50 border-slate-200 text-slate-400' :
                    'bg-indigo-50 border-indigo-100 text-indigo-600'
                  }`}>
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900 truncate">
                      {file.filename}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[11px] font-mono text-slate-400">{formatFileSize(file.size)}</span>
                      <span className="text-slate-300 text-xs">•</span>
                      <span className="text-xs text-slate-500">{file.statusMessage || statusMessages[file.status]}</span>
                    </div>
                  </div>
                </div>

                {/* Status Cluster */}
                <div className="flex items-center gap-3 shrink-0">
                  {/* Status Indicator */}
                  {file.status === 'processing' || file.status === 'indexing' ? (
                    <div className="flex items-center gap-2.5">
                      <CircularProgress progress={file.progress} color="text-indigo-600" />
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-600 border border-indigo-100">
                        {file.status === 'processing' ? 'Processing' : 'Indexing'}
                      </span>
                    </div>
                  ) : file.status === 'ready' ? (
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-700">
                        <Check className="w-4 h-4" />
                      </div>
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                        Ready
                      </span>
                    </div>
                  ) : file.status === 'failed' ? (
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-red-100 flex items-center justify-center text-red-600">
                        <X className="w-4 h-4" />
                      </div>
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-600 border border-red-200">
                        Failed
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                        <Clock className="w-3.5 h-3.5" />
                      </div>
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-50 text-slate-500 border border-slate-200">
                        Queued
                      </span>
                    </div>
                  )}

                  {/* Remove button — only for non-ready items */}
                  {file.status !== 'ready' ? (
                    <button
                      onClick={() => onRemoveFile(file.filename)}
                      className="text-slate-400 hover:text-red-500 hover:bg-red-50 p-1 rounded-lg transition-colors"
                      aria-label={`Remove ${file.filename}`}
                    >
                      <X size={16} />
                    </button>
                  ) : (
                    <div className="w-7 h-7 flex items-center justify-center">
                      <Check className="w-4 h-4 text-emerald-500" />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex flex-col sm:flex-row items-center justify-between gap-3">
          {/* Reassuring hint */}
          <div className="flex items-center gap-2 text-slate-500 text-xs">
            <Info className="w-4 h-4" />
            <span>Processing runs in background. You can safely minimize.</span>
          </div>
          {/* Action Buttons */}
          <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
            <button
              onClick={onCancelAll}
              className="w-full sm:w-auto px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-white hover:border-slate-300 transition-colors"
            >
              Cancel Batch Upload
            </button>
            <button
              onClick={onClose}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium shadow-sm hover:bg-indigo-700 transition-colors"
            >
              <span>Continue in Background</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
