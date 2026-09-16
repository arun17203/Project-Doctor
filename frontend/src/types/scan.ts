export interface DiscoveredFile {
  id: string
  file_path: string
  file_name: string
  extension: string
  language: string
  category: string
  size_bytes: number
  total_lines: number
  code_lines: number
  blank_lines: number
  comment_lines: number
  is_binary: boolean
  is_test: boolean
  is_config: boolean
  is_doc: boolean
  is_skipped: boolean
  created_at: string
}

export interface LanguageStat {
  files: number
  lines: number
  code_lines: number
  blank_lines: number
  comment_lines: number
  percentage: number
}

export interface DirectoryNode {
  name: string
  path: string
  type: 'directory' | 'file'
  size_bytes?: number
  language?: string
  category?: string
  lines?: number
  code_lines?: number
  children?: DirectoryNode[]
}

export interface ScanResult {
  id: string
  project_id: string
  total_files: number
  total_directories: number
  total_lines: number
  total_code_lines: number
  total_blank_lines: number
  total_comment_lines: number
  test_files_count: number
  config_files_count: number
  doc_files_count: number
  languages_summary: Record<string, LanguageStat>
  categories_summary: Record<string, number>
  directory_tree: DirectoryNode
  status: string
  scanned_at: string
}
