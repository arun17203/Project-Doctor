import React, { useState } from 'react'
import {
  Activity,
  ShieldCheck,
  ShieldAlert,
  Code2,
  Boxes,
  Network,
  Cpu,
  CheckSquare,
  Clock,
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  RefreshCw,
  Info,
  ChevronDown,
  ChevronUp,
  FileCode,
  ExternalLink,
} from 'lucide-react'
import type { HealthAnalysis, FixFirstItem, HealthStatus } from '../../types/health'

interface HealthDashboardProps {
  projectId: string
  analysis: HealthAnalysis
  analyzing?: boolean
  onReanalyze?: () => void
  onNavigateTab?: (tab: string) => void
}

const STATUS_CONFIG: Record<
  string,
  {
    bgBadge: string
    borderBadge: string
    textBadge: string
    strokeColor: string
  }
> = {
  Excellent: {
    bgBadge: 'bg-emerald-500/10',
    borderBadge: 'border-emerald-500/30',
    textBadge: 'text-emerald-400',
    strokeColor: '#34d399',
  },
  Good: {
    bgBadge: 'bg-blue-500/10',
    borderBadge: 'border-blue-500/30',
    textBadge: 'text-blue-400',
    strokeColor: '#38bdf8',
  },
  Fair: {
    bgBadge: 'bg-amber-500/10',
    borderBadge: 'border-amber-500/30',
    textBadge: 'text-amber-400',
    strokeColor: '#fbbf24',
  },
  'Needs Attention': {
    bgBadge: 'bg-orange-500/10',
    borderBadge: 'border-orange-500/30',
    textBadge: 'text-orange-400',
    strokeColor: '#fb923c',
  },
  Critical: {
    bgBadge: 'bg-rose-500/10',
    borderBadge: 'border-rose-500/30',
    textBadge: 'text-rose-400',
    strokeColor: '#f43f5e',
  },
}

