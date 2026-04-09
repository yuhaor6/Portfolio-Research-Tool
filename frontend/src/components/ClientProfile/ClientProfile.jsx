import { useState, useCallback } from 'react'
import { useClientProfile } from '../../hooks/usePortfolioData'
import { SectionTitle, MetricCard, LoadingSkeleton, ErrorBanner } from '../shared'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts'
import { colors, chartColors } from '../../theme/tokens'

const fmt$ = v => `$${Math.round(v).toLocaleString()}`
const fmtK = v => `$${(v / 1000).toFixed(0)}k`

function SliderField({ label, value, min, max, step, onChange, format }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-xs text-muted font-sans">{label}</span>
        <span className="text-xs text-cyan font-mono">{format ? format(value) : value}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none bg-border cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3.5
          [&::-webkit-slider-thumb]:w-3.5 [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-cyan"
      />
      <div className="flex justify-between text-[10px] text-muted/60 font-mono">
        <span>{format ? format(min) : min}</span>
        <span>{format ? format(max) : max}</span>
      </div>
    </div>
  )
}

export default function ClientProfile() {
  const { data: serverProfile, loading, error } = useClientProfile()
  const [profile, setProfile] = useState(null)
  const [recalcResult, setRecalcResult] = useState(null)
  const [recalcLoading, setRecalcLoading] = useState(false)
  const [recalcError, setRecalcError] = useState(null)

  // Use server profile as initial values once loaded (only once)
  const effectiveProfile = profile ?? serverProfile ?? {
    starting_salary: 95000,
    salary_growth_rate: 0.04,
    annual_expenses: 55000,
    goal_amount: 1000000,
    investment_horizon_years: 10,
    initial_investment: 35000,
    loan_balance: 40000,
    loan_rate: 0.065,
    tax_rate: 0.28,
    emergency_fund_months: 6,
  }

  const setField = useCallback((key, val) => {
    setProfile(prev => ({ ...(prev ?? effectiveProfile), [key]: val }))
  }, [effectiveProfile])

  const handleRecalculate = async () => {
    setRecalcLoading(true)
    setRecalcError(null)
    try {
      const res = await fetch('/api/recalculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(effectiveProfile),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const json = await res.json()
      setRecalcResult(json)
    } catch (e) {
      setRecalcError(e.message)
    } finally {
      setRecalcLoading(false)
    }
  }

  if (loading) return <LoadingSkeleton rows={4} />
  if (error)   return <ErrorBanner message={error} />

  const p = effectiveProfile
  const annualSavings = Math.max(0, p.starting_salary * (1 - p.tax_rate) - p.annual_expenses)
  const loanMonthlyPayment = p.loan_balance > 0
    ? (p.loan_balance * (p.loan_rate / 12)) / (1 - Math.pow(1 + p.loan_rate / 12, -120))
    : 0
  const netSavings = annualSavings - loanMonthlyPayment * 12

  const savingsScheduleData = recalcResult?.savings_schedule ?? serverProfile?.savings_schedule ?? []
  const scheduleChartData = savingsScheduleData.map(row => ({
    year:        row.year ?? row.Year,
    salary:      row.gross_salary ?? row['Gross Salary'] ?? 0,
    contribution: row.monthly_contribution != null
      ? (row.monthly_contribution * 12)
      : row['Annual Contribution'] ?? 0,
  }))

  return (
    <div className="space-y-6">
      <SectionTitle sub="Configure your financial profile — changes feed into all Monte Carlo simulations">
        Client Profile
      </SectionTitle>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sliders */}
        <div className="card-glow p-5 space-y-5">
          <div className="metric-label">Income & Expenses</div>
          <SliderField
            label="Starting Salary"
            value={p.starting_salary}
            min={40000} max={300000} step={5000}
            onChange={v => setField('starting_salary', v)}
            format={fmt$}
          />
          <SliderField
            label="Annual Salary Growth"
            value={p.salary_growth_rate}
            min={0.01} max={0.10} step={0.005}
            onChange={v => setField('salary_growth_rate', v)}
            format={v => `${(v * 100).toFixed(1)}%`}
          />
          <SliderField
            label="Annual Expenses"
            value={p.annual_expenses}
            min={20000} max={200000} step={2500}
            onChange={v => setField('annual_expenses', v)}
            format={fmt$}
          />
          <SliderField
            label="Tax Rate"
            value={p.tax_rate}
            min={0.10} max={0.45} step={0.01}
            onChange={v => setField('tax_rate', v)}
            format={v => `${(v * 100).toFixed(0)}%`}
          />

          <div className="metric-label pt-2 border-t border-border">Wealth & Goals</div>
          <SliderField
            label="Goal Amount"
            value={p.goal_amount}
            min={200000} max={5000000} step={50000}
            onChange={v => setField('goal_amount', v)}
            format={fmt$}
          />
          <SliderField
            label="Initial Investment"
            value={p.initial_investment}
            min={0} max={500000} step={5000}
            onChange={v => setField('initial_investment', v)}
            format={fmt$}
          />
          <SliderField
            label="Investment Horizon (years)"
            value={p.investment_horizon_years}
            min={5} max={40} step={1}
            onChange={v => setField('investment_horizon_years', v)}
            format={v => `${v} yr`}
          />

          <div className="metric-label pt-2 border-t border-border">Loan & Emergency Fund</div>
          <SliderField
            label="Loan Balance"
            value={p.loan_balance}
            min={0} max={200000} step={5000}
            onChange={v => setField('loan_balance', v)}
            format={fmt$}
          />
          <SliderField
            label="Loan Rate"
            value={p.loan_rate}
            min={0.02} max={0.15} step={0.005}
            onChange={v => setField('loan_rate', v)}
            format={v => `${(v * 100).toFixed(1)}%`}
          />
          <SliderField
            label="Emergency Fund (months)"
            value={p.emergency_fund_months}
            min={1} max={12} step={1}
            onChange={v => setField('emergency_fund_months', v)}
            format={v => `${v} mo`}
          />

          <button
            onClick={handleRecalculate}
            disabled={recalcLoading}
            className="w-full mt-2 py-2 rounded bg-cyan/20 border border-cyan text-cyan text-sm font-mono
              hover:bg-cyan/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {recalcLoading ? 'Recalculating…' : 'Recalculate Projections'}
          </button>
          {recalcError && <div className="text-xs text-red font-mono mt-1">{recalcError}</div>}
        </div>

        {/* Right panel: quick metrics + savings chart */}
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Net Annual Savings"
              value={fmtK(Math.max(0, netSavings))}
              sub="After tax, expenses, loan"
              color={netSavings > 0 ? 'green' : 'red'}
            />
            <MetricCard
              label="Monthly Loan Payment"
              value={fmtK(loanMonthlyPayment * 12)}
              sub="10-yr amortisation"
              color="amber"
            />
            <MetricCard
              label="Goal"
              value={fmtK(p.goal_amount)}
              sub={`in ${p.investment_horizon_years} years`}
              color="cyan"
            />
            <MetricCard
              label="Starting Wealth"
              value={fmtK(p.initial_investment)}
              sub="Initial portfolio"
              color="text"
            />
          </div>

          {scheduleChartData.length > 0 && (
            <div className="card-glow p-4">
              <div className="metric-label mb-3">Projected Annual Contributions ($)</div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={scheduleChartData} margin={{ top: 5, right: 10, bottom: 20, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={colors.border} vertical={false} />
                  <XAxis
                    dataKey="year"
                    tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  />
                  <YAxis
                    tickFormatter={v => `$${(v / 1000).toFixed(0)}k`}
                    tick={{ fill: colors.muted, fontSize: 9, fontFamily: 'JetBrains Mono' }}
                  />
                  <Tooltip
                    formatter={v => [fmt$(v), 'Contribution']}
                    contentStyle={{ background: colors.surface, border: `1px solid ${colors.border}`, fontSize: 11 }}
                  />
                  <Bar dataKey="contribution" radius={[3, 3, 0, 0]} fill={colors.cyan} opacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {scheduleChartData.length > 0 && (
            <div className="card-glow p-4">
              <div className="metric-label mb-3">Savings Schedule</div>
              <div className="overflow-x-auto max-h-52 overflow-y-auto">
                <table className="w-full text-xs font-mono">
                  <thead className="sticky top-0 bg-surface">
                    <tr className="border-b border-border">
                      <th className="text-left py-1.5 text-muted">Year</th>
                      <th className="text-right py-1.5 text-muted">Gross Salary</th>
                      <th className="text-right py-1.5 text-muted">Contribution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scheduleChartData.map(row => (
                      <tr key={row.year} className="border-b border-border/30">
                        <td className="py-1 text-muted">{row.year}</td>
                        <td className="py-1 text-right text-text">{fmt$(row.salary)}</td>
                        <td className="py-1 text-right text-cyan">{fmt$(row.contribution)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
