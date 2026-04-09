import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null, info: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    this.setState({ info })
    console.error('[ErrorBoundary]', error, info)
  }

  handleReset = () => {
    this.setState({ error: null, info: null })
  }

  render() {
    if (this.state.error) {
      const msg = this.state.error?.message ?? String(this.state.error)
      return (
        <div className="card border border-red/30 p-6 m-4 space-y-3">
          <div className="text-red font-mono text-sm font-semibold">
            Component Error
          </div>
          <div className="font-mono text-xs text-muted bg-bg rounded p-3 overflow-x-auto">
            {msg}
          </div>
          {this.state.info?.componentStack && (
            <details className="text-xs text-muted">
              <summary className="cursor-pointer hover:text-text">Stack trace</summary>
              <pre className="mt-2 overflow-x-auto font-mono text-[10px] leading-relaxed">
                {this.state.info.componentStack}
              </pre>
            </details>
          )}
          <button
            onClick={this.handleReset}
            className="text-xs font-sans text-cyan border border-cyan/30 rounded px-3 py-1 hover:bg-cyan/10 transition-colors"
          >
            Retry
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