export const HealthDashboard: React.FC<HealthDashboardProps> = ({
  analysis,
  analyzing = false,
  onReanalyze,
  onNavigateTab,
}) => {
  const [showAllFixFirst, setShowAllFixFirst] = useState(false)
  const [showCategoryDrivers, setShowCategoryDrivers] = useState(false)

  const statusConf = STATUS_CONFIG[analysis.status] || STATUS_CONFIG.Fair

  // Circular gauge calculations
  const radius = 64
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (analysis.overall_score / 100) * circumference

  const fixFirstItems = showAllFixFirst ? analysis.fix_first : analysis.fix_first.slice(0, 5)

  return (
    <div className="space-y-6">
      {/* Top Banner: Overall Health Score Gauge + Technical Debt Hero */}
      <div className="bg-[#0d1322] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-center justify-between gap-8">
          {/* Left: Overall Health Circular Gauge */}
          <div className="flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
            <div className="relative w-36 h-36 shrink-0 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="72"
                  cy="72"
                  r={radius}
                  stroke="#1e293b"
                  strokeWidth="10"
                  fill="transparent"
                />
                <circle
                  cx="72"
                  cy="72"
                  r={radius}
                  stroke={statusConf.strokeColor}
                  strokeWidth="10"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-1000 ease-out"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-extrabold font-mono text-white tracking-tight">
                  {Math.round(analysis.overall_score)}
                </span>
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider mt-0.5">
                  / 100
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-center sm:justify-start gap-2">
                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold font-mono border ${statusConf.bgBadge} ${statusConf.borderBadge} ${statusConf.textBadge}`}
                >
                  {analysis.status}
                </span>
                <span className="text-xs text-slate-400 font-mono">
                  {new Date(analysis.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <h2 className="text-xl font-bold tracking-tight text-white">Project Health Score</h2>
              <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
                Deterministic weighted diagnosis across Security (30%), Quality (25%), Maintainability (20%), Dependencies (15%), and Architecture (10%).
              </p>
            </div>
          </div>

          {/* Right: Technical Debt & Issue Summary Box */}
          <div className="flex flex-wrap items-center gap-4 w-full lg:w-auto justify-center lg:justify-end">
            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 min-w-[170px] space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Technical Debt</span>
              </div>
              <div className="text-2xl font-bold font-mono text-amber-400">
                {Math.round(analysis.technical_debt_hours)}h
              </div>
              <div className="text-[10px] text-slate-500">Estimated remediation effort</div>
            </div>

            <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 min-w-[200px] space-y-2">
              <div className="text-xs font-medium text-slate-400">Total Findings</div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span
                  className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20"
                  title="Critical issues"
                >
                  {analysis.critical_count} Crit
                </span>
                <span
                  className="px-2 py-0.5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20"
                  title="High issues"
                >
                  {analysis.high_count} High
                </span>
                <span
                  className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  title="Medium issues"
                >
                  {analysis.medium_count} Med
                </span>
                <span
                  className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700"
                  title="Low issues"
                >
                  {analysis.low_count} Low
                </span>
              </div>
              <div className="text-[10px] text-slate-500">Severity-weighted hours model</div>
            </div>

            {onReanalyze && (
              <button
                onClick={onReanalyze}
                disabled={analyzing}
                className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition shadow-sm disabled:opacity-50"
                title="Run new health diagnosis from latest analysis records"
              >
                <RefreshCw className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
                <span>Re-Analyze</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 6 Dimension Score Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* 1. Security Score */}
        <div
          onClick={() => onNavigateTab && onNavigateTab('security')}
          className="bg-[#0d1322] border border-slate-800 hover:border-rose-500/40 rounded-xl p-5 space-y-3 cursor-pointer transition shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Security (30% weight)
            </span>
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.security_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.security_score >= 80
                  ? 'text-emerald-400'
                  : analysis.security_score >= 60
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {analysis.security_score >= 80 ? 'Robust' : analysis.security_score >= 60 ? 'Moderate' : 'Vulnerable'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-rose-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.security_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>SQLi, secrets &amp; commands</span>
            <span className="text-primary group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
              View <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* 2. Code Quality Score */}
        <div
          onClick={() => onNavigateTab && onNavigateTab('quality')}
          className="bg-[#0d1322] border border-slate-800 hover:border-purple-500/40 rounded-xl p-5 space-y-3 cursor-pointer transition shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Code Quality (25% weight)
            </span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Code2 className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.quality_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.quality_score >= 80
                  ? 'text-emerald-400'
                  : analysis.quality_score >= 60
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {analysis.quality_score >= 80 ? 'Clean' : analysis.quality_score >= 60 ? 'Moderate' : 'Needs Refactor'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-purple-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.quality_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>Complexity &amp; code duplicates</span>
            <span className="text-primary group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
              View <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* 3. Maintainability Score */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Maintainability (20% weight)
            </span>
            <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.maintainability_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.maintainability_score >= 80
                  ? 'text-emerald-400'
                  : analysis.maintainability_score >= 60
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {analysis.maintainability_score >= 80 ? 'High' : analysis.maintainability_score >= 60 ? 'Fair' : 'Low'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.maintainability_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 pt-1">
            <span>Function lengths, nesting &amp; complexity</span>
          </div>
        </div>

        {/* 4. Dependencies Score */}
        <div
          onClick={() => onNavigateTab && onNavigateTab('dependencies')}
          className="bg-[#0d1322] border border-slate-800 hover:border-amber-500/40 rounded-xl p-5 space-y-3 cursor-pointer transition shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Dependencies (15% weight)
            </span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Boxes className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.dependency_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.dependency_score >= 80
                  ? 'text-emerald-400'
                  : analysis.dependency_score >= 60
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {analysis.dependency_score >= 80 ? 'Current' : 'Outdated/Vuln'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-amber-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.dependency_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>OSV advisories &amp; semver freshness</span>
            <span className="text-primary group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
              View <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* 5. Architecture Score */}
        <div
          onClick={() => onNavigateTab && onNavigateTab('architecture')}
          className="bg-[#0d1322] border border-slate-800 hover:border-indigo-500/40 rounded-xl p-5 space-y-3 cursor-pointer transition shadow-lg group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Architecture (10% weight)
            </span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Network className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.architecture_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.architecture_score >= 90
                  ? 'text-emerald-400'
                  : analysis.architecture_score >= 70
                  ? 'text-amber-400'
                  : 'text-rose-400'
              }`}
            >
              {analysis.architecture_score === 100 ? 'Acyclic' : 'Cycles Detected'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-indigo-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.architecture_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
            <span>Module couplings &amp; circular loops</span>
            <span className="text-primary group-hover:translate-x-0.5 transition-transform flex items-center gap-0.5">
              View <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        </div>

        {/* 6. Testing Health Score */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
              Testing Health
            </span>
            <div className="p-1.5 rounded-lg bg-lime-500/10 text-lime-400 border border-lime-500/20">
              <CheckSquare className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold font-mono text-white">
              {Math.round(analysis.testing_score)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </span>
            <span
              className={`text-xs font-semibold ${
                analysis.testing_score >= 80
                  ? 'text-emerald-400'
                  : analysis.testing_score > 0
                  ? 'text-amber-400'
                  : 'text-slate-500'
              }`}
            >
              {analysis.testing_score >= 80 ? 'Comprehensive' : analysis.testing_score > 0 ? 'Partial' : 'No Tests'}
            </span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
            <div
              className="bg-lime-500 h-1.5 rounded-full transition-all duration-700"
              style={{ width: `${analysis.testing_score}%` }}
            />
          </div>
          <div className="text-[11px] text-slate-400 pt-1">
            <span>Test-to-source file module ratio</span>
          </div>
        </div>
      </div>

      {/* Two Column Section: Why [Score]? Explanations + Technical Debt Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Why [Score]? Score Explanation Card */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Info className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-white">
                Why {Math.round(analysis.overall_score)}/100?
              </h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">Deterministic Drivers</span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-medium">
            {analysis.explanations?.summary}
          </p>

          {/* Primary negative / positive drivers list */}
          <div className="space-y-2.5">
            {analysis.explanations?.why_breakdown?.map((item, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/90 text-xs text-slate-300 flex items-start gap-2.5"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-primary mt-1.5 shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </div>
            ))}
          </div>

          {/* Toggle category level breakdown */}
          {analysis.explanations?.category_drivers && (
            <div className="pt-2 border-t border-slate-800/80">
              <button
                onClick={() => setShowCategoryDrivers(!showCategoryDrivers)}
                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 font-medium transition-colors"
              >
                {showCategoryDrivers ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" /> Hide Category Breakdown
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" /> Show Category Breakdown
                  </>
                )}
              </button>

              {showCategoryDrivers && (
                <div className="mt-3 space-y-2 text-xs text-slate-400 pl-2 border-l-2 border-slate-800">
                  {Object.entries(analysis.explanations.category_drivers).map(([category, drivers]) => {
                    if (!drivers || drivers.length === 0) return null
                    return (
                      <div key={category} className="space-y-1">
                        <strong className="text-slate-200 uppercase text-[10px] tracking-wider block font-mono">
                          {category}
                        </strong>
                        {drivers.map((d, dIdx) => (
                          <p key={dIdx} className="text-slate-400 text-[11px] leading-relaxed">
                            • {d}
                          </p>
                        ))}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Technical Debt Remediation Breakdown Card */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Technical Debt Breakdown</h3>
            </div>
            <span className="text-xs font-mono font-bold text-amber-400">
              Total: {Math.round(analysis.debt_breakdown?.total_hours || analysis.technical_debt_hours)}h
            </span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            Estimated engineering effort required to resolve known issues using the baseline remediation model (Critical = 8h, High = 4h, Medium = 2h, Low = 1h).
          </p>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Code Quality</span>
              <div className="text-xl font-bold font-mono text-purple-400 mt-0.5">
                {Math.round(analysis.debt_breakdown?.quality_hours ?? 0)}h
              </div>
              <span className="text-[10px] text-slate-500">Refactoring &amp; complexity</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Security</span>
              <div className="text-xl font-bold font-mono text-rose-400 mt-0.5">
                {Math.round(analysis.debt_breakdown?.security_hours ?? 0)}h
              </div>
              <span className="text-[10px] text-slate-500">Vulnerabilities &amp; secrets</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Dependencies</span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-0.5">
                {Math.round(analysis.debt_breakdown?.dependency_hours ?? 0)}h
              </div>
              <span className="text-[10px] text-slate-500">Upgrades &amp; patch testing</span>
            </div>

            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
              <span className="text-[11px] font-mono text-slate-400 uppercase">Architecture</span>
              <div className="text-xl font-bold font-mono text-indigo-400 mt-0.5">
                {Math.round(analysis.debt_breakdown?.architecture_hours ?? 0)}h
              </div>
              <span className="text-[10px] text-slate-500">Decoupling circular loops</span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
            <span className="text-slate-400">Want to reduce technical debt?</span>
            <a
              href="#fix-first-section"
              className="text-primary hover:text-blue-400 font-medium flex items-center gap-1"
            >
              View Prioritized Issues <ArrowRight className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>

      {/* Priority Action List: FIX FIRST */}
      <div id="fix-first-section" className="bg-[#0d1322] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-white">
              Fix First Priority Actions ({analysis.fix_first?.length || 0})
            </h3>
          </div>
          <span className="text-xs text-slate-400 font-mono">Highest-Impact Remediation Order</span>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed">
          The engine deterministically sorts all findings across security, quality, dependencies, and architecture so you address the highest-risk issues first.
        </p>

        {analysis.fix_first?.length === 0 ? (
          <div className="p-6 text-center text-xs text-slate-500 italic bg-slate-900/40 rounded-xl border border-slate-800">
            Zero high-priority issues detected! Your codebase is in excellent condition.
          </div>
        ) : (
          <div className="space-y-3">
            {fixFirstItems.map((item) => (
              <div
                key={item.rank}
                className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition space-y-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="h-5 w-5 rounded-full bg-slate-800 text-slate-300 font-mono text-[10px] font-bold flex items-center justify-center border border-slate-700">
                      {item.rank}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${
                        item.severity === 'CRITICAL'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                          : item.severity === 'HIGH'
                          ? 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                          : item.severity === 'MEDIUM'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}
                    >
                      {item.severity}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 text-[10px] font-mono">
                      {item.category}
                    </span>
                    <h4 className="text-xs font-semibold text-slate-100">{item.title}</h4>
                  </div>

                  <div className="text-xs font-mono text-slate-400 flex items-center gap-1" title={item.location}>
                    <FileCode className="w-3.5 h-3.5 text-slate-500" />
                    <span className="truncate max-w-[250px]">{item.location}</span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed pl-7">
                  {item.description}
                </p>

                {item.recommendation && (
                  <div className="ml-7 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>
                      <strong className="text-slate-300">Recommendation:</strong> {item.recommendation}
                    </span>
                  </div>
                )}
              </div>
            ))}

            {analysis.fix_first.length > 5 && (
              <div className="pt-2 text-center">
                <button
                  onClick={() => setShowAllFixFirst(!showAllFixFirst)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition"
                >
                  {showAllFixFirst
                    ? 'Show Top 5 Only'
                    : `Show All ${analysis.fix_first.length} Prioritized Issues`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default HealthDashboard

