import { useState } from 'react'
import { useEfficientFrontier } from '../../hooks/usePortfolioData'
import { SectionTitle, LoadingSkeleton, ErrorBanner, Toggle, MetricCard } from '../shared'
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine, Line, LineChart, LabelList } from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const CHART_SERIES = chartColors.series ?? []

// Capital Allocation Line: points from (0, rf) → tangency → beyond
function calPoints(rf_ann, tang_vol, tang_ret, maxVol) {
  const slope = (tang_ret - rf_ann) / tang_vol
  const pts = []
  for (let v = 0; v <= maxVol * 1.35; v += maxVol * 0.02) {
    pts.push({ x: +v.toFixed(2), y: +(rf_ann + slope * v).toFixed(2) })
  }
  return pts
}

export default function EfficientFrontier() {
  const [universe, setUniverse] = useState('12')
  const [selectedPoint, setSelectedPoint] = useState(null)
  const { data, loading, error } = useEfficientFrontier(universe)

  if (loading) return <LoadingSkeleton rows={4} />
  if (error)   return <ErrorBanner message={error} />

  const { frontier, tangency, min_var, assets, tickers } = data
  const RF_ANN = 0.04 * 100  // 4% annualised, in pct units

  // Build scatter: frontier dots
  const frontierDots = (frontier ?? []).map((pt, i) => ({
    x:      +(pt.ann_vol * 100).toFixed(2),
    y:      +(pt.ann_return * 100).toFixed(2),
    sharpe: pt.sharpe,
    weights: pt.weights,
    idx:    i,
    type:   'frontier',
  }))

  const assetDots = Object.entries(assets ?? {}).map(([t, a]) => ({
    x:      +(a.ann_vol * 100).toFixed(2),
    y:      +(a.ann_return * 100).toFixed(2),
    ticker: t,
    type:   'asset',
  }))

  const tangencyDot  = tangency ? [{ x: +(tangency.ann_vol * 100).toFixed(2), y: +(tangency.ann_return * 100).toFixed(2), sharpe: tangency.sharpe, type: 'tangency' }] : []
  const minVarDot    = min_var  ? [{ x: +(min_var.ann_vol * 100).toFixed(2),  y: +(min_var.ann_return * 100).toFixed(2),  type: 'minvar'   }] : []

  const maxVol = Math.max(...frontierDots.map(d => d.x), ...assetDots.map(d => d.x), 5)
  const calLine = tangency ? calPoints(RF_ANN, tangency.ann_vol * 100, tangency.ann_return * 100, maxVol) : []

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    if (d.type === 'asset') {
      return (
        <div className="card p-2 text-xs font-mono border border-border">
          <div className="text-amber font-semibold">{d.ticker}</div>
          <div>Vol: {d.x.toFixed(1)}%  Ret: {d.y.toFixed(1)}%</div>
        </div>
      )
    }
    if (d.type === 'minvar') {
      return (
        <div className="card p-2 text-xs font-mono border border-border">
          <div className="text-purple-400">Min Variance</div>
          <div>Vol: {d.x.toFixed(1)}%  Ret: {d.y.toFixed(1)}%</div>
        </div>
      )
    }
    return (
      <div className="card p-2 text-xs font-mono border border-border">
        <div className="text-cyan">{d.type === 'tangency' ? '★ Tangency' : 'Frontier'}</div>
        <div>Vol: {d.x.toFixed(1)}%  Ret: {d.y.toFixed(1)}%</div>
        {d.sharpe != null && <div>Sharpe: {d.sharpe.toFixed(3)}</div>}
        {d.type === 'tangency' && <div className="text-muted text-[10px] mt-1">Click to pin weights</div>}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle sub="No short-selling · max 5% crypto · CAL drawn through tangency portfolio">
          Efficient Frontier
        </SectionTitle>
        <Toggle
          options={[
            { label: '3-Asset',  value: '3' },
            { label: '5-Asset',  value: '5' },
            { label: '12-Asset', value: '12' },
          ]}
          value={universe}
          onChange={v => { setUniverse(v); setSelectedPoint(null) }}
        />
      </div>

      {tangency && (
        <div className="grid grid-cols-3 gap-4">
          <MetricCard label="Tangency Sharpe"  value={tangency.sharpe.toFixed(3)}                     color="cyan"  />
          <MetricCard label="Tangency Return"  value={`${(tangency.ann_return * 100).toFixed(1)}%`}   color="green" />
          <MetricCard label="Tangency Vol"     value={`${(tangency.ann_vol * 100).toFixed(1)}%`}      color="amber" />
        </div>
      )}

      <div className="card-glow p-4">
        <div className="text-xs text-muted font-sans mb-3 flex items-center gap-4">
          <span><span className="text-cyan font-semibold">—</span> Frontier points</span>
          <span><span className="text-amber font-semibold">●</span> Individual assets</span>
          <span><span className="text-cyan font-semibold">★</span> Tangency</span>
          <span><span className="text-muted font-semibold">- -</span> CAL (Risk-Free to Tangency)</span>
        </div>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 50 }}>
            <XAxis
              type="number" dataKey="x" name="Vol"
              domain={[0, 'auto']}
              label={{ value: 'Annualized Volatility (%)', position: 'insideBottom', offset: -12, fill: colors.muted, fontSize: 11 }}
              tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }}
            />
            <YAxis
              type="number" dataKey="y" name="Return"
              label={{ value: 'Annualized Return (%)', angle: -90, position: 'insideLeft', fill: colors.muted, fontSize: 11 }}
              tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* CAL: standalone line scatter in line mode */}
            <Scatter data={calLine} name="CAL" line={{ stroke: colors.cyan, strokeWidth: 1, strokeDasharray: '6 3' }} shape={() => null} />

            {/* Efficient Frontier */}
            <Scatter data={frontierDots} onClick={pt => setSelectedPoint(pt)} name="Frontier" line={{ stroke: colors.cyan, strokeWidth: 1.5 }}>
              {frontierDots.map((d, i) => (
                <Cell key={i} fill={colors.cyan} fillOpacity={0.35} r={2.5} cursor="pointer" />
              ))}
            </Scatter>

            {/* Min Variance */}
            {minVarDot.length > 0 && (
              <Scatter data={minVarDot} name="MinVar">
                <Cell fill="#b388ff" stroke="#b388ff" strokeWidth={2} r={7} />
              </Scatter>
            )}

            {/* Tangency */}
            {tangencyDot.length > 0 && (
              <Scatter data={tangencyDot} name="Tangency" onClick={() => setSelectedPoint(null)}>
                <Cell fill={colors.amber} stroke="#fff" strokeWidth={2} r={9} />
              </Scatter>
            )}

            {/* Individual assets */}
            <Scatter data={assetDots} name="Assets">
              {assetDots.map((d, i) => (
                <Cell key={i} fill={CHART_SERIES[i % CHART_SERIES.length]} fillOpacity={0.9} r={5} />
              ))}
              <LabelList dataKey="ticker" position="top" style={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Tangency weights */}
      {tangency && (
        <div className="card-glow p-4">
          <div className="metric-label mb-3">
            {selectedPoint ? `Frontier Point — Vol: ${selectedPoint.x?.toFixed(1)}%  Ret: ${selectedPoint.y?.toFixed(1)}%  Sharpe: ${selectedPoint.sharpe?.toFixed(3)}` : `Tangency Portfolio Weights · ${universe}-Asset Universe`}
          </div>
          <div className="grid grid-cols-3 lg:grid-cols-6 gap-3">
            {Object.entries((selectedPoint?.weights ? Object.fromEntries(tickers.map((t, i) => [t, selectedPoint.weights[i] ?? 0])) : tangency.weights))
              .filter(([, w]) => w > 0.005)
              .sort(([, a], [, b]) => b - a)
              .map(([ticker, w]) => (
                <div key={ticker} className="text-center">
                  <div className="text-xs text-muted font-mono mb-1">{ticker}</div>
                  <div className="h-16 w-full rounded-sm relative" style={{ backgroundColor: '#1e1e2a' }}>
                    <div
                      className="absolute bottom-0 left-0 right-0 rounded-sm transition-all duration-300"
                      style={{ height: `${w * 100}%`, backgroundColor: '#00d4ff', opacity: 0.8 }}
                    />
                  </div>
                  <div className="font-mono text-xs text-cyan mt-1">{(w * 100).toFixed(1)}%</div>
                </div>
              ))}
          </div>
          {selectedPoint && (
            <button onClick={() => setSelectedPoint(null)} className="mt-3 text-xs text-muted hover:text-cyan font-mono transition-colors">
              ← Back to tangency weights
            </button>
          )}
        </div>
      )}
    </div>
  )
}
