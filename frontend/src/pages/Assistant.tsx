import { useState, useRef, useEffect } from 'react'
import { useAuthStore } from '../store/auth'
import { useAssistantStore } from '../store/assistant'

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

export default function Assistant() {
  const user = useAuthStore((s) => s.user)
  const { messages, loading, error, suggestedQuestions, send, reset } =
    useAssistantStore()

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
    <div className="flex flex-col h-screen max-w-3xl mx-auto px-4 py-6">
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
  )
}
