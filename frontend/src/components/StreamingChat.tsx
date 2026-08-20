/**
 * Real-time Streaming Chat Component
 * Shows answer as tokens arrive (1-2s instead of 10-12s)
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { API_URL } from '@/lib/config';

interface Citation {
  filename: string;
  content: string;
  rerank_score: number;
}

interface StreamingChatProps {
  sessionId: string;
  tenantId: string;
}

export function StreamingChat({ sessionId, tenantId }: StreamingChatProps) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const answerEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom as answer streams in
  useEffect(() => {
    answerEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [answer]);

  const handleStream = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setAnswer('');
    setCitations([]);
    setError('');
    setProgress(0);
    setStatus('Retrieving documents...');

    try {
      // Call the /stream endpoint
      const response = await fetch(`${API_URL}/api/v1/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question,
          tenant_id: tenantId,
          session_id: sessionId,
          use_streaming: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';
      let currentAnswer = '';
      let eventType = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        // Decode chunk and append to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines[lines.length - 1]; // Keep incomplete line in buffer

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i];

          // Parse SSE format
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const data = JSON.parse(dataStr);

              if (eventType === 'status') {
                setStatus(data.msg || '');
                setProgress(data.percent || 0);
              } else if (eventType === 'token') {
                // Stream individual tokens
                currentAnswer += data.token;
                setAnswer(currentAnswer);
              } else if (eventType === 'metadata') {
                // Receive citations and metadata at end
                if (data.citations) {
                  setCitations(data.citations);
                }
                setProgress(data.percent || 100);
              } else if (eventType === 'error') {
                setError(data.error || 'Unknown error');
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e, dataStr);
            }
          }
        }
      }

      setStatus('');
      setProgress(100);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred';
      setError(message);
      console.error('Streaming error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 h-full">
      {/* Chat Input */}
      <form onSubmit={handleStream} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Loading...' : 'Send'}
        </button>
      </form>

      {/* Progress Bar */}
      {loading && progress > 0 && (
        <div className="w-full bg-gray-200 rounded-lg overflow-hidden">
          <div
            className="bg-blue-600 h-2 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Status */}
      {status && (
        <div className="text-sm text-gray-600 italic">
          {status}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Answer (Streaming in Real-time) */}
      {answer && (
        <div className="flex-1 overflow-y-auto border rounded-lg p-4 bg-gray-50">
          <div className="prose prose-sm max-w-none">
            {/* Simple markdown rendering */}
            {answer.split('\n').map((line, i) => {
              // Bold **text**
              const boldRegex = /\*\*(.+?)\*\*/g;
              const parts = line.split(boldRegex).map((part, j) =>
                j % 2 === 1 ? <strong key={j}>{part}</strong> : part
              );

              // Heading detection (though streaming may split across boundaries)
              if (line.startsWith('## ')) {
                return (
                  <h3 key={i} className="text-lg font-bold mt-3 mb-2">
                    {line.slice(3)}{parts}
                  </h3>
                );
              } else if (line.startsWith('- ')) {
                return (
                  <li key={i} className="ml-4">
                    {parts}
                  </li>
                );
              } else if (line.trim() === '') {
                return <div key={i} className="h-2" />;
              } else {
                return (
                  <p key={i} className="my-1">
                    {parts}
                  </p>
                );
              }
            })}
            <div ref={answerEndRef} />
          </div>
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="font-bold mb-2">Sources:</h4>
          <div className="space-y-2">
            {citations.map((cite, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded border-l-4 border-blue-500">
                <div className="font-semibold text-sm text-gray-800">
                  {cite.filename}
                  {cite.rerank_score && (
                    <span className="text-gray-500 ml-2">
                      (relevance: {cite.rerank_score.toFixed(2)})
                    </span>
                  )}
                </div>
                <div className="text-sm text-gray-600 mt-1 line-clamp-2">
                  {cite.content.slice(0, 200)}...
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
