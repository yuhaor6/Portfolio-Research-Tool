import { useSimulation, useRegime, useComparison, useClientProfile } from '../../hooks/usePortfolioData'
import { MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  AreaChart, Area, LineChart, Line, ResponsiveContainer,
  XAxis, YAxis, Tooltip, ReferenceLine,
} from 'recharts'
import { colors } from '../../theme/tokens'

function fmt(n) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000)     return `$${(n / 1_000).toFixed(0)}K`
  return `$${n?.toFixed(0) ?? '—'}`
}

function AllocationDonut({ weights }) {
  if (!weights) return null
  const entries = Object.entries(weights)
    .filter(([, w]) => w > 0.005)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)

  const total = entries.reduce((s, [, w]) => s + w, 0)
  const COLORS = ['#00d4ff', '#ff9f43', '#00c853', '#b388ff', '#ffd740', '#ff80ab', '#69f0ae', '#ff6d00']

  // Simple SVG donut
  const SIZE = 120, CX = 60, CY = 60, R = 50, INNER = 32
  let cumulativeAngle = -Math.PI / 2
  const slices = entries.map(([ticker, w], i) => {
    const fraction = w / total
    const angle = fraction * 2 * Math.PI
    const x1 = CX + R * Math.cos(cumulativeAngle)
    const y1 = CY + R * Math.sin(cumulativeAngle)
    cumulativeAngle += angle
    const x2 = CX + R * Math.cos(cumulativeAngle)
    const y2 = CY + R * Math.sin(cumulativeAngle)
    const ix1 = CX + INNER * Math.cos(cumulativeAngle - angle)
    const iy1 = CY + INNER * Math.sin(cumulativeAngle - angle)
    const ix2 = CX + INNER * Math.cos(cumulativeAngle)
    const iy2 = CY + INNER * Math.sin(cumulativeAngle)
    const large = fraction > 0.5 ? 1 : 0
    const d = `M ${ix1} ${iy1} L ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} L ${ix2} ${iy2} A ${INNER} ${INNER} 0 ${large} 0 ${ix1} ${iy1} Z`
    return { ticker, w, d, color: COLORS[i % COLORS.length] }
  })

  return (
    <div className="flex items-start gap-6">
      <svg width={SIZE} height={SIZE} className="flex-shrink-0">
        {slices.map(({ d, color, ticker }) => (
          <path key={ticker} d={d} fill={color} opacity={0.9} />
        ))}
      </svg>
      <div className="space-y-1.5 pt-1">
        {slices.map(({ ticker, w, color }) => (
          <div key={ticker} className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-sm flex-shrink-0" style={{ backgroundColor: color }} />
            <span className="font-mono text-xs text-muted w-16">{ticker}</span>
            <span className="font-mono text-xs text-text">{(w * 100).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function WealthSparkline({ bands }) {
  if (!bands) return null
  const data = bands.p50.map((v, i) => ({
    month: i,
    p50:   v,
    p25:   bands.p25[i],
    p75:   bands.p75[i],
    p5:    bands.p5[i],
    p95:   bands.p95[i],
  }))
  return (
    <ResponsiveContainer width="100%" height={80}>
      <AreaChart data={data} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
        <defs>
          <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="p75" stroke="none" fill="url(#cyanGrad)" />
        <Area type="monotone" dataKey="p25" stroke="none" fill="#0a0a0f" />
        <Line type="monotone" dataKey="p50" stroke="#00d4ff" strokeWidth={1.5} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export default function Dashboard() {
  const { data: simData, loading: simLoading, error: simError } = useSimulation('bootstrap', 'tangency_12')
  const { data: regimeData } = useRegime()
  const { data: frontierData } = useClientProfile()

  if (simLoading) return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <div key={i} className="card-glow p-4 h-24 animate-pulse" />)}
      </div>
      <LoadingSkeleton rows={4} />
    </div>
  )
  if (simError) return <ErrorBanner message={simError} />

  const metrics = simData?.metrics ?? {}
  const bands   = simData?.fan_chart

  const isBull = regimeData ? regimeData.current_regime === regimeData.bull_regime : null

  const tangencyWeights = simData?.weights_used
    ? {} // weights are not in simulation response, fetched from frontier
    : null

  return (
    <div className="space-y-6">
      {/* Hero metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="P(Goal)"
          value={metrics.p_goal != null ? `${(metrics.p_goal * 100).toFixed(1)}%` : '—'}
          sub="P(real wealth ≥ $1M)"
          color="cyan"
          footer="Bootstrap simulation · 50k paths"
        />
        <MetricCard
          label="Median Terminal Wealth"
          value={metrics.median_terminal != null ? fmt(metrics.median_terminal) : '—'}
          sub="Real (inflation-adj)"
          color="green"
        />
        <MetricCard
          label="Sharpe Ratio"
          value={metrics.sharpe != null ? metrics.sharpe.toFixed(3) : '—'}
          sub="Ann. risk-adj return"
          color={metrics.sharpe > 0.8 ? 'cyan' : 'amber'}
        />
        <MetricCard
          label="Current Regime"
          value={isBull === null ? '—' : isBull ? 'BULL' : 'BEAR'}
          sub={regimeData ? `${(regimeData.current_prob * 100).toFixed(0)}% confidence` : ''}
          color={isBull ? 'green' : isBull === false ? 'red' : 'muted'}
        />
      </div>

      {/* Wealth sparkline + second row metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card-glow p-4">
          <div className="metric-label mb-3">10-Year Wealth Projection</div>
          <WealthSparkline bands={bands} />
          <div className="flex justify-between mt-2 text-xs font-mono text-muted">
            <span>Today</span>
            <span>+5yr</span>
            <span>+10yr</span>
          </div>
        </div>

        {/* Secondary metrics */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Sortino Ratio"
            value={metrics.sortino != null ? metrics.sortino.toFixed(3) : '—'}
            sub="Downside risk-adj"
            color="amber"
          />
          <MetricCard
            label="Max Drawdown"
            value={metrics.max_drawdown_median != null
              ? `${(metrics.max_drawdown_median * 100).toFixed(1)}%`
              : '—'}
            sub="Median path"
            color="red"
          />
          <MetricCard
            label="95th Pct Wealth"
            value={metrics.p95 != null ? fmt(metrics.p95) : '—'}
            sub="Best-case scenario"
            color="green"
          />
          <MetricCard
            label="5th Pct Wealth"
            value={metrics.p5 != null ? fmt(metrics.p5) : '—'}
            sub="Stress scenario"
            color="amber"
          />
        </div>
      </div>

      {/* Methodology summary */}
      <div className="card p-4 text-xs text-muted font-sans leading-relaxed">
        <span className="text-cyan font-medium">Strategy: Tangency Portfolio (12 assets)</span>
        &nbsp;— MV-optimal allocation across equities (IVV, QUAL, USMV, VEA, VWO),
        fixed income (AGG, SHV, TIP), and alternatives (VNQ, GLD, BTC, ETH).
        Crypto capped at 5%. Simulation: block-bootstrap Monte Carlo (block size=12mo, 50k paths).
        Contributions from client savings schedule. Inflation: 2.5% p.a.
      </div>
    </div>
  )
}
