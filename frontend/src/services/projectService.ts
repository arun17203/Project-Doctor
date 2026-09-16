import { api } from './api'
import type { Project, ProjectCreatePayload } from '../types/project'
import type { ScanResult, DirectoryNode, DiscoveredFile } from '../types/scan'
import type { QualityAnalysis, QualityIssue, CodeSnippet } from '../types/quality'
import type { SecurityAnalysis, SecurityIssue, SecurityCodeSnippet } from '../types/security'
import type {
  DependencyAnalysis,
  ProjectDependency,
  DependencyIssue,
  DependencySummary,
} from '../types/dependency'
import type {
  ArchitectureAnalysis,
  ArchitectureNode,
  ArchitectureEdge,
  ArchitectureCycle,
  ArchitectureGraphData,
} from '../types/architecture'
import type { HealthAnalysis } from '../types/health'
import type { AIExplanation, ExplainIssueRequest } from '../types/ai'
import type { CodebaseQARequest, CodebaseQAResponse } from '../types/qa'
import type {
  HistoryListResponse,
  SnapshotDetail,
  VersionComparisonResponse,
} from '../types/history'
import type { DoctorPrescription } from '../types/remediation'

export const projectService = {
  async createProject(payload: ProjectCreatePayload): Promise<Project> {
    const response = await api.post<Project>('/projects', payload)
    return response.data
  },

  async getProjects(): Promise<Project[]> {
    const response = await api.get<Project[]>('/projects')
    return response.data
  },

  async getProject(projectId: string): Promise<Project> {
    const response = await api.get<Project>(`/projects/${projectId}`)
    return response.data
  },

  async uploadZip(
    projectId: string,
    file: File,
    onUploadProgress?: (progressEvent: any) => void
  ): Promise<Project> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post<Project>(`/projects/${projectId}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    })
    return response.data
  },

  async importGitHub(projectId: string, githubUrl: string): Promise<Project> {
    const response = await api.post<Project>(`/projects/${projectId}/github`, {
      github_url: githubUrl,
    })
    return response.data
  },

  async deleteProject(projectId: string): Promise<void> {
    await api.delete(`/projects/${projectId}`)
  },

  // Scanner endpoints (Stage 4)
  async scanProject(projectId: string): Promise<ScanResult> {
    const response = await api.post<ScanResult>(`/projects/${projectId}/scan`)
    return response.data
  },

  async getProjectScan(projectId: string): Promise<ScanResult> {
    const response = await api.get<ScanResult>(`/projects/${projectId}/scan`)
    return response.data
  },

  async getProjectTree(projectId: string): Promise<DirectoryNode> {
    const response = await api.get<DirectoryNode>(`/projects/${projectId}/tree`)
    return response.data
  },

  async getProjectFiles(
    projectId: string,
    category?: string,
    language?: string
  ): Promise<DiscoveredFile[]> {
    const params: Record<string, string> = {}
    if (category) params.category = category
    if (language) params.language = language
    const response = await api.get<DiscoveredFile[]>(`/projects/${projectId}/files`, { params })
    return response.data
  },

  async getProjectStatistics(projectId: string): Promise<any> {
    const response = await api.get(`/projects/${projectId}/statistics`)
    return response.data
  },

  async analyzeCodeQuality(projectId: string): Promise<QualityAnalysis> {
    const response = await api.post<QualityAnalysis>(`/projects/${projectId}/analyze/quality`)
    return response.data
  },

  async getLatestQualityAnalysis(projectId: string): Promise<QualityAnalysis> {
    const response = await api.get<QualityAnalysis>(`/projects/${projectId}/quality`)
    return response.data
  },

  async getQualityIssues(
    projectId: string,
    params?: {
      analysis_id?: string
      severity?: string
      issue_type?: string
      file_path?: string
      limit?: number
      offset?: number
    }
  ): Promise<QualityIssue[]> {
    const response = await api.get<QualityIssue[]>(`/projects/${projectId}/quality/issues`, {
      params,
    })
    return response.data
  },

  async getCodeSnippet(
    projectId: string,
    filePath: string,
    lineNumber: number,
    window?: number
  ): Promise<CodeSnippet> {
    const response = await api.get<CodeSnippet>(`/projects/${projectId}/quality/snippet`, {
      params: {
        file_path: filePath,
        line_number: lineNumber,
        window: window || 5,
      },
    })
    return response.data
  },

  async analyzeSecurity(projectId: string): Promise<SecurityAnalysis> {
    const response = await api.post<SecurityAnalysis>(`/projects/${projectId}/analyze/security`)
    return response.data
  },

  async getLatestSecurityAnalysis(projectId: string): Promise<SecurityAnalysis> {
    const response = await api.get<SecurityAnalysis>(`/projects/${projectId}/security`)
    return response.data
  },

  async getSecurityIssues(
    projectId: string,
    params?: {
      analysis_id?: string
      severity?: string
      category?: string
      issue_type?: string
      file_path?: string
      limit?: number
      offset?: number
    }
  ): Promise<SecurityIssue[]> {
    const response = await api.get<SecurityIssue[]>(`/projects/${projectId}/security/issues`, {
      params,
    })
    return response.data
  },

  async getSecuritySnippet(
    projectId: string,
    filePath: string,
    lineNumber: number,
    window?: number
  ): Promise<SecurityCodeSnippet> {
    const response = await api.get<SecurityCodeSnippet>(`/projects/${projectId}/security/snippet`, {
      params: {
        file_path: filePath,
        line_number: lineNumber,
        window: window || 5,
      },
    })
    return response.data
  },

  async analyzeDependencies(projectId: string): Promise<DependencyAnalysis> {
    const response = await api.post<DependencyAnalysis>(`/projects/${projectId}/analyze/dependencies`)
    return response.data
  },

  async getLatestDependencyAnalysis(projectId: string): Promise<DependencyAnalysis> {
    const response = await api.get<DependencyAnalysis>(`/projects/${projectId}/dependency-analysis`)
    return response.data
  },

  async getDependencySummary(projectId: string, analysisId?: string): Promise<DependencySummary> {
    const response = await api.get<DependencySummary>(`/projects/${projectId}/dependencies/summary`, {
      params: analysisId ? { analysis_id: analysisId } : undefined,
    })
    return response.data
  },

  async getProjectDependencies(
    projectId: string,
    params?: {
      analysis_id?: string
      status?: string
      ecosystem?: string
      dependency_type?: string
      manifest_file?: string
      search?: string
      limit?: number
      offset?: number
    }
  ): Promise<ProjectDependency[]> {
    const response = await api.get<ProjectDependency[]>(`/projects/${projectId}/dependencies`, {
      params,
    })
    return response.data
  },

  async getDependencyIssues(
    projectId: string,
    params?: {
      analysis_id?: string
      severity?: string
      issue_type?: string
      limit?: number
      offset?: number
    }
  ): Promise<DependencyIssue[]> {
    const response = await api.get<DependencyIssue[]>(`/projects/${projectId}/dependencies/issues`, {
      params,
    })
    return response.data
  },

  async getDependencyDetail(projectId: string, dependencyId: string): Promise<ProjectDependency> {
    const response = await api.get<ProjectDependency>(`/projects/${projectId}/dependencies/${dependencyId}`)
    return response.data
  },

  async analyzeArchitecture(projectId: string): Promise<ArchitectureAnalysis> {
    const response = await api.post<ArchitectureAnalysis>(`/projects/${projectId}/analyze/architecture`)
    return response.data
  },

  async getLatestArchitectureAnalysis(projectId: string): Promise<ArchitectureAnalysis> {
    const response = await api.get<ArchitectureAnalysis>(`/projects/${projectId}/architecture`)
    return response.data
  },

  async getArchitectureNodes(
    projectId: string,
    params?: {
      analysis_id?: string
      layer?: string
      search?: string
      limit?: number
      offset?: number
    }
  ): Promise<ArchitectureNode[]> {
    const response = await api.get<ArchitectureNode[]>(`/projects/${projectId}/architecture/nodes`, {
      params,
    })
    return response.data
  },

  async getArchitectureEdges(
    projectId: string,
    params?: {
      analysis_id?: string
      circular_only?: boolean
      limit?: number
      offset?: number
    }
  ): Promise<ArchitectureEdge[]> {
    const response = await api.get<ArchitectureEdge[]>(`/projects/${projectId}/architecture/edges`, {
      params,
    })
    return response.data
  },

  async getArchitectureCycles(projectId: string, analysisId?: string): Promise<ArchitectureCycle[]> {
    const response = await api.get<ArchitectureCycle[]>(`/projects/${projectId}/architecture/cycles`, {
      params: analysisId ? { analysis_id: analysisId } : undefined,
    })
    return response.data
  },

  async getArchitectureGraph(projectId: string, analysisId?: string): Promise<ArchitectureGraphData> {
    const response = await api.get<ArchitectureGraphData>(`/projects/${projectId}/architecture/graph`, {
      params: analysisId ? { analysis_id: analysisId } : undefined,
    })
    return response.data
  },

  async analyzeHealth(projectId: string): Promise<HealthAnalysis> {
    const response = await api.post<HealthAnalysis>(`/projects/${projectId}/analyze/health`)
    return response.data
  },

  async getLatestHealthAnalysis(projectId: string): Promise<HealthAnalysis> {
    const response = await api.get<HealthAnalysis>(`/projects/${projectId}/health`)
    return response.data
  },

  async getHealthHistory(projectId: string, limit?: number): Promise<HealthAnalysis[]> {
    const response = await api.get<HealthAnalysis[]>(`/projects/${projectId}/health/history`, {
      params: limit ? { limit } : undefined,
    })
    return response.data
  },

  async explainIssue(issueId: string, forceRegenerate: boolean = false): Promise<AIExplanation> {
    const response = await api.post<AIExplanation>(`/issues/${issueId}/explain`, {
      force_regenerate: forceRegenerate,
    })
    return response.data
  },

  async getIssueExplanation(issueId: string): Promise<AIExplanation> {
    const response = await api.get<AIExplanation>(`/issues/${issueId}/explanation`)
    return response.data
  },

  async regenerateIssueExplanation(issueId: string): Promise<AIExplanation> {
    const response = await api.post<AIExplanation>(`/issues/${issueId}/explanation/regenerate`)
    return response.data
  },

  async askCodebase(projectId: string, payload: CodebaseQARequest): Promise<CodebaseQAResponse> {
    const response = await api.post<CodebaseQAResponse>(`/projects/${projectId}/ask`, payload)
    return response.data
  },

  async getAnalysisHistory(
    projectId: string,
    page: number = 1,
    pageSize: number = 20
  ): Promise<HistoryListResponse> {
    const response = await api.get<HistoryListResponse>(`/projects/${projectId}/history`, {
      params: { page, page_size: pageSize },
    })
    return response.data
  },

  async getSnapshotDetails(projectId: string, version: number): Promise<SnapshotDetail> {
    const response = await api.get<SnapshotDetail>(`/projects/${projectId}/history/${version}`)
    return response.data
  },

  async compareVersions(
    projectId: string,
    fromVersion: number,
    toVersion: number
  ): Promise<VersionComparisonResponse> {
    const response = await api.get<VersionComparisonResponse>(
      `/projects/${projectId}/history/compare`,
      {
        params: { from: fromVersion, to: toVersion },
      }
    )
    return response.data
  },

  async runFullAnalysis(projectId: string, summary?: string): Promise<SnapshotDetail> {
    const response = await api.post<SnapshotDetail>(`/projects/${projectId}/analysis/run`, {
      summary,
    })
    return response.data
  },

  async createSnapshot(projectId: string, summary?: string): Promise<SnapshotDetail> {
    const response = await api.post<SnapshotDetail>(`/projects/${projectId}/snapshots`, {
      summary,
    })
    return response.data
  },

  async getRemediation(projectId: string): Promise<DoctorPrescription> {
    const response = await api.get<DoctorPrescription>(`/projects/${projectId}/remediation`)
    return response.data
  },

  async downloadPatch(projectId: string): Promise<Blob> {
    const response = await api.get(`/projects/${projectId}/remediation/download`, {
      responseType: 'blob',
    })
    return response.data
  },
}
