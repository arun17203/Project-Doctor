import React, { useState, useEffect } from 'react'
import {
  Stethoscope,
  Sparkles,
  Download,
  Copy,
  Check,
  ShieldAlert,
  Code2,
  Boxes,
  Clock,
  TrendingUp,
  FileCode,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Terminal,
  Info,
  RefreshCw,
} from 'lucide-react'
import { projectService } from '../../services/projectService'
import { useToast } from '../../context/ToastContext'
import type { DoctorPrescription, RemediationAction } from '../../types/remediation'

interface PrescriptionDashboardProps {
  projectId: string
  projectName: string
}

export const PrescriptionDashboard: React.FC<PrescriptionDashboardProps> = ({
  projectId,
  projectName,
}) => {
  const { success, error: toastError } = useToast()
  const [prescription, setPrescription] = useState<DoctorPrescription | null>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const [expandedActionId, setExpandedActionId] = useState<string | null>(null)
  const [activeView, setActiveView] = useState<'cards' | 'diff'>('cards')

  const fetchPrescription = async () => {
    try {
      setLoading(true)
      const data = await projectService.getRemediation(projectId)
      setPrescription(data)
      if (data.actions.length > 0) {
        setExpandedActionId(data.actions[0].id)
      }
    } catch (err: any) {
      toastError('Failed to load prescription', err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPrescription()
  }, [projectId])

  const handleCopyPatch = () => {
    if (!prescription?.unified_diff) return
    navigator.clipboard.writeText(prescription.unified_diff)
    setCopied(true)
    success('Patch copied to clipboard', 'You can apply it using: git apply <patch_file>')
    setTimeout(() => setCopied(false), 2500)
  }

  const handleDownloadPatch = async () => {
    try {
      const blob = await projectService.downloadPatch(projectId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = prescription?.patch_filename || `${projectName.toLowerCase()}_prescription.patch`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      success('Patch downloaded', `Saved as ${prescription?.patch_filename}`)
    } catch (err: any) {
      toastError('Download failed', err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 bg-[#0d1322] border border-slate-800 rounded-2xl">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin mb-3" />
        <p className="text-sm font-medium text-slate-300">Synthesizing Doctor's Prescriptions & Diffs...</p>
        <p className="text-xs text-slate-500 mt-1">Analyzing static issues, security risks, and manifest versions</p>
      </div>
    )
  }

  if (!prescription || prescription.actions.length === 0) {
    return (
      <div className="bg-[#0d1322] border border-slate-800 rounded-2xl p-10 text-center space-y-4">
        <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <CheckCircle2 className="w-7 h-7" />
        </div>
        <h3 className="text-lg font-bold text-white">Clean Bill of Health!</h3>
        <p className="text-sm text-slate-400 max-w-md mx-auto">
          No urgent prescriptions required. Your codebase currently has no critical security leaks,
          severe complexity hotspots, or vulnerable dependency versions requiring immediate patching.
        </p>
      </div>
    )
  }

  const scoreGain = Math.round(prescription.projected_health_score - prescription.current_health_score)

  return (
    <div className="space-y-6">
      {/* Top Hero Banner */}
      <div className="bg-[#0d1322] border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2.5">
              <span className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Stethoscope className="w-6 h-6" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold text-white tracking-tight">The Doctor's Prescription</h2>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    Auto-Fix Engine
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  Synthesized actionable remediation orders and unified git diffs for verified static findings.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            <button
              onClick={handleCopyPatch}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Copied!' : 'Copy Full Patch'}</span>
            </button>
            <button
              onClick={handleDownloadPatch}
              className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Download .patch File</span>
            </button>
          </div>
        </div>

        {/* Vitals Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-800/80">
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
              <span>Health Gain</span>
            </div>
            <div className="text-xl font-bold font-mono text-white flex items-baseline gap-1.5">
              <span>{Math.round(prescription.current_health_score)}</span>
              <span className="text-slate-500 text-sm">→</span>
              <span className="text-emerald-400">{Math.round(prescription.projected_health_score)}</span>
              {scoreGain > 0 && (
                <span className="text-xs font-mono text-emerald-400 font-semibold">(+{scoreGain} pts)</span>
              )}
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              <span>Debt Recovered</span>
            </div>
            <div className="text-xl font-bold font-mono text-amber-400">
              {prescription.estimated_debt_recovered_hours}h
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Critical Fixes</span>
            </div>
            <div className="text-xl font-bold font-mono text-rose-400">
              {prescription.critical_count}
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
              <span>Total Prescriptions</span>
            </div>
            <div className="text-xl font-bold font-mono text-indigo-400">
              {prescription.total_prescriptions}
            </div>
          </div>
        </div>
      </div>

      {/* Terminal Command Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <Terminal className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>Apply patch locally:</span>
          <code className="px-2 py-1 rounded bg-slate-950 text-indigo-300 border border-slate-800">
            git apply {prescription.patch_filename}
          </code>
        </div>
        <div className="text-[11px] text-slate-500">
          RFC 3986 Standard Unified Diff
        </div>
      </div>

      {/* View Switcher */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveView('cards')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeView === 'cards'
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200'
          }`}
        >
          Prescription Orders ({prescription.actions.length})
        </button>
        <button
          onClick={() => setActiveView('diff')}
          className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            activeView === 'diff'
              ? 'bg-indigo-600 text-white'
              : 'bg-slate-900 text-slate-400 hover:text-slate-200'
          }`}
        >
          Master Unified Diff (.patch)
        </button>
      </div>

      {/* Content Section */}
      {activeView === 'cards' ? (
        <div className="space-y-4">
          {prescription.actions.map((action, idx) => {
            const isExpanded = expandedActionId === action.id
            const isCritical = action.severity === 'CRITICAL'
            const isHigh = action.severity === 'HIGH'

            return (
              <div
                key={action.id}
                className="bg-[#0d1322] border border-slate-800 rounded-xl overflow-hidden transition-all duration-200"
              >
                {/* Card Header */}
                <div
                  onClick={() => setExpandedActionId(isExpanded ? null : action.id)}
                  className="p-4 sm:p-5 flex items-start sm:items-center justify-between gap-4 cursor-pointer hover:bg-slate-800/40"
                >
                  <div className="flex items-start sm:items-center gap-3.5">
                    <span className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 font-mono text-xs text-slate-300 flex items-center justify-center shrink-0">
                      #{idx + 1}
                    </span>
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${
                            isCritical
                              ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                              : isHigh
                              ? 'bg-orange-500/10 text-orange-400 border-orange-500/30'
                              : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                          }`}
                        >
                          {action.severity}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 uppercase">
                          {action.category}
                        </span>
                        <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                          <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                          {action.file_path}:{action.line_number}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-white">{action.title}</h4>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="hidden sm:inline-block text-xs font-mono text-slate-400">
                      ~{action.estimated_effort_minutes}m fix
                    </span>
                    <button className="p-1 text-slate-400 hover:text-white">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Details & Diff */}
                {isExpanded && (
                  <div className="p-5 border-t border-slate-800 bg-slate-950/60 space-y-4">
                    {/* Doctor's Orders Box */}
                    <div className="bg-indigo-950/30 border border-indigo-500/30 rounded-lg p-3.5 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300">
                        <Stethoscope className="w-4 h-4 text-indigo-400" />
                        <span>Doctor's Order (Treatment Instructions)</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans pl-5">
                        {action.doctor_order}
                      </p>
                    </div>

                    {/* Diff Preview */}
                    {action.diff_snippet && (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                          <span>Git Diff Patch:</span>
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(action.diff_snippet)
                              success('Snippet copied', 'Ready to paste into git')
                            }}
                            className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                          >
                            <Copy className="w-3 h-3" />
                            Copy Diff
                          </button>
                        </div>
                        <div className="bg-slate-950 rounded-lg border border-slate-800 p-3 font-mono text-xs overflow-x-auto">
                          {action.diff_snippet.split('\n').map((line, lIdx) => {
                            let lineClass = 'text-slate-400'
                            if (line.startsWith('+') && !line.startsWith('+++')) {
                              lineClass = 'text-emerald-400 bg-emerald-500/10 px-1 rounded'
                            } else if (line.startsWith('-') && !line.startsWith('---')) {
                              lineClass = 'text-rose-400 bg-rose-500/10 px-1 rounded'
                            } else if (line.startsWith('@@')) {
                              lineClass = 'text-cyan-400'
                            }
                            return (
                              <div key={lIdx} className={lineClass}>
                                {line}
                              </div>
                            )
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        /* Full Master Unified Diff Viewer */
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Complete Unified Patch Content:</span>
            <button
              onClick={handleCopyPatch}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 font-mono text-xs flex items-center gap-1.5"
            >
              <Copy className="w-3.5 h-3.5" />
              Copy Full Patch
            </button>
          </div>
          <div className="bg-slate-950 rounded-xl border border-slate-800 p-4 font-mono text-xs overflow-x-auto max-h-[600px] leading-relaxed">
            {prescription.unified_diff.split('\n').map((line, idx) => {
              let lineClass = 'text-slate-400'
              if (line.startsWith('+') && !line.startsWith('+++')) {
                lineClass = 'text-emerald-400 bg-emerald-500/10 px-1 rounded'
              } else if (line.startsWith('-') && !line.startsWith('---')) {
                lineClass = 'text-rose-400 bg-rose-500/10 px-1 rounded'
              } else if (line.startsWith('@@')) {
                lineClass = 'text-cyan-400'
              } else if (line.startsWith('---') || line.startsWith('+++')) {
                lineClass = 'text-indigo-300 font-bold'
              }
              return (
                <div key={idx} className={lineClass}>
                  {line}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
