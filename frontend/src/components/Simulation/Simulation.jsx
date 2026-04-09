import { useState } from 'react'
import { useSimulation, useComparison } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner, Toggle } from '../shared'
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar, Cell,
  XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { colors, fanColors, chartColors } from '../../theme/tokens'

const CHART_SERIES = chartColors.series ?? []

const MODES = [
  { label: 'Bootstrap',   value: 'bootstrap'   },
  { label: 'Parametric',  value: 'parametric'  },
  { label: 'Regime MC',   value: 'regime'      },
  { label: 'GARCH MC',    value: 'garch'       },
]

const STRATEGIES = [
  { label: 'Tangency 12',      value: 'tangency_12'      },
  { label: 'Tangency 5',       value: 'tangency_5'       },
  { label: 'Tangency 3',       value: 'tangency_3'       },
  { label: '60/40',            value: '60_40'            },
  { label: 'Equal Weight',     value: 'equal_weight'     },
  { label: 'Risk Parity',      value: 'risk_parity'      },
  { label: 'Glide Path',       value: 'tangency_12_glide'},
  { label: 'All Equity',       value: 'all_equity'       },
  { label: 'All Cash',         value: 'all_cash'         },
]

const MODE_DESCRIPTIONS = {
  bootstrap:  'Block Bootstrap: resamples 12-month blocks of historical returns. Non-parametric — preserves dependencies, fat tails, and crisis clustering.',
  parametric: 'Parametric Normal: multivariate Gaussian (μ, Σ). Fast and interpretable but underestimates tail risk and ignores skewness.',
  regime:     'Regime-Conditional MC: Markov chain switches between bull/bear regimes — each with its own (μ, Σ). Fatter left tails from crisis dynamics.',
  garch:      'GARCH-Filtered MC: forward-simulates GARCH(1,1) per asset. Captures volatility clustering — high-vol periods follow high-vol periods.',
}

function fmt(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(2)}M`
  return `$${(n / 1_000).toFixed(0)}K`
}

function FanChart({ bands, goal }) {
  if (!bands) return null
  const n = bands.p50.length
  const step = Math.max(1, Math.floor(n / 60))
  const data = []
  for (let i = 0; i < n; i += step) {
    data.push({ month: i, p5: bands.p5[i], p25: bands.p25[i], p50: bands.p50[i], p75: bands.p75[i], p95: bands.p95[i] })
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    const yr = (label / 12).toFixed(1)
    return (
      <div className="card p-2 text-xs font-mono border border-border">
        <div className="text-muted mb-1">Month {label} (Yr {yr})</div>
        {['p95','p75','p50','p25','p5'].map(k => (
          <div key={k} className="text-text">{k.toUpperCase()}: {fmt(payload.find(p => p.dataKey === k)?.value)}</div>
        ))}
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={340}>
      <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 20, left: 60 }}>
        <defs>
          <linearGradient id="band95" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.06} />
            <stop offset="100%" stopColor="#00d4ff" stopOpacity={0.02} />
          </linearGradient>
          <linearGradient id="band75" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.15} />
            <stop offset="100%" stopColor="#00d4ff" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <XAxis dataKey="month" tickFormatter={v => `Yr ${(v / 12).toFixed(0)}`} tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}K`} tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        <Tooltip content={<CustomTooltip />} />
        {goal && <ReferenceLine y={goal} stroke={colors.amber} strokeDasharray="4 4" label={{ value: `Goal $${(goal / 1e6).toFixed(1)}M`, fill: colors.amber, fontSize: 10 }} />}
        <Area type="monotone" dataKey="p95" stroke="none" fill="url(#band95)" />
        <Area type="monotone" dataKey="p5"  stroke="none" fill="#0a0a0f" />
        <Area type="monotone" dataKey="p75" stroke="none" fill="url(#band75)" />
        <Area type="monotone" dataKey="p25" stroke="none" fill="#0a0a0f" />
        <Line type="monotone" dataKey="p50" stroke="#00d4ff" strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

