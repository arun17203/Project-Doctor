import React, { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  Database,
  Server,
  FolderPlus,
  FileArchive,
  GitBranch,
  ArrowRight,
  Trash2,
  HardDrive,
  Loader2,
  Search,
  RefreshCw
} from 'lucide-react'
import { checkHealth, type HealthCheckResponse } from '../services/api'
import { projectService } from '../services/projectService'
import type { Project } from '../types/project'
import { AppShell } from '../components/layout/AppShell'
import { StatusBadge } from '../components/common/StatusBadge'
import { EmptyState, ErrorState } from '../components/common/EmptyState'
import { useToast } from '../context/ToastContext'
import { useDocumentTitle } from '../hooks/useDocumentTitle'

export default function DashboardPage() {
  useDocumentTitle('Project Doctor', 'Dashboard')
  const { success, error: toastError } = useToast()

  const [health, setHealth] = useState<HealthCheckResponse | null>(null)
  const [loadingHealth, setLoadingHealth] = useState(true)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [lastCheck, setLastCheck] = useState<string>('')

  const [projects, setProjects] = useState<Project[]>([])
  const [loadingProjects, setLoadingProjects] = useState(true)
  const [projectsError, setProjectsError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const fetchHealth = async () => {
    setLoadingHealth(true)
    setHealthError(null)
    try {
      const data = await checkHealth()
      setHealth(data)
      setLastCheck(new Date().toLocaleTimeString())
    } catch (err: any) {
      console.error('Health check failed:', err)
      setHealthError(err.message || 'Failed to connect to backend server')
      setHealth(null)
    } finally {
      setLoadingHealth(false)
    }
  }

  const fetchProjects = async () => {
    setLoadingProjects(true)
    setProjectsError(null)
    try {
      const list = await projectService.getProjects()
      setProjects(list)
    } catch (err: any) {
      console.error('Failed to fetch projects:', err)
      setProjectsError(err.response?.data?.detail || 'Failed to load projects.')
    } finally {
      setLoadingProjects(false)
    }
  }

  useEffect(() => {
    fetchHealth()
    fetchProjects()
    const interval = setInterval(fetchHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleDeleteProject = async (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.stopPropagation()
    e.preventDefault()
    if (!window.confirm(`Are you sure you want to permanently delete "${projectName}"?`)) {
      return
    }
    setDeletingId(projectId)
    try {
      await projectService.deleteProject(projectId)
      setProjects((prev) => prev.filter((p) => p.id !== projectId))
      success('Project Deleted', `"${projectName}" has been removed.`)
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || 'Failed to delete project'
      toastError('Delete Failed', errMsg)
    } finally {
      setDeletingId(null)
    }
  }

  const filteredProjects = useMemo(() => {
    if (!searchTerm.trim()) return projects
    const q = searchTerm.toLowerCase()
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.description && p.description.toLowerCase().includes(q)) ||
        (p.source_url && p.source_url.toLowerCase().includes(q))
    )
  }, [projects, searchTerm])

  const stages = [
    { num: 1, name: 'Core Architecture & Setup', desc: 'FastAPI, React 19, SQLAlchemy, Alembic, Tailwind v4', done: true },
    { num: 2, name: 'Authentication System', desc: 'JWT, bcrypt, User registration & login, protected routes', done: true },
    { num: 3, name: 'Project Import & Ingestion', desc: 'Safe ZIP upload & GitHub repository clone, sandboxed storage', done: true },
    { num: 4, name: 'Repository Scanner', desc: 'LOC, languages, directory tree & file categorization', done: true },
    { num: 5, name: 'Code Quality Analyzer', desc: 'AST cyclomatic complexity, long functions, duplicate detection', done: true },
    { num: 6, name: 'Security Audit Engine', desc: 'Secret scanning with masking, eval/exec & SQLi rules', done: true },
    { num: 7, name: 'Dependency Analyzer', desc: 'Real Google OSV advisories, PyPI/npm/Maven version checks, lockfile resolution', done: true },
    { num: 8, name: 'Architecture Graph', desc: 'Import mapping, layer classification & circular dependency check', done: true },
    { num: 9, name: 'Health & Tech Debt Engine', desc: 'Deterministic weighted score & remediation hours formula', done: true },
    { num: 10, name: 'AI Problem Explainer', desc: 'Google Gemini root-cause & remediation recommendations', done: true },
    { num: 11, name: 'Ask My Codebase Q&A', desc: 'Grounded repository assistant with strict evidence citations', done: true },
    { num: 12, name: 'Analysis History & Trends', desc: 'Multi-version comparison & health score tracking', done: true },
    { num: 13, name: 'Developer UI/UX Polish', desc: 'High-contrast developer tool design system, AppShell & modals', done: true },
    { num: 14, name: 'Automated Testing', desc: '95+ Pytest suite, Vitest component tests & CI/CD workflow', done: true },
    { num: 15, name: 'Deployment & Portfolio Ready', desc: 'Docker packaging, production healthchecks & documentation suite', done: true }
  ]

  return (
    <AppShell breadcrumbs={[{ label: 'Dashboard' }]}>
      <div className="p-4 sm:p-6 lg:p-8 space-y-8 max-w-7xl mx-auto w-full">
        {/* Real Projects Dashboard Section */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-xl font-bold tracking-tight text-white">Your Software Projects</h2>
                <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                  {projects.length}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Manage repositories and imported codebases prepared for automated health diagnostics.
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => {
                  fetchHealth()
                  fetchProjects()
                }}
                disabled={loadingHealth || loadingProjects}
                className="p-2 rounded-lg text-slate-400 hover:text-white bg-slate-900 border border-slate-800 hover:border-slate-700 transition"
                title="Refresh Projects & Telemetry"
              >
                <RefreshCw className={`h-4 w-4 ${loadingHealth || loadingProjects ? 'animate-spin text-blue-400' : ''}`} />
              </button>

              <Link
                to="/projects/new"
                className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-sm"
              >
                <FolderPlus className="h-4 w-4" />
                <span>New Project</span>
              </Link>
            </div>
          </div>

          {/* Search Filter when projects exist */}
          {projects.length > 0 && (
            <div className="relative max-w-md">
              <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter projects by name or description..."
                className="w-full bg-[#0d1322] border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 font-sans"
              />
            </div>
          )}

          {/* Projects Display: List, Loading, or Empty State */}
          {loadingProjects ? (
            <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-12 text-center text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500 mx-auto mb-2" />
              <p className="text-xs font-mono uppercase tracking-wider">Loading project database...</p>
            </div>
          ) : projectsError ? (
            <ErrorState
              title="Failed to Load Projects"
              message={projectsError}
              onRetry={fetchProjects}
            />
          ) : projects.length === 0 ? (
            <EmptyState
              title="No software projects yet"
              message="Import a codebase by uploading a ZIP archive or providing a public GitHub repository URL to start diagnostics."
              actionLabel="Import First Project"
              actionHref="/projects/new"
              actionIcon={<FolderPlus className="h-4 w-4" />}
            />
          ) : filteredProjects.length === 0 ? (
            <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-8 text-center text-slate-400 space-y-2">
              <p className="text-sm text-slate-300">No projects match &ldquo;{searchTerm}&rdquo;</p>
              <button
                onClick={() => setSearchTerm('')}
                className="text-xs text-blue-400 hover:text-blue-300 underline font-mono"
              >
                Clear filter
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredProjects.map((proj) => (
                <Link
                  key={proj.id}
                  to={`/projects/${proj.id}`}
                  className="group bg-[#0d1322] hover:bg-[#0f172a] border border-slate-800 hover:border-slate-700 rounded-xl p-5 flex flex-col justify-between transition-all duration-150 shadow-sm"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center space-x-2 min-w-0">
                        <div className="p-1.5 rounded-md bg-slate-900 border border-slate-800 text-blue-400 shrink-0">
                          {proj.source_type === 'zip' ? <FileArchive className="h-4 w-4" /> : <GitBranch className="h-4 w-4" />}
                        </div>
                        <span className="text-[10px] font-mono uppercase text-slate-400 font-medium">
                          {proj.source_type}
                        </span>
                      </div>

                      <StatusBadge status={proj.status} size="sm" />
                    </div>

                    <div>
                      <h3 className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors truncate">
                        {proj.name}
                      </h3>
                      <p className="text-xs text-slate-400 line-clamp-2 mt-1">
                        {proj.description || (proj.source_type === 'zip' ? proj.original_filename : proj.source_url) || 'No description'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-4 mt-4 border-t border-slate-800/80 text-[11px] text-slate-500">
                    <span className="font-mono">{new Date(proj.created_at).toLocaleDateString()}</span>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => handleDeleteProject(e, proj.id, proj.name)}
                        disabled={deletingId === proj.id}
                        className="p-1 rounded text-slate-500 hover:text-rose-400 transition"
                        title="Delete Project"
                      >
                        {deletingId === proj.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                      </button>
                      <ArrowRight className="h-3.5 w-3.5 text-slate-400 group-hover:text-blue-400 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Live System Telemetry Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-mono uppercase tracking-wider">FastAPI Engine</span>
              <Server className="h-4 w-4 text-blue-400" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-semibold text-white font-mono">
                {health?.status === 'healthy' ? '200 OK' : healthError ? 'OFFLINE' : 'CONNECTING'}
              </span>
            </div>
            <div className="text-xs text-slate-400 flex items-center space-x-1.5">
              {health?.status === 'healthy' ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Version {health.version} • {health.environment}</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                  <span className="truncate">{healthError || 'Reconnecting...'}</span>
                </>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-mono uppercase tracking-wider">Database Engine</span>
              <Database className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-semibold text-white font-mono">
                {health?.database === 'connected' ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <div className="text-xs text-slate-400 flex items-center space-x-1.5">
              {health?.database === 'connected' ? (
                <>
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>SQLAlchemy 2.0 • Ingestion Active</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                  <span>Database check pending</span>
                </>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-mono uppercase tracking-wider">Ingestion Engine</span>
              <HardDrive className="h-4 w-4 text-purple-400" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-semibold text-white font-mono">READY</span>
            </div>
            <div className="text-xs text-slate-400 flex items-center space-x-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-purple-400" />
              <span>Safe ZIP &amp; Git Sandboxing</span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-[#0d1322] p-5 space-y-3">
            <div className="flex items-center justify-between text-slate-400">
              <span className="text-xs font-mono uppercase tracking-wider">Telemetry</span>
              <Activity className="h-4 w-4 text-amber-400" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-sm font-mono text-slate-200 truncate">
                {health?.timestamp ? new Date(health.timestamp).toLocaleTimeString() : lastCheck || 'Active'}
              </span>
            </div>
            <div className="text-xs text-slate-400 flex items-center space-x-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
              <span>Auto-polling every 10s</span>
            </div>
          </div>
        </div>

        {/* 15-Stage Roadmap Progress Board */}
        <div className="rounded-xl border border-slate-800 bg-[#0d1322] p-6 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-lg font-semibold text-white">15-Stage Project Roadmap</h2>
              <p className="text-xs text-slate-400">Step-by-step verified construction of Project Doctor MCA Final-Year Project</p>
            </div>
            <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-md border border-emerald-500/20">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>All 15 Stages Complete (15 of 15 • Production Ready)</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {stages.map((stage) => (
              <div
                key={stage.num}
                className={`p-3.5 rounded-lg border transition-all ${
                  stage.done
                    ? 'border-emerald-500/30 bg-emerald-950/10'
                    : stage.num === 14
                    ? 'border-blue-500/40 bg-blue-950/15'
                    : 'border-slate-800/80 bg-slate-900/30 opacity-70'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                        stage.done
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                          : stage.num === 14
                          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/40'
                          : 'bg-slate-800 text-slate-500 border border-slate-700'
                      }`}
                    >
                      {stage.num}
                    </span>
                    <h4 className="text-xs font-medium text-slate-200">{stage.name}</h4>
                  </div>
                  {stage.done ? (
                    <span className="text-[10px] font-mono text-emerald-400 uppercase font-semibold">Done</span>
                  ) : stage.num === 14 ? (
                    <span className="text-[10px] font-mono text-blue-400 uppercase font-semibold animate-pulse">Next</span>
                  ) : (
                    <span className="text-[10px] font-mono text-slate-500 uppercase">Queued</span>
                  )}
                </div>
                <p className="text-[11px] text-slate-400 mt-2 pl-7">{stage.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppShell>
  )
}
