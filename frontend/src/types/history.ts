export interface SnapshotSummary {
  id: string
  project_id: string
  version_number: number
  status: string
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
  total_issues: number
  total_files: number
  total_lines: number
  created_at: string
  summary?: string | null
}

export interface FileManifestEntry {
  path: string
  lines: number
}

export interface SnapshotDetail extends SnapshotSummary {
  repository_scan_id?: string | null
  quality_analysis_id?: string | null
  security_analysis_id?: string | null
  dependency_analysis_id?: string | null
  architecture_analysis_id?: string | null
  health_analysis_id?: string | null

  critical_security_count: number
  high_security_count: number
  high_complexity_count: number
  long_functions_count: number
  duplicate_blocks_count: number
  total_dependencies: number
  vulnerable_dependencies_count: number
  outdated_dependencies_count: number
  architecture_nodes_count: number
  architecture_edges_count: number
  architecture_cycles_count: number

  file_manifest: FileManifestEntry[]
}

export interface HistoryListResponse {
  items: SnapshotSummary[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MetricDelta {
  metric_name: string
  from_value: number
  to_value: number
  difference: number
  direction: 'IMPROVED' | 'WORSENED' | 'UNCHANGED'
  unit: string
}

export interface FileDiffSummary {
  files_added: number
  files_removed: number
  files_modified: number
  total_files_before: number
  total_files_after: number
  sample_added: string[]
  sample_removed: string[]
}

export interface VersionComparisonResponse {
  project_id: string
  from_version: number
  to_version: number
  from_created_at: string
  to_created_at: string

  health_delta: MetricDelta
  security_delta: MetricDelta
  quality_delta: MetricDelta
  dependency_delta: MetricDelta
  architecture_delta: MetricDelta
  maintainability_delta: MetricDelta
  testing_delta: MetricDelta

  technical_debt_delta: MetricDelta

  critical_issues_delta: MetricDelta
  high_issues_delta: MetricDelta
  medium_issues_delta: MetricDelta
  low_issues_delta: MetricDelta
  total_issues_delta: MetricDelta

  vulnerable_deps_delta: MetricDelta
  outdated_deps_delta: MetricDelta
  complexity_delta: MetricDelta
  cycles_delta: MetricDelta

  file_diff: FileDiffSummary
  summary_headline: string
  summary_text: string
}
