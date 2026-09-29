import { API_URL } from '@/lib/config';
import { createClient } from '@/lib/supabase/client';

export class ApiError extends Error {
  status: number;
  detail: any;
  constructor(status: number, detail: any, message: string) {
    super(message);
    this.status = status;
    this.detail = detail;
    this.name = 'ApiError';
  }
}

export async function apiFetch<T = any>(path: string, options?: RequestInit, isRetry = false): Promise<T> {
  const supabase = createClient();
  let { data: { session } } = await supabase.auth.getSession();
  
  if (isRetry) {
    const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession();
    if (refreshError || !refreshData.session) {
      if (typeof window !== 'undefined') window.location.href = '/login';
      return new Promise(() => {}) as Promise<T>;
    }
    session = refreshData.session;
  }
  
  const fetchHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (options?.headers) {
    if (options.headers instanceof Headers) {
      options.headers.forEach((value, key) => { fetchHeaders[key] = value; });
    } else {
      Object.assign(fetchHeaders, options.headers as Record<string, string>);
    }
  }
  
  if (session?.access_token) {
    fetchHeaders['Authorization'] = `Bearer ${session.access_token}`;
  }

  // If body is FormData, let the browser automatically set Content-Type with boundary
  if (options?.body instanceof FormData) {
    delete fetchHeaders['Content-Type'];
    delete fetchHeaders['content-type'];
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: fetchHeaders
  });
  
  if (!res.ok) {
    if (res.status === 401 && !isRetry) {
      return apiFetch<T>(path, options, true);
    } else if (res.status === 401) {
      if (typeof window !== 'undefined') window.location.href = '/login';
      return new Promise(() => {}) as Promise<T>;
    }
    
    if (res.status === 403) {
      throw new ApiError(res.status, "Access denied.", "Access denied.");
    }
    
    const data = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, data.detail, data.detail || `HTTP ${res.status}`);
  }
  
  return res.json();
}
