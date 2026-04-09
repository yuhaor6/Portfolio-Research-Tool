import { useState } from 'react'
import { useRisk } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, ReferenceLine, Legend,
} from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const CHART_SERIES = chartColors.series ?? Object.values(chartColors).filter(Array.isArray).flat()

const STRATEGIES = [
  '60_40', 'equal_weight', 'risk_parity', 'tangency_3', 'tangency_5', 'tangency_12', 'tangency_12_glide',
]

const STRESS_COLORS = {
  '2008_gfc':      '#ff4444',
  covid_crash:     '#ff7b00',
  high_inflation:  '#ffcc00',
  job_loss:        '#aa99ff',
  stagflation:     '#ff44aa',
}

export default function RiskAnalysis() {
  const [strategy, setStrategy] = useState('tangency_12')
  const { data, loading, error } = useRisk(strategy)

  if (loading) return <LoadingSkeleton rows={5} />
  if (error)   return <ErrorBanner message={error} />

  const {
    metrics = {}, drawdown_series = [], var_breakdown = {},
    stress_scenarios = {}, strategy_comparison = [],
  } = data

  const ddData = drawdown_series.map((v, i) => ({
    month: i, drawdown: +(v * 100).toFixed(2),
  }))

  const varData = [
    { label: 'VaR 5%',  value: +((metrics.var_5 ?? 0) * 100).toFixed(1) },
    { label: 'CVaR 5%', value: +((metrics.cvar_5 ?? 0) * 100).toFixed(1) },
    { label: 'Max DD',  value: +((metrics.max_drawdown_median ?? 0) * 100).toFixed(1) },
  ]

  const stressRows = Object.entries(stress_scenarios)

  // Build aligned chart data for stress wealth paths
  const stressPathData = (() => {
    if (!stressRows.length) return []
    const maxLen = Math.max(...stressRows.map(([, r]) => r.median_path?.length ?? 0))
    if (maxLen === 0) return []
    return Array.from({ length: maxLen }, (_, i) => {
      const pt = { month: i }
      stressRows.forEach(([key, r]) => {
        if (r.median_path?.[i] != null) pt[key] = Math.round(r.median_path[i])
      })
      return pt
    })
  })()

  const compData = strategy_comparison.map((s, i) => ({
    name: s.strategy_label ?? s.strategy ?? `S${i}`,
    sharpe: +(s.sharpe ?? 0).toFixed(2),
    fill: CHART_SERIES[i % CHART_SERIES.length],
  })).sort((a, b) => b.sharpe - a.sharpe)

  return (
    <div className="space-y-6">
      <SectionTitle sub="Drawdown analysis, tail risk measures, and stress-test scenarios">
        Risk Analysis
      </SectionTitle>

      {/* Strategy selector */}
      <div className="flex flex-wrap gap-2">
        {STRATEGIES.map(s => (
          <button
            key={s}
            onClick={() => setStrategy(s)}
            className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${
              strategy === s
                ? 'bg-amber/10 border-amber text-amber'
                : 'border-border text-muted hover:text-text'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard label="Sharpe Ratio"   value={(metrics.sharpe ?? 0).toFixed(2)}   color="cyan" />
        <MetricCard label="Sortino Ratio"  value={(metrics.sortino ?? 0).toFixed(2)}  color="cyan" />
        <MetricCard label="Calmar Ratio"   value={(metrics.calmar ?? 0).toFixed(2)}   color="text" />
        <MetricCard label="VaR (5th)"      value={`${((metrics.var_5 ?? 0) * 100).toFixed(1)}%`} color="amber" />
        <MetricCard label="CVaR (5th)"     value={`${((metrics.cvar_5 ?? 0) * 100).toFixed(1)}%`} color="red" />
      </div>

      {/* Drawdown time series */}
      <div className="card-glow p-4">
        <div className="text-xs text-muted font-sans mb-3">
          Median path drawdown over horizon · strategy: <span className="text-amber">{strategy}</span>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={ddData} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
            <defs>
              <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#ff4444" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#ff4444" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis
              dataKey="month"
              tickFormatter={v => `M${v}`}
              tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
            />
            <YAxis
              tickFormatter={v => `${v}%`}
              tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
            />
            <Tooltip
              formatter={v => [`${v}%`, 'Drawdown']}
              contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
            />
            <ReferenceLine y={0} stroke={colors.border} />
            <Area type="monotone" dataKey="drawdown" stroke="#ff4444" strokeWidth={1.5} fill="url(#ddGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* VaR / CVaR / Max DD bar */}
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Tail Risk Summary</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={varData} margin={{ top: 5, right: 10, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis dataKey="label" tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <YAxis
                tickFormatter={v => `${v}%`}
                tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              />
              <Tooltip
                formatter={v => [`${v}%`, 'Magnitude']}
                contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
              />
              <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                {varData.map((entry, i) => (
                  <Cell key={entry.label} fill={['#ffcc00', '#ff7b00', '#ff4444'][i]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Stress scenario table */}
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Stress-Test Scenarios</div>
          {stressRows.length > 0 ? (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-1.5 text-muted">Scenario</th>
                  <th className="text-right py-1.5 text-muted">P(Goal)</th>
                  <th className="text-right py-1.5 text-muted">Median $</th>
                  <th className="text-right py-1.5 text-muted">Max DD</th>
                </tr>
              </thead>
              <tbody>
                {stressRows.map(([key, r]) => (
                  <tr key={key} className="border-b border-border/30">
                    <td className="py-1.5" style={{ color: STRESS_COLORS[key] ?? colors.text }}>
                      {r.label ?? key.replace(/_/g, ' ').toUpperCase()}
                    </td>
                    <td className="py-1.5 text-right text-text">
                      {((r.metrics?.p_goal ?? 0) * 100).toFixed(0)}%
                    </td>
                    <td className="py-1.5 text-right text-text">
                      ${((r.metrics?.median_terminal ?? 0) / 1000).toFixed(0)}k
                    </td>
                    <td className="py-1.5 text-right text-red">
                      {((r.metrics?.max_drawdown_median ?? 0) * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-xs text-muted">Run the full pipeline to obtain stress-test results.</div>
          )}
        </div>
      </div>

      {/* Stress scenario median wealth paths */}
      {stressPathData.length > 0 && (
        <div className="card-glow p-4">
          <div className="metric-label mb-1">Stress Scenario — Median Wealth Paths</div>
          <div className="text-xs text-muted font-sans mb-3">
            Median portfolio value under each stress scenario (monthly)
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={stressPathData} margin={{ top: 5, right: 20, bottom: 20, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                dataKey="month"
                tickFormatter={v => `M${v}`}
                tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              />
              <YAxis
                tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
                tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              />
              <Tooltip
                formatter={(v, name) => [`$${(v / 1000).toFixed(1)}k`, name.replace(/_/g, ' ')]}
                contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
              />
              <Legend
                wrapperStyle={{ fontSize: 10, fontFamily: 'JetBrains Mono', paddingTop: 8 }}
                formatter={name => name.replace(/_/g, ' ')}
              />
              {stressRows.map(([key]) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={STRESS_COLORS[key] ?? CHART_SERIES[0]}
                  strokeWidth={1.5}
                  dot={false}
                  strokeDasharray={key === 'stagflation' ? '5 3' : undefined}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Strategy Sharpe comparison */}
      {compData.length > 0 && (
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Sharpe Ratio — Strategy Comparison</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={compData} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} horizontal={false} />
              <XAxis type="number" tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
              <YAxis
                dataKey="name" type="category"
                tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                width={95}
              />
              <Tooltip
                formatter={v => [v.toFixed(2), 'Sharpe']}
                contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
              />
              <ReferenceLine x={0} stroke={colors.border} />
              <Bar dataKey="sharpe" radius={[0, 3, 3, 0]}>
                {compData.map(entry => (
                  <Cell key={entry.name} fill={entry.fill ?? CHART_SERIES[0]} opacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
