import React, { useState, useEffect } from 'react'
import {
  X,
  Sparkles,
  AlertTriangle,
  Flame,
  Wrench,
  CheckCircle2,
  Copy,
  Check,
  RefreshCw,
  Loader2,
  ExternalLink,
  ShieldAlert,
  Code2,
  Boxes,
  Network,
  Info,
  ChevronRight,
} from 'lucide-react'
import { projectService } from '../../services/projectService'
import type { AIExplanation } from '../../types/ai'

interface AIExplanationModalProps {
  isOpen: boolean
  onClose: () => void
  issueId: string | null
  issueTitle?: string
  issueLocation?: string
  issueSeverity?: string
  category?: 'quality' | 'security' | 'dependency' | 'architecture' | string
}

export const AIExplanationModal: React.FC<AIExplanationModalProps> = ({
  isOpen,
  onClose,
  issueId,
  issueTitle,
  issueLocation,
  issueSeverity = 'MEDIUM',
  category = 'quality',
}) => {
  const [explanation, setExplanation] = useState<AIExplanation | null>(null)
  const [loading, setLoading] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  // Fetch or auto-explain on open
  useEffect(() => {
    if (!isOpen || !issueId) {
      setExplanation(null)
      setError(null)
      setLoading(false)
      return
    }

    let isMounted = true

    const loadExplanation = async () => {
      setLoading(true)
      setError(null)

      try {
        // 1. Try to load existing explanation first
        try {
          const existing = await projectService.getIssueExplanation(issueId)
          if (isMounted) {
            setExplanation(existing)
            setLoading(false)
            return
          }
        } catch {
          // Not yet explained, trigger new explanation
        }

        // 2. If not found, call explain
        const generated = await projectService.explainIssue(issueId)
        if (isMounted) {
          setExplanation(generated)
        }
      } catch (err: any) {
        if (isMounted) {
          const detail =
            err.response?.data?.detail ||
            'AI explanation is currently unavailable. The underlying analysis is still available.'
          setError(detail)
        }
      } finally {
        if (isMounted) {
          setLoading(false)
        }
      }
    }

    loadExplanation()

    return () => {
      isMounted = false
    }
  }, [isOpen, issueId])

  if (!isOpen) return null

  const handleRegenerate = async () => {
    if (!issueId || regenerating || loading) return
    setRegenerating(true)
    setError(null)

    try {
      const refreshed = await projectService.regenerateIssueExplanation(issueId)
      setExplanation(refreshed)
    } catch (err: any) {
      const detail =
        err.response?.data?.detail ||
        'Failed to regenerate AI explanation. The underlying analysis remains available.'
      setError(detail)
    } finally {
      setRegenerating(false)
    }
  }

  const handleCopyActionPlan = () => {
    if (!explanation) return
    const text = `PROJECT DOCTOR • AI DIAGNOSTIC EXPLANATION
Issue: ${issueTitle || explanation.issue_type}
Location: ${issueLocation || 'Source Code'}
Authoritative Severity: ${issueSeverity}
AI Recommended Priority: ${explanation.priority}

SUMMARY:
${explanation.summary}

WHY IT MATTERS:
${explanation.why_it_matters}

POTENTIAL IMPACT:
${explanation.potential_impact}

RECOMMENDED FIX:
${explanation.recommendation}

DEVELOPER ACTION PLAN:
${explanation.developer_action}
`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/30'
      case 'HIGH':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/30'
      case 'MEDIUM':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30'
      case 'LOW':
        return 'bg-slate-700/30 text-slate-400 border-slate-700/50'
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30'
    }
  }

  const getCategoryIcon = () => {
    switch (category.toLowerCase()) {
      case 'security':
        return <ShieldAlert className="h-4 w-4 text-rose-400" />
      case 'quality':
        return <Code2 className="h-4 w-4 text-purple-400" />
      case 'dependency':
      case 'dependencies':
        return <Boxes className="h-4 w-4 text-amber-400" />
      case 'architecture':
        return <Network className="h-4 w-4 text-indigo-400" />
      default:
        return <Sparkles className="h-4 w-4 text-blue-400" />
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      <div
        className="bg-[#0d1322] border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col my-auto max-h-[92vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-5 sm:p-6 border-b border-slate-800 flex items-start justify-between gap-4 bg-[#0a0f1d]">
          <div className="space-y-1.5 min-w-0">
            <div className="flex items-center space-x-2.5">
              <span className="p-1.5 rounded-lg bg-blue-600/10 border border-blue-500/20">
                {getCategoryIcon()}
              </span>
              <span className="text-xs font-mono font-medium text-slate-400 uppercase tracking-wider">
                Stage 10 · AI Problem Explainer
              </span>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-blue-950/60 text-blue-400 border border-blue-800/40">
                <Sparkles className="h-2.5 w-2.5 mr-1" />
                Google Gemini
              </span>
            </div>

            <h2 className="text-lg font-bold text-white tracking-tight truncate">
              {issueTitle || 'Diagnostic Finding Explanation'}
            </h2>

            <div className="flex flex-wrap items-center gap-2 pt-0.5 text-xs">
              {issueLocation && (
                <span className="font-mono text-slate-400 bg-slate-900/90 px-2 py-0.5 rounded border border-slate-800 text-[11px]">
                  {issueLocation}
                </span>
              )}
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase border ${getSeverityBadgeClass(
                  issueSeverity
                )}`}
              >
                {issueSeverity} (Authoritative)
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition shrink-0"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 sm:p-6 space-y-5 overflow-y-auto flex-1">
          {/* Loading State */}
          {loading && (
            <div className="py-16 flex flex-col items-center justify-center space-y-4 text-center">
              <div className="relative">
                <div className="h-12 w-12 rounded-full border-2 border-blue-500/20 border-t-blue-500 animate-spin" />
                <Sparkles className="h-5 w-5 text-blue-400 absolute inset-0 m-auto" />
              </div>
              <div className="space-y-1">
                <div className="text-sm font-semibold text-white">Analyzing Finding with Gemini...</div>
                <p className="text-xs text-slate-400 max-w-sm">
                  Reviewing deterministic analyzer evidence, extracting sanitized context, and synthesizing developer action plan.
                </p>
              </div>
            </div>
          )}

          {/* Error / Unavailable State */}
          {!loading && error && (
            <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-3">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <div className="text-sm font-semibold text-amber-200">AI Explanation Unavailable</div>
                  <p className="text-xs text-amber-300/80 leading-relaxed">{error}</p>
                </div>
              </div>
              <div className="pt-2 flex items-center justify-end space-x-2 border-t border-amber-500/20">
                <button
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-xs font-medium border border-amber-500/30 transition disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                  <span>Retry with Gemini</span>
                </button>
              </div>
            </div>
          )}

          {/* Explanation Content */}
          {!loading && explanation && (
            <div className="space-y-4">
              {/* 1. Summary Card */}
              <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-500/30 space-y-1.5">
                <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-blue-400 uppercase">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Executive Summary</span>
                </div>
                <p className="text-xs sm:text-sm text-slate-200 leading-relaxed font-medium">
                  {explanation.summary}
                </p>
              </div>

              {/* 2 & 3. Why It Matters & Potential Impact Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-[#0b0f19] border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-amber-400 uppercase">
                    <Info className="h-3.5 w-3.5" />
                    <span>Why This Matters</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {explanation.why_it_matters}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#0b0f19] border border-slate-800 space-y-2">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-rose-400 uppercase">
                    <Flame className="h-3.5 w-3.5" />
                    <span>Potential Impact</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    {explanation.potential_impact}
                  </p>
                </div>
              </div>

              {/* 4. Recommended Fix */}
              <div className="p-4 rounded-xl bg-[#0b0f19] border border-slate-800 space-y-2">
                <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-emerald-400 uppercase">
                  <Wrench className="h-3.5 w-3.5" />
                  <span>Recommended Fix</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                  {explanation.recommendation}
                </p>
              </div>

              {/* 5. Developer Action Plan */}
              <div className="p-4 rounded-xl bg-[#0b0f19] border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-xs font-mono font-semibold text-sky-400 uppercase">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Developer Action Checklist</span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-400">
                    Recommended Urgency:{' '}
                    <span className="font-semibold text-slate-200">{explanation.priority}</span>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs text-slate-300 leading-relaxed whitespace-pre-line font-mono">
                  {explanation.developer_action}
                </div>
              </div>

              {/* Metadata Footer Strip */}
              <div className="pt-2 flex flex-wrap items-center justify-between text-[11px] font-mono text-slate-500 border-t border-slate-800/80 gap-2">
                <div>Provider: {explanation.provider} ({explanation.model})</div>
                <div>Generated: {new Date(explanation.updated_at).toLocaleTimeString()}</div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 sm:p-5 border-t border-slate-800 flex items-center justify-between bg-[#0a0f1d] gap-3">
          <div>
            {explanation && !loading && (
              <button
                onClick={handleRegenerate}
                disabled={regenerating}
                className="inline-flex items-center space-x-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                <span>{regenerating ? 'Regenerating...' : 'Regenerate Explanation'}</span>
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2.5">
            {explanation && !loading && (
              <button
                onClick={handleCopyActionPlan}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Action Plan</span>
                  </>
                )}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AIExplanationModal
