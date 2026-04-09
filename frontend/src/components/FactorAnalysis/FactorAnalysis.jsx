import { useFactor } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine, Cell,
} from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const CHART_SERIES = chartColors.series ?? Object.values(chartColors).filter(Array.isArray).flat()

const FACTOR_COLORS = {
  'Mkt-RF': colors.cyan,
  SMB:      colors.amber,
  HML:      '#aa99ff',
  RMW:      '#00c853',
  CMA:      '#ff7b00',
}

const TICKER_LABELS = {
  IVV: 'IVV', QUAL: 'QUAL', USMV: 'USMV', VEA: 'VEA', VWO: 'VWO',
  AGG: 'AGG', SHV: 'SHV', TIP: 'TIP', VNQ: 'VNQ', GLD: 'GLD',
  'BTC-USD': 'BTC', 'ETH-USD': 'ETH',
}

export default function FactorAnalysis() {
  const { data, loading, error } = useFactor()

  if (loading) return <LoadingSkeleton rows={5} />
  if (error)   return <ErrorBanner message={error} />

  const { capm = {}, ff5 = {}, rolling_beta = {} } = data

  const capmRows = Object.entries(capm).map(([ticker, r]) => ({
    ticker: TICKER_LABELS[ticker] ?? ticker,
    alpha:  r.alpha_annualized ?? r.alpha ?? 0,
    beta:   r.beta ?? 0,
    r2:     r.r_squared ?? 0,
    t_alpha: r.t_alpha ?? 0,
    t_beta:  r.t_beta ?? 0,
  })).sort((a, b) => b.beta - a.beta)

  // FF5 average loadings across all assets
  const factors = ['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA']
  const ff5BarData = factors.map(f => {
    const vals = Object.values(ff5).map(r => r[f] ?? 0)
    const avg = vals.reduce((a, b) => a + b, 0) / (vals.length || 1)
    return { factor: f, loading: +avg.toFixed(3) }
  })

  const rbAssets = Object.keys(rolling_beta)
  const rbDates  = Object.keys(rolling_beta[rbAssets[0]] ?? {})
  const rbChartData = rbDates.map(date => {
    const row = { date }
    rbAssets.forEach(a => { row[TICKER_LABELS[a] ?? a] = rolling_beta[a][date] ?? null })
    return row
  })

  return (
    <div className="space-y-6">
      <SectionTitle sub="CAPM α/β regressions and Fama-French 5-factor loadings">
        Factor Analysis
      </SectionTitle>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Highest Beta"
          value={(Math.max(...capmRows.map(r => r.beta))).toFixed(2)}
          sub={capmRows.sort((a, b) => b.beta - a.beta)[0]?.ticker}
          color="red"
        />
        <MetricCard
          label="Best Alpha (Ann.)"
          value={`${(Math.max(...capmRows.map(r => r.alpha)) * 100).toFixed(1)}%`}
          sub="CAPM regression"
          color="green"
        />
        <MetricCard
          label="Assets Analysed"
          value={capmRows.length}
          sub="CAPM + FF5"
          color="text"
        />
        <MetricCard
          label="Avg Market Beta"
          value={(capmRows.reduce((s, r) => s + r.beta, 0) / (capmRows.length || 1)).toFixed(2)}
          sub="Equal-weighted avg"
          color="cyan"
        />
      </div>

      {/* CAPM table */}
      <div className="card-glow p-4">
        <div className="metric-label mb-3">CAPM Regression Results</div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 text-muted">Asset</th>
                <th className="text-right py-2 text-muted">α (Ann.)</th>
                <th className="text-right py-2 text-muted">t(α)</th>
                <th className="text-right py-2 text-muted">β</th>
                <th className="text-right py-2 text-muted">t(β)</th>
                <th className="text-right py-2 text-muted">R²</th>
              </tr>
            </thead>
            <tbody>
              {capmRows.map(r => (
                <tr key={r.ticker} className="border-b border-border/30 hover:bg-surface/30 transition-colors">
                  <td className="py-1.5 text-cyan font-semibold">{r.ticker}</td>
                  <td className={`py-1.5 text-right ${r.alpha >= 0 ? 'text-green' : 'text-red'}`}>
                    {(r.alpha * 100).toFixed(2)}%
                  </td>
                  <td className={`py-1.5 text-right ${Math.abs(r.t_alpha) >= 2 ? 'text-amber' : 'text-muted'}`}>
                    {r.t_alpha.toFixed(2)}
                    {Math.abs(r.t_alpha) >= 2 && <span className="text-amber ml-1">*</span>}
                  </td>
                  <td className="py-1.5 text-right text-text">{r.beta.toFixed(3)}</td>
                  <td className={`py-1.5 text-right ${Math.abs(r.t_beta) >= 2 ? 'text-cyan' : 'text-muted'}`}>
                    {r.t_beta.toFixed(2)}
                  </td>
                  <td className="py-1.5 text-right text-muted">{(r.r2 * 100).toFixed(0)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="text-[10px] text-muted mt-2">* |t| ≥ 2.0 indicates statistical significance at ~95% confidence</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* FF5 average loadings */}
        <div className="card-glow p-4">
          <div className="metric-label mb-3">Fama-French 5-Factor Loadings (Portfolio Average)</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={ff5BarData} margin={{ top: 5, right: 10, bottom: 10, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis dataKey="factor" tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <YAxis tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
              <Tooltip
                formatter={v => [v.toFixed(3), 'Loading']}
                contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
              />
              <ReferenceLine y={0} stroke={colors.border} />
              <Bar dataKey="loading" radius={[3, 3, 0, 0]}>
                {ff5BarData.map(entry => (
                  <Cell key={entry.factor} fill={FACTOR_COLORS[entry.factor] ?? colors.cyan} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="text-[10px] text-muted mt-2">
            Mkt-RF: market premium · SMB: size · HML: value · RMW: profitability · CMA: investment
          </div>
        </div>

        {/* Rolling beta */}
        {rbChartData.length > 0 && (
          <div className="card-glow p-4">
            <div className="metric-label mb-3">Rolling 12-Month Market Beta</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={rbChartData} margin={{ top: 5, right: 10, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
                <XAxis
                  dataKey="date"
                  tickFormatter={v => v?.slice(0, 7)}
                  tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  interval={Math.floor(rbChartData.length / 6)}
                />
                <YAxis tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
                <Tooltip
                  contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 10 }}
                />
                <ReferenceLine y={1} stroke={colors.border} strokeDasharray="4 4" />
                {rbAssets.slice(0, 5).map((a, i) => (
                  <Line
                    key={a}
                    type="monotone"
                    dataKey={TICKER_LABELS[a] ?? a}
                    stroke={CHART_SERIES[i % CHART_SERIES.length]}
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
