// Shared reusable components
import { useEffect, useRef, useState } from 'react'

/**
 * Parses a display string like "12.34%" or "$1,234" into { num, prefix, suffix }.
 * Returns null if value is not numeric.
 */
function parseNumericValue(val) {
  if (typeof val !== 'string' && typeof val !== 'number') return null
  const str = String(val).trim()
  const match = str.match(/^([^0-9-]*)(-?[\d,]+(?:\.\d+)?)([^0-9]*)$/)
  if (!match) return null
  const num = parseFloat(match[2].replace(/,/g, ''))
  if (isNaN(num)) return null
  return { num, prefix: match[1], suffix: match[3], decimals: (match[2].split('.')[1] ?? '').length }
}

function formatNum(num, decimals) {
  if (decimals === 0) return Math.round(num).toLocaleString()
  return num.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

/**
 * Hook: smoothly animates a numeric value when it changes.
 * Returns the display string with identical prefix/suffix formatting.
 */
function useAnimatedValue(value, duration = 600) {
  const parsed = parseNumericValue(value)
  const [display, setDisplay] = useState(value)
  const rafRef = useRef(null)
  const prevRef = useRef(parsed?.num ?? null)

  useEffect(() => {
    if (!parsed) { setDisplay(value); prevRef.current = null; return }
    const from = prevRef.current ?? parsed.num
    const to = parsed.num
    prevRef.current = to
    if (from === to) { setDisplay(value); return }

    const start = performance.now()
    function step(now) {
      const t = Math.min((now - start) / duration, 1)
      const ease = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t // ease-in-out quad
      const current = from + (to - from) * ease
      setDisplay(`${parsed.prefix}${formatNum(current, parsed.decimals)}${parsed.suffix}`)
      if (t < 1) rafRef.current = requestAnimationFrame(step)
    }
    cancelAnimationFrame(rafRef.current)
    rafRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(rafRef.current)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return display
}

export function MetricCard({ label, value, sub, color = 'cyan', footer }) {
  const colorMap = {
    cyan:  'text-cyan',
    amber: 'text-amber',
    green: 'text-green',
    red:   'text-red',
    text:  'text-text',
  }
  const animated = useAnimatedValue(value)
  return (
    <div className="card-glow p-4 flex flex-col gap-1">
      <div className="metric-label">{label}</div>
      <div className={`font-mono text-2xl font-semibold ${colorMap[color] || 'text-cyan'}`}>
        {animated}
      </div>
      {sub && <div className="text-xs text-muted font-mono">{sub}</div>}
      {footer && <div className="text-xs text-muted font-sans mt-1">{footer}</div>}
    </div>
  )
}

export function SectionTitle({ children, sub }) {
  return (
    <div className="mb-4">
      <h2 className="font-sans font-semibold text-text text-base">{children}</h2>
      {sub && <p className="text-xs text-muted font-sans mt-0.5">{sub}</p>}
    </div>
  )
}

export function LoadingSkeleton({ rows = 3 }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 bg-surface rounded-lg animate-pulse"
          style={{ opacity: 1 - i * 0.2 }}
        />
      ))}
    </div>
  )
}

export function ErrorBanner({ message }) {
  return (
    <div className="card border-red/30 p-4 text-red text-sm font-mono">
      Error: {message}
      <div className="text-xs text-muted mt-1 font-sans">
        Make sure the PortfolioLab API server is running on http://localhost:8000.
        Run <code className="text-amber">python run_all.py</code> first.
      </div>
    </div>
  )
}

export function Toggle({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-border overflow-hidden">
      {options.map(({ label, value: v }) => (
        <button
          key={v}
          onClick={() => onChange(v)}
          className={`px-3 py-1.5 text-xs font-sans font-medium transition-colors duration-100
            ${v === value
              ? 'bg-cyan text-bg'
              : 'bg-surface text-muted hover:text-text'
            }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export function DataTable({ columns, rows, keyField = 'strategy' }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="border-b border-border">
            {columns.map(col => (
              <th
                key={col.key}
                className="py-2 px-3 text-left text-muted font-sans uppercase tracking-wider text-xs"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={row[keyField] || i}
              className="border-b border-border/50 hover:bg-surface/50 transition-colors"
            >
              {columns.map(col => (
                <td key={col.key} className={`py-2.5 px-3 ${col.className || ''}`}>
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
