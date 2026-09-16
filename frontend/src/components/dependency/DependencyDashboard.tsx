import React, { useState } from 'react'
import {
  Boxes,
  ShieldAlert,
  Clock,
  CheckCircle,
  HelpCircle,
  Search,
  ChevronRight,
  X,
  ExternalLink,
  Copy,
  Check,
  AlertTriangle,
  Layers,
  FileCode,
  ArrowUpRight,
  Filter,
  RefreshCw,
  Info,
  Sparkles,
} from 'lucide-react'
import type {
  ProjectDependency,
  DependencyAnalysis,
  DependencyStatus,
  VulnerabilityAdvisory,
} from '../../types/dependency'
import AIExplanationModal from '../ai/AIExplanationModal'

interface DependencyDashboardProps {
  projectId: string
  analysis: DependencyAnalysis
  dependencies: ProjectDependency[]
  loading?: boolean
  onRefresh?: () => void
  onReanalyze?: () => void
  analyzing?: boolean
}

export default function DependencyDashboard({
  projectId: _projectId,
  analysis,
  dependencies,
  loading = false,
  onRefresh,
  onReanalyze,
  analyzing = false,
}: DependencyDashboardProps) {
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL')
  const [selectedEcosystem, setSelectedEcosystem] = useState<string>('ALL')
  const [selectedType, setSelectedType] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [selectedDep, setSelectedDep] = useState<ProjectDependency | null>(null)
  const [selectedDepForAI, setSelectedDepForAI] = useState<ProjectDependency | null>(null)
  const [copiedText, setCopiedText] = useState<string | null>(null)

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text)
    setCopiedText(key)
    setTimeout(() => setCopiedText(null), 2000)
  }

  // Filter dependencies
  const filteredDeps = dependencies.filter((dep) => {
    if (selectedStatus !== 'ALL' && dep.status !== selectedStatus) {
      return false
    }
    if (selectedEcosystem !== 'ALL' && dep.ecosystem.toLowerCase() !== selectedEcosystem.toLowerCase()) {
      return false
    }
    if (selectedType !== 'ALL' && dep.dependency_type.toLowerCase() !== selectedType.toLowerCase()) {
      return false
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim()
      const matchName = dep.name.toLowerCase().includes(q)
      const matchManifest = dep.manifest_file.toLowerCase().includes(q)
      if (!matchName && !matchManifest) return false
    }
    return true
  })

  const getStatusBadge = (status: DependencyStatus, vulnCount: number) => {
    switch (status) {
      case 'VULNERABLE':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="h-3 w-3" />
            <span>VULNERABLE ({vulnCount})</span>
          </span>
        )
      case 'OUTDATED':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock className="h-3 w-3" />
            <span>OUTDATED</span>
          </span>
        )
      case 'CURRENT':
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle className="h-3 w-3" />
            <span>UP TO DATE</span>
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-500/15 text-slate-400 border border-slate-500/30">
            <HelpCircle className="h-3 w-3" />
            <span>UNKNOWN</span>
          </span>
        )
    }
  }

  const getSeverityBadge = (severity: string) => {
    const s = severity.toUpperCase()
    if (s === 'CRITICAL') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-600/40">
          CRITICAL
        </span>
      )
    }
    if (s === 'HIGH') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-orange-950 text-orange-300 border border-orange-600/40">
          HIGH
        </span>
      )
    }
    if (s === 'MEDIUM') {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-600/40">
          MEDIUM
        </span>
      )
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-600/40">
        LOW
      </span>
    )
  }

  const ecosystems = Array.from(new Set(dependencies.map((d) => d.ecosystem)))
  const manifests = analysis.metrics?.manifests_scanned || []

  return (
    <div className="space-y-6">
      {/* Network Warning Notification (if external OSV/registries were unreachable) */}
      {analysis.metrics?.network_warning && (
        <div className="rounded-xl bg-amber-950/40 border border-amber-500/30 p-4 flex items-start space-x-3 text-amber-300 text-xs">
          <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong className="font-semibold text-amber-200">Network Advisory Notice: </strong>
            Some external package registries or vulnerability feeds experienced temporary timeouts during this audit.
            Packages that could not be verified are safely classified as <span className="font-mono font-bold text-slate-300">UNKNOWN</span> without interrupting the audit.
          </div>
        </div>
      )}

      {/* Top Telemetry & Health Stat Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Total Deps</span>
          <div className="text-2xl font-mono font-bold text-white">{analysis.total_dependencies}</div>
          <span className="text-[10px] text-slate-500 font-mono">Discovered</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Direct</span>
          <div className="text-2xl font-mono font-bold text-blue-400">{analysis.direct_dependencies}</div>
          <span className="text-[10px] text-slate-500 font-mono">Declared roots</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Transitive</span>
          <div className="text-2xl font-mono font-bold text-slate-300">{analysis.transitive_dependencies}</div>
          <span className="text-[10px] text-slate-500 font-mono">Sub-dependencies</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Up To Date</span>
          <div className="text-2xl font-mono font-bold text-emerald-400">{analysis.current_count}</div>
          <span className="text-[10px] text-slate-500 font-mono">Latest release</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Outdated</span>
          <div className={`text-2xl font-mono font-bold ${analysis.outdated_count > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
            {analysis.outdated_count}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">Older versions</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Vulnerable</span>
          <div className={`text-2xl font-mono font-bold ${analysis.vulnerable_count > 0 ? 'text-rose-400' : 'text-slate-400'}`}>
            {analysis.vulnerable_count}
          </div>
          <span className="text-[10px] text-slate-500 font-mono">OSV Advisories</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0d1322] border border-slate-800 space-y-1">
          <span className="text-[11px] font-mono text-slate-500 uppercase">Unknown</span>
          <div className="text-2xl font-mono font-bold text-slate-400">{analysis.unknown_count}</div>
          <span className="text-[10px] text-slate-500 font-mono">Unpinned/Offline</span>
        </div>
      </div>

      {/* Manifests & Ecosystem Summary Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Manifests Scanned */}
        <div className="lg:col-span-7 bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <FileCode className="h-4 w-4 text-blue-400" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                Manifest Files Analyzed ({manifests.length})
              </h4>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Zero Code Execution</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {manifests.length > 0 ? (
              manifests.map((m, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-md bg-slate-900 border border-slate-800 text-slate-300 text-xs font-mono flex items-center space-x-1.5"
                >
                  <Layers className="h-3 w-3 text-slate-500" />
                  <span>{m}</span>
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">No manifests found</span>
            )}
          </div>
        </div>

        {/* Ecosystem Distribution */}
        <div className="lg:col-span-5 bg-[#0d1322] border border-slate-800 rounded-xl p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Boxes className="h-4 w-4 text-purple-400" />
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                Ecosystem Distribution
              </h4>
            </div>
            <span className="text-[10px] text-slate-500 font-mono">Static Mapping</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(analysis.metrics?.by_ecosystem || {}).map(([eco, count]) => (
              <div
                key={eco}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 flex items-center space-x-2 text-xs font-mono"
              >
                <span className="font-semibold text-slate-200">{eco}</span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-blue-400 text-[11px] font-bold">
                  {count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#0d1322] border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex flex-col md:flex-row gap-3 items-center justify-between">
          {/* Search Input */}
          <div className="relative w-full md:w-80">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search dependencies or manifests..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-8 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          {/* Quick Actions */}
          <div className="flex items-center space-x-2 self-end md:self-auto">
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-2 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition text-xs flex items-center space-x-1"
                title="Refresh dependencies"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
            {onReanalyze && (
              <button
                onClick={onReanalyze}
                disabled={analyzing}
                className="px-3 py-2 rounded-lg border border-blue-500/30 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 transition text-xs font-mono font-medium flex items-center space-x-1.5"
                title="Re-run dependency analysis"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${analyzing ? 'animate-spin' : ''}`} />
                <span>Re-audit Dependencies</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap gap-2 pt-1 border-t border-slate-800/60">
          <div className="flex items-center space-x-1 mr-2 text-[11px] font-mono text-slate-500">
            <Filter className="h-3 w-3" />
            <span>Filters:</span>
          </div>

          {/* Status Pills */}
          {['ALL', 'VULNERABLE', 'OUTDATED', 'CURRENT', 'UNKNOWN'].map((st) => (
            <button
              key={st}
              onClick={() => setSelectedStatus(st)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition ${
                selectedStatus === st
                  ? 'bg-blue-600 text-white font-semibold shadow'
                  : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
            >
              {st}
            </button>
          ))}

          <span className="h-4 w-px bg-slate-800 mx-1 self-center" />

          {/* Ecosystem Pills */}
          {['ALL', ...ecosystems].map((eco) => (
            <button
              key={eco}
              onClick={() => setSelectedEcosystem(eco)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition ${
                selectedEcosystem.toLowerCase() === eco.toLowerCase()
                  ? 'bg-purple-600 text-white font-semibold shadow'
                  : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
            >
              {eco}
            </button>
          ))}

          <span className="h-4 w-px bg-slate-800 mx-1 self-center" />

          {/* Type Pills */}
          {['ALL', 'direct', 'dev', 'transitive', 'peer'].map((t) => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-2.5 py-1 rounded text-[11px] font-mono transition ${
                selectedType.toLowerCase() === t.toLowerCase()
                  ? 'bg-emerald-600 text-white font-semibold shadow'
                  : 'bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Dependencies Table */}
      <div className="bg-[#0d1322] border border-slate-800 rounded-xl overflow-hidden shadow-xl">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
          <div>
            Showing <strong className="text-white">{filteredDeps.length}</strong> of{' '}
            <strong className="text-white">{dependencies.length}</strong> dependencies
          </div>
          <div className="text-[11px] text-slate-500">
            Real OSV vulnerability advisories & registry semver checks
          </div>
        </div>

        {filteredDeps.length === 0 ? (
          <div className="p-12 text-center space-y-2">
            <Boxes className="h-8 w-8 text-slate-600 mx-auto" />
            <div className="text-sm font-semibold text-slate-300">No dependencies matched your filters</div>
            <p className="text-xs text-slate-500">Try adjusting your search query or filter selections.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Package Name</th>
                  <th className="py-3 px-4">Ecosystem</th>
                  <th className="py-3 px-4">Declared</th>
                  <th className="py-3 px-4">Resolved</th>
                  <th className="py-3 px-4">Latest</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Manifest</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredDeps.map((dep) => (
                  <tr
                    key={dep.id}
                    className={`hover:bg-slate-900/60 transition cursor-pointer ${
                      dep.status === 'VULNERABLE' ? 'bg-rose-950/10' : ''
                    }`}
                    onClick={() => setSelectedDep(dep)}
                  >
                    <td className="py-3 px-4">{getStatusBadge(dep.status, dep.vulnerability_count)}</td>
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-200 hover:text-blue-400 transition flex items-center space-x-1.5">
                        <span>{dep.name}</span>
                        {dep.vulnerability_count > 0 && (
                          <AlertTriangle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 text-[11px]">
                        {dep.ecosystem}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {dep.declared_version || <span className="text-slate-600">—</span>}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-semibold">
                      {dep.resolved_version || <span className="text-slate-600">—</span>}
                    </td>
                    <td className="py-3 px-4">
                      {dep.latest_version ? (
                        <span className={dep.status === 'OUTDATED' ? 'text-amber-400 font-semibold' : 'text-slate-400'}>
                          {dep.latest_version}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono uppercase ${
                          dep.dependency_type === 'direct'
                            ? 'bg-blue-950/80 text-blue-300 border border-blue-800/40'
                            : dep.dependency_type === 'dev'
                            ? 'bg-purple-950/80 text-purple-300 border border-purple-800/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {dep.dependency_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px] truncate max-w-[180px]" title={dep.manifest_file}>
                      {dep.manifest_file}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        {(dep.status === 'VULNERABLE' || dep.status === 'OUTDATED') && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedDepForAI(dep)
                            }}
                            className="p-1 rounded text-purple-400 hover:text-purple-300 hover:bg-purple-950/40 transition"
                            title="Explain Vulnerability/Risk with AI"
                          >
                            <Sparkles className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedDep(dep)
                          }}
                          className="inline-flex items-center space-x-1 text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-800 transition text-[11px]"
                        >
                          <span>Details</span>
                          <ChevronRight className="h-3 w-3" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dependency Detail / Vulnerability Drawer Modal */}
      {selectedDep && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0d1322] border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/80">
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-blue-400">
                  <Boxes className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-mono flex items-center space-x-2">
                    <span>{selectedDep.name}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-normal">
                      {selectedDep.ecosystem}
                    </span>
                  </h3>
                  <div className="text-xs text-slate-400 font-mono mt-0.5">
                    {selectedDep.manifest_file}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedDep(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6 overflow-y-auto">
              {/* Version & Status Overview */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">Status</span>
                  <div>{getStatusBadge(selectedDep.status, selectedDep.vulnerability_count)}</div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">Declared</span>
                  <div className="text-sm font-mono font-bold text-slate-200">
                    {selectedDep.declared_version || 'Not pinned'}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">Resolved</span>
                  <div className="text-sm font-mono font-bold text-emerald-400">
                    {selectedDep.resolved_version || 'Unknown'}
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                  <span className="text-[10px] font-mono text-slate-500 uppercase">Latest Available</span>
                  <div className="text-sm font-mono font-bold text-blue-400">
                    {selectedDep.latest_version || 'Unknown'}
                  </div>
                </div>
              </div>

              {/* Vulnerabilities Section */}
              {selectedDep.advisories && selectedDep.advisories.length > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <ShieldAlert className="h-4 w-4 text-rose-400" />
                    <h4 className="text-sm font-bold text-white uppercase tracking-wider">
                      Known Security Vulnerabilities ({selectedDep.advisories.length})
                    </h4>
                  </div>

                  <div className="space-y-3">
                    {selectedDep.advisories.map((adv: VulnerabilityAdvisory, i: number) => (
                      <div
                        key={i}
                        className="rounded-xl bg-rose-950/20 border border-rose-500/30 p-4 space-y-3"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-sm text-rose-300">{adv.id}</span>
                            {getSeverityBadge(adv.severity)}
                          </div>
                          {adv.reference_url && (
                            <a
                              href={adv.reference_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center space-x-1 text-xs text-rose-400 hover:text-rose-300 font-mono"
                            >
                              <span>Advisory Link</span>
                              <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>

                        <p className="text-xs text-slate-300 leading-relaxed">{adv.summary}</p>

                        <div className="grid grid-cols-2 gap-2 text-xs font-mono pt-2 border-t border-rose-500/20">
                          <div>
                            <span className="text-slate-500">Affected Versions: </span>
                            <span className="text-rose-300 font-medium">
                              {adv.affected_versions || 'All matching'}
                            </span>
                          </div>
                          <div>
                            <span className="text-slate-500">Fixed In: </span>
                            <span className="text-emerald-400 font-bold">
                              {adv.fixed_version ? `>= ${adv.fixed_version}` : 'No fixed version published'}
                            </span>
                          </div>
                        </div>

                        {/* Remediation guidance */}
                        {adv.fixed_version && (
                          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono flex items-center justify-between">
                            <div className="text-slate-300">
                              <span className="text-slate-500">Suggested upgrade: </span>
                              <code className="text-emerald-400 font-bold">
                                {selectedDep.name}@{adv.fixed_version}
                              </code>
                            </div>
                            <button
                              onClick={() =>
                                handleCopy(
                                  `${selectedDep.name}@${adv.fixed_version}`,
                                  `fix-${i}`
                                )
                              }
                              className="text-slate-400 hover:text-white p-1 rounded"
                              title="Copy package command"
                            >
                              {copiedText === `fix-${i}` ? (
                                <Check className="h-3.5 w-3.5 text-emerald-400" />
                              ) : (
                                <Copy className="h-3.5 w-3.5" />
                              )}
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center space-x-3 text-xs text-slate-400">
                  <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
                  <span>No security advisories published in Google OSV for this package and version.</span>
                </div>
              )}

              {/* Outdated Recommendation */}
              {selectedDep.status === 'OUTDATED' && selectedDep.latest_version && (
                <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/30 space-y-2">
                  <div className="flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
                    <ArrowUpRight className="h-4 w-4" />
                    <span>Upgrade Recommendation</span>
                  </div>
                  <p className="text-xs text-slate-300">
                    Package <strong className="text-white">{selectedDep.name}</strong> is currently on version{' '}
                    <span className="font-mono text-amber-300">{selectedDep.resolved_version || selectedDep.declared_version}</span>.
                    The registry reports version <span className="font-mono text-emerald-400 font-bold">{selectedDep.latest_version}</span> as the latest release.
                  </p>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
              <div>
                {(selectedDep.status === 'VULNERABLE' || selectedDep.status === 'OUTDATED') && (
                  <button
                    onClick={() => setSelectedDepForAI(selectedDep)}
                    className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gradient-to-r from-purple-600/20 to-blue-600/20 hover:from-purple-600/30 hover:to-blue-600/30 border border-purple-500/40 text-purple-200 text-xs font-medium transition shadow-sm"
                  >
                    <Sparkles className="h-4 w-4 text-purple-400" />
                    <span>Explain Package Risk with AI</span>
                  </button>
                )}
              </div>
              <button
                onClick={() => setSelectedDep(null)}
                className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI Explanation Modal */}
      <AIExplanationModal
        isOpen={!!selectedDepForAI}
        onClose={() => setSelectedDepForAI(null)}
        issueId={selectedDepForAI?.id || ''}
        issueTitle={selectedDepForAI ? `Dependency: ${selectedDepForAI.name} (${selectedDepForAI.status})` : ''}
        issueLocation={selectedDepForAI?.manifest_file}
        issueSeverity={selectedDepForAI?.status === 'VULNERABLE' ? 'CRITICAL' : 'MEDIUM'}
        category="dependency"
      />
    </div>
  )
}
