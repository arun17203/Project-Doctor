export type DependencyStatus = 'CURRENT' | 'OUTDATED' | 'VULNERABLE' | 'UNKNOWN'
export type DependencyType = 'direct' | 'dev' | 'transitive' | 'peer' | string

export interface VulnerabilityAdvisory {
  id: string
  severity: string
  affected_versions?: string | null
  fixed_version?: string | null
  summary?: string | null
  reference_url?: string | null
}

export interface ProjectDependency {
  id: string
  analysis_id: string
  project_id: string
  manifest_file: string
  ecosystem: string
  name: string
  declared_version?: string | null
  resolved_version?: string | null
  dependency_type: DependencyType
  latest_version?: string | null
  status: DependencyStatus
  vulnerability_count: number
  advisories: VulnerabilityAdvisory[]
  created_at: string
}

export interface DependencyIssue {
  id: string
  analysis_id: string
  project_id: string
  dependency_id?: string | null
  category: string
  issue_type: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  package_name: string
  manifest_file: string
  version: string
  vulnerability_id?: string | null
  description: string
  recommendation?: string | null
  created_at: string
}

export interface DependencyMetrics {
  manifests_scanned?: string[]
  by_ecosystem?: Record<string, number>
  network_warning?: boolean
}

export interface DependencyAnalysis {
  id: string
  project_id: string
  scan_id: string
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
  started_at: string
  completed_at?: string | null
  total_dependencies: number
  direct_dependencies: number
  transitive_dependencies: number
  current_count: number
  outdated_count: number
  vulnerable_count: number
  unknown_count: number
  metrics: DependencyMetrics
  error_message?: string | null
}

export interface DependencySummary {
  analysis_id: string
  status: string
  total_dependencies: number
  direct_dependencies: number
  transitive_dependencies: number
  current_count: number
  outdated_count: number
  vulnerable_count: number
  unknown_count: number
  manifests: string[]
  by_ecosystem: Record<string, number>
  network_warning: boolean
  completed_at?: string | null
}
