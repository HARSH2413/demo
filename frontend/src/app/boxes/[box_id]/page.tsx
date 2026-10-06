import { redirect } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { API_URL } from '@/lib/config'
import SecureBrainDashboard from '@/app/workspace/chat/ChatDashboard'

export default async function BoxChatPage({ params }: { params: Promise<{ box_id: string }> }) {
  const supabase = await createClient()
  
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session || !session.access_token) {
      redirect('/login')
  }

  const { box_id: boxId } = await params;

  // Fetch the box using the backend API
  let box = null;
  let errorDetails = null;
  let statusCode = null;

  try {
      const res = await fetch(`${API_URL}/api/v1/boxes/${boxId}`, {
          headers: {
              'Authorization': `Bearer ${session.access_token}`
          },
          cache: 'no-store'
      });
      
      statusCode = res.status;
      
      if (res.ok) {
          const json = await res.json();
          box = json.data;
      } else {
          errorDetails = await res.text();
          console.error(`Box fetch failed: ${res.status} ${res.statusText} - ${errorDetails}`);
      }
  } catch (err) {
      console.error("Network Error fetching box:", err);
      errorDetails = String(err);
  }

  if (!box) {
      // Box doesn't exist or user doesn't have access
      return (
        <div className="flex h-full items-center justify-center bg-slate-50 text-center">
            <div>
                <h1 className="text-2xl font-bold text-slate-800 mb-2">
                    {statusCode === 404 ? "Box Not Found" : "Unable to Load Box"}
                </h1>
                <p className="text-slate-500 mb-6">
                    {statusCode === 404 
                        ? "The box you are looking for does not exist or you do not have permission to access it."
                        : `We encountered a server error while loading this box (HTTP ${statusCode || 'Unknown'}). Please try again later.`}
                </p>
                <Link href="/boxes" className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors">
                    Back to Boxes
                </Link>
            </div>
        </div>
      )
  }

  return (
    <SecureBrainDashboard boxId={boxId} boxName={box.name} />
  )
}
