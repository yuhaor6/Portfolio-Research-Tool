// hooks/usePortfolioData.js — Fetch data from FastAPI backend

import { useState, useEffect, useCallback } from 'react'

const BASE_URL = '/api'

function useFetch(endpoint, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${BASE_URL}${endpoint}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const json = await res.json()
      setData(json)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [endpoint])

  useEffect(() => { fetchData() }, [fetchData, ...deps])

  return { data, loading, error, refetch: fetchData }
}

export function useAssetStats() {
  return useFetch('/asset-stats')
}

export function useClientProfile() {
  return useFetch('/client-profile')
}

export function useEfficientFrontier(universe = '12') {
  return useFetch(`/efficient-frontier?universe=${universe}`, [universe])
}

export function useRegime() {
  return useFetch('/regime')
}

export function useGarch() {
  return useFetch('/garch')
}

export function useSimulation(mode = 'bootstrap', strategy = 'tangency_12') {
  return useFetch(`/simulation?mode=${mode}&strategy=${strategy}`, [mode, strategy])
}

export function useComparison() {
  return useFetch('/comparison')
}

export function useRisk(strategy = 'tangency_12') {
  return useFetch(`/risk?strategy=${strategy}`, [strategy])
}

export function useFactor(strategy = 'tangency_12') {
  return useFetch(`/factor?strategy=${strategy}`, [strategy])
}

export function useSensitivity(param = 'window') {
  return useFetch(`/sensitivity?param=${param}`, [param])
}

export async function recalculate(profile) {
  const res = await fetch(`${BASE_URL}/recalculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  })
  if (!res.ok) {
    const err = await res.json()
    throw new Error(err.detail || 'Recalculation failed')
  }
  return res.json()
}
