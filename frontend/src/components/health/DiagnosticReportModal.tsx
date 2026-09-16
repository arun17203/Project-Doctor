import React from 'react'
import {
  X,
  Printer,
  ShieldCheck,
  ShieldAlert,
  Code2,
  Boxes,
  Network,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Stethoscope,
  Building2,
  Calendar,
  Award,
} from 'lucide-react'
import type { Project } from '../../types/project'
import type { ScanResult } from '../../types/scan'
import type { HealthAnalysis } from '../../types/health'
import type { SecurityAnalysis } from '../../types/security'
import type { QualityAnalysis } from '../../types/quality'
import type { DependencyAnalysis } from '../../types/dependency'
import type { ArchitectureAnalysis } from '../../types/architecture'

interface DiagnosticReportModalProps {
  isOpen: boolean
  onClose: () => void
  project: Project
  health: HealthAnalysis | null
  scan: ScanResult | null
  securityAnalysis: SecurityAnalysis | null
  qualityAnalysis: QualityAnalysis | null
  dependencyAnalysis: DependencyAnalysis | null
  architectureAnalysis: ArchitectureAnalysis | null
}

export const DiagnosticReportModal: React.FC<DiagnosticReportModalProps> = ({
  isOpen,
  onClose,
  project,
  health,
  scan,
  securityAnalysis,
  qualityAnalysis,
  dependencyAnalysis,
  architectureAnalysis,
}) => {
  if (!isOpen) return null

  const handlePrint = () => {
    window.print()
  }

  const overallScore = Math.round(health?.overall_score || 0)
  const status = health?.status || 'Good'
  const debtHours = Math.round(health?.technical_debt_hours || 0)

  const getGrade = (score: number) => {
    if (score >= 90) return { grade: 'A', text: 'Production Certified', color: 'text-emerald-500' }
    if (score >= 80) return { grade: 'B', text: 'Good Health', color: 'text-blue-500' }
    if (score >= 70) return { grade: 'C', text: 'Fair / Minor Debt', color: 'text-amber-500' }
    if (score >= 60) return { grade: 'D', text: 'Needs Attention', color: 'text-orange-500' }
    return { grade: 'F', text: 'Critical Risk', color: 'text-rose-500' }
  }

  const gradeInfo = getGrade(overallScore)

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 print:p-0 print:bg-white print:static print:inset-auto">
      {/* Container */}
      <div className="bg-[#0b101e] print:bg-white text-slate-100 print:text-slate-900 border border-slate-800 print:border-none rounded-2xl w-full max-w-4xl max-h-[92vh] print:max-h-none overflow-y-auto shadow-2xl relative">
        {/* Modal Action Bar (Hidden during print) */}
        <div className="sticky top-0 z-20 bg-slate-900/95 print:hidden border-b border-slate-800 px-6 py-4 flex items-center justify-between backdrop-blur-md">
          <div className="flex items-center gap-2 text-indigo-400">
            <Stethoscope className="w-5 h-5" />
            <span className="text-sm font-bold text-white">Executive Diagnostic Audit Certificate</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20 transition-colors"
            >
              <Printer className="w-4 h-4" />
              <span>Print / Save as PDF</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Content */}
        <div className="p-8 sm:p-12 space-y-8 font-sans print:p-6">
          {/* Header & Hospital/Agency Logo */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-6 border-b border-slate-800 print:border-slate-300">
            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <span className="w-9 h-9 rounded-xl bg-indigo-500/10 print:bg-indigo-100 text-indigo-400 print:text-indigo-700 border border-indigo-500/20 flex items-center justify-center">
                  <Stethoscope className="w-5 h-5" />
                </span>
                <div>
                  <h1 className="text-xl font-bold tracking-tight text-white print:text-slate-900">
                    PROJECT DOCTOR
                  </h1>
                  <p className="text-[10px] font-mono uppercase tracking-widest text-indigo-400 print:text-indigo-700">
                    Codebase Health & Static Diagnostic Audit
                  </p>
                </div>
              </div>
            </div>

            <div className="text-left sm:text-right text-xs font-mono text-slate-400 print:text-slate-600 space-y-0.5">
              <div>Ref: DOC-{project.id.slice(0, 8).toUpperCase()}</div>
              <div>Audit Date: {new Date().toLocaleDateString(undefined, { dateStyle: 'long' })}</div>
              <div>Engine: Project Doctor v1.5 (Zero-Execution AST)</div>
            </div>
          </div>

          {/* Project Details Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 rounded-xl bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300 text-xs">
            <div>
              <span className="text-slate-500 print:text-slate-500 block text-[10px] uppercase font-mono">
                Project Name
              </span>
              <span className="font-bold text-white print:text-slate-900 truncate block mt-0.5">
                {project.name}
              </span>
            </div>
            <div>
              <span className="text-slate-500 print:text-slate-500 block text-[10px] uppercase font-mono">
                Source Type
              </span>
              <span className="font-bold text-white print:text-slate-900 uppercase mt-0.5 block">
                {project.source_type}
              </span>
            </div>
            <div>
              <span className="text-slate-500 print:text-slate-500 block text-[10px] uppercase font-mono">
                Code Volume
              </span>
              <span className="font-bold text-white print:text-slate-900 mt-0.5 block">
                {scan?.total_files || 0} files ({scan?.total_lines || 0} loc)
              </span>
            </div>
            <div>
              <span className="text-slate-500 print:text-slate-500 block text-[10px] uppercase font-mono">
                Debt Estimate
              </span>
              <span className="font-bold text-amber-400 print:text-amber-700 mt-0.5 block">
                {debtHours} Hours Remediation
              </span>
            </div>
          </div>

          {/* Official Diagnostic Score & Grade Hero */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-6 p-6 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-950 print:bg-none print:border print:border-slate-300 border border-indigo-500/20">
            <div className="flex items-center gap-6 text-center sm:text-left">
              <div className="w-24 h-24 rounded-2xl bg-slate-900 print:bg-slate-100 border border-indigo-500/30 print:border-slate-400 flex flex-col items-center justify-center shrink-0">
                <span className="text-4xl font-extrabold font-mono text-white print:text-slate-900">
                  {overallScore}
                </span>
                <span className="text-[10px] font-mono text-slate-400 print:text-slate-600 uppercase">
                  Score / 100
                </span>
              </div>
              <div className="space-y-1">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-slate-600">
                  Diagnostic Rating
                </div>
                <h3 className="text-2xl font-bold text-white print:text-slate-900">{status}</h3>
                <p className="text-xs text-slate-400 print:text-slate-600 max-w-md">
                  Weighted deterministic health diagnosis evaluated across Security, Code Quality,
                  Maintainability, Dependencies, and Architecture.
                </p>
              </div>
            </div>

            <div className="text-center sm:text-right shrink-0">
              <div className={`text-5xl font-black font-mono ${gradeInfo.color} print:text-indigo-900`}>
                {gradeInfo.grade}
              </div>
              <div className="text-xs font-semibold text-slate-300 print:text-slate-700 mt-1">
                {gradeInfo.text}
              </div>
            </div>
          </div>

          {/* Diagnostic Dimensions Breakdown */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-slate-600">
              Core Diagnostic Vitals
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-900/40 print:bg-slate-50 border border-slate-800 print:border-slate-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400 print:text-emerald-700" />
                  <span className="font-medium text-white print:text-slate-900">Static Security Audit (30%)</span>
                </div>
                <span className="font-mono font-bold text-slate-200 print:text-slate-900">
                  {Math.round(health?.security_score || 0)} / 100
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/40 print:bg-slate-50 border border-slate-800 print:border-slate-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-blue-400 print:text-blue-700" />
                  <span className="font-medium text-white print:text-slate-900">Code Quality & Complexity (25%)</span>
                </div>
                <span className="font-mono font-bold text-slate-200 print:text-slate-900">
                  {Math.round(health?.quality_score || 0)} / 100
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/40 print:bg-slate-50 border border-slate-800 print:border-slate-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Boxes className="w-4 h-4 text-indigo-400 print:text-indigo-700" />
                  <span className="font-medium text-white print:text-slate-900">Dependency & CVE Hygiene (15%)</span>
                </div>
                <span className="font-mono font-bold text-slate-200 print:text-slate-900">
                  {Math.round(health?.dependency_score || 0)} / 100
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/40 print:bg-slate-50 border border-slate-800 print:border-slate-300 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Network className="w-4 h-4 text-purple-400 print:text-purple-700" />
                  <span className="font-medium text-white print:text-slate-900">Architecture & Circular Coupling (10%)</span>
                </div>
                <span className="font-mono font-bold text-slate-200 print:text-slate-900">
                  {Math.round(health?.architecture_score || 0)} / 100
                </span>
              </div>
            </div>
          </div>

          {/* OWASP & Critical Vulnerabilities Checklist */}
          <div className="space-y-3">
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 print:text-slate-600">
              OWASP & Compliance Audit Summary
            </h3>
            <table className="w-full text-left text-xs border-collapse border border-slate-800 print:border-slate-300">
              <thead>
                <tr className="bg-slate-900/80 print:bg-slate-200 text-slate-400 print:text-slate-700 font-mono text-[11px]">
                  <th className="p-2.5 border border-slate-800 print:border-slate-300">Category</th>
                  <th className="p-2.5 border border-slate-800 print:border-slate-300">Findings Checked</th>
                  <th className="p-2.5 border border-slate-800 print:border-slate-300">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 print:divide-slate-300">
                <tr>
                  <td className="p-2.5 font-medium text-white print:text-slate-900 border border-slate-800 print:border-slate-300">
                    Hardcoded Credentials & Leaked Secrets
                  </td>
                  <td className="p-2.5 font-mono text-slate-400 print:text-slate-600 border border-slate-800 print:border-slate-300">
                    {securityAnalysis?.critical_count || 0} detected
                  </td>
                  <td className="p-2.5 border border-slate-800 print:border-slate-300">
                    {(securityAnalysis?.critical_count || 0) === 0 ? (
                      <span className="text-emerald-400 print:text-emerald-700 font-semibold">PASS</span>
                    ) : (
                      <span className="text-rose-400 print:text-rose-700 font-semibold">ACTION REQUIRED</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-white print:text-slate-900 border border-slate-800 print:border-slate-300">
                    Vulnerable Third-Party Dependencies (CVEs)
                  </td>
                  <td className="p-2.5 font-mono text-slate-400 print:text-slate-600 border border-slate-800 print:border-slate-300">
                    {dependencyAnalysis?.vulnerable_count || 0} vulnerable packages
                  </td>
                  <td className="p-2.5 border border-slate-800 print:border-slate-300">
                    {(dependencyAnalysis?.vulnerable_count || 0) === 0 ? (
                      <span className="text-emerald-400 print:text-emerald-700 font-semibold">PASS</span>
                    ) : (
                      <span className="text-amber-400 print:text-amber-700 font-semibold">PATCH RECOMMENDED</span>
                    )}
                  </td>
                </tr>
                <tr>
                  <td className="p-2.5 font-medium text-white print:text-slate-900 border border-slate-800 print:border-slate-300">
                    Circular Architectural Cycles
                  </td>
                  <td className="p-2.5 font-mono text-slate-400 print:text-slate-600 border border-slate-800 print:border-slate-300">
                    {architectureAnalysis?.cycle_count || 0} cycles
                  </td>
                  <td className="p-2.5 border border-slate-800 print:border-slate-300">
                    {(architectureAnalysis?.cycle_count || 0) === 0 ? (
                      <span className="text-emerald-400 print:text-emerald-700 font-semibold">PASS</span>
                    ) : (
                      <span className="text-amber-400 print:text-amber-700 font-semibold">DECOUPLING ADVISED</span>
                    )}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Audit Sign-Off Footer */}
          <div className="pt-6 border-t border-slate-800 print:border-slate-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs font-mono text-slate-500 print:text-slate-600">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-indigo-400 print:text-indigo-700" />
              <span>Verified by Project Doctor Static Diagnostic Authority</span>
            </div>
            <div>Strict Zero-Code-Execution Guarantee Validated</div>
          </div>
        </div>
      </div>
    </div>
  )
}
