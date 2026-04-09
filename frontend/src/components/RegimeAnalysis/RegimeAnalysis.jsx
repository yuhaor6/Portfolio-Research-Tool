import { useRegime } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  AreaChart, Area, ComposedChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, CartesianGrid,
} from 'recharts'
import { colors } from '../../theme/tokens'

export default function RegimeAnalysis() {
  const { data, loading, error } = useRegime()

  if (loading) return <LoadingSkeleton rows={5} />
  if (error)   return <ErrorBanner message={error} />

  const {
    bull_regime, bear_regime, regime_means, regime_vols,
    transition_matrix, current_regime, current_prob, smoothed_probs,
    ivv_cumulative = {},
  } = data

  const isBull = current_regime === bull_regime

  // Build timeline data merging probs + IVV cumulative return
  const timelineData = Object.entries(smoothed_probs ?? {}).map(([date, probs]) => ({
    date,
    bear_prob:  probs[bear_regime] ?? 0,
    bull_prob:  probs[bull_regime] ?? 0,
    ivv_cum:    ivv_cumulative[date] ?? null,
  }))

  const maxIvv = Math.max(...timelineData.map(d => d.ivv_cum ?? 0))

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="card p-2 text-xs font-mono border border-border">
        <div className="text-muted">{label}</div>
        <div className="text-green">Bull: {((payload.find(p => p.dataKey === 'bull_prob')?.value ?? 0) * 100).toFixed(1)}%</div>
        <div className="text-red">Bear: {((payload.find(p => p.dataKey === 'bear_prob')?.value ?? 0) * 100).toFixed(1)}%</div>
        {payload.find(p => p.dataKey === 'ivv_cum') &&
          <div className="text-cyan">IVV: {payload.find(p => p.dataKey === 'ivv_cum')?.value?.toFixed(2)}×</div>
        }
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SectionTitle sub="Hamilton 2-state Markov-switching model on IVV excess returns">
        Regime Analysis
      </SectionTitle>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Current Regime"
          value={isBull ? 'BULL' : 'BEAR'}
          sub={`${(current_prob * 100).toFixed(0)}% confidence`}
          color={isBull ? 'green' : 'red'}
        />
        <MetricCard
          label="Bull Regime Mean"
          value={`${(regime_means[bull_regime] * 100).toFixed(1)}%`}
          sub="Annualized"
          color="green"
        />
        <MetricCard
          label="Bear Regime Mean"
          value={`${(regime_means[bear_regime] * 100).toFixed(1)}%`}
          sub="Annualized"
          color="red"
        />
        <MetricCard
          label="Bear / Bull Vol Ratio"
          value={`${(regime_vols[bear_regime] / regime_vols[bull_regime]).toFixed(1)}×`}
          sub="Crisis amplification"
          color="amber"
        />
      </div>

      {/* Regime probability timeline with IVV overlay */}
      <div className="card-glow p-4">
        <div className="text-xs text-muted font-sans mb-1">
          Smoothed bear-state probability (red area) overlaid on IVV cumulative return (cyan line, right axis)
        </div>
        <div className="flex gap-4 text-[10px] font-mono mb-3">
          <span className="text-red">■ Bear regime prob</span>
          <span className="text-green">■ Bull regime prob</span>
          <span className="text-cyan">— IVV cum. return (right axis)</span>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <ComposedChart data={timelineData} margin={{ top: 5, right: 50, bottom: 20, left: 10 }}>
            <defs>
              <linearGradient id="bearGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#ff4444" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#ff4444" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="bullGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stopColor="#00c853" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#00c853" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="date"
              tickFormatter={v => v?.slice(0, 7)}
              tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              interval={Math.floor(timelineData.length / 8)}
            />
            {/* Left Y — probability 0→1 */}
            <YAxis
              yAxisId="prob"
              tickFormatter={v => `${(v * 100).toFixed(0)}%`}
              tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              domain={[0, 1]}
            />
            {/* Right Y — IVV cumulative (rebased to 1) */}
            <YAxis
              yAxisId="ivv"
              orientation="right"
              tickFormatter={v => `${v.toFixed(1)}×`}
              tick={{ fill: colors.cyan, fontSize: 9, fontFamily: 'JetBrains Mono' }}
              domain={[0, 'auto']}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine yAxisId="prob" y={0.5} stroke={colors.border} strokeDasharray="4 4" />
            <Area yAxisId="prob" type="monotone" dataKey="bull_prob" stroke="#00c853" strokeWidth={1} fill="url(#bullGrad)" />
            <Area yAxisId="prob" type="monotone" dataKey="bear_prob" stroke="#ff4444" strokeWidth={1.5} fill="url(#bearGrad)" />
            {timelineData.some(d => d.ivv_cum != null) && (
              <Line yAxisId="ivv" type="monotone" dataKey="ivv_cum" stroke={colors.cyan} strokeWidth={1.5} dot={false} connectNulls />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Regime stats table + transition matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Regime stats */}
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Regime-Conditional Statistics</div>
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-muted">Metric</th>
                <th className="text-right py-2 text-green">Bull</th>
                <th className="text-right py-2 text-red">Bear</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/30">
                <td className="py-2 text-muted">Ann. Mean Return</td>
                <td className="py-2 text-right text-green">{(regime_means[bull_regime] * 100).toFixed(1)}%</td>
                <td className="py-2 text-right text-red">{(regime_means[bear_regime] * 100).toFixed(1)}%</td>
              </tr>
              <tr className="border-b border-border/30">
                <td className="py-2 text-muted">Ann. Volatility</td>
                <td className="py-2 text-right text-text">{(regime_vols[bull_regime] * 100).toFixed(1)}%</td>
                <td className="py-2 text-right text-text">{(regime_vols[bear_regime] * 100).toFixed(1)}%</td>
              </tr>
              <tr>
                <td className="py-2 text-muted">Duration (approx)</td>
                <td className="py-2 text-right text-cyan">
                  {transition_matrix ? `${(1 / (1 - transition_matrix[bull_regime][bull_regime])).toFixed(0)} mo` : '—'}
                </td>
                <td className="py-2 text-right text-amber">
                  {transition_matrix ? `${(1 / (1 - transition_matrix[bear_regime][bear_regime])).toFixed(0)} mo` : '—'}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Transition matrix */}
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Markov Transition Matrix P(next | current)</div>
          {transition_matrix && (
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-2 text-muted">From ↓ To →</th>
                  <th className="text-right py-2 text-green">Bull</th>
                  <th className="text-right py-2 text-red">Bear</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border/30">
                  <td className="py-2 text-green">Bull</td>
                  <td className="py-2 text-right text-cyan">{(transition_matrix[bull_regime][bull_regime] * 100).toFixed(1)}%</td>
                  <td className="py-2 text-right text-text">{(transition_matrix[bull_regime][bear_regime] * 100).toFixed(1)}%</td>
                </tr>
                <tr>
                  <td className="py-2 text-red">Bear</td>
                  <td className="py-2 text-right text-text">{(transition_matrix[bear_regime][bull_regime] * 100).toFixed(1)}%</td>
                  <td className="py-2 text-right text-cyan">{(transition_matrix[bear_regime][bear_regime] * 100).toFixed(1)}%</td>
                </tr>
              </tbody>
            </table>
          )}
          {transition_matrix && (
            <div className="text-xs text-muted mt-3">
              Expected bull duration: {(1 / (1 - transition_matrix[bull_regime][bull_regime])).toFixed(0)} months ·
              Bear duration: {(1 / (1 - transition_matrix[bear_regime][bear_regime])).toFixed(0)} months
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
