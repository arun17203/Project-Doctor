import React, { useState, useEffect } from 'react'
import {
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  FileCode,
  Search,
  SlidersHorizontal,
  ChevronRight,
  X,
  Code2,
  Copy,
  Check,
  Loader2,
  ExternalLink,
  Flame,
  ArrowUpDown,
  BookOpen,
  Sparkles
} from 'lucide-react'
import type { QualityIssue, CodeSnippet, SeverityLevel } from '../../types/quality'
import { projectService } from '../../services/projectService'
import AIExplanationModal from '../ai/AIExplanationModal'

interface IssueExplorerProps {
  projectId: string
  issues: QualityIssue[]
  loading?: boolean
  onRefresh?: () => void
}

export default function IssueExplorer({ projectId, issues, loading = false, onRefresh }: IssueExplorerProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('ALL')
  const [selectedType, setSelectedType] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedIssue, setSelectedIssue] = useState<QualityIssue | null>(null)
  const [selectedIssueForAI, setSelectedIssueForAI] = useState<QualityIssue | null>(null)

  // Snippet modal state
  const [snippet, setSnippet] = useState<CodeSnippet | null>(null)
  const [loadingSnippet, setLoadingSnippet] = useState<boolean>(false)
  const [snippetError, setSnippetError] = useState<string | null>(null)
  const [copied, setCopied] = useState<boolean>(false)

  // Fetch code snippet whenever selected issue changes
  useEffect(() => {
    if (!selectedIssue) {
      setSnippet(null)
      return
    }

    const fetchSnippet = async () => {
      setLoadingSnippet(true)
      setSnippetError(null)
      try {
        const data = await projectService.getCodeSnippet(
          projectId,
          selectedIssue.file_path,
          selectedIssue.line_number,
          5
        )
        setSnippet(data)
      } catch (err: any) {
        console.error('Failed to load code snippet:', err)
        setSnippetError(err.response?.data?.detail || 'Failed to load source code preview.')
      } finally {
        setLoadingSnippet(false)
      }
    }

    fetchSnippet()
  }, [projectId, selectedIssue])

  // Severities and counts
  const criticalCount = issues.filter((i) => i.severity === 'CRITICAL').length
  const highCount = issues.filter((i) => i.severity === 'HIGH').length
  const mediumCount = issues.filter((i) => i.severity === 'MEDIUM').length
  const lowCount = issues.filter((i) => i.severity === 'LOW').length

  // Filter issues
  const filteredIssues = issues.filter((issue) => {
    if (selectedSeverity !== 'ALL' && issue.severity !== selectedSeverity) {
      return false
    }
    if (selectedType !== 'ALL' && issue.issue_type !== selectedType) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchFile = issue.file_path.toLowerCase().includes(q)
      const matchSymbol = issue.symbol_name?.toLowerCase().includes(q) || false
      const matchMsg = issue.message.toLowerCase().includes(q)
      if (!matchFile && !matchSymbol && !matchMsg) return false
    }
    return true
  })

  const getSeverityBadge = (sev: SeverityLevel | string) => {
    switch (sev) {
      case 'CRITICAL':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30 uppercase">
            <Flame className="h-3 w-3 text-rose-400" />
            <span>CRITICAL</span>
          </span>
        )
      case 'HIGH':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30 uppercase">
            <AlertTriangle className="h-3 w-3 text-amber-400" />
            <span>HIGH</span>
          </span>
        )
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/10 text-blue-400 border border-blue-500/30 uppercase">
            <AlertCircle className="h-3 w-3 text-blue-400" />
            <span>MEDIUM</span>
          </span>
        )
      case 'LOW':
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30 uppercase">
            <Info className="h-3 w-3 text-slate-400" />
            <span>LOW</span>
          </span>
        )
    }
  }

  const formatIssueType = (type: string) => {
    switch (type) {
      case 'high_complexity':
        return 'High Complexity'
      case 'long_function':
        return 'Long Function'
      case 'deep_nesting':
        return 'Deep Nesting'
      case 'duplicate_code':
        return 'Duplicate Code'
      case 'unused_import':
        return 'Unused Import'
      case 'todo_comment':
        return 'TODO / Debt'
      default:
        return type.replace(/_/g, ' ')
    }
  }

  const handleCopySnippet = () => {
    if (!snippet) return
    const text = snippet.lines.map((l) => `${l.line_number}: ${l.content}`).join('\n')
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Filter and Search Bar */}
      <div className="rounded-xl border border-slate-800 bg-[#0d1322] p-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Severity Pills */}
          <div className="flex items-center flex-wrap gap-2">
            <button
              onClick={() => setSelectedSeverity('ALL')}
              className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all ${
                selectedSeverity === 'ALL'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-slate-900/80 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              All ({issues.length})
            </button>
            <button
              onClick={() => setSelectedSeverity('CRITICAL')}
              className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all flex items-center space-x-1.5 ${
                selectedSeverity === 'CRITICAL'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/30'
              }`}
            >
              <span>Critical</span>
              <span className="px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 text-[10px] font-bold">
                {criticalCount}
              </span>
            </button>
            <button
              onClick={() => setSelectedSeverity('HIGH')}
              className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all flex items-center space-x-1.5 ${
                selectedSeverity === 'HIGH'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/30'
              }`}
            >
              <span>High</span>
              <span className="px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 text-[10px] font-bold">
                {highCount}
              </span>
            </button>
            <button
              onClick={() => setSelectedSeverity('MEDIUM')}
              className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all flex items-center space-x-1.5 ${
                selectedSeverity === 'MEDIUM'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/30'
              }`}
            >
              <span>Medium</span>
              <span className="px-1.5 py-0.2 rounded bg-blue-950 text-blue-300 text-[10px] font-bold">
                {mediumCount}
              </span>
            </button>
            <button
              onClick={() => setSelectedSeverity('LOW')}
              className={`px-3 py-1 rounded-md text-xs font-mono font-medium transition-all flex items-center space-x-1.5 ${
                selectedSeverity === 'LOW'
                  ? 'bg-slate-700 text-white shadow-sm'
                  : 'bg-slate-800/60 text-slate-400 hover:bg-slate-800 border border-slate-700/50'
              }`}
            >
              <span>Low</span>
              <span className="px-1.5 py-0.2 rounded bg-slate-900 text-slate-300 text-[10px] font-bold">
                {lowCount}
              </span>
            </button>
          </div>

          {/* Search Input */}
          <div className="relative min-w-[240px]">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search file, symbol, issue..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900/90 border border-slate-800 rounded-md text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>
        </div>

        {/* Secondary Filters: Issue Type */}
        <div className="flex items-center space-x-3 pt-2 border-t border-slate-800/60 text-xs text-slate-400">
          <span className="text-[11px] font-mono uppercase text-slate-500">Filter by Rule:</span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-blue-500"
          >
            <option value="ALL">All Rule Categories</option>
            <option value="high_complexity">High Complexity</option>
            <option value="long_function">Long Function</option>
            <option value="deep_nesting">Deep Nesting</option>
            <option value="duplicate_code">Duplicate Code</option>
            <option value="unused_import">Unused Import</option>
            <option value="todo_comment">TODO / Technical Debt</option>
          </select>

          <span className="text-[11px] text-slate-500">
            Showing <strong className="text-white font-mono">{filteredIssues.length}</strong> of{' '}
            <strong className="text-white font-mono">{issues.length}</strong> issues
          </span>
        </div>
      </div>

      {/* Main Content Layout: Issue Table + Detail Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Issues Table */}
        <div className={`space-y-2 ${selectedIssue ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="rounded-xl border border-slate-800 bg-[#0d1322] overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Issue Type</th>
                    <th className="py-3 px-4">File & Location</th>
                    <th className="py-3 px-4">Symbol</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-slate-300 font-mono">
                  {loading ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-500">
                        <div className="flex flex-col items-center justify-center space-y-2">
                          <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
                          <span>Loading code quality issues...</span>
                        </div>
                      </td>
                    </tr>
                  ) : filteredIssues.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-500">
                        <div className="flex flex-col items-center justify-center space-y-2">
                          <CheckCircle className="h-8 w-8 text-emerald-500/60" />
                          <span className="text-slate-400 font-medium">No issues matching criteria!</span>
                          <span className="text-[11px] text-slate-600">
                            Try broadening your search or severity filter.
                          </span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    filteredIssues.map((issue) => {
                      const isSelected = selectedIssue?.id === issue.id
                      return (
                        <tr
                          key={issue.id}
                          onClick={() => setSelectedIssue(issue)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? 'bg-blue-600/15 border-l-2 border-l-blue-500'
                              : 'hover:bg-slate-800/40'
                          }`}
                        >
                          <td className="py-3 px-4 whitespace-nowrap">
                            {getSeverityBadge(issue.severity)}
                          </td>
                          <td className="py-3 px-4">
                            <div className="font-semibold text-white truncate max-w-[170px]">
                              {formatIssueType(issue.issue_type)}
                            </div>
                            <div className="text-[11px] text-slate-400 truncate max-w-[200px]">
                              {issue.message}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            <div className="text-slate-300 truncate max-w-[200px]" title={issue.file_path}>
                              {issue.file_path}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              Line {issue.line_number}
                              {issue.end_line && issue.end_line !== issue.line_number && `–${issue.end_line}`}
                            </div>
                          </td>
                          <td className="py-3 px-4">
                            {issue.symbol_name ? (
                              <span className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-blue-400 text-[11px]">
                                {issue.symbol_name}
                              </span>
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </td>
                          <td className="py-3 px-4 text-right">
                            <div className="flex items-center justify-end space-x-1">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSelectedIssueForAI(issue)
                                }}
                                className="p-1 rounded text-purple-400/80 hover:text-purple-300 hover:bg-purple-950/40 transition"
                                title="Explain Root Cause with AI"
                              >
                                <Sparkles className="h-4 w-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  setSelectedIssue(issue)
                                }}
                                className={`p-1 rounded text-slate-400 hover:text-white transition ${
                                  isSelected ? 'text-blue-400' : ''
                                }`}
                                title="Inspect Issue"
                              >
                                <ChevronRight className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Selected Issue Detail & Code Snippet Panel */}
        {selectedIssue && (
          <div className="lg:col-span-5 space-y-4">
            <div className="rounded-xl border border-slate-800 bg-[#0d1322] p-5 space-y-5 sticky top-20 shadow-xl">
              {/* Header */}
              <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    {getSeverityBadge(selectedIssue.severity)}
                    <span className="text-xs font-mono uppercase text-slate-400">
                      {formatIssueType(selectedIssue.issue_type)}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-white">{selectedIssue.message}</h3>
                </div>
                <button
                  onClick={() => setSelectedIssue(null)}
                  className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition"
                  title="Close panel"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Location & Symbol Metadata */}
              <div className="grid grid-cols-2 gap-3 text-xs font-mono bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">File & Line</span>
                  <span className="text-slate-200 truncate block mt-0.5" title={selectedIssue.file_path}>
                    {selectedIssue.file_path}:{selectedIssue.line_number}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase">Target Symbol</span>
                  <span className="text-blue-400 block mt-0.5 truncate">
                    {selectedIssue.symbol_name || 'Module-level'}
                  </span>
                </div>
              </div>

              {/* Why This Matters (Description) */}
              <div className="space-y-1.5">
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                  <BookOpen className="h-3.5 w-3.5 text-blue-400" />
                  <span>Why This Matters</span>
                </h4>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-md border border-slate-800/50">
                  {selectedIssue.description}
                </p>
              </div>

              {/* Quantitative Evidence */}
              {selectedIssue.evidence && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                    <SlidersHorizontal className="h-3.5 w-3.5 text-amber-400" />
                    <span>Evidence</span>
                  </h4>
                  <div className="text-xs text-amber-300 font-mono bg-amber-500/5 border border-amber-500/20 px-3 py-2 rounded-md">
                    {selectedIssue.evidence}
                  </div>
                </div>
              )}

              {/* Suggested Remediation */}
              {selectedIssue.recommendation && (
                <div className="space-y-1.5">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Deterministic Remediation</span>
                  </h4>
                  <div className="text-xs text-emerald-300 bg-emerald-500/5 border border-emerald-500/20 px-3 py-2.5 rounded-md leading-relaxed">
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
                  <Sparkles className="h-4 w-4 text-purple-400 group-hover:scale-110 transition-transform" />
                  <span>Explain Root Cause with AI</span>
                </button>
              </div>

              {/* Read-Only Source Code Preview */}
              <div className="space-y-2 pt-2 border-t border-slate-800">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5 font-mono">
                    <Code2 className="h-3.5 w-3.5 text-purple-400" />
                    <span>Read-Only Source Context</span>
                  </h4>
                  <button
                    onClick={handleCopySnippet}
                    disabled={!snippet}
                    className="flex items-center space-x-1 text-[10px] font-mono text-slate-400 hover:text-white transition disabled:opacity-40"
                    title="Copy snippet"
                  >
                    {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <div className="rounded-lg bg-[#070a12] border border-slate-800 overflow-hidden text-[11px] font-mono">
                  {loadingSnippet ? (
                    <div className="p-8 text-center text-slate-500 flex flex-col items-center justify-center space-y-1.5">
                      <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
                      <span>Reading file safely...</span>
                    </div>
                  ) : snippetError ? (
                    <div className="p-4 text-rose-400 bg-rose-500/5 text-xs">
                      {snippetError}
                    </div>
                  ) : snippet ? (
                    <div className="max-h-64 overflow-y-auto divide-y divide-slate-800/30">
                      {snippet.lines.map((line) => (
                        <div
                          key={line.line_number}
                          className={`flex items-baseline px-3 py-1 ${
                            line.is_highlighted
                              ? 'bg-rose-500/15 border-l-2 border-rose-500 text-rose-200'
                              : 'text-slate-400 hover:bg-slate-900/50'
                          }`}
                        >
                          <span
                            className={`w-10 select-none text-right pr-3 shrink-0 text-[10px] ${
                              line.is_highlighted ? 'text-rose-400 font-bold' : 'text-slate-600'
                            }`}
                          >
                            {line.line_number}
                          </span>
                          <pre className="overflow-x-auto whitespace-pre font-mono text-slate-300 text-[11px]">
                            {line.content || ' '}
                          </pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-4 text-center text-slate-500">
                      No code preview available.
                    </div>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 italic">
                  Read-only view with automatic credential masking. Zero code execution.
                </p>
              </div>
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
        category="quality"
      />
    </div>
  )
}
