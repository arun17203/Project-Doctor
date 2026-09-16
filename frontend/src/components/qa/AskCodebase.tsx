import React, { useState, useRef, useEffect } from 'react'
import {
  Sparkles,
  Send,
  User,
  Bot,
  FileCode2,
  ExternalLink,
  Copy,
  Check,
  RotateCcw,
  AlertTriangle,
  Loader2,
  HelpCircle,
  Code2,
  Terminal,
  ShieldCheck,
  ChevronRight,
  X,
  Layers,
} from 'lucide-react'
import { projectService } from '../../services/projectService'
import type { ChatMessage, SourceCitation } from '../../types/qa'
import type { CodeSnippet } from '../../types/quality'

interface AskCodebaseProps {
  projectId: string
  projectName: string
}

const SUGGESTED_QUESTIONS = [
  'Where is user authentication and authorization implemented?',
  'What are the most critical security vulnerabilities found in this codebase?',
  'Are there any circular dependencies detected in the architecture graph?',
  'Which dependencies are flagged with vulnerabilities or license concerns?',
  'What technical debt issues are dragging down the project health score?',
  'What are the primary entry points and module structure of this application?',
]

export const AskCodebase: React.FC<AskCodebaseProps> = ({ projectId, projectName }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputQuestion, setInputQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [errorBanner, setErrorBanner] = useState<string | null>(null)
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  // Snippet Preview Modal state
  const [previewCitation, setPreviewCitation] = useState<SourceCitation | null>(null)
  const [previewSnippet, setPreviewSnippet] = useState<CodeSnippet | null>(null)
  const [loadingSnippet, setLoadingSnippet] = useState(false)
  const [snippetError, setSnippetError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  // Stepped animation when loading
  useEffect(() => {
    if (!loading) {
      setLoadingStep(0)
      return
    }

    const interval = setInterval(() => {
      setLoadingStep((prev) => (prev < 2 ? prev + 1 : prev))
    }, 1800)

    return () => clearInterval(interval)
  }, [loading])

  const handleSend = async (questionText?: string) => {
    const q = (questionText || inputQuestion).trim()
    if (!q || loading) return

    setErrorBanner(null)
    const userMsgId = `user-${Date.now()}`
    const userMsg: ChatMessage = {
      id: userMsgId,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    // Prepare previous conversation context (up to last 6 turns)
    const historyPayload = messages
      .filter((m) => !m.isError && m.content)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMsg])
    setInputQuestion('')
    setLoading(true)
    setLoadingStep(0)

    try {
      const response = await projectService.askCodebase(projectId, {
        question: q,
        conversation: historyPayload,
      })

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }

      setMessages((prev) => [...prev, assistantMsg])
    } catch (err: any) {
      const status = err?.response?.status
      const detail = err?.response?.data?.detail || err?.message || 'Failed to generate answer'

      let displayError = detail
      if (status === 503) {
        displayError =
          'Google Gemini service is currently unavailable or GEMINI_API_KEY is not configured in backend/.env. Please verify your API key.'
      }

      setErrorBanner(displayError)

      const errorAssistantMsg: ChatMessage = {
        id: `assistant-err-${Date.now()}`,
        role: 'assistant',
        content:
          status === 503
            ? '⚠️ Google Gemini AI engine is currently unavailable. To enable AI Codebase Q&A, ensure `GEMINI_API_KEY` is configured in your backend `.env` file.'
            : `⚠️ Unable to answer: ${displayError}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      }

      setMessages((prev) => [...prev, errorAssistantMsg])
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleCopyAnswer = (text: string, idx: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIndex(idx)
    setTimeout(() => setCopiedIndex(null), 2000)
  }

  const handleOpenSnippetPreview = async (citation: SourceCitation) => {
    setPreviewCitation(citation)
    setPreviewSnippet(null)
    setSnippetError(null)
    setLoadingSnippet(true)

    try {
      const line = citation.line_start || 1
      const snippet = await projectService.getCodeSnippet(projectId, citation.file_path, line, 10)
      setPreviewSnippet(snippet)
    } catch (err: any) {
      setSnippetError(
        err?.response?.data?.detail || 'Source snippet preview could not be loaded for this file.'
      )
    } finally {
      setLoadingSnippet(false)
    }
  }

  const handleResetChat = () => {
    setMessages([])
    setErrorBanner(null)
  }

  // Format simple markdown blocks: code blocks ```, inline backticks, lists, headers
  const renderFormattedAnswer = (content: string) => {
    const parts = content.split(/(```[\s\S]*?```)/g)

    return (
      <div className="space-y-2.5 text-xs sm:text-sm text-slate-200 leading-relaxed font-sans">
        {parts.map((part, idx) => {
          if (part.startsWith('```')) {
            const lines = part.slice(3, -3).trim().split('\n')
            const firstLine = lines[0].trim()
            const hasLang = firstLine.match(/^[a-zA-Z0-9_-]+$/)
            const language = hasLang ? firstLine : 'code'
            const codeBody = hasLang ? lines.slice(1).join('\n') : lines.join('\n')

            return (
              <div
                key={idx}
                className="my-3 rounded-lg overflow-hidden border border-slate-800 bg-[#070b14]"
              >
                <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900/90 border-b border-slate-800/80 text-[11px] font-mono text-slate-400">
                  <span className="flex items-center space-x-1.5">
                    <Terminal className="h-3 w-3 text-slate-500" />
                    <span>{language}</span>
                  </span>
                  <button
                    onClick={() => navigator.clipboard.writeText(codeBody)}
                    className="hover:text-white transition flex items-center space-x-1"
                    title="Copy code"
                  >
                    <Copy className="h-3 w-3" />
                    <span className="text-[10px]">Copy</span>
                  </button>
                </div>
                <pre className="p-3 text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed">
                  <code>{codeBody}</code>
                </pre>
              </div>
            )
          }

          // Handle regular paragraphs, bullet points, and headers
          const lines = part.split('\n')
          return (
            <div key={idx} className="space-y-1.5">
              {lines.map((line, lineIdx) => {
                const trimmed = line.trim()
                if (!trimmed) return <div key={lineIdx} className="h-1" />

                if (trimmed.startsWith('### ')) {
                  return (
                    <h4 key={lineIdx} className="text-sm font-semibold text-white pt-2">
                      {trimmed.slice(4)}
                    </h4>
                  )
                }
                if (trimmed.startsWith('## ')) {
                  return (
                    <h3 key={lineIdx} className="text-sm font-bold text-white pt-2.5">
                      {trimmed.slice(3)}
                    </h3>
                  )
                }
                if (trimmed.startsWith('# ')) {
                  return (
                    <h2 key={lineIdx} className="text-base font-bold text-white pt-3">
                      {trimmed.slice(2)}
                    </h2>
                  )
                }

                if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                  return (
                    <div key={lineIdx} className="flex items-start space-x-2 pl-2">
                      <span className="text-indigo-400 mt-1 font-bold">•</span>
                      <span className="flex-1 text-slate-300">
                        {renderInlineFormatting(trimmed.slice(2))}
                      </span>
                    </div>
                  )
                }

                return (
                  <p key={lineIdx} className="text-slate-300 leading-relaxed">
                    {renderInlineFormatting(trimmed)}
                  </p>
                )
              })}
            </div>
          )
        })}
      </div>
    )
  }

  // Format bold (**text**) and inline code (`code`)
  const renderInlineFormatting = (text: string) => {
    const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g)
    return tokens.map((token, i) => {
      if (token.startsWith('`') && token.endsWith('`')) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 font-mono text-[11px] text-indigo-300 mx-0.5"
          >
            {token.slice(1, -1)}
          </code>
        )
      }
      if (token.startsWith('**') && token.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-white">
            {token.slice(2, -2)}
          </strong>
        )
      }
      return token
    })
  }

  return (
    <div className="flex flex-col h-[760px] bg-[#0d1322] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Top Header Bar */}
      <div className="px-5 py-4 bg-[#090d18] border-b border-slate-800 flex items-center justify-between gap-4">
        <div className="flex items-center space-x-3 min-w-0">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-violet-900/30 shrink-0">
            <Sparkles className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center space-x-2">
              <h3 className="text-sm sm:text-base font-bold text-white tracking-tight truncate">
                Ask My Codebase
              </h3>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-violet-950/80 text-violet-300 border border-violet-800/40">
                <Sparkles className="h-2.5 w-2.5 mr-1" />
                Gemini 2.5 Flash
              </span>
              <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                <ShieldCheck className="h-2.5 w-2.5 mr-1" />
                Grounded &amp; Verified
              </span>
            </div>
            <p className="text-xs text-slate-400 truncate">
              Answers strictly constrained to <span className="text-slate-200 font-medium">{projectName}</span> source files &amp; static analysis findings.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {messages.length > 0 && (
            <button
              onClick={handleResetChat}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-850 transition"
              title="Reset conversation session"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Clear Chat</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Banner if any */}
      {errorBanner && (
        <div className="px-5 py-2.5 bg-amber-950/30 border-b border-amber-500/30 flex items-center justify-between text-xs text-amber-300">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
            <span>{errorBanner}</span>
          </div>
          <button
            onClick={() => setErrorBanner(null)}
            className="text-amber-400 hover:text-amber-200 ml-3"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Main Message History Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6 bg-[#090d18]/40">
        {/* Empty State with Suggested Prompts */}
        {messages.length === 0 && (
          <div className="py-8 sm:py-12 flex flex-col items-center justify-center text-center max-w-xl mx-auto space-y-6">
            <div className="h-14 w-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shadow-inner">
              <HelpCircle className="h-7 w-7" />
            </div>

            <div className="space-y-1.5">
              <h4 className="text-base font-semibold text-white">
                What would you like to know about this repository?
              </h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Project Doctor retrieves real AST definitions, deterministic security vulnerabilities, code-quality smells, dependencies, and architecture edges to answer your technical questions.
              </p>
            </div>

            {/* Suggested Chips */}
            <div className="w-full space-y-2 pt-2">
              <div className="text-[11px] font-mono text-slate-500 uppercase tracking-wider text-left">
                Suggested questions:
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(q)}
                    disabled={loading}
                    className="p-3 rounded-xl bg-[#0e1424] hover:bg-[#151f38] border border-slate-800 hover:border-indigo-500/40 text-left text-xs text-slate-300 hover:text-white transition group flex items-start space-x-2 shadow-xs"
                  >
                    <ChevronRight className="h-3.5 w-3.5 text-indigo-400 mt-0.5 shrink-0 group-hover:translate-x-0.5 transition-transform" />
                    <span className="leading-snug">{q}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Render Chat Messages */}
        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className={`flex flex-col ${
              msg.role === 'user' ? 'items-end' : 'items-start'
            } space-y-1.5`}
          >
            {/* Sender Label & Avatar */}
            <div
              className={`flex items-center space-x-2 text-[11px] font-mono text-slate-500 ${
                msg.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`h-5 w-5 rounded-md flex items-center justify-center ${
                  msg.role === 'user'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'bg-violet-600/20 text-violet-400 border border-violet-500/30'
                }`}
              >
                {msg.role === 'user' ? <User className="h-3 w-3" /> : <Bot className="h-3 w-3" />}
              </div>
              <span>{msg.role === 'user' ? 'You' : 'Project Doctor Assistant'}</span>
              <span>•</span>
              <span>{msg.timestamp}</span>
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[88%] sm:max-w-[80%] rounded-2xl p-4 sm:p-5 shadow-md ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-tr-xs'
                  : msg.isError
                  ? 'bg-rose-950/30 border border-rose-500/30 text-rose-200 rounded-tl-xs'
                  : 'bg-[#0f172a] border border-slate-800 rounded-tl-xs space-y-4'
              }`}
            >
              {msg.role === 'user' ? (
                <div className="text-xs sm:text-sm font-sans whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                </div>
              ) : (
                <>
                  {renderFormattedAnswer(msg.content)}

                  {/* Grounded Source Citations */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="pt-3 border-t border-slate-800/80 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-1.5 text-[11px] font-mono font-semibold uppercase text-violet-400 tracking-wider">
                          <Layers className="h-3 w-3" />
                          <span>Grounded Source Citations ({msg.sources.length})</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">Verified Files</span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {msg.sources.map((src, sIdx) => (
                          <div
                            key={sIdx}
                            className="p-2.5 rounded-lg bg-[#070b14] border border-slate-800 hover:border-violet-500/40 transition flex flex-col justify-between space-y-1.5"
                          >
                            <div className="flex items-start justify-between gap-1.5">
                              <div className="flex items-center space-x-1.5 min-w-0">
                                <FileCode2 className="h-3.5 w-3.5 text-violet-400 shrink-0" />
                                <span
                                  className="text-xs font-mono font-medium text-slate-200 truncate"
                                  title={src.file_path}
                                >
                                  {src.file_path}
                                </span>
                              </div>
                              {src.line_start && (
                                <span className="font-mono text-[10px] text-violet-300 bg-violet-950/60 px-1.5 py-0.5 rounded border border-violet-800/40 shrink-0">
                                  L{src.line_start}
                                  {src.line_end && src.line_end !== src.line_start
                                    ? `-${src.line_end}`
                                    : ''}
                                </span>
                              )}
                            </div>

                            {src.reason && (
                              <p className="text-[11px] text-slate-400 leading-snug line-clamp-2">
                                {src.reason}
                              </p>
                            )}

                            <div className="pt-1 flex items-center justify-end">
                              <button
                                onClick={() => handleOpenSnippetPreview(src)}
                                className="inline-flex items-center space-x-1 text-[10px] font-mono text-violet-400 hover:text-violet-300 transition"
                              >
                                <span>Inspect Snippet</span>
                                <ExternalLink className="h-2.5 w-2.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions & Copy Bar */}
                  {!msg.isError && (
                    <div className="pt-2 flex items-center justify-between border-t border-slate-800/60 text-[11px] font-mono text-slate-500">
                      <span className="flex items-center space-x-1">
                        <ShieldCheck className="h-3 w-3 text-emerald-400" />
                        <span>Constrained to project repository</span>
                      </span>

                      <button
                        onClick={() => handleCopyAnswer(msg.content, idx)}
                        className="inline-flex items-center space-x-1 text-slate-400 hover:text-white transition"
                        title="Copy answer"
                      >
                        {copiedIndex === idx ? (
                          <>
                            <Check className="h-3 w-3 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3" />
                            <span>Copy Answer</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {/* Thinking / Generation in progress */}
        {loading && (
          <div className="flex flex-col items-start space-y-2">
            <div className="flex items-center space-x-2 text-[11px] font-mono text-violet-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Project Doctor Assistant is inspecting codebase...</span>
            </div>

            <div className="rounded-2xl rounded-tl-xs p-4 bg-[#0f172a] border border-slate-800 max-w-md w-full space-y-2.5">
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <div className="h-8 w-8 rounded-full border-2 border-violet-500/20 border-t-violet-500 animate-spin" />
                  <Sparkles className="h-3.5 w-3.5 text-violet-400 absolute inset-0 m-auto" />
                </div>
                <div className="space-y-0.5">
                  <div className="text-xs font-medium text-white">
                    {loadingStep === 0 && 'Retrieving relevant source files & AST symbols...'}
                    {loadingStep === 1 && 'Correlating deterministic security, quality & graph data...'}
                    {loadingStep === 2 && 'Synthesizing verified citations with Gemini 2.5 Flash...'}
                  </div>
                  <div className="text-[10px] text-slate-400 font-mono">
                    Zero hallucinations · Strictly grounded response
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Bottom Input Form */}
      <div className="p-4 bg-[#090d18] border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex items-end space-x-2"
        >
          <div className="flex-1 relative rounded-xl bg-[#0f172a] border border-slate-800 focus-within:border-violet-500 transition">
            <textarea
              ref={inputRef}
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              placeholder="Ask anything about your codebase (e.g., 'How is authentication structured?', 'Which endpoints are exposed?')..."
              rows={2}
              className="w-full bg-transparent px-3.5 py-2.5 text-xs sm:text-sm text-slate-200 placeholder-slate-500 focus:outline-hidden resize-none leading-relaxed font-sans"
            />
            <div className="px-3 pb-1.5 flex items-center justify-between text-[10px] font-mono text-slate-500">
              <span>Press Enter to send · Shift+Enter for newline</span>
              <span>{inputQuestion.length}/1000</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !inputQuestion.trim()}
            className="h-11 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white text-xs font-medium transition flex items-center space-x-2 shadow-md disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                <span>Send</span>
                <Send className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </form>
      </div>

      {/* Snippet Preview Modal */}
      {previewCitation && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
          <div
            className="bg-[#0d1322] border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col my-auto max-h-[90vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-4 sm:p-5 border-b border-slate-800 flex items-start justify-between gap-3 bg-[#0a0f1d]">
              <div className="space-y-1 min-w-0">
                <div className="flex items-center space-x-2">
                  <span className="p-1 rounded bg-violet-600/10 border border-violet-500/20 text-violet-400">
                    <FileCode2 className="h-4 w-4" />
                  </span>
                  <span className="text-xs font-mono font-semibold text-slate-300 uppercase tracking-wider">
                    Source Code Citation Preview
                  </span>
                </div>
                <div className="font-mono text-sm text-white font-semibold truncate">
                  {previewCitation.file_path}
                </div>
                {previewCitation.reason && (
                  <p className="text-xs text-slate-400 pt-0.5 leading-snug">
                    {previewCitation.reason}
                  </p>
                )}
              </div>

              <button
                onClick={() => setPreviewCitation(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition shrink-0"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body: Code Snippet */}
            <div className="p-4 sm:p-5 flex-1 overflow-y-auto">
              {loadingSnippet && (
                <div className="py-16 flex flex-col items-center justify-center space-y-3">
                  <Loader2 className="h-6 w-6 text-violet-400 animate-spin" />
                  <span className="text-xs text-slate-400 font-mono">
                    Loading code snippet from disk...
                  </span>
                </div>
              )}

              {snippetError && (
                <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs text-amber-300">
                  {snippetError}
                </div>
              )}

              {previewSnippet && (
                <div className="rounded-xl border border-slate-800 bg-[#070b14] overflow-hidden">
                  <div className="px-4 py-2 bg-slate-900/90 border-b border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                    <span>
                      File:{' '}
                      <strong className="text-slate-200">
                        {previewCitation?.file_path.split('.').pop()?.toUpperCase() || 'Source'}
                      </strong>
                    </span>
                    <span>
                      Target Line: <strong className="text-violet-400">L{previewSnippet.target_line}</strong>
                    </span>
                  </div>

                  <div className="p-3 overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <tbody>
                        {previewSnippet.lines.map((line) => {
                          const isTarget = line.is_highlighted || line.line_number === previewSnippet.target_line
                          return (
                            <tr
                              key={line.line_number}
                              className={isTarget ? 'bg-violet-950/40 border-l-2 border-violet-500' : ''}
                            >
                              <td className="w-12 py-0.5 pr-4 text-right select-none text-slate-600 text-[11px]">
                                {line.line_number}
                              </td>
                              <td
                                className={`py-0.5 whitespace-pre ${
                                  isTarget ? 'text-violet-200 font-semibold' : 'text-slate-300'
                                }`}
                              >
                                {line.content}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3 sm:p-4 border-t border-slate-800 bg-[#0a0f1d] flex items-center justify-between text-xs">
              <span className="text-slate-500 font-mono text-[11px]">
                Read-only verified source extraction
              </span>
              <button
                onClick={() => setPreviewCitation(null)}
                className="px-4 py-1.5 rounded-lg border border-slate-800 text-xs text-slate-300 hover:text-white hover:bg-slate-800 transition"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
