import { create } from 'zustand'
import {
  queryAssistant,
  type AssistantQueryResponse,
  type CitationSchema,
  type ContextTurn,
} from '../api/assistant'

const MAX_CONTEXT_TURNS = 12

export interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface AssistantState {
  messages: Message[]
  citations: CitationSchema[]
  suggestedQuestions: string[]
  loading: boolean
  error: string | null
  send: (message: string) => Promise<void>
  reset: () => void
}

export const useAssistantStore = create<AssistantState>((set, get) => ({
  messages: [],
  citations: [],
  suggestedQuestions: [],
  loading: false,
  error: null,

  send: async (message: string) => {
    if (get().loading) return

    const userMessage: Message = { role: 'user', content: message }
    set((s) => ({
      messages: [...s.messages, userMessage],
      loading: true,
      error: null,
    }))

    const context: ContextTurn[] = get()
      .messages.slice(-MAX_CONTEXT_TURNS)
      .map((m) => ({ role: m.role, content: m.content }))

    try {
      const response: AssistantQueryResponse = await queryAssistant(
        message,
        context,
      )
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.answer,
      }
      set((s) => ({
        messages: [...s.messages, assistantMessage],
        citations: response.citations,
        suggestedQuestions: response.suggested_questions,
        loading: false,
      }))
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'An error occurred'
      set({ error: errorMessage, loading: false })
    }
  },

  reset: () =>
    set({
      messages: [],
      citations: [],
      suggestedQuestions: [],
      loading: false,
      error: null,
    }),
}))
