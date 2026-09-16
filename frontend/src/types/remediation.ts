export interface RemediationAction {
  id: string
  title: string
  category: 'security' | 'quality' | 'dependency'
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  file_path: string
  line_number: number
  doctor_order: string
  rationale: string
  diff_snippet: string
  estimated_effort_minutes: number
}

export interface DoctorPrescription {
  project_id: string
  project_name: string
  current_health_score: number
  projected_health_score: number
  current_technical_debt_hours: number
  estimated_debt_recovered_hours: number
  total_prescriptions: number
  critical_count: number
  high_count: number
  medium_count: number
  actions: RemediationAction[]
  unified_diff: string
  patch_filename: string
}
