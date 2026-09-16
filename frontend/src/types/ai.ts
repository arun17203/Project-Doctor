export interface AIExplanation {
  id: string
  issue_id: string
  project_id: string
  issue_category: string
  issue_type: string
  provider: string
  model: string
  summary: string
  why_it_matters: string
  potential_impact: string
  recommendation: string
  priority: string
  developer_action: string
  created_at: string
  updated_at: string
  available?: boolean
  error_message?: string
}

export interface ExplainIssueRequest {
  force_regenerate?: boolean
}
