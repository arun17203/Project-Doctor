import React, { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  FileArchive,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Clock,
  Trash2,
  ShieldCheck,
  HardDrive,
  Loader2,
  ExternalLink,
  Code2,
  FolderTree,
  FileCheck2,
  FileCog,
  FileText,
  FileCode,
  RefreshCw,
  Layers,
  Flame,
  AlertTriangle,
  Info,
  SlidersHorizontal,
  ShieldAlert,
  KeyRound,
  Lock,
  Terminal,
  Cpu,
  Settings,
  Hash,
  Boxes,
  Network,
  HeartPulse,
  Sparkles,
  TrendingUp,
  Stethoscope,
} from 'lucide-react'
import { projectService } from '../services/projectService'
import FileExplorer from '../components/scanner/FileExplorer'
import IssueExplorer from '../components/quality/IssueExplorer'
import SecurityIssueExplorer from '../components/security/SecurityIssueExplorer'
import DependencyDashboard from '../components/dependency/DependencyDashboard'
import { ArchitectureGraph } from '../components/architecture/ArchitectureGraph'
import HealthDashboard from '../components/health/HealthDashboard'
import { AskCodebase } from '../components/qa/AskCodebase'
import HistoryDashboard from '../components/history/HistoryDashboard'
import { PrescriptionDashboard } from '../components/remediation/PrescriptionDashboard'
import { DiagnosticReportModal } from '../components/health/DiagnosticReportModal'
import { AppShell } from '../components/layout/AppShell'
import { StatusBadge } from '../components/common/StatusBadge'
import { useToast } from '../context/ToastContext'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import type { Project } from '../types/project'
import type { ScanResult } from '../types/scan'
import type { QualityAnalysis, QualityIssue } from '../types/quality'
import type { SecurityAnalysis, SecurityIssue } from '../types/security'
import type { DependencyAnalysis, ProjectDependency } from '../types/dependency'
import type { ArchitectureAnalysis, ArchitectureGraphData } from '../types/architecture'
import type { HealthAnalysis } from '../types/health'

const TAB_LABELS: Record<string, string> = {
  health: 'Health & Diagnostics',
  prescription: "Doctor's Prescription",
  scanner: 'Repository Structure',
  quality: 'Code Quality',
  security: 'Security Audit',
  dependencies: 'Dependencies',
  architecture: 'Architecture',
  qa: 'Ask My Codebase',
  history: 'History & Trends',
}

