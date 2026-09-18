import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { API_URL } from '@/lib/config'
import SecureBrainDashboard from '@/app/workspace/chat/ChatDashboard'

export default async function BoxChatPage({ params }: { params: { box_id: string } }) {
  const supabase = await createClient()
  
  const { data: { session } } = await supabase.auth.getSession()
  
  if (!session || !session.access_token) {
      redirect('/login')
  }

  const boxId = params.box_id;

  // Fetch the box using the backend API
  let box = null;
  try {
      const res = await fetch(`${API_URL}/api/v1/boxes/${boxId}`, {
          headers: {
              'Authorization': `Bearer ${session.access_token}`
          },
          cache: 'no-store'
      });
      if (res.ok) {
          const json = await res.json();
          box = json.data;
      }
  } catch (err) {
      console.error("Error fetching box:", err);
  }

  if (!box) {
      // Box doesn't exist or user doesn't have access
      return (
        <div className="flex h-screen items-center justify-center bg-slate-50 text-center">
            <div>
                <h1 className="text-2xl font-bold text-slate-800 mb-2">Box Not Found</h1>
                <p className="text-slate-500 mb-6">The box you are looking for does not exist or you do not have permission to access it.</p>
                <a href="/boxes" className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-colors">
                    Back to Boxes
                </a>
            </div>
        </div>
      )
  }

  return (
    <SecureBrainDashboard boxId={boxId} boxName={box.name} />
  )
}