function TerminalHistogram({ terminalHist, goal }) {
  if (!terminalHist) return null
  const { values, percentiles } = terminalHist
  const data = percentiles
    .filter((_, i) => i % 4 === 0)
    .map((p, i) => ({ pct: p.toFixed(0), value: values[i * 4] }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 10, right: 10, bottom: 20, left: 50 }}>
        <XAxis dataKey="pct" tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} label={{ value: 'Percentile', position: 'bottom', fill: colors.muted, fontSize: 10 }} />
        <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}K`} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
        <Tooltip formatter={v => [fmt(v), 'Wealth']} contentStyle={{ background: '#141419', border: '1px solid #1e1e2a', fontSize: 11 }} />
        {goal && <ReferenceLine y={goal} stroke={colors.amber} strokeDasharray="4 4" />}
        <Bar dataKey="value" radius={[2, 2, 0, 0]}>
          {data.map(d => <Cell key={d.pct} fill={d.value >= (goal ?? Infinity) ? '#00c853' : '#00d4ff'} fillOpacity={0.75} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function ComparisonTable({ rows }) {
  const [sortKey, setSortKey]   = useState('sharpe')
  const [sortDesc, setSortDesc] = useState(true)

  const toggleSort = key => {
    if (sortKey === key) setSortDesc(d => !d)
    else { setSortKey(key); setSortDesc(true) }
  }
  const sorted = [...rows].sort((a, b) => sortDesc ? (b[sortKey] ?? 0) - (a[sortKey] ?? 0) : (a[sortKey] ?? 0) - (b[sortKey] ?? 0))

  const cols = [
    { key: 'label',          label: 'Strategy', fmt: v => v, right: false },
    { key: 'sharpe',         label: 'Sharpe',   fmt: v => v?.toFixed(3), right: true, color: v => v > 0.8 ? 'text-cyan' : 'text-text' },
    { key: 'sortino',        label: 'Sortino',  fmt: v => v?.toFixed(3), right: true },
    { key: 'calmar',         label: 'Calmar',   fmt: v => v?.toFixed(3), right: true },
    { key: 'p_goal',         label: 'P(Goal)',  fmt: v => v != null ? `${(v * 100).toFixed(0)}%` : '—', right: true, color: v => v > 0.3 ? 'text-green' : 'text-muted' },
    { key: 'median_terminal',label: 'Median $', fmt: v => fmt(v), right: true },
    { key: 'max_drawdown_median', label: 'Max DD', fmt: v => v != null ? `-${(v * 100).toFixed(1)}%` : '—', right: true, color: v => v > 0.25 ? 'text-red' : 'text-text' },
    { key: 'var_5',          label: 'VaR 5%',   fmt: v => v != null ? `${(v * 100).toFixed(1)}%` : '—', right: true },
  ]

  const sortIndicator = key => sortKey === key ? (sortDesc ? ' ▼' : ' ▲') : ''

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-border">
            {cols.map(c => (
              <th
                key={c.key}
                onClick={() => c.key !== 'strategy_label' && toggleSort(c.key)}
                className={`py-2 px-2 font-sans text-muted text-xs tracking-wide select-none ${c.right ? 'text-right' : 'text-left'} ${c.key !== 'strategy_label' ? 'cursor-pointer hover:text-text' : ''}`}
              >
                {c.label}{sortIndicator(c.key)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={row.strategy ?? i} className="border-b border-border/30 hover:bg-surface/40 transition-colors">
              {cols.map(c => {
                const v = row[c.key]
                const colorClass = c.color ? c.color(v) : 'text-text'
                return (
                  <td key={c.key} className={`py-2 px-2 ${c.right ? 'text-right' : ''} ${colorClass}`}>
                    {c.fmt(v)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StrategyRadar({ rows }) {
  if (!rows?.length) return null
  // Normalize metrics to 0–1 scale for radar
  const metrics = ['sharpe', 'sortino', 'calmar', 'p_goal']
  const normalize = (key) => {
    const vals = rows.map(r => r[key] ?? 0).filter(v => isFinite(v))
    const mn = Math.min(...vals), mx = Math.max(...vals)
    if (mx === mn) return rows.map(() => 0.5)
    return rows.map(r => (+((r[key] ?? mn) - mn) / (mx - mn)).toFixed(3))
  }
  const normed = Object.fromEntries(metrics.map(m => [m, normalize(m)]))
  // Also normalize inverse of max_drawdown (lower = better → invert)
  const ddVals = rows.map(r => r.max_drawdown_median ?? 0)
  const ddMn = Math.min(...ddVals), ddMx = Math.max(...ddVals)
  normed.drawdown_score = ddMx === ddMn ? rows.map(() => 0.5) : rows.map(r => +(1 - ((r.max_drawdown_median ?? ddMn) - ddMn) / (ddMx - ddMn)).toFixed(3))

  const LABELS = { sharpe: 'Sharpe', sortino: 'Sortino', calmar: 'Calmar', p_goal: 'P(Goal)', drawdown_score: 'Low DD' }
  const allMetrics = [...metrics, 'drawdown_score']

  // Pick top 4 by sharpe for readability
  const topRows = [...rows].sort((a, b) => (b.sharpe ?? 0) - (a.sharpe ?? 0)).slice(0, 4)

  const radarData = allMetrics.map(m => {
    const entry = { subject: LABELS[m] }
    topRows.forEach((r, i) => {
      entry[`s${i}`] = +normed[m][rows.indexOf(r)]
    })
    return entry
  })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
        <PolarGrid stroke={colors.border} />
        <PolarAngleAxis dataKey="subject" tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
        <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
        <Tooltip contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 10 }} />
        {topRows.map((r, i) => (
          <Radar key={r.strategy} name={r.label ?? r.strategy} dataKey={`s${i}`}
            stroke={CHART_SERIES[i % CHART_SERIES.length]} fill={CHART_SERIES[i % CHART_SERIES.length]}
            fillOpacity={0.1} strokeWidth={1.5}
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  )
}

export default function Simulation() {
  const [mode, setMode]         = useState('bootstrap')
  const [strategy, setStrategy] = useState('tangency_12')
  const [tab, setTab]           = useState('fan')  // 'fan' | 'compare'
  const { data, loading, error } = useSimulation(mode, strategy)
  const { data: compData }       = useComparison()
  const GOAL = 1_000_000

  if (loading) return <LoadingSkeleton rows={5} />
  if (error)   return <ErrorBanner message={error} />

  const metrics = data?.metrics ?? {}
  const bands   = data?.fan_chart
  const hist    = data?.terminal_hist
  const compRows = compData?.strategies ?? compData ?? []

  return (
    <div className="space-y-6">
      {/* Header + controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <SectionTitle sub="Real (inflation-adjusted) wealth paths over 10-year horizon">
          Monte Carlo Simulation
        </SectionTitle>
        <div className="flex flex-col gap-2 items-end">
          <Toggle options={MODES} value={mode} onChange={setMode} />
          <select
            value={strategy}
            onChange={e => setStrategy(e.target.value)}
            className="bg-surface border border-border text-xs font-mono text-text rounded px-2 py-1.5 focus:outline-none focus:border-cyan"
          >
            {STRATEGIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 border-b border-border pb-1">
        {[
          { id: 'fan',     label: 'Fan Chart'          },
          { id: 'compare', label: 'Strategy Comparison' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-3 py-1.5 text-xs font-sans rounded-t transition-colors ${
              tab === t.id ? 'text-cyan border-b-2 border-cyan' : 'text-muted hover:text-text'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'fan' && (
        <>
          {/* Key metrics */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard label="P(Goal)"       value={metrics.p_goal != null ? `${(metrics.p_goal * 100).toFixed(1)}%` : '—'} sub="P(wealth ≥ $1M real)" color="cyan" />
            <MetricCard label="Median Wealth" value={fmt(metrics.median_terminal)} color="green" />
            <MetricCard label="5th Percentile" value={fmt(metrics.p5)} sub="Worst-case (5%)" color="amber" />
            <MetricCard label="CVaR (5%)"     value={fmt(metrics.cvar_5)} sub="Avg below 5th pct" color="red" />
          </div>

          <div className="card-glow p-4">
            <div className="text-xs text-muted font-sans mb-2">Wealth fan chart · bands: 5 / 25 / 50 / 75 / 95th percentiles</div>
            <FanChart bands={bands} goal={GOAL} />
          </div>

          <div className="card-glow p-4">
            <div className="text-xs text-muted font-sans mb-2">Terminal wealth distribution (real) · amber line = $1M goal</div>
            <TerminalHistogram terminalHist={hist} goal={GOAL} />
          </div>

          <div className="card p-4 text-xs text-muted font-sans leading-relaxed">
            {MODE_DESCRIPTIONS[mode]}
          </div>
        </>
      )}

      {tab === 'compare' && compRows.length > 0 && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card-glow p-4">
              <div className="metric-label mb-3">Strategy Radar (top 4 by Sharpe)</div>
              <StrategyRadar rows={compRows} />
              <div className="text-[10px] text-muted mt-1">All axes normalised 0→1. Larger polygon = better risk-adjusted performance.</div>
            </div>
            <div className="card-glow p-4">
              <div className="metric-label mb-3">P(Goal) by Strategy</div>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart
                  data={[...compRows].sort((a, b) => (b.p_goal ?? 0) - (a.p_goal ?? 0))}
                  layout="vertical"
                  margin={{ top: 5, right: 30, bottom: 5, left: 100 }}
                >
                  <XAxis type="number" tickFormatter={v => `${(v * 100).toFixed(0)}%`} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} domain={[0, 1]} />
                  <YAxis dataKey="strategy_label" type="category" tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} width={95} />
                  <Tooltip formatter={v => [`${(v * 100).toFixed(1)}%`, 'P(Goal)']} contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }} />
                  <ReferenceLine x={0} stroke={colors.border} />
                  <Bar dataKey="p_goal" radius={[0, 3, 3, 0]}>
                    {[...compRows].sort((a, b) => (b.p_goal ?? 0) - (a.p_goal ?? 0)).map((r, i) => (
                      <Cell key={r.strategy} fill={CHART_SERIES[i % CHART_SERIES.length]} opacity={0.85} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card-glow p-4">
            <div className="metric-label mb-3">Full Strategy Comparison · click column header to sort</div>
            <ComparisonTable rows={compRows} />
          </div>
        </>
      )}
    </div>
  )
}

