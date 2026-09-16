import React, { useState, useEffect, useMemo } from 'react'
import {
  History,
  TrendingUp,
  TrendingDown,
  Minus,
  Play,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Code2,
  Boxes,
  Network,
  HeartPulse,
  Flame,
  FileCode2,
  ChevronRight,
  X,
  Scale,
  RefreshCw,
  GitCompare,
  Layers,
  Info,
} from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  AreaChart,
  Area,
} from 'recharts'
import { projectService } from '../../services/projectService'
import type {
  SnapshotSummary,
  SnapshotDetail,
  VersionComparisonResponse,
  MetricDelta,
} from '../../types/history'

interface HistoryDashboardProps {
  projectId: string
  projectName: string
  onNavigateTab?: (tab: string) => void
}

type TrendMetricKey =
  | 'health'
  | 'security'
  | 'quality'
  | 'dependencies'
  | 'architecture'
  | 'maintainability'
  | 'debt'
  | 'issues'

export const HistoryDashboard: React.FC<HistoryDashboardProps> = ({
  projectId,
  projectName,
  onNavigateTab,
}) => {
  const [snapshots, setSnapshots] = useState<SnapshotSummary[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Running full analysis
  const [runningAnalysis, setRunningAnalysis] = useState(false)
  const [analysisStepIndex, setAnalysisStepIndex] = useState(0)
  const [analysisNote, setAnalysisNote] = useState('')
  const [showRunModal, setShowRunModal] = useState(false)

  // Comparison State
  const [compareFrom, setCompareFrom] = useState<number | null>(null)
  const [compareTo, setCompareTo] = useState<number | null>(null)
  const [comparison, setComparison] = useState<VersionComparisonResponse | null>(null)
  const [comparing, setComparing] = useState(false)
  const [comparisonError, setComparisonError] = useState<string | null>(null)

  // Details Modal State
  const [selectedSnapshot, setSelectedSnapshot] = useState<SnapshotDetail | null>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)

  // Selected Trend Metric for Chart
  const [activeMetric, setActiveMetric] = useState<TrendMetricKey>('health')

  const analysisStages = [
    'Repository Scanner: Analyzing source tree & file discovery...',
    'Code Quality: Calculating AST cyclomatic complexity & duplicate blocks...',
    'Security Audit: Scanning for hardcoded secrets, injection & unsafe calls...',
    'Dependencies: Querying Google OSV database & manifest advisories...',
    'Architecture Graph: Resolving import topology & circular cycles...',
    'Health Diagnostic: Calculating weighted score & technical debt hours...',
    'History Snapshot Engine: Creating immutable Version record...',
  ]

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await projectService.getAnalysisHistory(projectId, page, 50)
      setSnapshots(data.items)
      setTotalCount(data.total)

      // Default comparison if at least 2 versions exist
      if (data.items.length >= 2 && !compareFrom && !compareTo) {
        const sorted = [...data.items].sort((a, b) => a.version_number - b.version_number)
        const v1 = sorted[0].version_number
        const vLatest = sorted[sorted.length - 1].version_number
        setCompareFrom(v1)
        setCompareTo(vLatest)
      } else if (data.items.length === 1 && !compareFrom) {
        setCompareFrom(data.items[0].version_number)
        setCompareTo(data.items[0].version_number)
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load analysis history.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [projectId, page])

  // Automatically trigger comparison when both from and to are selected and distinct
  useEffect(() => {
    if (!compareFrom || !compareTo) return

    const loadComparison = async () => {
      setComparing(true)
      setComparisonError(null)
      try {
        const comp = await projectService.compareVersions(projectId, compareFrom, compareTo)
        setComparison(comp)
      } catch (err: any) {
        setComparisonError(
          err?.response?.data?.detail || 'Failed to compare selected versions.'
        )
        setComparison(null)
      } finally {
        setComparing(false)
      }
    }

    loadComparison()
  }, [projectId, compareFrom, compareTo])

  const handleStartAnalysisRun = async () => {
    setShowRunModal(false)
    setRunningAnalysis(true)
    setAnalysisStepIndex(0)
    setError(null)

    // Simulate stepped progress tracker
    const interval = setInterval(() => {
      setAnalysisStepIndex((prev) => (prev < analysisStages.length - 1 ? prev + 1 : prev))
    }, 2000)

    try {
      await projectService.runFullAnalysis(projectId, analysisNote || undefined)
      setAnalysisNote('')
      await fetchHistory()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Analysis run failed.')
    } finally {
      clearInterval(interval)
      setRunningAnalysis(false)
    }
  }

  const handleOpenSnapshotDetails = async (version: number) => {
    setLoadingDetails(true)
    try {
      const details = await projectService.getSnapshotDetails(projectId, version)
      setSelectedSnapshot(details)
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to fetch snapshot details')
    } finally {
      setLoadingDetails(false)
    }
  }

  // Derived statistics: Current vs Previous
  const { currentSnap, previousSnap, healthDiff, debtDiff, criticalDiff } = useMemo(() => {
    if (snapshots.length === 0) {
      return { currentSnap: null, previousSnap: null, healthDiff: 0, debtDiff: 0, criticalDiff: 0 }
    }
    const current = snapshots[0] // sorted newest first
    const previous = snapshots.length > 1 ? snapshots[1] : null

    const hDiff = previous ? current.overall_score - previous.overall_score : 0
    const dDiff = previous ? current.technical_debt_hours - previous.technical_debt_hours : 0
    const cDiff = previous ? current.critical_count - previous.critical_count : 0

    return {
      currentSnap: current,
      previousSnap: previous,
      healthDiff: Math.round(hDiff * 10) / 10,
      debtDiff: Math.round(dDiff * 10) / 10,
      criticalDiff: cDiff,
    }
  }, [snapshots])

  // Chart data formatted chronologically (#1, #2, #3...)
  const chartData = useMemo(() => {
    return [...snapshots]
      .sort((a, b) => a.version_number - b.version_number)
      .map((s) => ({
        version: `#${s.version_number}`,
        rawVersion: s.version_number,
        date: new Date(s.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' }),
        health: s.overall_score,
        security: s.security_score,
        quality: s.quality_score,
        dependencies: s.dependency_score,
        architecture: s.architecture_score,
        maintainability: s.maintainability_score,
        testing: s.testing_score,
        debt: s.technical_debt_hours,
        criticalIssues: s.critical_count,
        highIssues: s.high_count,
        totalIssues: s.total_issues,
      }))
  }, [snapshots])

  const getDirectionBadge = (delta: MetricDelta) => {
    const isImproved = delta.direction === 'IMPROVED'
    const isWorsened = delta.direction === 'WORSENED'

    const color = isImproved
      ? 'text-emerald-400 bg-emerald-950/40 border-emerald-500/30'
      : isWorsened
      ? 'text-rose-400 bg-rose-950/40 border-rose-500/30'
      : 'text-slate-400 bg-slate-900 border-slate-700'

    const sign = delta.difference > 0 ? `+${delta.difference}` : `${delta.difference}`

    return (
      <span
        className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-mono font-semibold border ${color}`}
      >
        {isImproved ? (
          <TrendingUp className="h-3 w-3" />
        ) : isWorsened ? (
          <TrendingDown className="h-3 w-3" />
        ) : (
          <Minus className="h-3 w-3" />
        )}
        <span>
          {sign} {delta.unit}
        </span>
        <span className="text-[10px] uppercase opacity-75 font-normal">({delta.direction})</span>
      </span>
    )
  }

  return (
    <div className="space-y-8">
      {/* Top Header & Telemetry Strip */}
      <div className="p-6 rounded-2xl bg-[#0d1322] border border-slate-800 space-y-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2.5">
              <div className="h-8 w-8 rounded-lg bg-blue-600/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <History className="h-4 w-4" />
              </div>
              <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
                Stage 12 · Analysis History &amp; Trends
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-blue-950/60 text-blue-300 border border-blue-800/40">
                Immutable Snapshots
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight text-white">
              Project Diagnostic History
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Every completed analysis run records an immutable snapshot version. Track health
              trajectories, compare any two versions, and evaluate technical debt reductions over
              time.
            </p>
          </div>

          <div className="flex items-center space-x-3 shrink-0">
            <button
              onClick={() => setShowRunModal(true)}
              disabled={runningAnalysis}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-xs font-medium transition shadow-md disabled:opacity-50"
            >
              {runningAnalysis ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  <span>Run New Analysis Version</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Overview Metric Cards Grid */}
        {snapshots.length > 0 && currentSnap ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-slate-800/80">
            {/* 1. Current Health */}
            <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono uppercase text-[11px]">Latest Health</span>
                <HeartPulse className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {Math.round(currentSnap.overall_score)}
                  <span className="text-xs text-slate-500 font-normal">/100</span>
                </span>
                {previousSnap && healthDiff !== 0 && (
                  <span
                    className={`inline-flex items-center text-xs font-mono font-semibold ${
                      healthDiff > 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {healthDiff > 0 ? `+${healthDiff}` : healthDiff}
                    {healthDiff > 0 ? (
                      <TrendingUp className="h-3 w-3 ml-0.5" />
                    ) : (
                      <TrendingDown className="h-3 w-3 ml-0.5" />
                    )}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500">
                {previousSnap ? (
                  <span>
                    Previous: <strong className="text-slate-300 font-mono">{Math.round(previousSnap.overall_score)}</strong> (Version #{previousSnap.version_number})
                  </span>
                ) : (
                  <span>Initial Baseline Version</span>
                )}
              </div>
            </div>

            {/* 2. Technical Debt */}
            <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono uppercase text-[11px]">Technical Debt</span>
                <Clock className="h-4 w-4 text-amber-400" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {Math.round(currentSnap.technical_debt_hours)}
                  <span className="text-xs text-slate-500 font-normal">h</span>
                </span>
                {previousSnap && debtDiff !== 0 && (
                  <span
                    className={`inline-flex items-center text-xs font-mono font-semibold ${
                      debtDiff < 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {debtDiff > 0 ? `+${debtDiff}h` : `${debtDiff}h`}
                    {debtDiff < 0 ? (
                      <TrendingDown className="h-3 w-3 ml-0.5" />
                    ) : (
                      <TrendingUp className="h-3 w-3 ml-0.5" />
                    )}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500">
                Estimated remediation effort
              </div>
            </div>

            {/* 3. Critical Issues */}
            <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono uppercase text-[11px]">Critical Issues</span>
                <Flame className="h-4 w-4 text-rose-400" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">
                  {currentSnap.critical_count}
                </span>
                {previousSnap && criticalDiff !== 0 && (
                  <span
                    className={`inline-flex items-center text-xs font-mono font-semibold ${
                      criticalDiff < 0 ? 'text-emerald-400' : 'text-rose-400'
                    }`}
                  >
                    {criticalDiff > 0 ? `+${criticalDiff}` : criticalDiff}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-500">
                {currentSnap.high_count} High · {currentSnap.total_issues} Total issues
              </div>
            </div>

            {/* 4. Total Versions */}
            <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-mono uppercase text-[11px]">Recorded Versions</span>
                <Layers className="h-4 w-4 text-blue-400" />
              </div>
              <div className="flex items-baseline space-x-2">
                <span className="text-2xl font-bold text-white font-mono">
                  #{currentSnap.version_number}
                </span>
                <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-800/40">
                  LATEST
                </span>
              </div>
              <div className="text-[11px] text-slate-500">
                {totalCount} total historical snapshot{totalCount > 1 ? 's' : ''}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-6 px-4 rounded-xl bg-[#090d18] border border-slate-800 text-center space-y-2">
            <Info className="h-6 w-6 text-blue-400 mx-auto" />
            <h4 className="text-sm font-semibold text-white">No previous analysis available.</h4>
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              Run your first full analysis to record Version #1 baseline. Subsequent analyses will automatically generate chronological comparisons and trend lines.
            </p>
          </div>
        )}
      </div>

      {/* Live Pipeline Running Modal / Stepper */}
      {runningAnalysis && (
        <div className="p-6 rounded-2xl bg-[#0d1322] border border-blue-500/40 space-y-4 shadow-2xl">
          <div className="flex items-center space-x-3">
            <Loader2 className="h-5 w-5 animate-spin text-blue-400 shrink-0" />
            <div>
              <h3 className="text-base font-semibold text-white">
                Running Full Analysis Pipeline &amp; Recording Snapshot...
              </h3>
              <p className="text-xs text-slate-400">
                Executing static repository scanners, quality rules, security audits, and health diagnostics
              </p>
            </div>
          </div>

          <div className="space-y-2 pt-2 border-t border-slate-800">
            {analysisStages.map((stageName, idx) => (
              <div key={idx} className="flex items-center space-x-3 text-xs font-mono">
                {idx < analysisStepIndex ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : idx === analysisStepIndex ? (
                  <Loader2 className="h-4 w-4 text-blue-400 animate-spin shrink-0" />
                ) : (
                  <div className="h-4 w-4 rounded-full border border-slate-700 shrink-0" />
                )}
                <span
                  className={
                    idx < analysisStepIndex
                      ? 'text-emerald-300 line-through opacity-70'
                      : idx === analysisStepIndex
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

      {/* Multi-Metric Trend Chart */}
      {snapshots.length > 0 && (
        <div className="p-6 rounded-2xl bg-[#0d1322] border border-slate-800 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white tracking-tight">
                Historical Trend Trajectory
              </h3>
              <p className="text-xs text-slate-400">
                Multi-metric evolution over successive project versions
              </p>
            </div>

            {/* Metric Switcher Pills */}
            <div className="flex flex-wrap items-center gap-1.5 bg-[#090d18] p-1.5 rounded-xl border border-slate-800">
              <button
                onClick={() => setActiveMetric('health')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'health'
                    ? 'bg-emerald-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Health
              </button>
              <button
                onClick={() => setActiveMetric('security')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'security'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Security
              </button>
              <button
                onClick={() => setActiveMetric('quality')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'quality'
                    ? 'bg-purple-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Quality
              </button>
              <button
                onClick={() => setActiveMetric('dependencies')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'dependencies'
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Dependencies
              </button>
              <button
                onClick={() => setActiveMetric('architecture')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'architecture'
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Architecture
              </button>
              <button
                onClick={() => setActiveMetric('debt')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'debt'
                    ? 'bg-cyan-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Tech Debt
              </button>
              <button
                onClick={() => setActiveMetric('issues')}
                className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                  activeMetric === 'issues'
                    ? 'bg-red-600 text-white shadow-xs'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Issues
              </button>
            </div>
          </div>

          {/* Chart Canvas */}
          <div className="h-[280px] w-full pt-2">
            {chartData.length === 1 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl space-y-2">
                <Scale className="h-8 w-8 text-blue-400" />
                <h4 className="text-sm font-semibold text-white">Version #1 Baseline Established</h4>
                <p className="text-xs text-slate-400 max-w-sm">
                  A single analysis has been recorded. Run additional analysis runs after making code changes to see trend lines connect across versions.
                </p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorMetric" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor={
                          activeMetric === 'health'
                            ? '#10b981'
                            : activeMetric === 'security'
                            ? '#f43f5e'
                            : activeMetric === 'quality'
                            ? '#a855f7'
                            : activeMetric === 'dependencies'
                            ? '#f59e0b'
                            : activeMetric === 'architecture'
                            ? '#6366f1'
                            : activeMetric === 'debt'
                            ? '#06b6d4'
                            : '#ef4444'
                        }
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor={
                          activeMetric === 'health'
                            ? '#10b981'
                            : activeMetric === 'security'
                            ? '#f43f5e'
                            : activeMetric === 'quality'
                            ? '#a855f7'
                            : activeMetric === 'dependencies'
                            ? '#f59e0b'
                            : activeMetric === 'architecture'
                            ? '#6366f1'
                            : activeMetric === 'debt'
                            ? '#06b6d4'
                            : '#ef4444'
                        }
                        stopOpacity={0}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="version"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}
                  />
                  <YAxis
                    stroke="#64748b"
                    domain={
                      activeMetric === 'debt' || activeMetric === 'issues'
                        ? [0, 'auto']
                        : [0, 100]
                    }
                    tick={{ fill: '#94a3b8', fontSize: 11, fontFamily: 'monospace' }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0d1322',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                      color: '#f8fafc',
                      fontFamily: 'monospace',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey={
                      activeMetric === 'health'
                        ? 'health'
                        : activeMetric === 'security'
                        ? 'security'
                        : activeMetric === 'quality'
                        ? 'quality'
                        : activeMetric === 'dependencies'
                        ? 'dependencies'
                        : activeMetric === 'architecture'
                        ? 'architecture'
                        : activeMetric === 'debt'
                        ? 'debt'
                        : 'criticalIssues'
                    }
                    name={
                      activeMetric === 'health'
                        ? 'Health Score'
                        : activeMetric === 'security'
                        ? 'Security Score'
                        : activeMetric === 'quality'
                        ? 'Quality Score'
                        : activeMetric === 'dependencies'
                        ? 'Dependencies Score'
                        : activeMetric === 'architecture'
                        ? 'Architecture Score'
                        : activeMetric === 'debt'
                        ? 'Technical Debt (Hours)'
                        : 'Critical Issues'
                    }
                    stroke={
                      activeMetric === 'health'
                        ? '#10b981'
                        : activeMetric === 'security'
                        ? '#f43f5e'
                        : activeMetric === 'quality'
                        ? '#a855f7'
                        : activeMetric === 'dependencies'
                        ? '#f59e0b'
                        : activeMetric === 'architecture'
                        ? '#6366f1'
                        : activeMetric === 'debt'
                        ? '#06b6d4'
                        : '#ef4444'
                    }
                    strokeWidth={2.5}
                    fillOpacity={1}
                    fill="url(#colorMetric)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      )}

      {/* Version Comparison Section */}
      {snapshots.length >= 2 && (
        <div className="p-6 rounded-2xl bg-[#0d1322] border border-slate-800 space-y-6 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <GitCompare className="h-4 w-4 text-indigo-400" />
                <h3 className="text-base font-bold text-white tracking-tight">
                  Version Comparison
                </h3>
              </div>
              <p className="text-xs text-slate-400">
                Deterministic diffing of scores, issues, debt, and repository files
              </p>
            </div>

            {/* Version Selectors */}
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-mono">From:</span>
                <select
                  value={compareFrom || ''}
                  onChange={(e) => setCompareFrom(Number(e.target.value))}
                  className="bg-[#090d18] border border-slate-800 text-xs font-mono text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-hidden focus:border-indigo-500"
                >
                  {snapshots.map((s) => (
                    <option key={`from-${s.version_number}`} value={s.version_number}>
                      Version #{s.version_number} ({Math.round(s.overall_score)} pts)
                    </option>
                  ))}
                </select>
              </div>

              <ArrowRight className="h-3.5 w-3.5 text-slate-500" />

              <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400 font-mono">To:</span>
                <select
                  value={compareTo || ''}
                  onChange={(e) => setCompareTo(Number(e.target.value))}
                  className="bg-[#090d18] border border-slate-800 text-xs font-mono text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-hidden focus:border-indigo-500"
                >
                  {snapshots.map((s) => (
                    <option key={`to-${s.version_number}`} value={s.version_number}>
                      Version #{s.version_number} ({Math.round(s.overall_score)} pts)
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {comparing && (
            <div className="py-8 flex items-center justify-center space-x-2 text-xs text-slate-400 font-mono">
              <Loader2 className="h-4 w-4 animate-spin text-indigo-400" />
              <span>Calculating deterministic version diff...</span>
            </div>
          )}

          {comparisonError && (
            <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 text-xs text-rose-300">
              {comparisonError}
            </div>
          )}

          {!comparing && comparison && (
            <div className="space-y-6">
              {/* Deterministic Change Headline & Summary Box */}
              <div
                className={`p-4 rounded-xl border space-y-1.5 ${
                  comparison.health_delta.direction === 'IMPROVED'
                    ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-200'
                    : comparison.health_delta.direction === 'WORSENED'
                    ? 'bg-rose-950/20 border-rose-500/30 text-rose-200'
                    : 'bg-slate-900 border-slate-800 text-slate-200'
                }`}
              >
                <div className="text-xs font-mono uppercase font-bold tracking-wider">
                  {comparison.summary_headline}
                </div>
                <p className="text-xs sm:text-sm leading-relaxed font-sans opacity-95">
                  {comparison.summary_text}
                </p>
              </div>

              {/* Side-by-Side Metric Delta Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {/* Health */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Health Score</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.health_delta.from_value} →{' '}
                      <strong className="text-white">{comparison.health_delta.to_value}</strong>
                    </span>
                    {getDirectionBadge(comparison.health_delta)}
                  </div>
                </div>

                {/* Security */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Security Score</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.security_delta.from_value} →{' '}
                      <strong className="text-white">{comparison.security_delta.to_value}</strong>
                    </span>
                    {getDirectionBadge(comparison.security_delta)}
                  </div>
                </div>

                {/* Code Quality */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Code Quality</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.quality_delta.from_value} →{' '}
                      <strong className="text-white">{comparison.quality_delta.to_value}</strong>
                    </span>
                    {getDirectionBadge(comparison.quality_delta)}
                  </div>
                </div>

                {/* Technical Debt */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Technical Debt</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.technical_debt_delta.from_value}h →{' '}
                      <strong className="text-white">
                        {comparison.technical_debt_delta.to_value}h
                      </strong>
                    </span>
                    {getDirectionBadge(comparison.technical_debt_delta)}
                  </div>
                </div>

                {/* Critical Issues */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Critical Issues</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.critical_issues_delta.from_value} →{' '}
                      <strong className="text-white">
                        {comparison.critical_issues_delta.to_value}
                      </strong>
                    </span>
                    {getDirectionBadge(comparison.critical_issues_delta)}
                  </div>
                </div>

                {/* High Issues */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">High Issues</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.high_issues_delta.from_value} →{' '}
                      <strong className="text-white">
                        {comparison.high_issues_delta.to_value}
                      </strong>
                    </span>
                    {getDirectionBadge(comparison.high_issues_delta)}
                  </div>
                </div>

                {/* Vulnerable Dependencies */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Vulnerable Deps</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.vulnerable_deps_delta.from_value} →{' '}
                      <strong className="text-white">
                        {comparison.vulnerable_deps_delta.to_value}
                      </strong>
                    </span>
                    {getDirectionBadge(comparison.vulnerable_deps_delta)}
                  </div>
                </div>

                {/* Architecture Cycles */}
                <div className="p-3.5 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                  <div className="text-[11px] font-mono text-slate-400 uppercase">Architecture Cycles</div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-sm font-mono text-slate-300">
                      {comparison.cycles_delta.from_value} →{' '}
                      <strong className="text-white">
                        {comparison.cycles_delta.to_value}
                      </strong>
                    </span>
                    {getDirectionBadge(comparison.cycles_delta)}
                  </div>
                </div>
              </div>

              {/* Repository File Differences Box */}
              <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-semibold text-slate-300 uppercase">
                    Repository File Diff
                  </span>
                  <span className="text-[11px] font-mono text-slate-500">
                    {comparison.file_diff.total_files_before} files →{' '}
                    {comparison.file_diff.total_files_after} files
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
                  <span className="text-emerald-400">
                    +{comparison.file_diff.files_added} added
                  </span>
                  <span className="text-rose-400">
                    -{comparison.file_diff.files_removed} removed
                  </span>
                  <span className="text-amber-400">
                    ~{comparison.file_diff.files_modified} modified
                  </span>
                </div>

                {comparison.file_diff.sample_added.length > 0 && (
                  <div className="space-y-1 text-xs">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Sample Added:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {comparison.file_diff.sample_added.map((path, pIdx) => (
                        <span
                          key={pIdx}
                          className="px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/40 text-[11px] font-mono"
                        >
                          +{path}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {comparison.file_diff.sample_removed.length > 0 && (
                  <div className="space-y-1 text-xs">
                    <span className="text-[10px] font-mono text-slate-500 uppercase">
                      Sample Removed:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {comparison.file_diff.sample_removed.map((path, pIdx) => (
                        <span
                          key={pIdx}
                          className="px-2 py-0.5 rounded bg-rose-950/40 text-rose-300 border border-rose-800/40 text-[11px] font-mono"
                        >
                          -{path}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Version History Table */}
      <div className="p-6 rounded-2xl bg-[#0d1322] border border-slate-800 space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h3 className="text-base font-bold text-white tracking-tight">
              All Recorded Analysis Versions
            </h3>
            <p className="text-xs text-slate-400">
              Chronological log of immutable snapshots for {projectName}
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">{totalCount} total versions</span>
        </div>

        {snapshots.length === 0 ? (
          <div className="py-8 text-center text-xs text-slate-500 font-mono">
            No analysis snapshots recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs font-sans">
              <thead className="bg-[#090d18] border-b border-slate-800 text-[11px] font-mono uppercase text-slate-400">
                <tr>
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Date &amp; Time</th>
                  <th className="py-3 px-4">Health Score</th>
                  <th className="py-3 px-4">Technical Debt</th>
                  <th className="py-3 px-4">Issues Breakdown</th>
                  <th className="py-3 px-4">Files / LOC</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-[#0d1322]">
                {snapshots.map((snap) => (
                  <tr key={snap.id} className="hover:bg-slate-850/40 transition">
                    <td className="py-3.5 px-4 font-mono font-bold text-white flex items-center space-x-2">
                      <span className="h-6 w-6 rounded-md bg-blue-600/20 text-blue-400 border border-blue-500/30 flex items-center justify-center text-xs">
                        #{snap.version_number}
                      </span>
                      {snap.version_number === snapshots[0].version_number && (
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 px-1.5 py-0.2 rounded border border-emerald-800/40">
                          LATEST
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {new Date(snap.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono font-semibold border ${
                          snap.overall_score >= 80
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : snap.overall_score >= 60
                            ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                        }`}
                      >
                        {Math.round(snap.overall_score)} / 100
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      {Math.round(snap.technical_debt_hours)}h
                    </td>
                    <td className="py-3.5 px-4 font-mono text-xs">
                      <span className="text-rose-400">{snap.critical_count} crit</span> ·{' '}
                      <span className="text-orange-400">{snap.high_count} high</span> ·{' '}
                      <span className="text-slate-400">{snap.total_issues} total</span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-400">
                      {snap.total_files} files · {snap.total_lines.toLocaleString()} LOC
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleOpenSnapshotDetails(snap.version_number)}
                        className="px-2.5 py-1 rounded-lg border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 transition"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Run Full Analysis Modal */}
      {showRunModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-[#0d1322] border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center space-x-3 text-white">
              <div className="h-9 w-9 rounded-xl bg-blue-600/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
                <Play className="h-4 w-4 fill-current" />
              </div>
              <div>
                <h3 className="text-base font-bold">Run New Analysis Version</h3>
                <p className="text-xs text-slate-400">
                  Executes Stages 4 through 9 and records Version #{totalCount + 1}
                </p>
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-mono text-slate-400">
                Optional Version Note / Changelog:
              </label>
              <textarea
                value={analysisNote}
                onChange={(e) => setAnalysisNote(e.target.value)}
                placeholder="e.g., Refactored user authentication and upgraded vulnerable lodash dependency"
                rows={2}
                className="w-full bg-[#090d18] border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-hidden focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowRunModal(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-400 hover:text-white transition"
              >
                Cancel
              </button>
              <button
                onClick={handleStartAnalysisRun}
                className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition flex items-center space-x-1.5"
              >
                <span>Start Full Analysis</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Snapshot Read-Only Inspection Modal */}
      {selectedSnapshot && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div
            className="bg-[#0d1322] border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col my-auto max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-[#0a0f1d]">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="h-6 px-2 rounded bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-mono font-bold flex items-center">
                    Snapshot Version #{selectedSnapshot.version_number}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {new Date(selectedSnapshot.created_at).toLocaleString()}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white">Historical Analysis Details</h3>
                {selectedSnapshot.summary && (
                  <p className="text-xs text-slate-300 italic pt-0.5">
                    "{selectedSnapshot.summary}"
                  </p>
                )}
              </div>

              <button
                onClick={() => setSelectedSnapshot(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6 overflow-y-auto flex-1">
              {/* Scores Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Overall Health</div>
                  <div className="text-xl font-bold font-mono text-emerald-400">
                    {selectedSnapshot.overall_score}/100
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Security</div>
                  <div className="text-xl font-bold font-mono text-rose-400">
                    {selectedSnapshot.security_score}/100
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Code Quality</div>
                  <div className="text-xl font-bold font-mono text-purple-400">
                    {selectedSnapshot.quality_score}/100
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-[10px] font-mono text-slate-500 uppercase">Tech Debt</div>
                  <div className="text-xl font-bold font-mono text-amber-400">
                    {selectedSnapshot.technical_debt_hours}h
                  </div>
                </div>
              </div>

              {/* Underlying Stages Audit Traceability */}
              <div className="p-4 rounded-xl bg-[#090d18] border border-slate-800 space-y-2">
                <div className="text-xs font-mono font-semibold uppercase text-slate-300">
                  Traceability References
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-slate-400">
                  <div>Scan ID: {selectedSnapshot.repository_scan_id || 'N/A'}</div>
                  <div>Quality ID: {selectedSnapshot.quality_analysis_id || 'N/A'}</div>
                  <div>Security ID: {selectedSnapshot.security_analysis_id || 'N/A'}</div>
                  <div>Dependency ID: {selectedSnapshot.dependency_analysis_id || 'N/A'}</div>
                  <div>Architecture ID: {selectedSnapshot.architecture_analysis_id || 'N/A'}</div>
                  <div>Health ID: {selectedSnapshot.health_analysis_id || 'N/A'}</div>
                </div>
              </div>

              {/* Granular Telemetry Tallies */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-slate-500">Critical Issues</div>
                  <div className="text-base font-bold text-rose-400">
                    {selectedSnapshot.critical_count}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-slate-500">High Issues</div>
                  <div className="text-base font-bold text-orange-400">
                    {selectedSnapshot.high_count}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-slate-500">Total Dependencies</div>
                  <div className="text-base font-bold text-slate-200">
                    {selectedSnapshot.total_dependencies} ({selectedSnapshot.vulnerable_dependencies_count} vuln)
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-[#090d18] border border-slate-800">
                  <div className="text-slate-500">Architecture Nodes</div>
                  <div className="text-base font-bold text-slate-200">
                    {selectedSnapshot.architecture_nodes_count} ({selectedSnapshot.architecture_cycles_count} cycles)
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-800 bg-[#0a0f1d] flex items-center justify-between text-xs">
              <span className="text-slate-500 font-mono text-[11px]">
                Immutable historical snapshot · Read-only
              </span>
              <button
                onClick={() => setSelectedSnapshot(null)}
                className="px-4 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default HistoryDashboard
