import {
  LayoutDashboard, User, BarChart3, TrendingUp,
  Activity, Zap, Play, Shield, PieChart,
} from 'lucide-react'
import { useRegime } from '../../hooks/usePortfolioData'

const PAGE_ICONS = {
  dashboard:  LayoutDashboard,
  profile:    User,
  assets:     BarChart3,
  frontier:   TrendingUp,
  regime:     Activity,
  garch:      Zap,
  simulation: Play,
  risk:       Shield,
  factor:     PieChart,
}

function RegimePill() {
  const { data } = useRegime()
  if (!data) return null
  const isBull = data.current_regime === data.bull_regime
  return (
    <span className={isBull ? 'badge-bull' : 'badge-bear'}>
      {isBull ? '▲ BULL' : '▼ BEAR'}
      &nbsp;
      {(data.current_prob * 100).toFixed(0)}%
    </span>
  )
}

export default function Layout({ activePage, pages, onNavigate, children }) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-surface border-r border-border flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-border">
          <div className="font-mono text-cyan text-lg font-semibold tracking-tight">
            Portfolio<span className="text-amber">Lab</span>
          </div>
          <div className="text-muted text-xs font-sans mt-0.5">Quant Research Platform</div>
        </div>

        {/* Nav items */}
        <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
          {Object.entries(pages).map(([key, { label }]) => {
            const Icon = PAGE_ICONS[key] || LayoutDashboard
            return (
              <div
                key={key}
                className={`nav-item ${activePage === key ? 'active' : ''}`}
                onClick={() => onNavigate(key)}
              >
                <Icon size={16} className="flex-shrink-0" />
                <span>{label}</span>
              </div>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-3 border-t border-border text-xs text-muted font-mono">
          v1.0 · 12 assets · 50k paths
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-14 bg-surface border-b border-border flex items-center justify-between px-6 flex-shrink-0">
          <div className="font-sans font-medium text-text text-sm">
            {pages[activePage]?.label}
          </div>
          <div className="flex items-center gap-4">
            <RegimePill />
            <span className="text-muted text-xs font-mono">April 2026</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