// Color map for programming languages
const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3572A5',
  JavaScript: '#f1e05a',
  TypeScript: '#3178c6',
  Java: '#b07219',
  C: '#555555',
  'C++': '#f34b7d',
  'C#': '#178600',
  Go: '#00ADD8',
  PHP: '#4F5D95',
  Ruby: '#701516',
  HTML: '#e34c26',
  CSS: '#563d7c',
  SCSS: '#c6538c',
  SQL: '#e38c00',
  Rust: '#dea584',
  Markdown: '#083fa1',
  Shell: '#89e051',
  Other: '#64748b',
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [scan, setScan] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Scanner execution state
  const [scanning, setScanning] = useState(false)
  const [scanStepIndex, setScanStepIndex] = useState(0)
  const [scanError, setScanError] = useState<string | null>(null)

  // Stage 13 UI state
  const [activeTab, setActiveTab] = useState<'health' | 'prescription' | 'scanner' | 'quality' | 'security' | 'dependencies' | 'architecture' | 'qa' | 'history'>('health')
  const [showAuditModal, setShowAuditModal] = useState(false)
  useDocumentTitle('Project Doctor', project ? `${project.name} · ${TAB_LABELS[activeTab] || 'Diagnostics'}` : 'Project Diagnostics')
  const { success, error: toastError, info } = useToast()
  const [runningFullAnalysis, setRunningFullAnalysis] = useState(false)
  const [fullAnalysisStage, setFullAnalysisStage] = useState('')

  // Stage 5 Code Quality Analyzer state
  const [qualityAnalysis, setQualityAnalysis] = useState<QualityAnalysis | null>(null)
  const [qualityIssues, setQualityIssues] = useState<QualityIssue[]>([])
  const [analyzingQuality, setAnalyzingQuality] = useState(false)
  const [qualityStepIndex, setQualityStepIndex] = useState(0)
  const [qualityError, setQualityError] = useState<string | null>(null)

  // Stage 6 Security Audit Engine state
  const [securityAnalysis, setSecurityAnalysis] = useState<SecurityAnalysis | null>(null)
  const [securityIssues, setSecurityIssues] = useState<SecurityIssue[]>([])
  const [analyzingSecurity, setAnalyzingSecurity] = useState(false)
  const [securityStepIndex, setSecurityStepIndex] = useState(0)
  const [securityError, setSecurityError] = useState<string | null>(null)

  // Stage 7 Dependency Analyzer state
  const [dependencyAnalysis, setDependencyAnalysis] = useState<DependencyAnalysis | null>(null)
  const [dependenciesList, setDependenciesList] = useState<ProjectDependency[]>([])
  const [analyzingDependencies, setAnalyzingDependencies] = useState(false)
  const [dependencyStepIndex, setDependencyStepIndex] = useState(0)
  const [dependencyError, setDependencyError] = useState<string | null>(null)

  // Stage 8 Architecture Graph state
  const [architectureAnalysis, setArchitectureAnalysis] = useState<ArchitectureAnalysis | null>(null)
  const [architectureGraphData, setArchitectureGraphData] = useState<ArchitectureGraphData | null>(null)
  const [analyzingArchitecture, setAnalyzingArchitecture] = useState(false)
  const [architectureStepIndex, setArchitectureStepIndex] = useState(0)
  const [architectureError, setArchitectureError] = useState<string | null>(null)

  // Stage 9 Health & Technical Debt Engine state
  const [healthAnalysis, setHealthAnalysis] = useState<HealthAnalysis | null>(null)
  const [analyzingHealth, setAnalyzingHealth] = useState(false)
  const [healthStepIndex, setHealthStepIndex] = useState(0)
  const [healthError, setHealthError] = useState<string | null>(null)

  // Delete modal state
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const scanStages = [
    'Discovering project files & directory hierarchy...',
    'Detecting programming languages & file extensions...',
    'Counting source, code, blank, and comment lines...',
    'Categorizing files (source, tests, configs, docs)...',
    'Building hierarchical directory tree...',
    'Persisting telemetry to database...'
  ]

  const qualityStages = [
    'Preparing static analysis engine & environment...',
    'Parsing Python AST & JS/TS structural tokens...',
    'Calculating McCabe cyclomatic complexity per function...',
    'Analyzing function line lengths & control-flow nesting...',
    'Detecting cross-file duplicate code blocks...',
    'Scanning for unused imports & technical debt comments...',
    'Persisting real quality findings & metrics to database...'
  ]

  const securityStages = [
    'Initializing static security rule engine & sandboxed parser...',
    'Scanning for hardcoded API keys, private keys & cloud credentials...',
    'Inspecting SQL AST nodes for unparameterized injection vulnerabilities...',
    'Detecting arbitrary operating system command execution & subshells...',
    'Auditing dangerous dynamic code execution (eval, exec, Function)...',
    'Reviewing insecure configurations (DEBUG flags, disabled SSL, wildcard CORS)...',
    'Auditing cryptographic hash functions and password assignment handling...'
  ]

  const dependencyStages = [
    'Scanning repository directory tree for dependency manifests...',
    'Parsing requirements.txt, pyproject.toml, and Pipfile manifests...',
    'Parsing package.json and resolving package-lock.json dependency trees...',
    'Parsing Maven pom.xml and classifying test/dev scopes...',
    'Querying Google OSV database for known vulnerability advisories...',
    'Checking upstream package registries (PyPI, npm, Maven) for latest releases...',
    'Calculating dependency health metrics and persisting to database...'
  ]

  const architectureStages = [
    'Scanning source files and resolving local module paths...',
    'Parsing Python AST import nodes & standard library filters...',
    'Extracting JavaScript / TypeScript imports and require calls...',
    'Resolving relative paths, directory index files & file extensions...',
    'Heuristically classifying architectural layers (Presentation, API, Service, Data)...',
    'Running cycle detection algorithm to identify circular dependencies...',
    'Constructing dependency graph nodes, edges, and computing topology metrics...'
  ]

  const healthStages = [
    'Verifying repository scan, quality, security, dependency & architecture prerequisites...',
    'Reading stored findings across all 5 diagnostic dimensions...',
    'Evaluating deterministic maintainability & cyclomatic complexity scores...',
    'Computing security risk, dependency health, and architecture stability formulas...',
    'Aggregating weighted overall software health score & status...',
    'Calculating remediation technical debt hours by severity model...',
    'Ranking deterministic Fix First priority actions & persisting diagnostic report...'
  ]

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    setError(null)

    try {
      const proj = await projectService.getProject(id)
      setProject(proj)

      // Try fetching existing scan
      try {
        const existingScan = await projectService.getProjectScan(id)
        setScan(existingScan)
      } catch {
        setScan(null)
      }

      // Try fetching existing quality analysis
      try {
        const existingQuality = await projectService.getLatestQualityAnalysis(id)
        setQualityAnalysis(existingQuality)
        const issues = await projectService.getQualityIssues(id)
        setQualityIssues(issues)
      } catch {
        setQualityAnalysis(null)
        setQualityIssues([])
      }

      // Try fetching existing security analysis
      try {
        const existingSecurity = await projectService.getLatestSecurityAnalysis(id)
        setSecurityAnalysis(existingSecurity)
        const secIssues = await projectService.getSecurityIssues(id)
        setSecurityIssues(secIssues)
      } catch {
        setSecurityAnalysis(null)
        setSecurityIssues([])
      }

      // Try fetching existing dependency analysis
      try {
        const existingDeps = await projectService.getLatestDependencyAnalysis(id)
        setDependencyAnalysis(existingDeps)
        const deps = await projectService.getProjectDependencies(id)
        setDependenciesList(deps)
      } catch {
        setDependencyAnalysis(null)
        setDependenciesList([])
      }

      // Try fetching existing architecture analysis & graph
      try {
        const existingArch = await projectService.getLatestArchitectureAnalysis(id)
        setArchitectureAnalysis(existingArch)
        const graph = await projectService.getArchitectureGraph(id)
        setArchitectureGraphData(graph)
      } catch {
        setArchitectureAnalysis(null)
        setArchitectureGraphData(null)
      }

      // Try fetching existing health analysis
      try {
        const existingHealth = await projectService.getLatestHealthAnalysis(id)
        setHealthAnalysis(existingHealth)
      } catch {
        setHealthAnalysis(null)
      }
    } catch (err: any) {
      console.error('Failed to load project details:', err)
      setError(err.response?.data?.detail || 'Project not found or unauthorized.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id])

  const handleStartScan = async () => {
    if (!id) return
    setScanning(true)
    setScanError(null)
    setScanStepIndex(0)

    const stepInterval = setInterval(() => {
      setScanStepIndex((prev) => (prev < scanStages.length - 1 ? prev + 1 : prev))
    }, 400)

    try {
      const result = await projectService.scanProject(id)
      clearInterval(stepInterval)
      setScan(result)
    } catch (err: any) {
      clearInterval(stepInterval)
      setScanError(err.response?.data?.detail || 'Repository scan failed. Please check files.')
    } finally {
      setScanning(false)
    }
  }

  const handleStartQualityAnalysis = async () => {
    if (!id) return
    setAnalyzingQuality(true)
    setQualityError(null)
    setQualityStepIndex(0)

    const stepInterval = setInterval(() => {
      setQualityStepIndex((prev) => (prev < qualityStages.length - 1 ? prev + 1 : prev))
    }, 450)

    try {
      const result = await projectService.analyzeCodeQuality(id)
      clearInterval(stepInterval)
      setQualityAnalysis(result)
      const issues = await projectService.getQualityIssues(id)
      setQualityIssues(issues)
      setActiveTab('quality')
    } catch (err: any) {
      clearInterval(stepInterval)
      console.error('Quality analysis failed:', err)
      setQualityError(err.response?.data?.detail || 'Code quality analysis failed.')
    } finally {
      setAnalyzingQuality(false)
    }
  }

  const handleStartSecurityAnalysis = async () => {
    if (!id) return
    setAnalyzingSecurity(true)
    setSecurityError(null)
    setSecurityStepIndex(0)

    const stepInterval = setInterval(() => {
      setSecurityStepIndex((prev) => (prev < securityStages.length - 1 ? prev + 1 : prev))
    }, 450)

    try {
      const result = await projectService.analyzeSecurity(id)
      clearInterval(stepInterval)
      setSecurityAnalysis(result)
      const secIssues = await projectService.getSecurityIssues(id)
      setSecurityIssues(secIssues)
      setActiveTab('security')
    } catch (err: any) {
      clearInterval(stepInterval)
      console.error('Security audit failed:', err)
      setSecurityError(err.response?.data?.detail || 'Security audit analysis failed.')
    } finally {
      setAnalyzingSecurity(false)
    }
  }

  const handleStartDependencyAnalysis = async () => {
    if (!id) return
    setAnalyzingDependencies(true)
    setDependencyError(null)
    setDependencyStepIndex(0)

    const stepInterval = setInterval(() => {
      setDependencyStepIndex((prev) => (prev < dependencyStages.length - 1 ? prev + 1 : prev))
    }, 450)

    try {
      const result = await projectService.analyzeDependencies(id)
      clearInterval(stepInterval)
      setDependencyAnalysis(result)
      const deps = await projectService.getProjectDependencies(id)
      setDependenciesList(deps)
      setActiveTab('dependencies')
    } catch (err: any) {
      clearInterval(stepInterval)
      console.error('Dependency audit failed:', err)
      setDependencyError(err.response?.data?.detail || 'Dependency audit analysis failed.')
    } finally {
      setAnalyzingDependencies(false)
    }
  }

  const handleStartArchitectureAnalysis = async () => {
    if (!id) return
    setAnalyzingArchitecture(true)
    setArchitectureError(null)
    setArchitectureStepIndex(0)

    const stepInterval = setInterval(() => {
      setArchitectureStepIndex((prev) => (prev < architectureStages.length - 1 ? prev + 1 : prev))
    }, 400)

    try {
      const result = await projectService.analyzeArchitecture(id)
      clearInterval(stepInterval)
      setArchitectureAnalysis(result)
      const graph = await projectService.getArchitectureGraph(id)
      setArchitectureGraphData(graph)
      setActiveTab('architecture')
    } catch (err: any) {
      clearInterval(stepInterval)
      console.error('Architecture analysis failed:', err)
      setArchitectureError(err.response?.data?.detail || 'Architecture analysis failed.')
    } finally {
      setAnalyzingArchitecture(false)
    }
  }

  const handleStartHealthAnalysis = async () => {
    if (!id) return
    setAnalyzingHealth(true)
    setHealthError(null)
    setHealthStepIndex(0)

    const stepInterval = setInterval(() => {
      setHealthStepIndex((prev) => (prev < healthStages.length - 1 ? prev + 1 : prev))
    }, 400)

    try {
      const result = await projectService.analyzeHealth(id)
      clearInterval(stepInterval)
      setHealthAnalysis(result)
      setActiveTab('health')
    } catch (err: any) {
      clearInterval(stepInterval)
      console.error('Health diagnostic analysis failed:', err)
      setHealthError(err.response?.data?.detail || 'Health diagnostic analysis failed.')
    } finally {
      setAnalyzingHealth(false)
    }
  }

  const handleRunFullAnalysis = async () => {
    if (!id || runningFullAnalysis) return
    setRunningFullAnalysis(true)
    info('Full Diagnostics Started', 'Executing automated pipeline across all diagnostic engines...')

    try {
      // 1. Scan
      setFullAnalysisStage('Stage 1/5: Scanning repository files & directory tree...')
      const scanRes = await projectService.scanProject(id)
      setScan(scanRes)

      // 2. Code Quality
      setFullAnalysisStage('Stage 2/5: Analyzing code complexity, functions & duplications...')
      const qualRes = await projectService.analyzeCodeQuality(id)
      setQualityAnalysis(qualRes)
      const qualIssues = await projectService.getQualityIssues(id)
      setQualityIssues(qualIssues)

      // 3. Security
      setFullAnalysisStage('Stage 3/5: Auditing security rules, secrets & safe masking...')
      const secRes = await projectService.analyzeSecurity(id)
      setSecurityAnalysis(secRes)
      const secIssues = await projectService.getSecurityIssues(id)
      setSecurityIssues(secIssues)

      // 4. Dependencies
      setFullAnalysisStage('Stage 4/5: Resolving lockfiles & querying Google OSV advisories...')
      const depRes = await projectService.analyzeDependencies(id)
      setDependencyAnalysis(depRes)
      const depList = await projectService.getProjectDependencies(id)
      setDependenciesList(depList)

      // 5. Architecture
      setFullAnalysisStage('Stage 5/5: Mapping imports & module architecture graph...')
      const archRes = await projectService.analyzeArchitecture(id)
      setArchitectureAnalysis(archRes)
      const archGraph = await projectService.getArchitectureGraph(id)
      setArchitectureGraphData(archGraph)

      // 6. Master Health
      setFullAnalysisStage('Final Stage: Computing deterministic health score & technical debt...')
      const healthRes = await projectService.analyzeHealth(id)
      setHealthAnalysis(healthRes)
      setActiveTab('health')
      success(
        'Full Diagnostics Complete',
        `Overall Health: ${Math.round(healthRes.overall_score)}/100 (${healthRes.status}) · ${Math.round(healthRes.technical_debt_hours)}h Debt`
      )
    } catch (err: any) {
      console.error('Full analysis pipeline failed:', err)
      const msg = err.response?.data?.detail || err.message || 'Full analysis pipeline failed.'
      toastError('Analysis Incomplete', msg)
    } finally {
      setRunningFullAnalysis(false)
      setFullAnalysisStage('')
    }
  }

  const handleDelete = async () => {
    if (!id) return
    setDeleting(true)
    try {
      await projectService.deleteProject(id)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete project.')
      setDeleting(false)
      setShowDeleteConfirm(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center text-slate-400">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="h-7 w-7 text-blue-500 animate-spin" />
          <span className="text-xs font-mono tracking-wider uppercase">Loading repository telemetry...</span>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col justify-center items-center p-4">
        <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-8 max-w-md w-full text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h2 className="text-lg font-semibold text-white">Project Not Found</h2>
          <p className="text-xs text-slate-400">{error || 'This project does not exist or you do not have permission to view it.'}</p>
          <Link
            to="/"
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Return to Dashboard</span>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <AppShell
      projectId={project.id}
      projectName={project.name}
      activeTab={activeTab}
      onTabChange={(tab) => setActiveTab(tab as any)}
      breadcrumbs={[
        { label: 'Projects', href: '/' },
        { label: project.name, href: `/projects/${project.id}` },
        { label: TAB_LABELS[activeTab] || 'Overview' }
      ]}
    >
      <div className="p-4 sm:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto w-full">
        {/* Project Context Header (Stage 13 Developer UI/UX Polish) */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-5 sm:p-6 shadow-xl space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
            <div className="space-y-1.5 min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white truncate">
                  {project.name}
                </h1>

                {/* Source Type Badge */}
                <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-md bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
                  {project.source_type === 'zip' ? (
                    <>
                      <FileArchive className="h-3.5 w-3.5 text-blue-400" />
                      <span className="truncate max-w-[180px]">
                        {project.original_filename || 'ZIP Archive'}
                      </span>
                    </>
                  ) : (
                    <>
                      <GitBranch className="h-3.5 w-3.5 text-emerald-400" />
                      <a
                        href={project.source_url || undefined}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate max-w-[220px] text-blue-400 hover:underline flex items-center gap-1"
                      >
                        <span>{project.source_url?.replace(/^https?:\/\//, '')}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </>
                  )}
                </div>

                <StatusBadge status={project.status} size="sm" />
              </div>

              <p className="text-xs text-slate-400 max-w-3xl line-clamp-2">
                {project.description || 'Software repository configured for automated health diagnostics.'}
              </p>
            </div>

            {/* Header Action Buttons */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => setShowAuditModal(true)}
                disabled={!healthAnalysis}
                className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-slate-700 text-xs font-medium transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                title="Export executive codebase medical chart & compliance audit certificate"
              >
                <FileText className="h-4 w-4 text-indigo-400" />
                <span className="hidden sm:inline">Export Audit Report</span>
              </button>

              <button
                onClick={handleRunFullAnalysis}
                disabled={runningFullAnalysis || project.status !== 'READY'}
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
                title="Execute all diagnostic engines sequentially"
              >
                {runningFullAnalysis ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4" />
                    <span>{healthAnalysis ? 'Re-Analyze All' : 'Run Full Diagnostic'}</span>
                  </>
                )}
              </button>

              <button
                onClick={() => setShowDeleteConfirm(true)}
                disabled={runningFullAnalysis || deleting}
                className="p-2 rounded-lg border border-slate-800 text-slate-400 hover:text-rose-400 hover:bg-rose-950/20 hover:border-rose-900/30 transition text-xs"
                title="Delete Project"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Quick Telemetry & Stats Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/80 text-xs font-mono">
            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-500 uppercase">Lines of Code</span>
              <div className="text-slate-200 font-medium">
                {scan ? `${scan.total_code_lines.toLocaleString()} LOC` : 'Pending Scan'}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-500 uppercase">Primary Languages</span>
              <div className="text-slate-200 font-medium truncate">
                {scan && Object.keys(scan.languages_summary).length > 0
                  ? Object.keys(scan.languages_summary).slice(0, 3).join(', ')
                  : 'Undetected'}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-500 uppercase">Total Findings</span>
              <div className="text-slate-200 font-medium">
                {qualityAnalysis || securityAnalysis || dependencyAnalysis ? (
                  <span className="text-amber-400">
                    {(qualityAnalysis?.total_issues || 0) +
                      (securityAnalysis?.total_issues || 0) +
                      (dependencyAnalysis?.vulnerable_count || 0)}{' '}
                    issues
                  </span>
                ) : (
                  'Pending Audit'
                )}
              </div>
            </div>

            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-500 uppercase">Health &amp; Tech Debt</span>
              <div className="text-slate-200 font-medium">
                {healthAnalysis ? (
                  <span
                    className={
                      healthAnalysis.overall_score >= 80
                        ? 'text-emerald-400'
                        : healthAnalysis.overall_score >= 60
                        ? 'text-amber-400'
                        : 'text-rose-400'
                    }
                  >
                    {Math.round(healthAnalysis.overall_score)}/100 · {Math.round(healthAnalysis.technical_debt_hours)}h
                  </span>
                ) : (
                  'Not Evaluated'
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Scan Error Banner */}
        {scanError && (
          <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-4 flex items-start space-x-3 text-rose-300 text-xs">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed font-medium">{scanError}</div>
          </div>
        )}

        {/* Live Full Analysis Progress Banner */}
        {runningFullAnalysis && (
          <div className="bg-[#0d1322] border border-blue-500/40 rounded-xl p-5 shadow-2xl space-y-3">
            <div className="flex items-center space-x-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-400 shrink-0" />
              <div>
                <h3 className="text-sm font-semibold text-white">Full Diagnostic Pipeline In Progress</h3>
                <p className="text-xs text-blue-300 font-mono mt-0.5">{fullAnalysisStage}</p>
              </div>
            </div>
          </div>
        )}

        {/* Live Scanning Progress Card */}
        {scanning && (
          <div className="bg-[#0d1322] border border-blue-500/40 rounded-xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center space-x-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
              <div>
                <h3 className="text-base font-semibold text-white">Scanning Repository in Progress...</h3>
                <p className="text-xs text-slate-400">Please wait while the backend safely inspects the codebase</p>
              </div>
            </div>

            {/* Stages Tracker */}
            <div className="space-y-2 pt-2 border-t border-slate-800/80">
              {scanStages.map((stageName, idx) => (
                <div key={stageName} className="flex items-center space-x-3 text-xs font-mono">
                  {idx < scanStepIndex ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  ) : idx === scanStepIndex ? (
                    <Loader2 className="h-4 w-4 text-blue-400 animate-spin shrink-0" />
                  ) : (
                    <span className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                  )}
                  <span
                    className={
                      idx < scanStepIndex
                        ? 'text-emerald-300 line-through opacity-70'
                        : idx === scanStepIndex
                        ? 'text-blue-300 font-medium'
                        : 'text-slate-500'
                    }
                  >
                    {stageName}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Horizontal Navigation Tabs Bar */}
        <div className="flex items-center space-x-1.5 border-b border-slate-800 pb-2 overflow-x-auto">
          {/* Health */}
          <button
            onClick={() => setActiveTab('health')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'health'
                ? 'bg-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <HeartPulse className="h-4 w-4" />
            <span>Health &amp; Diagnostics</span>
            {healthAnalysis ? (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 text-[10px] font-bold">
                {Math.round(healthAnalysis.overall_score)}/100
              </span>
            ) : (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px]">
                Ready
              </span>
            )}
          </button>

          {/* Doctor's Prescription / Auto-Fix */}
          <button
            onClick={() => setActiveTab('prescription')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'prescription'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <Stethoscope className="h-4 w-4" />
            <span>Doctor's Prescription</span>
            <span className="ml-1 px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 text-[10px] font-bold">
              Auto-Fix
            </span>
          </button>

          {/* Scanner */}
          <button
            onClick={() => setActiveTab('scanner')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'scanner'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <FolderTree className="h-4 w-4" />
            <span>Structure</span>
            {scan && (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-900 text-slate-300 text-[10px]">
                {scan.total_files} Files
              </span>
            )}
          </button>

          {/* Code Quality */}
          <button
            onClick={() => setActiveTab('quality')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'quality'
                ? 'bg-purple-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <Code2 className="h-4 w-4" />
            <span>Code Quality</span>
            {qualityAnalysis ? (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 text-[10px] font-bold">
                {qualityAnalysis.total_issues}
              </span>
            ) : (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px]">Ready</span>
            )}
          </button>

          {/* Security Audit */}
          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'security'
                ? 'bg-rose-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <ShieldAlert className="h-4 w-4" />
            <span>Security Audit</span>
            {securityAnalysis ? (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 text-[10px] font-bold">
                {securityAnalysis.total_issues}
              </span>
            ) : (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px]">Ready</span>
            )}
          </button>

          {/* Dependencies */}
          <button
            onClick={() => setActiveTab('dependencies')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'dependencies'
                ? 'bg-amber-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <Boxes className="h-4 w-4" />
            <span>Dependencies</span>
            {dependencyAnalysis ? (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded text-[10px] font-bold ${
                  dependencyAnalysis.vulnerable_count > 0 ? 'bg-rose-950 text-rose-300' : 'bg-amber-950 text-amber-300'
                }`}
              >
                {dependencyAnalysis.total_dependencies}
                {dependencyAnalysis.vulnerable_count > 0 ? ` (${dependencyAnalysis.vulnerable_count} Vuln)` : ''}
              </span>
            ) : (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px]">Ready</span>
            )}
          </button>

          {/* Architecture */}
          <button
            onClick={() => setActiveTab('architecture')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'architecture'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <Network className="h-4 w-4" />
            <span>Architecture</span>
            {architectureAnalysis ? (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded text-[10px] font-bold ${
                  architectureAnalysis.cycle_count > 0 ? 'bg-red-950 text-red-300' : 'bg-indigo-950 text-indigo-300'
                }`}
              >
                {architectureAnalysis.node_count}
              </span>
            ) : (
              <span className="ml-1 px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px]">Ready</span>
            )}
          </button>

          {/* Ask Codebase (Stage 11) */}
          <button
            onClick={() => setActiveTab('qa')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'qa'
                ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <Sparkles className="h-4 w-4 text-violet-400" />
            <span>Ask My Codebase</span>
            <span className="ml-1 px-1.5 py-0.2 rounded bg-violet-950 text-violet-300 text-[10px] font-bold border border-violet-800/40">
              AI Q&amp;A
            </span>
          </button>

          {/* History & Trends (Stage 12) */}
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center space-x-2 px-3.5 py-2 rounded-lg text-xs font-mono font-medium transition whitespace-nowrap ${
              activeTab === 'history'
                ? 'bg-gradient-to-r from-teal-600 to-emerald-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white hover:bg-slate-900/60'
            }`}
          >
            <TrendingUp className="h-4 w-4 text-teal-400" />
            <span>History &amp; Trends</span>
          </button>
        </div>

        {/* Tab 1: Scanned Project Structure Overview Section */}
        {scan && activeTab === 'scanner' && (
          <div className="space-y-8">
            {/* Top Stat Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Total Files</span>
                <div className="text-2xl font-mono font-bold text-white">{scan.total_files}</div>
                <span className="text-[10px] text-slate-500 font-mono">Filtered & Verified</span>
              </div>

              <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Directories</span>
                <div className="text-2xl font-mono font-bold text-white">{scan.total_directories}</div>
                <span className="text-[10px] text-slate-500 font-mono">Folder Hierarchy</span>
              </div>

              <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Lines of Code</span>
                <div className="text-2xl font-mono font-bold text-emerald-400 font-mono">
                  {scan.total_code_lines.toLocaleString()}
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {scan.total_lines.toLocaleString()} total lines
                </span>
              </div>

              <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Languages</span>
                <div className="text-2xl font-mono font-bold text-blue-400">
                  {Object.keys(scan.languages_summary).length}
                </div>
                <span className="text-[10px] text-slate-500 font-mono">
                  {Object.keys(scan.languages_summary).slice(0, 2).join(', ') || 'Detected'}
                </span>
              </div>

              <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                <span className="text-[11px] font-mono text-slate-500 uppercase">Test Files</span>
                <div className="text-2xl font-mono font-bold text-purple-400">{scan.test_files_count}</div>
                <span className="text-[10px] text-slate-500 font-mono">Automated Specs</span>
              </div>
            </div>

            {/* Language Breakdown & File Categorization Cards */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Language Breakdown (Left 7 cols) */}
              <div className="lg:col-span-7 bg-[#0d1322] border border-slate-800 rounded-xl p-6 space-y-5 shadow-xl">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Code2 className="h-4 w-4 text-blue-400" />
                    <h3 className="text-sm font-semibold text-white">Programming Languages</h3>
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">Calculated from Real Line Counts</span>
                </div>

                {/* Multi-segment Language Bar */}
                <div className="h-3 w-full rounded-full overflow-hidden flex bg-slate-900 border border-slate-800">
                  {Object.entries(scan.languages_summary).map(([lang, stat]) => (
                    <div
                      key={lang}
                      style={{
                        width: `${stat.percentage}%`,
                        backgroundColor: LANGUAGE_COLORS[lang] || '#64748b',
                      }}
                      title={`${lang}: ${stat.percentage}% (${stat.lines.toLocaleString()} lines)`}
                      className="h-full transition-all duration-300"
                    />
                  ))}
                </div>

                {/* Languages List */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                  {Object.entries(scan.languages_summary).map(([lang, stat]) => (
                    <div key={lang} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1">
                      <div className="flex items-center space-x-1.5">
                        <span
                          className="h-2.5 w-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: LANGUAGE_COLORS[lang] || '#64748b' }}
                        />
                        <span className="text-xs font-medium text-slate-200 truncate">{lang}</span>
                      </div>
                      <div className="flex items-baseline justify-between text-[11px] font-mono text-slate-400">
                        <span>{stat.percentage}%</span>
                        <span className="text-slate-500">{stat.lines.toLocaleString()}L</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* File Categorization (Right 5 cols) */}
              <div className="lg:col-span-5 bg-[#0d1322] border border-slate-800 rounded-xl p-6 space-y-5 shadow-xl">
                <div className="flex items-center space-x-2">
                  <Layers className="h-4 w-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-white">File Categorization</h3>
                </div>

                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center space-x-2.5">
                    <FileCode className="h-4 w-4 text-blue-400 shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">Source Code</div>
                      <div className="text-sm font-mono font-semibold text-white">
                        {scan.categories_summary['Source Code'] || 0}
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center space-x-2.5">
                    <FileCheck2 className="h-4 w-4 text-purple-400 shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">Tests</div>
                      <div className="text-sm font-mono font-semibold text-white">{scan.test_files_count}</div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center space-x-2.5">
                    <FileCog className="h-4 w-4 text-amber-400 shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">Configs</div>
                      <div className="text-sm font-mono font-semibold text-white">{scan.config_files_count}</div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center space-x-2.5">
                    <FileText className="h-4 w-4 text-emerald-400 shrink-0" />
                    <div>
                      <div className="text-[10px] text-slate-500 uppercase font-mono">Documentation</div>
                      <div className="text-sm font-mono font-semibold text-white">{scan.doc_files_count}</div>
                    </div>
                  </div>
                </div>

                {/* Line count stats box */}
                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1.5 text-xs font-mono">
                  <div className="flex justify-between text-slate-400">
                    <span>Code Lines:</span>
                    <span className="text-emerald-400 font-semibold">{scan.total_code_lines.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Comment Lines:</span>
                    <span className="text-blue-400">{scan.total_comment_lines.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Blank Lines:</span>
                    <span className="text-slate-500">{scan.total_blank_lines.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Hierarchical Interactive File Explorer */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-white">Repository Directory Tree</h3>
                  <p className="text-xs text-slate-400">
                    Click folders to expand and select files to inspect line counts and static metadata
                  </p>
                </div>

                <button
                  onClick={handleStartScan}
                  disabled={scanning}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md border border-slate-800 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
                  title="Re-run Repository Scan"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${scanning ? 'animate-spin' : ''}`} />
                  <span>Re-scan Repository</span>
                </button>
              </div>

              <FileExplorer tree={scan.directory_tree} />
            </div>
          </div>
        )}

        {/* Tab 2: Code Quality Analyzer Section */}
        {scan && activeTab === 'quality' && (
          <div className="space-y-8">
            {/* Quality Error Banner */}
            {qualityError && (
              <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-4 flex items-start space-x-3 text-rose-300 text-xs">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="leading-relaxed font-medium">{qualityError}</div>
              </div>
            )}

            {/* Quality CTA if not analyzed yet */}
            {!qualityAnalysis && !analyzingQuality && (
              <div className="bg-[#0d1322] border border-purple-500/30 rounded-xl p-6 sm:p-8 space-y-4 shadow-xl">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        STAGE 5: CODE QUALITY ANALYZER
                      </span>
                      <span className="text-xs text-slate-400">Deterministic Static AST Analysis</span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-white">Analyze Code Quality</h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-purple-600/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
                    <Code2 className="h-5 w-5" />
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                  Repository scan completed. Initiate comprehensive static code analysis across Python, JavaScript, and TypeScript source files to measure cyclomatic complexity, identify oversized functions, pinpoint deep nesting, discover cross-file duplicate code, and locate technical debt comments.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono text-slate-400">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Cyclomatic Complexity</strong>
                    McCabe branch decision path counting via Python AST
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Duplication & Nesting</strong>
                    10+ line normalized block matching & control-flow depths
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Imports & Debt</strong>
                    Unused import detection & TODO/FIXME markers
                  </div>
                </div>

                <button
                  onClick={handleStartQualityAnalysis}
                  disabled={analyzingQuality}
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50"
                >
                  <Code2 className="h-4 w-4" />
                  <span>Analyze Code Quality</span>
                </button>
              </div>
            )}

            {/* Live Quality Analysis Progress Card */}
            {analyzingQuality && (
              <div className="bg-[#0d1322] border border-purple-500/40 rounded-xl p-6 sm:p-8 space-y-5 shadow-2xl">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 animate-spin text-purple-400" />
                  <div>
                    <h3 className="text-base font-semibold text-white">Analyzing Code Quality in Progress...</h3>
                    <p className="text-xs text-slate-400">Evaluating AST nodes, function lengths, and code patterns statically</p>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  {qualityStages.map((stageName, idx) => (
                    <div key={stageName} className="flex items-center space-x-3 text-xs font-mono">
                      {idx < qualityStepIndex ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : idx === qualityStepIndex ? (
                        <Loader2 className="h-4 w-4 text-purple-400 animate-spin shrink-0" />
                      ) : (
                        <span className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span
                        className={
                          idx < qualityStepIndex
                            ? 'text-emerald-300 line-through opacity-70'
                            : idx === qualityStepIndex
                            ? 'text-purple-300 font-medium'
                            : 'text-slate-500'
                        }
                      >
                        {stageName}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Quality Analysis Results */}
            {qualityAnalysis && (
              <div className="space-y-8">
                {/* 5 Real Severity Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-4 rounded-xl bg-[#0d1322] border border-purple-500/30 space-y-1">
                    <span className="text-[11px] font-mono text-purple-400 uppercase">Quality Issues</span>
                    <div className="text-2xl font-mono font-bold text-white">{qualityAnalysis.total_issues}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Total Detected</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-rose-500/30 space-y-1">
                    <div className="flex items-center justify-between text-rose-400">
                      <span className="text-[11px] font-mono uppercase">Critical</span>
                      <Flame className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-rose-400">{qualityAnalysis.critical_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Complexity &gt; 15</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-amber-500/30 space-y-1">
                    <div className="flex items-center justify-between text-amber-400">
                      <span className="text-[11px] font-mono uppercase">High</span>
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-amber-400">{qualityAnalysis.high_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">High Severity</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-blue-500/30 space-y-1">
                    <div className="flex items-center justify-between text-blue-400">
                      <span className="text-[11px] font-mono uppercase">Medium</span>
                      <AlertCircle className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-blue-400">{qualityAnalysis.medium_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Moderate Issues</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-700/60 space-y-1">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[11px] font-mono uppercase">Low</span>
                      <Info className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-slate-300">{qualityAnalysis.low_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Imports &amp; Debt</span>
                  </div>
                </div>

                {/* Maintainability Metrics Panel */}
                <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <SlidersHorizontal className="h-4 w-4 text-purple-400" />
                      <h3 className="text-sm font-semibold text-white">Basic Maintainability Metrics</h3>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">Calculated Deterministically</span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 pt-2 font-mono text-xs">
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">Avg Complexity</span>
                      <span className="text-base font-bold text-white">{qualityAnalysis.metrics.avg_complexity}</span>
                      <span className="text-[10px] text-slate-500 block">per function</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">Max Complexity</span>
                      <span className={`text-base font-bold ${qualityAnalysis.metrics.max_complexity >= 16 ? 'text-rose-400' : 'text-white'}`}>
                        {qualityAnalysis.metrics.max_complexity}
                      </span>
                      <span className="text-[10px] text-slate-500 block">peak decision paths</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">Avg Function Length</span>
                      <span className="text-base font-bold text-white">{qualityAnalysis.metrics.avg_function_length}</span>
                      <span className="text-[10px] text-slate-500 block">lines of code</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">Max Function Length</span>
                      <span className={`text-base font-bold ${qualityAnalysis.metrics.max_function_length > 50 ? 'text-amber-400' : 'text-white'}`}>
                        {qualityAnalysis.metrics.max_function_length}
                      </span>
                      <span className="text-[10px] text-slate-500 block">longest function</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">Duplicate Blocks</span>
                      <span className="text-base font-bold text-blue-400">{qualityAnalysis.metrics.duplicate_blocks_count}</span>
                      <span className="text-[10px] text-slate-500 block">10+ line blocks</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <span className="text-[10px] text-slate-500 uppercase block">TODO / Debt Tags</span>
                      <span className="text-base font-bold text-slate-300">{qualityAnalysis.metrics.todo_comments_count}</span>
                      <span className="text-[10px] text-slate-500 block">unresolved comments</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-800/80 text-[11px] font-mono text-slate-400">
                    <span>Functions Analyzed: <strong className="text-white">{qualityAnalysis.metrics.total_functions}</strong></span>
                    <span>Classes: <strong className="text-white">{qualityAnalysis.metrics.total_classes}</strong></span>
                    <span>Unused Imports: <strong className="text-white">{qualityAnalysis.metrics.unused_imports_count}</strong></span>
                    <span>Files Parsed: <strong className="text-white">{qualityAnalysis.metrics.files_analyzed}</strong></span>
                    {qualityAnalysis.metrics.unparseable_files > 0 && (
                      <span className="text-amber-400">Unparseable Files: <strong>{qualityAnalysis.metrics.unparseable_files}</strong></span>
                    )}
                  </div>
                </div>

                {/* Interactive Issue Explorer Component */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-white">
                        Detected Issues ({qualityAnalysis.total_issues})
                      </h3>
                      <p className="text-xs text-slate-400">
                        Filter by severity, rule type, or search for affected symbols and files
                      </p>
                    </div>

                    <button
                      onClick={handleStartQualityAnalysis}
                      disabled={analyzingQuality}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md border border-slate-800 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      title="Re-run Quality Analysis"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${analyzingQuality ? 'animate-spin' : ''}`} />
                      <span>Re-analyze Code Quality</span>
                    </button>
                  </div>

                  <IssueExplorer
                    projectId={project.id}
                    issues={qualityIssues}
                    loading={analyzingQuality}
                    onRefresh={handleStartQualityAnalysis}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Security Audit Overview & Issue Explorer */}
        {scan && activeTab === 'security' && (
          <div className="space-y-8">
            {/* Security Error Banner */}
            {securityError && (
              <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-4 flex items-start space-x-3 text-rose-300 text-xs">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="leading-relaxed font-medium">{securityError}</div>
              </div>
            )}

            {/* Action / Trigger Banner: Ready to Audit Security */}
            {!securityAnalysis && !analyzingSecurity && (
              <div className="bg-[#0d1322] border border-rose-500/30 rounded-xl p-6 sm:p-8 space-y-4 shadow-xl">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                        STAGE 6: SECURITY AUDIT ENGINE
                      </span>
                      <span className="text-xs text-slate-400">Static AST &amp; Pattern Vulnerability Discovery</span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-white">Security Vulnerability Audit</h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-rose-600/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
                    <ShieldAlert className="h-5 w-5" />
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                  Execute comprehensive static security analysis against the scanned codebase. Detects hardcoded secrets &amp; cloud tokens (with strict masking), SQL injection, OS command injection, dangerous dynamic code execution (eval, exec, Function), insecure configurations (DEBUG flags, disabled SSL, wildcard CORS), weak cryptographic algorithms (MD5, SHA1), and plaintext password handling.
                </p>

                <div className="flex items-center space-x-4 pt-2">
                  <button
                    onClick={handleStartSecurityAnalysis}
                    disabled={project.status !== 'READY'}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    <span>Start Security Audit</span>
                  </button>
                  <span className="text-xs text-slate-500 font-mono">
                    100% Static Analysis • Zero Code Execution • Credentials Masked
                  </span>
                </div>
              </div>
            )}

            {/* Live Security Analysis Progress Card */}
            {analyzingSecurity && (
              <div className="bg-[#0d1322] border border-rose-500/40 rounded-xl p-6 sm:p-8 space-y-5 shadow-2xl">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 animate-spin text-rose-400" />
                  <div>
                    <h3 className="text-base font-semibold text-white">Security Audit in Progress...</h3>
                    <p className="text-xs text-slate-400">Auditing source files for secrets, injections, and execution vulnerabilities</p>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  {securityStages.map((stageName, idx) => (
                    <div key={stageName} className="flex items-center space-x-3 text-xs font-mono">
                      {idx < securityStepIndex ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : idx === securityStepIndex ? (
                        <Loader2 className="h-4 w-4 text-rose-400 animate-spin shrink-0" />
                      ) : (
                        <span className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span
                        className={
                          idx < securityStepIndex
                            ? 'text-emerald-300 line-through opacity-70'
                            : idx === securityStepIndex
                            ? 'text-rose-300 font-medium'
                            : 'text-slate-500'
                        }
                      >
                        {stageName}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Security Audit Results */}
            {securityAnalysis && (
              <div className="space-y-8">
                {/* 5 Real Severity Metric Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <div className="p-4 rounded-xl bg-[#0d1322] border border-rose-500/30 space-y-1">
                    <span className="text-[11px] font-mono text-rose-400 uppercase">Security Issues</span>
                    <div className="text-2xl font-mono font-bold text-white">{securityAnalysis.total_issues}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Total Findings</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-rose-500/40 space-y-1">
                    <div className="flex items-center justify-between text-rose-400">
                      <span className="text-[11px] font-mono uppercase">Critical</span>
                      <Flame className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-rose-400">{securityAnalysis.critical_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Injection &amp; Live Secrets</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-amber-500/30 space-y-1">
                    <div className="flex items-center justify-between text-amber-400">
                      <span className="text-[11px] font-mono uppercase">High</span>
                      <AlertTriangle className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-amber-400">{securityAnalysis.high_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Tokens &amp; Unsafe Exec</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-yellow-500/30 space-y-1">
                    <div className="flex items-center justify-between text-yellow-400">
                      <span className="text-[11px] font-mono uppercase">Medium</span>
                      <AlertCircle className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-yellow-400">{securityAnalysis.medium_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Config &amp; Weak Crypto</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-700/60 space-y-1">
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-[11px] font-mono uppercase">Low</span>
                      <Info className="h-4 w-4" />
                    </div>
                    <div className="text-2xl font-mono font-bold text-slate-300">{securityAnalysis.low_count}</div>
                    <span className="text-[10px] text-slate-500 font-mono">Informational</span>
                  </div>
                </div>

                {/* Category Breakdown Panel */}
                <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 space-y-4 shadow-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <ShieldAlert className="h-4 w-4 text-rose-400" />
                      <h3 className="text-sm font-semibold text-white">Vulnerability Breakdown by Category</h3>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500">
                      Files Audited: {securityAnalysis.metrics.files_audited}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2 font-mono text-xs">
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Secrets</span>
                        <KeyRound className="w-3.5 h-3.5 text-amber-400" />
                      </div>
                      <span className="text-base font-bold text-amber-400">
                        {securityAnalysis.metrics.by_category?.['SECRETS'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">Keys &amp; Credentials</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Injection</span>
                        <Terminal className="w-3.5 h-3.5 text-rose-400" />
                      </div>
                      <span className="text-base font-bold text-rose-400">
                        {securityAnalysis.metrics.by_category?.['INJECTION'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">SQL &amp; OS Shell</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Dangerous Calls</span>
                        <Cpu className="w-3.5 h-3.5 text-purple-400" />
                      </div>
                      <span className="text-base font-bold text-purple-400">
                        {securityAnalysis.metrics.by_category?.['DANGEROUS_CALLS'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">eval &amp; exec</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Config</span>
                        <Settings className="w-3.5 h-3.5 text-blue-400" />
                      </div>
                      <span className="text-base font-bold text-blue-400">
                        {securityAnalysis.metrics.by_category?.['CONFIGURATION'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">DEBUG &amp; TLS</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Crypto</span>
                        <Hash className="w-3.5 h-3.5 text-emerald-400" />
                      </div>
                      <span className="text-base font-bold text-emerald-400">
                        {securityAnalysis.metrics.by_category?.['CRYPTO'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">MD5 &amp; SHA1</span>
                    </div>

                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] text-slate-500 uppercase">Passwords</span>
                        <Lock className="w-3.5 h-3.5 text-orange-400" />
                      </div>
                      <span className="text-base font-bold text-orange-400">
                        {securityAnalysis.metrics.by_category?.['AUTHENTICATION'] || 0}
                      </span>
                      <span className="text-[10px] text-slate-500 block">Unhashed Storage</span>
                    </div>
                  </div>
                </div>

                {/* Interactive Security Issue Explorer Component */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-white">
                        Security Findings ({securityAnalysis.total_issues})
                      </h3>
                      <p className="text-xs text-slate-400">
                        Filter by severity, vulnerability category, or search across filenames and messages
                      </p>
                    </div>

                    <button
                      onClick={handleStartSecurityAnalysis}
                      disabled={analyzingSecurity}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-md border border-slate-800 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
                      title="Re-run Security Audit"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${analyzingSecurity ? 'animate-spin' : ''}`} />
                      <span>Re-audit Security</span>
                    </button>
                  </div>

                  <SecurityIssueExplorer
                    projectId={project.id}
                    issues={securityIssues}
                    loading={analyzingSecurity}
                    onRefresh={handleStartSecurityAnalysis}
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Dependency Analyzer Section */}
        {scan && activeTab === 'dependencies' && (
          <div className="space-y-8">
            {/* Dependency Error Banner */}
            {dependencyError && (
              <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-4 flex items-start space-x-3 text-rose-300 text-xs">
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="leading-relaxed font-medium">{dependencyError}</div>
              </div>
            )}

            {/* Dependency CTA if not analyzed yet */}
            {!dependencyAnalysis && !analyzingDependencies && (
              <div className="bg-[#0d1322] border border-amber-500/30 rounded-xl p-6 sm:p-8 space-y-4 shadow-xl">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        STAGE 7: DEPENDENCY ANALYZER
                      </span>
                      <span className="text-xs text-slate-400">Static Manifest &amp; Vulnerability Audit</span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-white">Audit Project Dependencies</h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-amber-600/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <Boxes className="h-5 w-5" />
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                  Inspect repository manifests (<code className="text-amber-300 font-mono text-xs">requirements.txt</code>, <code className="text-amber-300 font-mono text-xs">pyproject.toml</code>, <code className="text-amber-300 font-mono text-xs">Pipfile</code>, <code className="text-amber-300 font-mono text-xs">package.json</code>, <code className="text-amber-300 font-mono text-xs">package-lock.json</code>, <code className="text-amber-300 font-mono text-xs">pom.xml</code>) with zero code execution. Query the Google OSV advisory database for verified security vulnerabilities and check upstream package registries (PyPI, npm, Maven) for latest version releases.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs font-mono text-slate-400">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Zero Code Execution</strong>
                    <span>Purely static AST &amp; lockfile parsing</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Google OSV Advisories</strong>
                    <span>Real CVE &amp; GHSA vulnerability feeds</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Direct vs Transitive</strong>
                    <span>Full lockfile dependency tree resolution</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleStartDependencyAnalysis}
                    disabled={project.status !== 'READY'}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Boxes className="h-4 w-4" />
                    <span>Start Dependency Audit</span>
                  </button>
                </div>
              </div>
            )}

            {/* Live Dependency Audit Progress Tracker */}
            {analyzingDependencies && (
              <div className="bg-[#0d1322] border border-amber-500/40 rounded-xl p-6 sm:p-8 space-y-5 shadow-2xl">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 animate-spin text-amber-400" />
                  <div>
                    <h3 className="text-base font-semibold text-white">Running Dependency Audit...</h3>
                    <p className="text-xs text-slate-400">Static manifest ingestion &amp; OSV vulnerability matching</p>
                  </div>
                </div>

                <div className="space-y-2.5 pt-2">
                  {dependencyStages.map((stageName, idx) => (
                    <div key={idx} className="flex items-center space-x-3 text-xs font-mono">
                      {idx < dependencyStepIndex ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : idx === dependencyStepIndex ? (
                        <Loader2 className="h-4 w-4 text-amber-400 animate-spin shrink-0" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span
                        className={
                          idx < dependencyStepIndex
                            ? 'text-emerald-300 line-through opacity-70'
                            : idx === dependencyStepIndex
                            ? 'text-amber-300 font-medium'
                            : 'text-slate-500'
                        }
                      >
                        {stageName}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Render Dependency Dashboard when Analysis Complete */}
            {dependencyAnalysis && (
              <DependencyDashboard
                projectId={project.id}
                analysis={dependencyAnalysis}
                dependencies={dependenciesList}
                loading={analyzingDependencies}
                onRefresh={loadData}
                onReanalyze={handleStartDependencyAnalysis}
                analyzing={analyzingDependencies}
              />
            )}
          </div>
        )}

        {/* Tab 5: Architecture Graph Section */}
        {scan && activeTab === 'architecture' && (
          <div className="space-y-6">
            {/* CTA Card when Architecture not yet analyzed */}
            {!architectureAnalysis && !analyzingArchitecture && (
              <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6 shadow-xl">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-indigo-400 font-mono text-xs">
                      <Network className="h-4 w-4" />
                      <span>Stage 8 · Architecture &amp; Module Dependency Engine</span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-white">Interactive Architecture Graph</h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-indigo-600/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                    <Network className="h-5 w-5" />
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                  Construct an interactive dependency graph of your codebase from real imports and module references.
                  Features automatic architectural layer classification (Presentation, API, Service, Data, Utility),
                  circular dependency cycle detection, in/out degree coupling metrics, and interactive inspection.
                </p>

                {architectureError && (
                  <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                    <span>{architectureError}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Zero Code Execution</strong>
                    <span>Pure static Python AST &amp; JS/TS regex parsing</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Layer Classification</strong>
                    <span>Inferred Presentation, API, Service &amp; Data boundaries</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Cycle Detection</strong>
                    <span>DFS identification of circular import loops</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleStartArchitectureAnalysis}
                    disabled={project.status !== 'READY'}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Network className="h-4 w-4" />
                    <span>Build Architecture Graph</span>
                  </button>
                </div>
              </div>
            )}

            {/* Live Architecture Analysis Progress Tracker */}
            {analyzingArchitecture && (
              <div className="bg-[#0d1322] border border-indigo-500/40 rounded-xl p-6 sm:p-8 space-y-5 shadow-2xl">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
                  <div>
                    <h3 className="text-base font-semibold text-white">Analyzing Architecture &amp; Dependencies...</h3>
                    <p className="text-xs text-slate-400">Static import resolution, layer heuristics, and cycle detection</p>
                  </div>
                </div>

                <div className="space-y-2.5 pt-2">
                  {architectureStages.map((stageName, idx) => (
                    <div key={idx} className="flex items-center space-x-3 text-xs font-mono">
                      {idx < architectureStepIndex ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : idx === architectureStepIndex ? (
                        <Loader2 className="h-4 w-4 text-indigo-400 animate-spin shrink-0" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span
                        className={
                          idx < architectureStepIndex
                            ? 'text-emerald-300 line-through opacity-70'
                            : idx === architectureStepIndex
                            ? 'text-indigo-300 font-medium'
                            : 'text-slate-500'
                        }
                      >
                        {stageName}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Render Architecture Graph when Analysis Complete */}
            {architectureAnalysis && architectureGraphData && (
              <div className="space-y-4">
                {/* Summary Metrics Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Analyzed Modules</span>
                    <div className="text-2xl font-mono font-bold text-white">
                      {architectureAnalysis.node_count}
                    </div>
                    <span className="text-[10px] text-slate-500">Source files with graph nodes</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Dependency Edges</span>
                    <div className="text-2xl font-mono font-bold text-sky-400">
                      {architectureAnalysis.edge_count}
                    </div>
                    <span className="text-[10px] text-slate-500">Resolved local module imports</span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Circular Cycles</span>
                    <div
                      className={`text-2xl font-mono font-bold ${
                        architectureAnalysis.cycle_count > 0 ? 'text-red-400' : 'text-emerald-400'
                      }`}
                    >
                      {architectureAnalysis.cycle_count}
                    </div>
                    <span className="text-[10px] text-slate-500">
                      {architectureAnalysis.cycle_count > 0 ? 'Circular dependency loops' : 'Zero cycles detected'}
                    </span>
                  </div>

                  <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
                    <span className="text-[11px] font-mono text-slate-400 uppercase">Architecture Status</span>
                    <div className="text-2xl font-mono font-bold text-indigo-400">
                      {architectureAnalysis.status}
                    </div>
                    <span className="text-[10px] text-slate-500">
                      {new Date(architectureAnalysis.started_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {/* Toolbar / Actions Strip */}
                <div className="flex items-center justify-between bg-[#0d1322] border border-slate-800 rounded-xl px-4 py-3">
                  <div className="flex items-center space-x-2 text-xs text-slate-400">
                    <Network className="h-4 w-4 text-indigo-400" />
                    <span>
                      Showing <strong>{architectureGraphData.nodes.length}</strong> modules and{' '}
                      <strong>{architectureGraphData.edges.length}</strong> import relations
                    </span>
                  </div>

                  <button
                    onClick={handleStartArchitectureAnalysis}
                    disabled={analyzingArchitecture}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${analyzingArchitecture ? 'animate-spin' : ''}`} />
                    <span>Re-Analyze Architecture</span>
                  </button>
                </div>

                {/* Graph Canvas */}
                <ArchitectureGraph graphData={architectureGraphData} />
              </div>
            )}
          </div>
        )}

        {/* Tab 6: Health & Technical Debt Engine Section */}
        {scan && activeTab === 'health' && (
          <div className="space-y-6">
            {/* CTA Card when Health Diagnostic not yet executed */}
            {!healthAnalysis && !analyzingHealth && (
              <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 sm:p-8 space-y-6 shadow-xl">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2 text-emerald-400 font-mono text-xs">
                      <HeartPulse className="h-4 w-4" />
                      <span>Stage 9 · Software Health &amp; Technical Debt Engine</span>
                    </div>
                    <h2 className="text-xl font-bold tracking-tight text-white">Full Health &amp; Diagnostic Audit</h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-emerald-600/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <HeartPulse className="h-5 w-5" />
                  </div>
                </div>

                <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
                  Run Project Doctor's master diagnostic calculation. Aggregates telemetry and findings from the Repository Scanner,
                  Code Quality Analyzer, Security Audit Engine, Dependency Analyzer, and Architecture Graph into a unified,
                  100% deterministic Health Score (0–100), dimension breakdown, remediation technical debt estimate in developer hours,
                  and an actionable Fix First priority queue.
                </p>

                {/* Diagnostic Prerequisites Checklist */}
                <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                  <h4 className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                    Diagnostic Prerequisites Check
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2.5 text-xs font-mono">
                    <div className={`p-2.5 rounded-lg border flex items-center space-x-2 ${
                      scan ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-slate-800 bg-slate-950/40 text-slate-500'
                    }`}>
                      {scan ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" /> : <AlertCircle className="h-3.5 w-3.5 shrink-0" />}
                      <span>Scan (Stage 4)</span>
                    </div>
                    <div className={`p-2.5 rounded-lg border flex items-center space-x-2 ${
                      qualityAnalysis ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                    }`}>
                      {qualityAnalysis ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                      <span>Quality (Stage 5)</span>
                    </div>
                    <div className={`p-2.5 rounded-lg border flex items-center space-x-2 ${
                      securityAnalysis ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                    }`}>
                      {securityAnalysis ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                      <span>Security (Stage 6)</span>
                    </div>
                    <div className={`p-2.5 rounded-lg border flex items-center space-x-2 ${
                      dependencyAnalysis ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                    }`}>
                      {dependencyAnalysis ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                      <span>Deps (Stage 7)</span>
                    </div>
                    <div className={`p-2.5 rounded-lg border flex items-center space-x-2 ${
                      architectureAnalysis ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300' : 'border-amber-500/30 bg-amber-950/20 text-amber-300'
                    }`}>
                      {architectureAnalysis ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" /> : <AlertTriangle className="h-3.5 w-3.5 shrink-0" />}
                      <span>Arch (Stage 8)</span>
                    </div>
                  </div>
                  {(!qualityAnalysis || !securityAnalysis || !dependencyAnalysis || !architectureAnalysis) && (
                    <p className="text-[11px] text-amber-400 font-sans pt-1">
                      Note: Stages 5 through 8 must be analyzed before running the master health diagnostic.
                    </p>
                  )}
                </div>

                {healthError && (
                  <div className="p-3.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center space-x-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                    <span>{healthError}</span>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-slate-400">
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Deterministic Math</strong>
                    <span>Transparent scoring formulas with zero random numbers</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Technical Debt Model</strong>
                    <span>Severity-weighted remediation effort in developer hours</span>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                    <strong className="text-white block font-semibold">Priority Action Queue</strong>
                    <span>Strictly sorted Fix First list for highest impact</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleStartHealthAnalysis}
                    disabled={project.status !== 'READY'}
                    className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <HeartPulse className="h-4 w-4" />
                    <span>Run Health Diagnostic</span>
                  </button>
                </div>
              </div>
            )}

            {/* Live Health Analysis Progress Tracker */}
            {analyzingHealth && (
              <div className="bg-[#0d1322] border border-emerald-500/40 rounded-xl p-6 sm:p-8 space-y-5 shadow-2xl">
                <div className="flex items-center space-x-3">
                  <Loader2 className="h-5 w-5 animate-spin text-emerald-400" />
                  <div>
                    <h3 className="text-base font-semibold text-white">Running Master Health Diagnostic...</h3>
                    <p className="text-xs text-slate-400">Deterministic scoring, technical debt calculation &amp; priority ranking</p>
                  </div>
                </div>

                <div className="space-y-2.5 pt-2">
                  {healthStages.map((stageName, idx) => (
                    <div key={idx} className="flex items-center space-x-3 text-xs font-mono">
                      {idx < healthStepIndex ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : idx === healthStepIndex ? (
                        <Loader2 className="h-4 w-4 text-emerald-400 animate-spin shrink-0" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span
                        className={
                          idx < healthStepIndex
                            ? 'text-emerald-300 line-through opacity-70'
                            : idx === healthStepIndex
                            ? 'text-emerald-300 font-medium'
                            : 'text-slate-500'
                        }
                      >
                        {stageName}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Render Health Dashboard when Analysis Complete */}
            {healthAnalysis && (
              <HealthDashboard
                projectId={project.id}
                analysis={healthAnalysis}
                onReanalyze={handleStartHealthAnalysis}
                analyzing={analyzingHealth}
                onNavigateTab={(tab: string) => setActiveTab(tab as any)}
              />
            )}
          </div>
        )}

        {/* Tab 7: Ask My Codebase Q&A (Stage 11) */}
        {scan && activeTab === 'qa' && (
          <div className="space-y-6">
            <AskCodebase projectId={project.id} projectName={project.name} />
          </div>
        )}

        {/* Tab 8: Analysis History & Trends (Stage 12) */}
        {scan && activeTab === 'history' && (
          <div className="space-y-6">
            <HistoryDashboard
              projectId={project.id}
              projectName={project.name}
              onNavigateTab={(tab: string) => setActiveTab(tab as any)}
            />
          </div>
        )}

        {/* Tab: Doctor's Prescription & Auto-Fix Section */}
        {activeTab === 'prescription' && (
          <PrescriptionDashboard
            projectId={project.id}
            projectName={project.name}
          />
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
            <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
              <div className="flex items-center space-x-3 text-rose-400">
                <AlertCircle className="h-6 w-6" />
                <h3 className="text-base font-semibold text-white">Delete Project</h3>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Are you sure you want to permanently delete <strong className="text-white">{project.name}</strong>? This will remove all database records, scan telemetry, and purge extracted source files from disk.
              </p>
              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={deleting}
                  className="px-4 py-2 rounded-lg border border-slate-800 text-xs text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition disabled:opacity-50"
                >
                  {deleting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Deleting...</span>
                    </>
                  ) : (
                    <span>Confirm Delete</span>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Executive Diagnostic Audit Report Modal */}
        <DiagnosticReportModal
          isOpen={showAuditModal}
          onClose={() => setShowAuditModal(false)}
          project={project}
          health={healthAnalysis}
          scan={scan}
          securityAnalysis={securityAnalysis}
          qualityAnalysis={qualityAnalysis}
          dependencyAnalysis={dependencyAnalysis}
          architectureAnalysis={architectureAnalysis}
        />
      </div>
    </AppShell>
  )
}
