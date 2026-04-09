import { useState } from 'react'
import { useAssetStats } from '../../hooks/usePortfolioData'
import { SectionTitle, LoadingSkeleton, ErrorBanner, Toggle } from '../shared'
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LineChart, Line, Legend,
} from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const CATEGORIES = {
  equity:       { label: 'Equity',       color: '#00d4ff' },
  fixed_income: { label: 'Fixed Income', color: '#ff9f43' },
  alternatives: { label: 'Alternatives', color: '#00c853' },
  crypto:       { label: 'Crypto',       color: '#b388ff' },
}

const ASSET_META = {
  IVV:     { category: 'equity' },
  QUAL:    { category: 'equity' },
  USMV:    { category: 'equity' },
  VEA:     { category: 'equity' },
  VWO:     { category: 'equity' },
  AGG:     { category: 'fixed_income' },
  SHV:     { category: 'fixed_income' },
  TIP:     { category: 'fixed_income' },
  VNQ:     { category: 'alternatives' },
  GLD:     { category: 'alternatives' },
  'BTC-USD': { category: 'crypto' },
  'ETH-USD': { category: 'crypto' },
}

function CorrelationHeatmap({ corr }) {
  const tickers = Object.keys(corr)
  const n = tickers.length
  const cellSize = Math.min(44, Math.floor(600 / n))

  return (
    <div className="overflow-x-auto">
      <div style={{ display: 'grid', gridTemplateColumns: `${cellSize + 8}px repeat(${n}, ${cellSize}px)` }}>
        {/* Header row */}
        <div />
        {tickers.map(t => (
          <div key={t}
            className="text-center font-mono text-xs text-muted truncate pb-1"
            style={{ fontSize: '10px', writingMode: 'vertical-rl', transform: 'rotate(180deg)', height: cellSize + 12 }}
          >
            {t}
          </div>
        ))}
        {/* Data rows */}
        {tickers.map(row => (
          <>
            <div key={row + '_label'}
              className="font-mono text-xs text-muted truncate pr-2 flex items-center justify-end"
              style={{ fontSize: '10px', height: cellSize }}
            >
              {row}
            </div>
            {tickers.map(col => {
              const val = corr[row]?.[col] ?? 0
              const abs = Math.abs(val)
              const r = val >= 0
                ? `rgba(0, 212, 255, ${abs * 0.8})`
                : `rgba(255, 68, 68, ${abs * 0.8})`
              return (
                <div
                  key={col}
                  title={`${row}/${col}: ${val.toFixed(3)}`}
                  style={{ width: cellSize, height: cellSize, backgroundColor: r }}
                  className="border border-bg flex items-center justify-center cursor-pointer"
                >
                  {cellSize >= 36 && (
                    <span className="font-mono text-text/80" style={{ fontSize: '9px' }}>
                      {val.toFixed(2)}
                    </span>
                  )}
                </div>
              )
            })}
          </>
        ))}
      </div>
    </div>
  )
}

function AssetCard({ ticker, stat }) {
  const cat = ASSET_META[ticker]?.category ?? 'equity'
  const color = CATEGORIES[cat]?.color ?? '#00d4ff'
  return (
    <div className="card p-3 hover:border-border/80 transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-mono text-sm font-semibold text-text">{ticker}</div>
          <div
            className="text-xs font-sans mt-0.5 px-1.5 py-0.5 rounded inline-block"
            style={{ backgroundColor: color + '1a', color }}
          >
            {CATEGORIES[cat]?.label}
          </div>
        </div>
        <div className="text-right">
          <div className="font-mono text-sm font-semibold"
            style={{ color: stat.ann_return >= 0 ? '#00c853' : '#ff4444' }}>
            {(stat.ann_return * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-muted font-mono">ann. return</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs font-mono">
        <div>
          <div className="text-muted">Vol</div>
          <div className="text-text">{(stat.ann_vol * 100).toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-muted">Sharpe</div>
          <div className="text-text">{stat.sharpe.toFixed(2)}</div>
        </div>
        <div>
          <div className="text-muted">Max DD</div>
          <div className="text-red">{(stat.max_drawdown * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  )
}

export default function AssetUniverse() {
  const { data, loading, error } = useAssetStats()
  const [view, setView] = useState('cards')

  if (loading) return <LoadingSkeleton rows={6} />
  if (error)   return <ErrorBanner message={error} />

  const { stats, correlation } = data
  const tickers = Object.keys(stats)

  // Build scatter data
  const scatterData = tickers.map(t => ({
    ticker: t,
    x: stats[t].ann_vol * 100,
    y: stats[t].ann_return * 100,
    sharpe: stats[t].sharpe,
    category: ASSET_META[t]?.category ?? 'equity',
  }))

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="card p-2 text-xs font-mono border border-border">
        <div className="text-cyan font-semibold">{d.ticker}</div>
        <div>Vol: {d.x.toFixed(1)}% | Return: {d.y.toFixed(1)}%</div>
        <div>Sharpe: {d.sharpe.toFixed(2)}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* View toggle */}
      <div className="flex items-center justify-between">
        <SectionTitle sub="12-asset universe · 2017–2025">Asset Universe</SectionTitle>
        <Toggle
          options={[
            { label: 'Cards',  value: 'cards' },
            { label: 'Scatter',value: 'scatter' },
            { label: 'Heatmap',value: 'heatmap' },
          ]}
          value={view}
          onChange={setView}
        />
      </div>

      {view === 'cards' && (
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {tickers.map(t => (
            <AssetCard key={t} ticker={t} stat={stats[t]} />
          ))}
        </div>
      )}

      {view === 'scatter' && (
        <div className="card-glow p-4">
          <div className="text-xs text-muted font-sans mb-3">Risk/Return space (annualized, 2017–2025)</div>
          <ResponsiveContainer width="100%" height={380}>
            <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
              <XAxis
                type="number" dataKey="x" name="Vol"
                label={{ value: 'Annualized Vol (%)', position: 'bottom', fill: colors.muted, fontSize: 11 }}
                tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }}
              />
              <YAxis
                type="number" dataKey="y" name="Return"
                label={{ value: 'Ann. Return (%)', angle: -90, position: 'left', fill: colors.muted, fontSize: 11 }}
                tick={{ fill: colors.muted, fontSize: 10, fontFamily: 'JetBrains Mono' }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Scatter data={scatterData} name="Assets">
                {scatterData.map(d => (
                  <Cell
                    key={d.ticker}
                    fill={CATEGORIES[d.category]?.color ?? '#00d4ff'}
                    fillOpacity={0.85}
                  />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-2 justify-center">
            {Object.entries(CATEGORIES).map(([k, v]) => (
              <div key={k} className="flex items-center gap-1.5 text-xs text-muted">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: v.color }} />
                {v.label}
              </div>
            ))}
          </div>
        </div>
      )}

      {view === 'heatmap' && (
        <div className="card-glow p-4">
          <div className="text-xs text-muted font-sans mb-3">
            Pearson correlation matrix · cyan = positive · red = negative
          </div>
          <CorrelationHeatmap corr={correlation} />
        </div>
      )}
    </div>
  )
}
