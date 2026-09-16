export type ArchitectureLayer =
  | 'Presentation'
  | 'API'
  | 'Service'
  | 'Data'
  | 'Utility'
  | 'Configuration'
  | 'Test'
  | 'Unknown'

export interface ArchitectureNodeMetrics {
  in_degree?: number
  out_degree?: number
  degree?: number
  external_imports_count?: number
  is_in_cycle?: boolean
  file_size?: number
  lines_of_code?: number
  [key: string]: any
}

export interface ArchitectureNode {
  id: string
  analysis_id: string
  project_id: string
  file_path: string
  name: string
  language: string
  layer: ArchitectureLayer | string
  node_type: string
  directory: string
  metrics: ArchitectureNodeMetrics
  created_at: string
}

export interface ArchitectureEdge {
  id: string
  analysis_id: string
  project_id: string
  source_node_id: string
  target_node_id: string
  relationship_type: string
  raw_import?: string | null
  is_circular: boolean
  created_at: string
}

export interface ArchitectureAnalysisMetrics {
  total_files_analyzed?: number
  total_edges_found?: number
  isolated_nodes_count?: number
  max_in_degree?: number
  max_out_degree?: number
  layers_breakdown?: Record<string, number>
  [key: string]: any
}

export interface ArchitectureAnalysis {
  id: string
  project_id: string
  scan_id: string
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED'
  started_at: string
  completed_at?: string | null
  node_count: number
  edge_count: number
  cycle_count: number
  metrics: ArchitectureAnalysisMetrics
  error_message?: string | null
}

export interface ArchitectureCycle {
  cycle: string[]
  length: number
}

export interface ArchitectureGraphData {
  analysis: ArchitectureAnalysis
  nodes: ArchitectureNode[]
  edges: ArchitectureEdge[]
  cycles: string[][]
}
