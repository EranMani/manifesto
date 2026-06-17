import { useState, useRef, useEffect } from 'react'
import { useAuthStore } from '../store/auth'
import { useAssistantStore } from '../store/assistant'
import EvidenceGraph from '../components/EvidenceGraph'
import type { CitationSchema } from '../api/assistant'

const POLICY_PROMPTS = [
  'What does the return policy say?',
  'Summarize the shipping guidelines',
  'What are the employee leave rules?',
]

const LOGISTICS_PROMPTS = [
  'Show open purchase orders',
  'Which shipments are delayed?',
  'Summarize vendor performance this month',
]

function CitationCard({ citation }: { citation: CitationSchema }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 text-sm">
      <p className="font-medium text-gray-900">{citation.source_title}</p>
      <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
        {citation.section && <span>Section: {citation.section}</span>}
        {citation.page_number != null && <span>Page {citation.page_number}</span>}
      </div>
      <p className="mt-2 text-xs leading-relaxed text-gray-600">{citation.excerpt}</p>
    </div>
  )
}

export default function Assistant() {
  const user = useAuthStore((s) => s.user)
  const {
    messages,
    intent,
    graph,
    citations,
    loading,
    error,
    suggestedQuestions,
    send,
    reset,
  } = useAssistantStore()

  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const canSendDisabled = loading || input.trim() === ''
  const isManagerOrAdmin =
    user?.role === 'manager' || user?.role === 'admin'

  const defaultPrompts = isManagerOrAdmin
    ? [...LOGISTICS_PROMPTS, ...POLICY_PROMPTS]
    : POLICY_PROMPTS

  const prompts =
    suggestedQuestions.length > 0 ? suggestedQuestions : defaultPrompts

  const showGraph =
    intent === 'logistics' || intent === 'mixed'
  const showCitations =
    intent === 'policy' || intent === 'mixed'
  const hasEvidence =
    (showGraph && graph && graph.nodes.length > 0) ||
    (showCitations && citations.length > 0)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (canSendDisabled) return
    const text = input.trim()
    setInput('')
    send(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handlePromptClick = (prompt: string) => {
    if (loading) return
    send(prompt)
  }

  return (
    <div className="flex flex-col lg:flex-row h-screen">
      <div className="flex flex-col flex-1 min-w-0 px-4 py-6 max-w-3xl mx-auto w-full">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">Assistant</h1>
          {messages.length > 0 && (
            <button
              onClick={reset}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              New conversation
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto space-y-4 mb-4">
          {messages.length === 0 && !loading && (
            <div className="text-center text-gray-400 mt-16">
              <p className="text-lg mb-6">What can I help you with?</p>
              <div className="flex flex-wrap justify-center gap-2">
                {prompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => handlePromptClick(prompt)}
                    className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-50 text-gray-600"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-4 py-2 rounded-lg whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 text-gray-500 px-4 py-2 rounded-lg">
                Thinking...
              </div>
            </div>
          )}

          {error && (
            <div className="flex justify-start">
              <div className="bg-red-50 text-red-600 px-4 py-2 rounded-lg">
                {error}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {messages.length > 0 && suggestedQuestions.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {suggestedQuestions.map((q) => (
              <button
                key={q}
                onClick={() => handlePromptClick(q)}
                disabled={loading}
                className="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50 text-gray-600 disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            rows={1}
            className="flex-1 border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSend}
            disabled={canSendDisabled}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>

      {hasEvidence && (
        <div className="lg:w-[540px] shrink-0 border-t lg:border-t-0 lg:border-l border-gray-200 overflow-y-auto p-4 bg-gray-50">
          {showGraph && graph && graph.nodes.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Evidence Graph
              </h3>
              <EvidenceGraph graph={graph} />
            </div>
          )}
          {showCitations && citations.length > 0 && (
            <div className={showGraph && graph && graph.nodes.length > 0 ? 'mt-4' : ''}>
              <h3 className="text-sm font-semibold text-gray-700 mb-2">
                Sources
              </h3>
              <div className="space-y-2">
                {citations.map((c, i) => (
                  <CitationCard key={i} citation={c} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
