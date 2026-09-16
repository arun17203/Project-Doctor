export interface SourceCitation {
  file_path: string
  line_start?: number | null
  line_end?: number | null
  reason?: string | null
}

export interface ChatMessageInput {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: SourceCitation[]
  timestamp: string
  isError?: boolean
  isLoading?: boolean
}

export interface CodebaseQARequest {
  question: string
  conversation?: ChatMessageInput[]
}

export interface CodebaseQAResponse {
  answer: string
  sources: SourceCitation[]
  project_id: string
  provider: string
  model: string
  available: boolean
  error_message?: string | null
}
