import apiClient from './client'

export interface ContextTurn {
  role: string
  content: string
}

export interface CitationSchema {
  source_title: string
  document_id: string
  chunk_id: string
  section: string | null
  page_number: number | null
  excerpt: string
  score: number
}

export interface GraphNodeSchema {
  id: string
  type: string
  label: string
  status: string | null
  status_category: string | null
}

export interface GraphEdgeSchema {
  source: string
  target: string
  relationship: string
}

export interface GraphSchema {
  nodes: GraphNodeSchema[]
  edges: GraphEdgeSchema[]
  highlighted_path: string[]
}

export interface AssistantQueryResponse {
  intent: string
  answer: string
  graph: GraphSchema | null
  citations: CitationSchema[]
  suggested_questions: string[]
}

export async function queryAssistant(
  message: string,
  context: ContextTurn[] = [],
): Promise<AssistantQueryResponse> {
  const { data } = await apiClient.post<AssistantQueryResponse>(
    '/api/v1/assistant/query',
    { message, context },
  )
  return data
}
