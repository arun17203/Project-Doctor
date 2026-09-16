import React, { useState, useEffect, useRef } from 'react'
import { FileCode, X, Copy, Check, ShieldAlert, Code2, AlertTriangle, ExternalLink } from 'lucide-react'

interface CodeLine {
  line_number: number
  content: string
  is_target?: boolean
}

interface CodeSnippetModalProps {
  isOpen: boolean
  onClose: () => void
  filePath: string
  lines: CodeLine[]
  targetLine?: number
  language?: string
  symbolName?: string
  recommendation?: string
  severity?: string
}

export const CodeSnippetModal: React.FC<CodeSnippetModalProps> = ({
  isOpen,
  onClose,
  filePath,
  lines,
  targetLine,
  language = 'Code',
  symbolName,
  recommendation,
  severity,
}) => {
  const [copied, setCopied] = useState(false)
  const targetRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isOpen && targetRef.current) {
      setTimeout(() => {
        targetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 100)
    }
  }, [isOpen, targetLine])

  if (!isOpen) return null

  const handleCopy = () => {
    const rawCode = lines.map((l) => l.content).join('\n')
    navigator.clipboard.writeText(rawCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`Source file viewer for ${filePath}`}
    >
      <div className="bg-[#0d1322] border border-slate-800 rounded-xl shadow-2xl max-w-4xl w-full flex flex-col max-h-[88vh] overflow-hidden">
        {/* Header Strip */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-[#090d16]/70">
          <div className="flex items-center space-x-2.5 min-w-0">
            <FileCode className="h-4 w-4 text-blue-400 shrink-0" />
            <span className="font-mono text-xs font-semibold text-white truncate max-w-md">
              {filePath}
            </span>
            {targetLine && (
              <span className="text-[11px] font-mono text-slate-400">
                :L{targetLine}
              </span>
            )}
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 uppercase">
              {language}
            </span>
            {severity && (
              <span
                className={`text-[10px] font-mono uppercase px-1.5 py-0.2 rounded font-semibold ${
                  severity.toLowerCase() === 'critical'
                    ? 'bg-rose-500/20 text-rose-400'
                    : severity.toLowerCase() === 'high'
                    ? 'bg-orange-500/20 text-orange-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}
              >
                {severity}
              </span>
            )}
          </div>

          <div className="flex items-center space-x-2 shrink-0">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white text-xs font-mono transition"
              title="Copy snippet"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
              aria-label="Close code snippet"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Symbol / Function Banner if available */}
        {symbolName && (
          <div className="px-4 py-1.5 bg-slate-900/50 border-b border-slate-800/80 text-[11px] font-mono text-slate-400 flex items-center space-x-2">
            <span className="text-slate-500">Target Symbol:</span>
            <code className="text-blue-300 font-semibold">{symbolName}</code>
          </div>
        )}

        {/* Read-Only Code Viewer Body */}
        <div className="flex-1 overflow-auto bg-[#070a12] p-2 sm:p-4 font-mono text-xs text-slate-200 selection:bg-blue-900 selection:text-white">
          <div className="min-w-full inline-block">
            {lines.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs">
                No code lines available for this target location.
              </div>
            ) : (
              lines.map((l) => {
                const isTarget = l.is_target || l.line_number === targetLine
                return (
                  <div
                    key={l.line_number}
                    ref={isTarget ? targetRef : undefined}
                    className={`flex items-stretch font-mono leading-relaxed group ${
                      isTarget
                        ? 'bg-rose-950/30 border-l-2 border-rose-500 text-rose-100 font-medium'
                        : 'hover:bg-slate-900/40 border-l-2 border-transparent'
                    }`}
                  >
                    {/* Line Indicator & Number */}
                    <div className="w-12 sm:w-16 shrink-0 select-none text-right pr-3 sm:pr-4 text-slate-600 group-hover:text-slate-400 tabular-nums text-[11px] flex items-center justify-end space-x-1">
                      {isTarget && <span className="text-rose-400 font-bold text-xs">&gt;</span>}
                      <span>{l.line_number}</span>
                    </div>
                    {/* Code Content (Strictly sanitized, secrets masked) */}
                    <pre className="flex-1 pl-2 pr-4 overflow-x-auto whitespace-pre font-mono text-xs">
                      {l.content || ' '}
                    </pre>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Recommendation / Remediation Footer */}
        {recommendation && (
          <div className="p-3 bg-[#090d16] border-t border-slate-800 text-xs space-y-1">
            <span className="font-semibold text-slate-300 text-[11px] uppercase tracking-wide flex items-center space-x-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
              <span>Recommended Remediation</span>
            </span>
            <p className="text-slate-400 text-[11px] leading-relaxed">{recommendation}</p>
          </div>
        )}

        {/* Close Strip */}
        <div className="px-4 py-2 bg-[#0b0f19] border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-500">
          <span>Read-only source inspector • Zero code execution</span>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default CodeSnippetModal
