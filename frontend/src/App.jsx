import { useState } from 'react'
import Layout from './components/Layout/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './components/Dashboard/Dashboard'
import ClientProfile from './components/ClientProfile/ClientProfile'
import AssetUniverse from './components/AssetUniverse/AssetUniverse'
import EfficientFrontier from './components/EfficientFrontier/EfficientFrontier'
import RegimeAnalysis from './components/RegimeAnalysis/RegimeAnalysis'
import VolatilityDynamics from './components/VolatilityDynamics/VolatilityDynamics'
import Simulation from './components/Simulation/Simulation'
import RiskAnalysis from './components/RiskAnalysis/RiskAnalysis'
import FactorAnalysis from './components/FactorAnalysis/FactorAnalysis'

const PAGES = {
  dashboard:    { label: 'Dashboard',         component: Dashboard },
  profile:      { label: 'Client Profile',    component: ClientProfile },
  assets:       { label: 'Asset Universe',    component: AssetUniverse },
  frontier:     { label: 'Efficient Frontier',component: EfficientFrontier },
  regime:       { label: 'Regime Analysis',   component: RegimeAnalysis },
  garch:        { label: 'Volatility (GARCH)',component: VolatilityDynamics },
  simulation:   { label: 'Simulation',        component: Simulation },
  risk:         { label: 'Risk Analysis',     component: RiskAnalysis },
  factor:       { label: 'Factor Analysis',   component: FactorAnalysis },
}

export default function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const Page = PAGES[activePage]?.component ?? Dashboard

  return (
    <Layout activePage={activePage} pages={PAGES} onNavigate={setActivePage}>
      <ErrorBoundary key={activePage}>
        <Page />
      </ErrorBoundary>
    </Layout>
  )
}
