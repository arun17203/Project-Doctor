export type SecuritySeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
export type SecurityConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW'

export type SecurityIssueType =
  | 'hardcoded_secret'
  | 'sql_injection'
  | 'command_injection'
  | 'dangerous_eval'
  | 'insecure_config'
  | 'weak_crypto'
  | 'insecure_password'

export type SecurityCategory =
  | 'SECRETS'
  | 'INJECTION'
  | 'DANGEROUS_CALLS'
  | 'CONFIGURATION'
  | 'CRYPTO'
  | 'AUTHENTICATION'
  | string

export interface SecurityIssue {
  id: string
  analysis_id: string
  project_id: string
  category: string
  issue_type: SecurityIssueType | string
  severity: SecuritySeverityLevel
  confidence: SecurityConfidenceLevel
  file_path: string
  line_number: number
  end_line: number | null
  symbol_name: string | null
  message: string
  description: string
  evidence: string | null
  recommendation: string | null
  created_at: string
}

export interface SecurityMetrics {
  files_audited: number
  files_skipped: number
  by_category: Record<string, number>
  by_type: Record<string, number>
  by_severity: Record<string, number>
}

export interface SecurityAnalysis {
  id: string
  project_id: string
  scan_id: string
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
  started_at: string
  completed_at: string | null
  total_issues: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  metrics: SecurityMetrics
  error_message: string | null
}

export interface SecuritySnippetLine {
  line_number: number
  content: string
  is_highlighted: boolean
}

export interface SecurityCodeSnippet {
  file_path: string
  start_line: number
  end_line: number
  target_line: number
  lines: SecuritySnippetLine[]
}
