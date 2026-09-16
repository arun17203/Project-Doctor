import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  FolderPlus,
  UploadCloud,
  FileArchive,
  GitBranch,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X
} from 'lucide-react'
import { projectService } from '../services/projectService'
import { AppShell } from '../components/layout/AppShell'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useToast } from '../context/ToastContext'

export default function NewProjectPage() {
  useDocumentTitle('Project Doctor', 'Import Project')
  const navigate = useNavigate()
  const { success, error: toastError } = useToast()

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [sourceType, setSourceType] = useState<'zip' | 'github'>('zip')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [githubUrl, setGithubUrl] = useState('')

  const [submitting, setSubmitting] = useState(false)
  const [uploadStep, setUploadStep] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (!file.name.toLowerCase().endsWith('.zip')) {
        setErrorMessage('Please select a valid .zip archive file.')
        return
      }
      if (file.size > 50 * 1024 * 1024) {
        setErrorMessage('File size exceeds the 50MB maximum limit.')
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (!file.name.toLowerCase().endsWith('.zip')) {
        setErrorMessage('Please drop a valid .zip archive file.')
        return
      }
      if (file.size > 50 * 1024 * 1024) {
        setErrorMessage('File size exceeds the 50MB maximum limit.')
        return
      }
      setSelectedFile(file)
      setErrorMessage(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    const trimmedName = name.trim()
    if (!trimmedName) {
      setErrorMessage('Please provide a project name.')
      return
    }

    if (sourceType === 'zip' && !selectedFile) {
      setErrorMessage('Please select a ZIP file to upload.')
      return
    }

    if (sourceType === 'github') {
      const trimmedUrl = githubUrl.trim()
      if (!trimmedUrl) {
        setErrorMessage('Please enter a public GitHub repository URL.')
        return
      }
      const ghPattern = /^https?:\/\/(www\.)?github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+\/?(\.git)?$/
      if (!ghPattern.test(trimmedUrl)) {
        setErrorMessage('Invalid GitHub URL. Format must be: https://github.com/owner/repo')
        return
      }
    }

    setSubmitting(true)

    try {
      // Step 1: Create project entity in database
      setUploadStep('Initializing project record...')
      const project = await projectService.createProject({
        name: trimmedName,
        description: description.trim() || undefined,
        source_type: sourceType,
        source_url: sourceType === 'github' ? githubUrl.trim() : undefined,
      })

      // Step 2: Upload or Clone
      if (sourceType === 'zip' && selectedFile) {
        setUploadStep('Uploading ZIP archive...')
        await projectService.uploadZip(project.id, selectedFile)
      } else if (sourceType === 'github') {
        setUploadStep('Cloning repository from GitHub...')
        await projectService.importGitHub(project.id, githubUrl.trim())
      }

      setUploadStep('Project ready! Redirecting...')
      success('Project Created', `"${trimmedName}" is ready for automated diagnostics.`)
      setTimeout(() => {
        navigate(`/projects/${project.id}`)
      }, 500)
    } catch (err: any) {
      setSubmitting(false)
      setUploadStep('')
      const msg = err.response?.data?.detail || err.message || 'Failed to import project. Please check inputs.'
      setErrorMessage(msg)
      toastError('Import Failed', msg)
    }
  }

  return (
    <AppShell
      breadcrumbs={[
        { label: 'Projects', href: '/' },
        { label: 'Import Project' }
      ]}
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 w-full space-y-6">
        <div>
          <div className="flex items-center space-x-2 text-blue-400 text-xs font-mono uppercase tracking-wider mb-1">
            <FolderPlus className="h-4 w-4" />
            <span>Project Ingestion</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Import Codebase</h1>
          <p className="text-xs text-slate-400 mt-1">
            Upload source code as a ZIP archive or clone directly from a public GitHub repository for automated diagnostics.
          </p>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="rounded-lg bg-rose-950/40 border border-rose-500/30 p-4 flex items-start space-x-3 text-rose-300 text-xs">
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="leading-relaxed font-medium">{errorMessage}</div>
          </div>
        )}

        {/* Form Card */}
        <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-6 sm:p-8 shadow-xl space-y-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Project Name */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5" htmlFor="projectName">
                Project Name <span className="text-rose-400">*</span>
              </label>
              <input
                id="projectName"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Enterprise Web Application"
                required
                disabled={submitting}
                className="block w-full px-3.5 py-2.5 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition font-sans"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5" htmlFor="projectDesc">
                Description <span className="text-slate-500">(optional)</span>
              </label>
              <textarea
                id="projectDesc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief summary of architecture, stack, or diagnostic goals..."
                rows={2}
                disabled={submitting}
                className="block w-full px-3.5 py-2 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition font-sans"
              />
            </div>

            {/* Ingestion Method Tabs */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-2">
                Import Method <span className="text-rose-400">*</span>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setSourceType('zip')}
                  disabled={submitting}
                  className={`flex items-center justify-center space-x-2 py-3 px-4 rounded-lg border text-xs font-medium transition ${
                    sourceType === 'zip'
                      ? 'border-blue-500/50 bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/30'
                      : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  <FileArchive className="h-4 w-4" />
                  <span>Upload ZIP Archive</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSourceType('github')}
                  disabled={submitting}
                  className={`flex items-center justify-center space-x-2 py-3 px-4 rounded-lg border text-xs font-medium transition ${
                    sourceType === 'github'
                      ? 'border-blue-500/50 bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/30'
                      : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  <GitBranch className="h-4 w-4" />
                  <span>Public GitHub URL</span>
                </button>
              </div>
            </div>

            {/* ZIP Upload Dropzone */}
            {sourceType === 'zip' && (
              <div className="space-y-2">
                <div
                  onDragOver={(e) => {
                    e.preventDefault()
                    setIsDragging(true)
                  }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-6 text-center transition-all ${
                    isDragging
                      ? 'border-blue-500 bg-blue-950/20'
                      : selectedFile
                      ? 'border-emerald-500/40 bg-emerald-950/10'
                      : 'border-slate-800 hover:border-slate-700 bg-slate-900/40'
                  }`}
                >
                  {selectedFile ? (
                    <div className="flex items-center justify-between max-w-sm mx-auto p-3 rounded-lg bg-slate-900 border border-slate-800">
                      <div className="flex items-center space-x-3 overflow-hidden">
                        <FileArchive className="h-6 w-6 text-emerald-400 shrink-0" />
                        <div className="text-left truncate">
                          <p className="text-xs font-medium text-slate-200 truncate">{selectedFile.name}</p>
                          <p className="text-[10px] text-slate-500 font-mono">
                            {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedFile(null)}
                        disabled={submitting}
                        className="p-1 rounded text-slate-400 hover:text-rose-400 transition"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="inline-flex p-3 rounded-full bg-slate-900 text-blue-400 border border-slate-800">
                        <UploadCloud className="h-6 w-6" />
                      </div>
                      <div>
                        <p className="text-xs font-medium text-slate-200">
                          Drop your project <code className="text-blue-400 font-mono">.zip</code> archive here, or{' '}
                          <label
                            htmlFor="fileInput"
                            className="text-blue-400 hover:text-blue-300 cursor-pointer underline underline-offset-2"
                          >
                            browse files
                          </label>
                        </p>
                        <p className="text-[11px] text-slate-500 mt-1 font-mono">Maximum archive size: 50MB</p>
                      </div>
                      <input
                        id="fileInput"
                        type="file"
                        accept=".zip"
                        onChange={handleFileChange}
                        disabled={submitting}
                        className="hidden"
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  <span>Safely extracted: node_modules, .git, and build artifacts automatically ignored</span>
                </div>
              </div>
            )}

            {/* GitHub URL Input */}
            {sourceType === 'github' && (
              <div className="space-y-2">
                <label className="block text-xs font-medium text-slate-300" htmlFor="githubUrl">
                  GitHub Repository URL <span className="text-rose-400">*</span>
                </label>
                <div className="relative rounded-md shadow-sm">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <GitBranch className="h-4 w-4" />
                  </div>
                  <input
                    id="githubUrl"
                    type="url"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/owner/repository"
                    disabled={submitting}
                    required
                    className="block w-full pl-9 pr-3 py-2.5 bg-slate-900/90 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 transition font-mono"
                  />
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-slate-500 font-mono">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  <span>Public repository • Cloned with shallow depth=1 • .git hooks stripped</span>
                </div>
              </div>
            )}

            {/* Submission / Ingestion Progress Status */}
            {submitting && (
              <div className="rounded-lg bg-blue-950/30 border border-blue-500/20 p-4 flex items-center space-x-3 text-blue-300 text-xs font-mono">
                <Loader2 className="h-4 w-4 animate-spin text-blue-400 shrink-0" />
                <span className="font-medium">{uploadStep}</span>
              </div>
            )}

            {/* Submit Button */}
            <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800/80">
              <Link
                to="/"
                className="px-4 py-2 rounded-lg border border-slate-800 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-900 transition"
              >
                Cancel
              </Link>
              <button
                type="submit"
                disabled={submitting}
                className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                    <span>Processing Ingestion...</span>
                  </>
                ) : (
                  <>
                    <span>Create &amp; Import Project</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </AppShell>
  )
}
