export type HealthStatus = 'Excellent' | 'Good' | 'Fair' | 'Needs Attention' | 'Critical'

export interface FixFirstItem {
  rank: number
  category: 'Security' | 'Code Quality' | 'Dependencies' | 'Architecture' | string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO' | string
  title: string
  location: string
  file_path: string
  line_number?: number | null
  description: string
  recommendation: string
}

export interface TechnicalDebtBreakdown {
  quality_hours: number
  security_hours: number
  dependency_hours: number
  architecture_hours: number
  total_hours: number
}

export interface HealthExplanations {
  summary: string
  why_breakdown: string[]
  category_drivers: Record<string, string[]>
}

export interface HealthAnalysis {
  id: string
  project_id: string
  repository_scan_id: string

  quality_analysis_id?: string | null
  security_analysis_id?: string | null
  dependency_analysis_id?: string | null
  architecture_analysis_id?: string | null

  overall_score: number
  quality_score: number
  security_score: number
  dependency_score: number
  architecture_score: number
  maintainability_score: number
  testing_score: number

  technical_debt_hours: number

  critical_count: number
  high_count: number
  medium_count: number
  low_count: number

  status: HealthStatus | string

  explanations: HealthExplanations
  debt_breakdown: TechnicalDebtBreakdown
  fix_first: FixFirstItem[]
  weights_used: Record<string, number>

  created_at: string
  updated_at: string
}
