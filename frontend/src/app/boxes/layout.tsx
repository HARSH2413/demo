import React from 'react';
import { createClient } from '@/lib/supabase/server';
import ShellLayout from '@/components/layout/ShellLayout';

export default async function BoxesLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  const userEmail = user?.email || undefined;
  const userName = user?.user_metadata?.full_name || undefined;

  return (
    <ShellLayout userEmail={userEmail} userName={userName}>
      {children}
    </ShellLayout>
  );
}
