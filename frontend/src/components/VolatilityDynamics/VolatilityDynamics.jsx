import { useState, useMemo } from 'react'
import { useGarch } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, ReferenceLine, BarChart, Bar, Cell,
} from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const CHART_SERIES = chartColors.series ?? Object.values(chartColors).filter(Array.isArray).flat()

const TICKER_LABELS = {
  IVV: 'IVV', QUAL: 'QUAL', USMV: 'USMV', VEA: 'VEA', VWO: 'VWO',
  AGG: 'AGG', SHV: 'SHV', TIP: 'TIP', VNQ: 'VNQ', GLD: 'GLD',
  'BTC-USD': 'BTC', 'ETH-USD': 'ETH',
}

function corrColor(v) {
  // -1 → red, 0 → surface, +1 → cyan
  if (v == null) return colors.surface
  const abs = Math.abs(v)
  if (v > 0) return `rgba(0, 212, 255, ${0.15 + abs * 0.7})` // cyan tint
  return `rgba(255, 68, 68, ${0.15 + abs * 0.7})`             // red tint
}

function DccHeatmap({ tickers, matrix }) {
  if (!tickers?.length || !matrix?.length) return <div className="text-xs text-muted">No DCC data available.</div>

  return (
    <div className="overflow-x-auto">
      <table className="text-xs font-mono select-none">
        <thead>
          <tr>
            <th className="w-10" />
            {tickers.map(t => (
              <th key={t} className="px-1 py-1 text-center text-muted" style={{ minWidth: 42 }}>
                {TICKER_LABELS[t] ?? t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={tickers[i]}>
              <td className="pr-2 text-muted text-right py-0.5">{TICKER_LABELS[tickers[i]] ?? tickers[i]}</td>
              {row.map((v, j) => (
                <td
                  key={j}
                  className="text-center py-1 px-1 rounded"
                  style={{ backgroundColor: corrColor(v), color: v < -0.5 || v > 0.5 ? '#fff' : colors.text }}
                  title={`${tickers[i]} / ${tickers[j]}: ${typeof v === 'number' ? v.toFixed(3) : '—'}`}
                >
                  {i === j ? '1.00' : (typeof v === 'number' ? v.toFixed(2) : '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function VolatilityDynamics() {
  const { data, loading, error } = useGarch()
  const [selectedAsset, setSelectedAsset] = useState(null)
  const [dccDateIdx, setDccDateIdx] = useState(null)

  if (loading) return <LoadingSkeleton rows={5} />
  if (error)   return <ErrorBanner message={error} />

  const {
    conditional_vol = {},
    tickers: allTickers = [],
    forecasts = {},
    dcc_tickers = [],
    dcc_correlation = {},
  } = data

  // Support older key names from server
  const condVol = conditional_vol

  const assets = allTickers.length ? allTickers : Object.keys(condVol)
  const active  = selectedAsset || assets[0]

  // Build vol time series for active asset
  const volEntry = condVol[active] ?? {}
  const volDates = volEntry.dates ?? []
  const volValues = volEntry.vol ?? []
  const volSeries = volDates.map((date, i) => ({ date, vol: +(volValues[i] * 100).toFixed(2) }))

  // Current vol snapshot bar data
  const volBar = assets.filter(a => condVol[a]?.current != null).map((a, i) => ({
    asset: TICKER_LABELS[a] ?? a,
    vol:   +((condVol[a].current ?? 0) * 100).toFixed(1),
    fill:  CHART_SERIES[i % CHART_SERIES.length],
  }))

  // DCC slider
  const dccDates = Object.keys(dcc_correlation).sort()
  const effectiveDccIdx = dccDateIdx ?? (dccDates.length - 1)
  const dccDate  = dccDates[effectiveDccIdx] ?? ''
  const dccMatrix = dcc_correlation[dccDate] ?? []

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    return (
      <div className="card p-2 text-xs font-mono border border-border">
        <div className="text-muted">{label}</div>
        <div className="text-cyan">{TICKER_LABELS[active] ?? active}: {payload[0]?.value?.toFixed(1)}%</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <SectionTitle sub="ARCH/GARCH(1,1) per-asset conditional volatility · rolling DCC correlations">
        Volatility Dynamics
      </SectionTitle>

      {/* Asset selector */}
      <div className="flex flex-wrap gap-2">
        {assets.map((a, i) => (
          <button
            key={a}
            onClick={() => setSelectedAsset(a)}
            className={`px-3 py-1 rounded text-xs font-mono border transition-colors ${
              (selectedAsset ?? assets[0]) === a
                ? 'bg-cyan/10 border-cyan text-cyan'
                : 'border-border text-muted hover:text-text'
            }`}
          >
            {TICKER_LABELS[a] ?? a}
          </button>
        ))}
      </div>

      {/* Summary cards for selected asset */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Current Ann. Vol"    value={`${((condVol[active]?.current ?? 0) * 100).toFixed(1)}%`}  sub={active}               color="cyan"  />
        <MetricCard label="Historical Avg"      value={`${((condVol[active]?.hist_avg ?? 0) * 100).toFixed(1)}%`} sub="Since 2005"            color="text"  />
        <MetricCard label="Hist. Percentile"    value={`${(condVol[active]?.percentile ?? 0).toFixed(0)}%`}       sub="Current vol rank"      color="amber" />
        <MetricCard label="12M Forecast"        value={`${((forecasts[active]?.at(-1) ?? 0) * 100).toFixed(1)}%`} sub="GARCH(1,1) step-ahead" color="text"  />
      </div>

      {/* Conditional vol time series */}
      <div className="card-glow p-4">
        <div className="text-xs text-muted font-sans mb-3">
          Conditional annualised volatility — {TICKER_LABELS[active] ?? active}
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={volSeries} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis dataKey="date" tickFormatter={v => v?.slice(0, 7)} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} interval={Math.max(1, Math.floor(volSeries.length / 8))} />
            <YAxis tickFormatter={v => `${v}%`} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={+(condVol[active]?.hist_avg ?? 0) * 100} stroke={colors.amber} strokeDasharray="4 4" label={{ value: 'Avg', position: 'right', fill: colors.amber, fontSize: 9 }} />
            <Line type="monotone" dataKey="vol" stroke={colors.cyan} strokeWidth={1.5} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Current vol cross-section */}
      {volBar.length > 0 && (
        <div className="card-glow p-4">
          <div className="text-xs text-muted font-sans mb-3">Current GARCH-estimated annual volatility — cross section</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={[...volBar].sort((a, b) => b.vol - a.vol)} margin={{ top: 5, right: 20, bottom: 30, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
              <XAxis dataKey="asset" tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }} />
              <YAxis tickFormatter={v => `${v}%`} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
              <Tooltip formatter={v => [`${v}%`, 'Ann. Vol']} contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }} />
              <Bar dataKey="vol" radius={[3, 3, 0, 0]}>
                {[...volBar].sort((a, b) => b.vol - a.vol).map(entry => (
                  <Cell key={entry.asset} fill={entry.fill} opacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* DCC Correlation Heatmap with date slider */}
      {dccDates.length > 0 && (
        <div className="card-glow p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="metric-label">DCC Rolling Correlation — {dccDate}</div>
            <div className="text-xs text-muted font-mono">{effectiveDccIdx + 1} / {dccDates.length}</div>
          </div>
          <input
            type="range"
            min={0}
            max={dccDates.length - 1}
            value={effectiveDccIdx}
            onChange={e => setDccDateIdx(Number(e.target.value))}
            className="w-full h-1.5 rounded-full appearance-none bg-border cursor-pointer mb-4
              [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3.5
              [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-cyan"
          />
          <DccHeatmap tickers={dcc_tickers} matrix={dccMatrix} />
          <div className="text-[10px] text-muted mt-3">
            36-month rolling window DCC proxy · cyan = positive correlation · red = negative
          </div>
        </div>
      )}

      {/* GARCH forecast term structure */}
      {forecasts[active]?.length > 0 && (
        <div className="card-glow p-4">
          <div className="text-xs text-muted font-sans mb-3">
            12-month GARCH(1,1) volatility term structure — {TICKER_LABELS[active] ?? active}
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={forecasts[active].map((v, i) => ({ month: `M+${i + 1}`, vol: +(v * 100).toFixed(2) }))} margin={{ top: 5, right: 20, bottom: 20, left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis dataKey="month" tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
              <YAxis tickFormatter={v => `${v}%`} tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }} />
              <Tooltip formatter={v => [`${v}%`, 'Forecast Vol']} contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }} />
              <Line type="monotone" dataKey="vol" stroke={colors.amber} strokeWidth={2} dot={{ r: 3, fill: colors.amber }} />
              <ReferenceLine
                y={+(condVol[active]?.current ?? 0) * 100}
                stroke={colors.cyan} strokeDasharray="4 4"
                label={{ value: 'Current', position: 'right', fill: colors.cyan, fontSize: 9 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}


