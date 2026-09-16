import React, { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Activity,
  FolderTree,
  Code2,
  ShieldAlert,
  Boxes,
  Network,
  HeartPulse,
  Sparkles,
  TrendingUp,
  LayoutDashboard,
  FolderPlus,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Search,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  Cpu,
  User as UserIcon,
  HelpCircle,
  ExternalLink,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { checkHealth, type HealthCheckResponse } from '../../services/api'

interface AppShellProps {
  children: React.ReactNode
  projectId?: string
  projectName?: string
  activeTab?: string
  onTabChange?: (tab: string) => void
  breadcrumbs?: Array<{ label: string; href?: string; onClick?: () => void }>
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  projectId,
  projectName,
  activeTab,
  onTabChange,
  breadcrumbs = [],
}) => {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()

  const [collapsed, setCollapsed] = useState(false)
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false)
  const [systemHealth, setSystemHealth] = useState<HealthCheckResponse | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let mounted = true
    const fetchStatus = async () => {
      try {
        const data = await checkHealth()
        if (mounted) setSystemHealth(data)
      } catch {
        if (mounted) setSystemHealth(null)
      }
    }
    fetchStatus()
    const timer = setInterval(fetchStatus, 30000)
    return () => {
      mounted = false
      clearInterval(timer)
    }
  }, [])

  // Close mobile drawer on route change
  useEffect(() => {
    setMobileDrawerOpen(false)
  }, [location.pathname])

  const handleNavClick = (tabId?: string, href?: string) => {
    if (tabId && onTabChange) {
      onTabChange(tabId)
    } else if (href) {
      navigate(href)
    }
    setMobileDrawerOpen(false)
  }

  const isProjectView = Boolean(projectId)

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Global Top Navigation Bar */}
      <header className="h-14 border-b border-slate-800/80 bg-[#0d1322]/95 backdrop-blur-md sticky top-0 z-40 flex items-center justify-between px-3 sm:px-5">
        {/* Left: Brand + Mobile Toggle + Breadcrumbs */}
        <div className="flex items-center space-x-3 sm:space-x-4 min-w-0">
          <button
            type="button"
            onClick={() => setMobileDrawerOpen(!mobileDrawerOpen)}
            aria-label="Toggle navigation menu"
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            {mobileDrawerOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

          {/* Logo & Application Identity */}
          <Link
            to="/"
            className="flex items-center space-x-2.5 shrink-0 group focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-blue-500 rounded-md"
          >
            <div className="h-7 w-7 rounded-md bg-blue-600/15 border border-blue-500/30 flex items-center justify-center text-blue-400 group-hover:border-blue-400/60 transition">
              <Activity className="h-4 w-4" />
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="font-semibold tracking-tight text-white text-sm">Project Doctor</span>
              <span className="hidden sm:inline-block text-[10px] font-mono uppercase px-1 py-0.2 rounded bg-slate-800 text-slate-400 border border-slate-700/80">
                v1.0.0
              </span>
            </div>
          </Link>

          {/* Breadcrumb Path */}
          <nav aria-label="Breadcrumb" className="hidden lg:flex items-center space-x-1.5 text-xs text-slate-400 border-l border-slate-800 pl-4">
            <Link to="/" className="hover:text-slate-200 transition">Projects</Link>
            {projectName && (
              <>
                <span className="text-slate-600">/</span>
                <span className="font-medium text-slate-200 truncate max-w-[160px]">{projectName}</span>
              </>
            )}
            {activeTab && (
              <>
                <span className="text-slate-600">/</span>
                <span className="capitalize text-blue-400 font-mono text-[11px]">{activeTab}</span>
              </>
            )}
          </nav>
        </div>

        {/* Right Section: System Telemetry + User Controls */}
        <div className="flex items-center space-x-2 sm:space-x-4 shrink-0">
          {/* System Status Indicator */}
          <div
            className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono border border-slate-800 bg-slate-900/50"
            title={`Backend Status: ${systemHealth?.status || 'checking'} • Database: ${systemHealth?.database || 'checking'}`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                systemHealth?.status === 'healthy' ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
              }`}
            />
            <span className="text-slate-400 hidden xl:inline">System</span>
            <span className="text-slate-300">
              {systemHealth?.status === 'healthy' ? 'Online' : 'Checking'}
            </span>
          </div>

          {/* User Account Strip */}
          {user && (
            <div className="flex items-center space-x-2 border-l border-slate-800/80 pl-2 sm:pl-3">
              <div className="h-7 w-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs font-semibold uppercase">
                {user.name ? user.name[0] : user.email[0]}
              </div>
              <div className="hidden md:flex flex-col text-left text-[11px] leading-tight">
                <span className="font-medium text-slate-200 truncate max-w-[110px]">{user.name || 'User'}</span>
                <span className="text-slate-500 font-mono text-[10px] truncate max-w-[110px]">{user.email}</span>
              </div>
              <button
                type="button"
                onClick={logout}
                title="Sign out"
                aria-label="Sign out"
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 transition"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Body Shell (Sidebar + Content) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Desktop Collapsible Sidebar */}
        <aside
          aria-label="Sidebar navigation"
          className={`hidden md:flex flex-col border-r border-slate-800/80 bg-[#0d1322]/60 transition-all duration-200 shrink-0 ${
            collapsed ? 'w-14' : 'w-56'
          }`}
        >
          {/* Navigation Links Scroll Container */}
          <div className="flex-1 py-4 px-2 space-y-6 overflow-y-auto">
            {/* MAIN Section */}
            <div className="space-y-1">
              {!collapsed && (
                <span className="px-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
                  Main
                </span>
              )}
              <button
                type="button"
                onClick={() => handleNavClick(undefined, '/')}
                className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                  location.pathname === '/'
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
                title="Dashboard"
              >
                <LayoutDashboard className="h-4 w-4 shrink-0" />
                {!collapsed && <span>Dashboard</span>}
              </button>

              <button
                type="button"
                onClick={() => handleNavClick(undefined, '/projects/new')}
                className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                  location.pathname === '/projects/new'
                    ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
                title="Import Project"
              >
                <FolderPlus className="h-4 w-4 shrink-0" />
                {!collapsed && <span>Import Project</span>}
              </button>
            </div>

            {/* ANALYSIS Section (Active when inside project context) */}
            {isProjectView && (
              <div className="space-y-1">
                {!collapsed && (
                  <span className="px-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
                    Analysis
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => handleNavClick('health')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'health'
                      ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Health & Debt"
                >
                  <HeartPulse className="h-4 w-4 text-emerald-400 shrink-0" />
                  {!collapsed && <span>Health &amp; Debt</span>}
                </button>

                <button
                  type="button"
                  onClick={() => handleNavClick('scanner')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'scanner'
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Repository Structure"
                >
                  <FolderTree className="h-4 w-4 text-blue-400 shrink-0" />
                  {!collapsed && <span>Repository Files</span>}
                </button>

                <button
                  type="button"
                  onClick={() => handleNavClick('quality')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'quality'
                      ? 'bg-purple-600/15 text-purple-400 border border-purple-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Code Quality"
                >
                  <Code2 className="h-4 w-4 text-purple-400 shrink-0" />
                  {!collapsed && <span>Code Quality</span>}
                </button>

                <button
                  type="button"
                  onClick={() => handleNavClick('security')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'security'
                      ? 'bg-rose-600/15 text-rose-400 border border-rose-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Security Audit"
                >
                  <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0" />
                  {!collapsed && <span>Security Audit</span>}
                </button>

                <button
                  type="button"
                  onClick={() => handleNavClick('dependencies')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'dependencies'
                      ? 'bg-amber-600/15 text-amber-400 border border-amber-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Dependencies"
                >
                  <Boxes className="h-4 w-4 text-amber-400 shrink-0" />
                  {!collapsed && <span>Dependencies</span>}
                </button>

                <button
                  type="button"
                  onClick={() => handleNavClick('architecture')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'architecture'
                      ? 'bg-cyan-600/15 text-cyan-400 border border-cyan-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Architecture Graph"
                >
                  <Network className="h-4 w-4 text-cyan-400 shrink-0" />
                  {!collapsed && <span>Architecture</span>}
                </button>
              </div>
            )}

            {/* AI DIAGNOSTICS Section */}
            {isProjectView && (
              <div className="space-y-1">
                {!collapsed && (
                  <span className="px-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
                    AI Assistant
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => handleNavClick('qa')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'qa'
                      ? 'bg-violet-600/15 text-violet-300 border border-violet-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Ask My Codebase"
                >
                  <Sparkles className="h-4 w-4 text-violet-400 shrink-0" />
                  {!collapsed && <span>Ask Codebase</span>}
                </button>
              </div>
            )}

            {/* HISTORY Section */}
            {isProjectView && (
              <div className="space-y-1">
                {!collapsed && (
                  <span className="px-2 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
                    History
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => handleNavClick('history')}
                  className={`w-full flex items-center space-x-2.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition ${
                    activeTab === 'history'
                      ? 'bg-teal-600/15 text-teal-300 border border-teal-500/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                  title="Analysis History & Trends"
                >
                  <TrendingUp className="h-4 w-4 text-teal-400 shrink-0" />
                  {!collapsed && <span>History &amp; Trends</span>}
                </button>
              </div>
            )}
          </div>

          {/* Sidebar Collapse Toggle Footer */}
          <div className="p-2 border-t border-slate-800/80">
            <button
              type="button"
              onClick={() => setCollapsed(!collapsed)}
              aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="w-full flex items-center justify-center p-2 rounded-md text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition"
            >
              {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
            </button>
          </div>
        </aside>

        {/* Mobile Slide-Out Drawer */}
        {mobileDrawerOpen && (
          <div className="fixed inset-0 z-50 md:hidden flex">
            {/* Backdrop */}
            <div
              className="fixed inset-0 bg-black/70 backdrop-blur-xs"
              onClick={() => setMobileDrawerOpen(false)}
            />

            {/* Drawer Surface */}
            <div className="relative w-64 max-w-[80vw] bg-[#0d1322] border-r border-slate-800 h-full flex flex-col p-4 space-y-6 z-10 shadow-2xl">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div className="flex items-center space-x-2 text-white font-semibold text-sm">
                  <Activity className="h-4 w-4 text-blue-400" />
                  <span>Project Doctor</span>
                </div>
                <button
                  type="button"
                  onClick={() => setMobileDrawerOpen(false)}
                  aria-label="Close navigation"
                  className="text-slate-400 hover:text-white p-1"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Navigation Items in Drawer */}
              <div className="flex-1 overflow-y-auto space-y-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono uppercase text-slate-500 font-semibold px-2">Main</span>
                  <button
                    onClick={() => handleNavClick(undefined, '/')}
                    className="w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-slate-300 hover:bg-slate-800 text-left"
                  >
                    <LayoutDashboard className="h-4 w-4 text-blue-400" />
                    <span>Dashboard</span>
                  </button>
                  <button
                    onClick={() => handleNavClick(undefined, '/projects/new')}
                    className="w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-slate-300 hover:bg-slate-800 text-left"
                  >
                    <FolderPlus className="h-4 w-4 text-emerald-400" />
                    <span>Import Project</span>
                  </button>
                </div>

                {isProjectView && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase text-slate-500 font-semibold px-2">Analysis</span>
                    <button
                      onClick={() => handleNavClick('health')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'health' ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <HeartPulse className="h-4 w-4 text-emerald-400" />
                      <span>Health &amp; Debt</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('scanner')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'scanner' ? 'bg-blue-500/20 text-blue-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <FolderTree className="h-4 w-4 text-blue-400" />
                      <span>Repository Files</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('quality')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'quality' ? 'bg-purple-500/20 text-purple-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Code2 className="h-4 w-4 text-purple-400" />
                      <span>Code Quality</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('security')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'security' ? 'bg-rose-500/20 text-rose-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <ShieldAlert className="h-4 w-4 text-rose-400" />
                      <span>Security Audit</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('dependencies')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'dependencies' ? 'bg-amber-500/20 text-amber-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Boxes className="h-4 w-4 text-amber-400" />
                      <span>Dependencies</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('architecture')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'architecture' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Network className="h-4 w-4 text-cyan-400" />
                      <span>Architecture</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('qa')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'qa' ? 'bg-violet-500/20 text-violet-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <Sparkles className="h-4 w-4 text-violet-400" />
                      <span>Ask Codebase</span>
                    </button>
                    <button
                      onClick={() => handleNavClick('history')}
                      className={`w-full flex items-center space-x-2 px-2.5 py-2 rounded-md text-xs text-left ${
                        activeTab === 'history' ? 'bg-teal-500/20 text-teal-300' : 'text-slate-300 hover:bg-slate-800'
                      }`}
                    >
                      <TrendingUp className="h-4 w-4 text-teal-400" />
                      <span>History &amp; Trends</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Mobile Drawer Sign Out */}
              {user && (
                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400 truncate max-w-[140px]">{user.email}</span>
                  <button
                    onClick={logout}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 transition"
                    title="Sign out"
                  >
                    <LogOut className="h-4 w-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto bg-[#0b0f19] flex flex-col focus-visible:outline-hidden">
          <div className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
            {children}
          </div>

          {/* Unified Platform Footer */}
          <footer className="border-t border-slate-800/80 bg-[#090d16] py-3.5 px-4 sm:px-8 text-xs text-slate-500 mt-auto">
            <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-slate-400">Project Doctor</span>
                <span>•</span>
                <span>Software Health &amp; Diagnostics Engine</span>
              </div>
              <div className="flex items-center space-x-4 font-mono text-[11px] text-slate-400">
                <span>Deterministic Diagnostics</span>
                <span>•</span>
                <span>Zero Fake Data</span>
                <span>•</span>
                <span>Sandboxed Storage</span>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}

export default AppShell
