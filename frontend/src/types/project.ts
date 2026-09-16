export type ProjectStatus = 'CREATED' | 'UPLOADING' | 'CLONING' | 'PROCESSING' | 'READY' | 'FAILED'

export interface Project {
  id: string
  user_id: string
  name: string
  description: string | null
  source_type: 'zip' | 'github'
  source_url: string | null
  original_filename: string | null
  status: ProjectStatus
  created_at: string
  updated_at: string
}

export interface ProjectCreatePayload {
  name: string
  description?: string
  source_type: 'zip' | 'github'
  source_url?: string
}
