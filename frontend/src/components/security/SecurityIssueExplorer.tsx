import React, { useState, useEffect } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  FileCode,
  Search,
  ChevronRight,
  X,
  Code2,
  Copy,
  Check,
  Loader2,
  Lock,
  Flame,
  ShieldCheck,
  KeyRound,
  Terminal,
  Cpu,
  Settings,
  Hash,
  Fingerprint,
  Sparkles
} from 'lucide-react'
import type { SecurityIssue, SecurityCodeSnippet, SecuritySeverityLevel } from '../../types/security'
import { projectService } from '../../services/projectService'
import AIExplanationModal from '../ai/AIExplanationModal'

interface SecurityIssueExplorerProps {
  projectId: string
  issues: SecurityIssue[]
  loading?: boolean
  onRefresh?: () => void
}

export default function SecurityIssueExplorer({
  projectId,
  issues,
  loading = false,
  onRefresh,
}: SecurityIssueExplorerProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL')
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedIssue, setSelectedIssue] = useState<SecurityIssue | null>(null)
  const [selectedIssueForAI, setSelectedIssueForAI] = useState<SecurityIssue | null>(null)

  // Snippet preview state
  const [snippet, setSnippet] = useState<SecurityCodeSnippet | null>(null)
  const [loadingSnippet, setLoadingSnippet] = useState<boolean>(false)
  const [snippetError, setSnippetError] = useState<string | null>(null)
  const [copiedEvidence, setCopiedEvidence] = useState<boolean>(false)
  const [copiedRemediation, setCopiedRemediation] = useState<boolean>(false)

  // Fetch masked code snippet whenever selected issue changes
  useEffect(() => {
    if (!selectedIssue) {
      setSnippet(null)
      return
    }

    const fetchSnippet = async () => {
      setLoadingSnippet(true)
      setSnippetError(null)
      try {
        const data = await projectService.getSecuritySnippet(
          projectId,
          selectedIssue.file_path,
          selectedIssue.line_number,
          5
        )
        setSnippet(data)
      } catch (err: any) {
        console.error('Failed to load security snippet:', err)
        setSnippetError(err.response?.data?.detail || 'Failed to load source code preview.')
      } finally {
        setLoadingSnippet(false)
      }
    }

    fetchSnippet()
  }, [projectId, selectedIssue])

  // Severity counts
  const criticalCount = issues.filter((i) => i.severity === 'CRITICAL').length
  const highCount = issues.filter((i) => i.severity === 'HIGH').length
  const mediumCount = issues.filter((i) => i.severity === 'MEDIUM').length
  const lowCount = issues.filter((i) => i.severity === 'LOW').length

  // Filter issues
  const filteredIssues = issues.filter((issue) => {
    if (selectedSeverity !== 'ALL' && issue.severity !== selectedSeverity) {
      return false
    }
    if (selectedCategory !== 'ALL' && issue.category.toUpperCase() !== selectedCategory.toUpperCase()) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchFile = issue.file_path.toLowerCase().includes(q)
      const matchMsg = issue.message.toLowerCase().includes(q)
      const matchType = issue.issue_type.toLowerCase().includes(q)
      if (!matchFile && !matchMsg && !matchType) return false
    }
    return true
  })

  const getSeverityBadge = (sev: SecuritySeverityLevel | string) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 uppercase">
            <Flame className="w-3 h-3 text-rose-500" />
            <span>CRITICAL</span>
          </span>
        )
      case 'HIGH':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 uppercase">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            <span>HIGH</span>
          </span>
        )
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 uppercase">
            <AlertCircle className="w-3 h-3 text-yellow-400" />
            <span>MEDIUM</span>
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sky-500/10 text-sky-400 border border-sky-500/30 uppercase">
            <Info className="w-3 h-3 text-sky-400" />
            <span>LOW</span>
          </span>
        )
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category.toUpperCase()) {
      case 'SECRETS':
        return <KeyRound className="w-3.5 h-3.5 text-amber-400" />
      case 'INJECTION':
        return <Terminal className="w-3.5 h-3.5 text-rose-400" />
      case 'DANGEROUS_CALLS':
        return <Cpu className="w-3.5 h-3.5 text-purple-400" />
      case 'CONFIGURATION':
        return <Settings className="w-3.5 h-3.5 text-blue-400" />
      case 'CRYPTO':
        return <Hash className="w-3.5 h-3.5 text-emerald-400" />
      case 'AUTHENTICATION':
        return <Lock className="w-3.5 h-3.5 text-orange-400" />
      default:
        return <ShieldAlert className="w-3.5 h-3.5 text-slate-400" />
    }
  }

  const handleCopy = (text: string, type: 'evidence' | 'remediation') => {
    navigator.clipboard.writeText(text)
    if (type === 'evidence') {
      setCopiedEvidence(true)
      setTimeout(() => setCopiedEvidence(false), 2000)
    } else {
      setCopiedRemediation(true)
      setTimeout(() => setCopiedRemediation(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      {/* 1. Header & Filters Toolbar */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Severity Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedSeverity('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedSeverity === 'ALL'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              All Severities ({issues.length})
            </button>
            <button
              onClick={() => setSelectedSeverity('CRITICAL')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedSeverity === 'CRITICAL'
                  ? 'bg-rose-500 text-white shadow-sm'
                  : 'bg-slate-800 text-rose-400 hover:bg-slate-700'
              }`}
            >
              <Flame className="w-3.5 h-3.5" />
              <span>Critical ({criticalCount})</span>
            </button>
            <button
              onClick={() => setSelectedSeverity('HIGH')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedSeverity === 'HIGH'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'bg-slate-800 text-amber-400 hover:bg-slate-700'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>High ({highCount})</span>
            </button>
            <button
              onClick={() => setSelectedSeverity('MEDIUM')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedSeverity === 'MEDIUM'
                  ? 'bg-yellow-500 text-slate-900 font-semibold shadow-sm'
                  : 'bg-slate-800 text-yellow-400 hover:bg-slate-700'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Medium ({mediumCount})</span>
            </button>
            <button
              onClick={() => setSelectedSeverity('LOW')}
              className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                selectedSeverity === 'LOW'
                  ? 'bg-sky-500 text-white shadow-sm'
                  : 'bg-slate-800 text-sky-400 hover:bg-slate-700'
              }`}
            >
              <Info className="w-3.5 h-3.5" />
              <span>Low ({lowCount})</span>
            </button>
          </div>

          {/* Search Input */}
          <div className="relative min-w-[240px] flex-1 max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search file, message, or rule..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/80">
          <span className="text-[11px] font-medium text-slate-400 mr-1.5">Category:</span>
          {['ALL', 'SECRETS', 'INJECTION', 'DANGEROUS_CALLS', 'CONFIGURATION', 'CRYPTO', 'AUTHENTICATION'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
                selectedCategory === cat
                  ? 'bg-slate-700 text-white font-semibold'
                  : 'bg-slate-800/50 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {cat === 'ALL' ? 'All Categories' : cat.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Main Content Split View: Issue List & Details Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Issues List */}
        <div className={`${selectedIssue ? 'lg:col-span-6' : 'lg:col-span-12'} space-y-3 transition-all duration-200`}>
          <div className="flex items-center justify-between text-xs text-slate-400 px-1">
            <span>Showing {filteredIssues.length} of {issues.length} detected security findings</span>
            {selectedIssue && (
              <button
                onClick={() => setSelectedIssue(null)}
                className="text-blue-400 hover:text-blue-300 font-medium lg:hidden"
              >
                Close Drawer
              </button>
            )}
          </div>

          {filteredIssues.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center">
              <ShieldCheck className="w-12 h-12 text-emerald-400/60 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-slate-200">No Security Issues Found</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                No vulnerabilities matched the selected filter criteria. All examined patterns passed static security checks.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {filteredIssues.map((issue) => {
                const isSelected = selectedIssue?.id === issue.id
                return (
                  <div
                    key={issue.id}
                    onClick={() => setSelectedIssue(issue)}
                    className={`group relative p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-blue-950/20 border-blue-500/50 shadow-md ring-1 ring-blue-500/20'
                        : 'bg-slate-900/40 border-slate-800/80 hover:bg-slate-800/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1.5 flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          {getSeverityBadge(issue.severity)}
                          <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                            {getCategoryIcon(issue.category)}
                            <span className="uppercase">{issue.category}</span>
                          </span>
                          <span className="text-[10px] font-mono text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                            Confidence: {issue.confidence}
                          </span>
                        </div>

                        <h4 className="text-sm font-medium text-slate-200 group-hover:text-blue-300 transition-colors truncate">
                          {issue.message}
                        </h4>

                        <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono">
                          <FileCode className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                          <span className="truncate">{issue.file_path}:{issue.line_number}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-1 shrink-0">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedIssueForAI(issue)
                          }}
                          className="p-1 rounded text-purple-400/80 hover:text-purple-300 hover:bg-purple-950/40 transition"
                          title="Explain Threat with AI"
                        >
                          <Sparkles className="w-4 h-4" />
                        </button>
                        <ChevronRight
                          className={`w-4 h-4 text-slate-500 transition-transform ${
                            isSelected ? 'rotate-90 text-blue-400' : 'group-hover:translate-x-0.5'
                          }`}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right: Selected Issue Detail Drawer */}
        {selectedIssue && (
          <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl sticky top-6 space-y-6">
            {/* Drawer Header */}
            <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-800">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  {getSeverityBadge(selectedIssue.severity)}
                  <span className="text-xs font-mono text-slate-400 uppercase">
                    {selectedIssue.category} • {selectedIssue.issue_type.replace(/_/g, ' ')}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-slate-100">{selectedIssue.message}</h3>
                <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                  <FileCode className="w-3.5 h-3.5 text-slate-500" />
                  <span>{selectedIssue.file_path} (Line {selectedIssue.line_number})</span>
                </div>
              </div>

              <button
                onClick={() => setSelectedIssue(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Masked Evidence Box */}
            {selectedIssue.evidence && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                    <Lock className="w-3.5 h-3.5 text-amber-400" />
                    <span>Discovered Evidence (Strictly Masked)</span>
                  </span>
                  <button
                    onClick={() => handleCopy(selectedIssue.evidence!, 'evidence')}
                    className="inline-flex items-center space-x-1 text-slate-400 hover:text-white text-[11px]"
                  >
                    {copiedEvidence ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-rose-300 overflow-x-auto whitespace-pre-wrap">
                  {selectedIssue.evidence}
                </pre>
              </div>
            )}

            {/* Vulnerability Explanation */}
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Why this matters
              </h4>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                {selectedIssue.description}
              </p>
            </div>

            {/* Remediation Guide */}
            {selectedIssue.recommendation && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <h4 className="font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Remediation Advice</span>
                  </h4>
                  <button
                    onClick={() => handleCopy(selectedIssue.recommendation!, 'remediation')}
                    className="inline-flex items-center space-x-1 text-slate-400 hover:text-white text-[11px]"
                  >
                    {copiedRemediation ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="text-xs text-emerald-300/90 leading-relaxed bg-emerald-950/20 border border-emerald-500/20 p-3 rounded-lg">
                  {selectedIssue.recommendation}
                </div>
              </div>
            )}

            {/* AI Problem Explainer Trigger */}
            <div className="pt-2">
              <button
                onClick={() => setSelectedIssueForAI(selectedIssue)}
                className="w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-lg bg-gradient-to-r from-purple-600/20 via-blue-600/20 to-purple-600/20 hover:from-purple-600/30 hover:via-blue-600/30 hover:to-purple-600/30 border border-purple-500/40 text-purple-200 text-xs font-medium transition shadow-sm group"
              >
                <Sparkles className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
                <span>Explain Threat & Impact with AI</span>
              </button>
            </div>

            {/* Read-Only Source Code Preview with Masking */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-300 flex items-center space-x-1.5">
                  <Code2 className="w-3.5 h-3.5 text-blue-400" />
                  <span>Source Context (Read-Only • Zero Execution)</span>
                </span>
                {snippet && (
                  <span className="text-[11px] font-mono text-slate-400">
                    Lines {snippet.start_line} - {snippet.end_line}
                  </span>
                )}
              </div>

              {loadingSnippet ? (
                <div className="p-8 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-center space-x-2 text-xs text-slate-400">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                  <span>Loading source preview...</span>
                </div>
              ) : snippetError ? (
                <div className="p-4 bg-slate-950 border border-rose-500/30 rounded-lg text-xs text-rose-400">
                  {snippetError}
                </div>
              ) : snippet ? (
                <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden font-mono text-xs max-h-64 overflow-y-auto">
                  {snippet.lines.map((line) => (
                    <div
                      key={line.line_number}
                      className={`flex items-start px-3 py-1 ${
                        line.is_highlighted
                          ? 'bg-rose-500/20 border-l-2 border-rose-500 text-rose-200'
                          : 'text-slate-400 hover:bg-slate-900/50'
                      }`}
                    >
                      <span className="w-10 shrink-0 text-slate-400 select-none text-right pr-3">
                        {line.line_number}
                      </span>
                      <span className="overflow-x-auto whitespace-pre">{line.content}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        )}
      </div>

      {/* AI Explanation Modal */}
      <AIExplanationModal
        isOpen={!!selectedIssueForAI}
        onClose={() => setSelectedIssueForAI(null)}
        issueId={selectedIssueForAI?.id || ''}
        issueTitle={selectedIssueForAI?.message || ''}
        issueLocation={selectedIssueForAI ? `${selectedIssueForAI.file_path}:${selectedIssueForAI.line_number}` : undefined}
        issueSeverity={selectedIssueForAI?.severity}
        category="security"
      />
    </div>
  )
}
