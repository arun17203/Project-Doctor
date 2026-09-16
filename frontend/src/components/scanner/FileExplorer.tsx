import React, { useState } from 'react'
import {
  Folder,
  FolderOpen,
  FileCode,
  FileText,
  FileCheck2,
  FileCog,
  FileImage,
  FileQuestion,
  ChevronRight,
  ChevronDown,
  Search,
  CheckCircle2,
  Info,
  ShieldCheck
} from 'lucide-react'
import type { DirectoryNode } from '../../types/scan'

interface FileExplorerProps {
  tree: DirectoryNode
}

export default function FileExplorer({ tree }: FileExplorerProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(() => {
    // Expand root by default
    return new Set<string>([''])
  })
  const [selectedFile, setSelectedFile] = useState<DirectoryNode | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const toggleFolder = (path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }

  const getFileIcon = (node: DirectoryNode) => {
    const cat = node.category || 'Other'
    if (cat === 'Tests') return <FileCheck2 className="h-4 w-4 text-purple-400 shrink-0" />
    if (cat === 'Configuration') return <FileCog className="h-4 w-4 text-amber-400 shrink-0" />
    if (cat === 'Documentation') return <FileText className="h-4 w-4 text-emerald-400 shrink-0" />
    if (cat === 'Assets') return <FileImage className="h-4 w-4 text-pink-400 shrink-0" />
    if (cat === 'Source Code') return <FileCode className="h-4 w-4 text-blue-400 shrink-0" />
    return <FileQuestion className="h-4 w-4 text-slate-400 shrink-0" />
  }

  const renderTree = (node: DirectoryNode, depth = 0) => {
    if (node.type === 'directory') {
      const isExpanded = expandedPaths.has(node.path)
      const children = node.children || []

      // If search query is active, filter children
      const matchingChildren = searchQuery
        ? children.filter((c) => {
            if (c.type === 'file') return c.name.toLowerCase().includes(searchQuery.toLowerCase())
            return true
          })
        : children

      return (
        <div key={node.path || 'root'} className="select-none">
          {node.path !== '' && (
            <button
              onClick={() => toggleFolder(node.path)}
              style={{ paddingLeft: `${depth * 14}px` }}
              className="w-full flex items-center space-x-2 py-1.5 px-2 rounded hover:bg-slate-800/60 text-slate-300 hover:text-white transition text-xs text-left"
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 text-slate-500 shrink-0" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-slate-500 shrink-0" />
              )}
              {isExpanded ? (
                <FolderOpen className="h-4 w-4 text-blue-400 shrink-0" />
              ) : (
                <Folder className="h-4 w-4 text-blue-400/80 shrink-0" />
              )}
              <span className="font-mono truncate">{node.name}</span>
            </button>
          )}

          {(isExpanded || node.path === '') && (
            <div className={node.path === '' ? '' : 'border-l border-slate-800/80 ml-3.5'}>
              {matchingChildren.map((child) => renderTree(child, depth + 1))}
            </div>
          )}
        </div>
      )
    }

    // File leaf node
    const isSelected = selectedFile?.path === node.path
    if (searchQuery && !node.name.toLowerCase().includes(searchQuery.toLowerCase())) {
      return null
    }

    return (
      <button
        key={node.path}
        onClick={() => setSelectedFile(node)}
        style={{ paddingLeft: `${depth * 14}px` }}
        className={`w-full flex items-center space-x-2 py-1.5 px-2 rounded transition text-xs text-left ${
          isSelected
            ? 'bg-blue-600/20 text-blue-300 font-medium border border-blue-500/30'
            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
        }`}
      >
        <span className="w-3.5" />
        {getFileIcon(node)}
        <span className="font-mono truncate">{node.name}</span>
        {node.lines !== undefined && node.lines > 0 && (
          <span className="text-[10px] font-mono text-slate-600 ml-auto pl-2 shrink-0">
            {node.lines}L
          </span>
        )}
      </button>
    )
  }

  const formatSize = (bytes?: number) => {
    if (bytes === undefined) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  return (
    <div className="bg-[#0d1322] border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      {/* Search & Header Bar */}
      <div className="p-3.5 border-b border-slate-800/80 bg-slate-900/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <Folder className="h-4 w-4 text-blue-400" />
          <span className="text-xs font-semibold text-white">Repository File Explorer</span>
        </div>

        <div className="relative max-w-xs w-full">
          <Search className="h-3.5 w-3.5 text-slate-500 absolute left-2.5 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search discovered files..."
            className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-md text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 font-mono"
          />
        </div>
      </div>

      {/* Main Grid: Tree Browser & File Inspector */}
      <div className="grid grid-cols-1 md:grid-cols-12 min-h-[380px]">
        {/* Left: Tree View */}
        <div className="md:col-span-7 p-3 overflow-y-auto max-h-[460px] border-b md:border-b-0 md:border-r border-slate-800/80">
          {renderTree(tree)}
        </div>

        {/* Right: File Metadata Inspector */}
        <div className="md:col-span-5 p-5 bg-slate-900/30 flex flex-col justify-between">
          {selectedFile ? (
            <div className="space-y-5">
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase font-medium border ${
                      selectedFile.category === 'Tests'
                        ? 'bg-purple-500/10 text-purple-400 border-purple-500/30'
                        : selectedFile.category === 'Configuration'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        : selectedFile.category === 'Documentation'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-blue-500/10 text-blue-400 border-blue-500/30'
                    }`}
                  >
                    {selectedFile.category || 'Source Code'}
                  </span>
                  {selectedFile.language && selectedFile.language !== 'Other' && (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      {selectedFile.language}
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-white font-mono break-all">{selectedFile.name}</h3>
                <p className="text-[11px] text-slate-500 font-mono break-all mt-0.5">{selectedFile.path}</p>
              </div>

              {/* Line Count Breakdown Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Total Lines</div>
                  <div className="text-base font-mono font-semibold text-white">{selectedFile.lines || 0}</div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Code Lines</div>
                  <div className="text-base font-mono font-semibold text-emerald-400">
                    {selectedFile.code_lines || 0}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">File Size</div>
                  <div className="text-sm font-mono font-medium text-slate-200">{formatSize(selectedFile.size_bytes)}</div>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Execution</div>
                  <div className="text-sm font-mono font-medium text-blue-400">Pure Static</div>
                </div>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 flex items-start space-x-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">
                  Project Doctor inspects file structure and counts lines strictly in read-only mode without executing code.
                </span>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 space-y-2 my-auto">
              <Info className="h-8 w-8 text-slate-600 mb-1" />
              <p className="text-xs font-medium text-slate-300">Select a file to inspect</p>
              <p className="text-[11px] text-slate-500 max-w-xs">
                Click any file from the directory tree to inspect language, classification, and line counts.
              </p>
            </div>
          )}

          <div className="pt-4 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono flex items-center justify-between">
            <span>Repository Scanner</span>
            <span>Stage 4 Active</span>
          </div>
        </div>
      </div>
    </div>
  )
}
