export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export type QualityIssueType =
  | 'high_complexity'
  | 'long_function'
  | 'deep_nesting'
  | 'duplicate_code'
  | 'unused_import'
  | 'todo_comment'

export interface QualityIssue {
  id: string
  analysis_id: string
  project_id: string
  issue_type: QualityIssueType | string
  severity: SeverityLevel
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

export interface QualityMetrics {
  avg_complexity: number
  max_complexity: number
  avg_function_length: number
  max_function_length: number
  total_functions: number
  total_classes: number
  duplicate_blocks_count: number
  todo_comments_count: number
  unused_imports_count: number
  files_analyzed: number
  files_skipped: number
  unparseable_files: number
}

export interface QualityAnalysis {
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
  metrics: QualityMetrics
  error_message: string | null
}

export interface SnippetLine {
  line_number: number
  content: string
  is_highlighted: boolean
}

export interface CodeSnippet {
  file_path: string
  start_line: number
  end_line: number
  target_line: number
  lines: SnippetLine[]
}
