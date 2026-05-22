import React, { useState, useEffect } from 'react'
import { API_BASE } from './utils/api'
import { useToast } from './components/Toast'
import yaml from 'js-yaml'
import './DSpyOptimizer.css'
import './DSpyOptimizerAboutStyles.css'
import './DSpyOptimizerAdditional.css'

export default function DSpyOptimizer() {
  const [status, setStatus] = useState({ status: 'loading', llm_provider: 'Loading...', optimizations: {}, available_types: [] })
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('analytics')

  // Optimization state
  const [optimizeResult, setOptimizeResult] = useState(null)
  const [isOptimizing, setIsOptimizing] = useState(false)
  const [optimizationHistory, setOptimizationHistory] = useState([])

  // Feedback state
  const [feedbackStats, setFeedbackStats] = useState(null)
  const [feedbackTrends, setFeedbackTrends] = useState([])

  // Test suite state
  const [testSuites, setTestSuites] = useState([])
  const [selectedTestSuite, setSelectedTestSuite] = useState(null)
  const [testResults, setTestResults] = useState(null)
  const [isGeneratingTests, setIsGeneratingTests] = useState(false)
  const [isRunningTests, setIsRunningTests] = useState(false)

  // Config state
  const [toolConfigs, setToolConfigs] = useState(null)
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(false)
  const [selectedToolConfig, setSelectedToolConfig] = useState(null)
  const [configHistory, setConfigHistory] = useState([])

  // Pattern analysis state
  const [patterns, setPatterns] = useState([])
  const [selectedPattern, setSelectedPattern] = useState(null)

  // UI state
  const [expandedTools, setExpandedTools] = useState({})
  const [expandedTests, setExpandedTests] = useState({})
  const [expandedPatterns, setExpandedPatterns] = useState({})
  const [expandedHistory, setExpandedHistory] = useState({})

  // History filters
  const [historyFilter, setHistoryFilter] = useState('all')
  const [historySearch, setHistorySearch] = useState('')

  // Call logs
  const [callLogs, setCallLogs] = useState(null)

  const { success, error: showError} = useToast()

  // Load all data on mount
  useEffect(() => {
    fetchStatus()
    fetchFeedbackStats()
    fetchTestSuites()
    fetchToolConfigs()
  }, [])

  const fetchStatus = async (force = false) => {
    // Skip if already loading, or already have status (unless force refresh)
    if (isLoading || (!force && status)) return

    setIsLoading(true)
    try {
      console.log('[DSPy] Fetching status from:', `${API_BASE}/dspy/status`)
      const response = await fetch(`${API_BASE}/dspy/status`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        timeout: 10000 // 10 second timeout
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      console.log('[DSPy] Status received:', data)
      setStatus(data)
    } catch (err) {
      console.error('[DSPy] Failed to fetch status:', err)
      showError(`Failed to fetch DSPy status: ${err.message}`)
      // Set a default status
      setStatus({
        status: 'ready',
        llm_provider: 'mock',
        optimizations: {},
        available_types: []
      })
    } finally {
      setIsLoading(false)
    }
  }

  const fetchToolConfigs = async () => {
    setIsLoadingConfigs(true)
    try {
      const response = await fetch('http://localhost:8001/configs')
      const data = await response.json()
      setToolConfigs(data.configs)
    } catch (err) {
      console.error('Failed to fetch tool configs:', err)
      showError('Failed to fetch tool configurations')
    } finally {
      setIsLoadingConfigs(false)
    }
  }

  const fetchCallLogs = async () => {
    try {
      const response = await fetch(`${API_BASE}/dspy/call-logs`)
      const data = await response.json()
      if (data.status === 'success') {
        setCallLogs(data.logs)
      }
    } catch (err) {
      console.error('Failed to fetch call logs:', err)
      showError('Failed to fetch call logs')
    }
  }

  const fetchTestSuites = async () => {
    try {
      const response = await fetch(`${API_BASE}/mcp/test-suites`)
      const data = await response.json()
      if (data.status === 'success') {
        setTestSuites(data.suites || [])
      }
    } catch (err) {
      console.error('Failed to fetch test suites:', err)
    }
  }

  const generateTestSuite = async (count = 5) => {
    setIsGeneratingTests(true)
    try {
      const response = await fetch(`${API_BASE}/mcp/test-suite/generate?count=${count}`, {
        method: 'POST'
      })
      const data = await response.json()
      if (data.status === 'success') {
        success(`Generated ${data.test_count} test cases in suite ${data.suite_id}`)
        await fetchTestSuites()
      } else {
        showError(data.message || 'Failed to generate test suite')
      }
    } catch (err) {
      console.error('Failed to generate test suite:', err)
      showError('Failed to generate test suite')
    } finally {
      setIsGeneratingTests(false)
    }
  }

  const runTestSuite = async (suiteId) => {
    setIsRunningTests(true)
    setSelectedTestSuite(suiteId)
    try {
      const response = await fetch(`${API_BASE}/mcp/test-suite/${suiteId}/run`, {
        method: 'POST'
      })
      const data = await response.json()
      setTestResults(data)
      if (data.success_rate >= 80) {
        success(`Test suite passed! ${data.passed}/${data.total_tests} tests successful`)
      } else {
        showError(`Test suite completed with ${data.success_rate.toFixed(1)}% success rate`)
      }
      await fetchTestSuites()
    } catch (err) {
      console.error('Failed to run test suite:', err)
      showError('Failed to run test suite')
    } finally {
      setIsRunningTests(false)
    }
  }

  const getTestResults = async (suiteId) => {
    try {
      const response = await fetch(`${API_BASE}/mcp/test-suite/${suiteId}/results`)
      const data = await response.json()
      setTestResults(data)
      setSelectedTestSuite(suiteId)
    } catch (err) {
      console.error('Failed to fetch test results:', err)
      showError('Failed to fetch test results')
    }
  }

  const toggleToolExpanded = (toolName) => {
    setExpandedTools(prev => ({
      ...prev,
      [toolName]: !prev[toolName]
    }))
  }

  const exportToolConfigs = () => {
    if (!toolConfigs) {
      showError('No configurations to export')
      return
    }

    const dataStr = JSON.stringify(toolConfigs, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `mcp-tool-configs-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    success('Tool configurations exported successfully!')
  }

  const exportOrchestratorConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/dspy/orchestrator-config`)
      const data = await response.json()

      if (data.status === 'success') {
        const dataStr = JSON.stringify(data.config, null, 2)
        const dataBlob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(dataBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `orchestrator-config-${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        success('Orchestrator configuration exported successfully!')
      } else {
        showError('Failed to export orchestrator configuration')
      }
    } catch (err) {
      console.error('Failed to export orchestrator config:', err)
      showError('Failed to export orchestrator configuration')
    }
  }

  const exportSingleToolConfig = (toolName, config) => {
    try {
      // Convert JSON to YAML
      const yamlStr = yaml.dump(config, {
        indent: 2,
        lineWidth: 120,
        noRefs: true,
        sortKeys: false
      })

      const yamlBlob = new Blob([yamlStr], { type: 'text/yaml' })
      const url = URL.createObjectURL(yamlBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${toolName}.yaml`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      success(`Exported ${toolName}.yaml successfully!`)
    } catch (err) {
      console.error('Failed to export tool config:', err)
      showError(`Failed to export ${toolName} configuration`)
    }
  }

  const exportAllToolConfigs = () => {
    if (!toolConfigs || Object.keys(toolConfigs).length === 0) {
      showError('No configurations to export')
      return
    }

    try {
      let exportedCount = 0
      Object.entries(toolConfigs).forEach(([toolName, config]) => {
        const yamlStr = yaml.dump(config, {
          indent: 2,
          lineWidth: 120,
          noRefs: true,
          sortKeys: false
        })

        const yamlBlob = new Blob([yamlStr], { type: 'text/yaml' })
        const url = URL.createObjectURL(yamlBlob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${toolName}.yaml`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        exportedCount++
      })
      success(`Exported ${exportedCount} YAML configuration files!`)
    } catch (err) {
      console.error('Failed to export all configs:', err)
      showError('Failed to export all configurations')
    }
  }

  const runTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    try {
      const response = await fetch(`${API_BASE}/dspy/test`)
      const data = await response.json()
      setTestResult(data)
      if (data.status === 'success') {
        success('DSPy test completed successfully!')
      } else {
        showError('DSPy test failed')
      }
    } catch (err) {
      console.error('Test failed:', err)
      showError('Failed to run DSPy test')
      setTestResult({ status: 'error', error: err.message })
    } finally {
      setIsTesting(false)
    }
  }

  const fetchFeedbackStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/dspy/feedback/stats`)
      const data = await response.json()
      if (data.status === 'success') {
        setFeedbackStats(data)
      }
    } catch (err) {
      console.error('[DSPy] Failed to fetch feedback stats:', err)
    }
  }

  const runFeedbackOptimization = async () => {
    setIsOptimizing(true)
    setOptimizeResult(null)
    try {
      const response = await fetch(`${API_BASE}/dspy/optimize-from-feedback`, {
        method: 'POST'
      })
      const data = await response.json()

      if (data.status === 'success') {
        setOptimizeResult(data)

        // Add to history
        const historyEntry = {
          ...data,
          id: Date.now(),
          timestamp: new Date().toISOString()
        }
        setOptimizationHistory(prev => [historyEntry, ...prev])

        // Extract patterns from result
        if (data.analysis_summary) {
          setPatterns(prev => [...prev, ...(data.analysis_summary.patterns || [])])
        }

        success(`Optimization complete! Updated ${data.configs_updated} configs based on ${data.examples_analyzed} examples`)

        // Refresh all data
        fetchStatus(true)
        fetchFeedbackStats()
        fetchToolConfigs()
      } else if (data.status === 'insufficient_data') {
        setOptimizeResult(data)
        showError(data.message)
      } else {
        setOptimizeResult(data)
        showError('Feedback-based optimization failed')
      }
    } catch (err) {
      console.error('Feedback optimization failed:', err)
      showError('Failed to run feedback-based optimization')
      setOptimizeResult({ status: 'error', error: err.message })
    } finally {
      setIsOptimizing(false)
    }
  }

  const tabs = [
    { id: 'analytics', label: 'Analytics Dashboard', icon: '📊' },
    { id: 'optimizations', label: 'Optimization History', icon: '🔄' },
    { id: 'patterns', label: 'Pattern Analysis', icon: '🔍' },
    { id: 'tests', label: 'Test Suites', icon: '✓' },
    { id: 'configs', label: 'Config Changes', icon: '⚙' },
    { id: 'overview', label: 'Overview', icon: '◈' }
  ]

  const optimizationTypes = [
    {
      id: 'param_enhance',
      name: 'Parameter Enhancement',
      description: 'Automatically fix parameter names and generate missing values',
      icon: '⚡',
      color: 'blue'
    },
    {
      id: 'param_recovery',
      name: 'Error Recovery',
      description: 'Intelligently recover from tool call failures',
      icon: '⟲',
      color: 'orange'
    },
    {
      id: 'plan_gen',
      name: 'Plan Generation',
      description: 'Optimize workflow plan generation from user goals',
      icon: '⌘',
      color: 'purple'
    },
    {
      id: 'tool_select',
      name: 'Tool Selection',
      description: 'Choose the best tool for each task',
      icon: '⚙',
      color: 'green'
    }
  ]

  // Remove full-screen loading - show UI immediately

  return (
    <div className="dspy-optimizer">
      {/* Header */}
      <div className="dspy-header">
        <div className="dspy-header-left">
          <h1 className="dspy-title">
            <span className="dspy-icon">◉</span>
            DSPy MCP Optimizer
          </h1>
          <p className="dspy-subtitle">Optimize tool calls and workflow generation with machine learning</p>
        </div>
        <div className="dspy-header-right">
          <div className={`dspy-status-badge ${status?.status || 'ready'}`}>
            <span className="status-dot"></span>
            <span className="status-label">{status?.status === 'loading' ? 'Loading' : (status?.status || 'Ready')}</span>
          </div>
          <button className="dspy-refresh-btn" onClick={() => fetchStatus(true)} title="Refresh status">
            <span className="refresh-icon">⟳</span>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="dspy-tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`dspy-tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => {
              setActiveTab(tab.id)
              if (tab.id === 'configs' && !toolConfigs) {
                fetchToolConfigs()
              }
            }}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="dspy-content">
        {/* Analytics Dashboard Tab */}
        {activeTab === 'analytics' && (
          <div className="dspy-analytics">
            <div className="analytics-header">
              <h2>📊 Real-Time Analytics Dashboard</h2>
              <p>Comprehensive system performance metrics and improvement tracking</p>
            </div>

            {/* Key Metrics Grid */}
            <div className="analytics-section">
              <h3>🎯 Key Performance Indicators</h3>
              <div className="kpi-grid">
                <div className="kpi-card">
                  <div className="kpi-icon">📈</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Total Optimizations Run</div>
                    <div className="kpi-value">{optimizationHistory.length}</div>
                    <div className="kpi-sublabel">
                      {optimizationHistory.filter(h => h.status === 'success').length} successful
                    </div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon">📝</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Examples Analyzed</div>
                    <div className="kpi-value">
                      {optimizationHistory.reduce((sum, h) => sum + (h.examples_analyzed || 0), 0)}
                    </div>
                    <div className="kpi-sublabel">
                      Avg: {optimizationHistory.length > 0
                        ? Math.round(optimizationHistory.reduce((sum, h) => sum + (h.examples_analyzed || 0), 0) / optimizationHistory.length)
                        : 0} per run
                    </div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon">⚙</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Configs Updated</div>
                    <div className="kpi-value">
                      {optimizationHistory.reduce((sum, h) => sum + (h.configs_updated || 0), 0)}
                    </div>
                    <div className="kpi-sublabel">
                      {Object.keys(toolConfigs || {}).length} total tool configs
                    </div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon">🔍</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Patterns Detected</div>
                    <div className="kpi-value">{patterns.length}</div>
                    <div className="kpi-sublabel">
                      {patterns.filter(p => p.confidence >= 0.7).length} high confidence
                    </div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon">✓</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Test Suites</div>
                    <div className="kpi-value">{testSuites.length}</div>
                    <div className="kpi-sublabel">
                      {testSuites.filter(s => s.has_results).length} executed
                    </div>
                  </div>
                </div>

                <div className="kpi-card">
                  <div className="kpi-icon">📊</div>
                  <div className="kpi-content">
                    <div className="kpi-label">Test Success Rate</div>
                    <div className="kpi-value">
                      {testResults ? `${testResults.success_rate.toFixed(1)}%` : 'N/A'}
                    </div>
                    <div className="kpi-sublabel">
                      {testResults ? `${testResults.passed}/${testResults.total_tests} passed` : 'No tests run'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="analytics-section">
              <h3>⚡ Recent Optimization Activity</h3>
              {optimizationHistory.length > 0 ? (
                <div className="recent-activity-timeline">
                  {optimizationHistory.slice(0, 5).map((opt, idx) => (
                    <div key={opt.id} className={`activity-item ${opt.status}`}>
                      <div className="activity-timestamp">
                        {new Date(opt.timestamp).toLocaleString()}
                      </div>
                      <div className="activity-content">
                        <div className="activity-header">
                          <span className={`activity-status ${opt.status}`}>
                            {opt.status === 'success' ? '✓' : opt.status === 'insufficient_data' ? '⏳' : '✗'}
                          </span>
                          <strong>Feedback Optimization #{optimizationHistory.length - idx}</strong>
                        </div>
                        <div className="activity-details">
                          <span className="detail-badge">📝 {opt.examples_analyzed || 0} examples</span>
                          <span className="detail-badge">⚙ {opt.configs_updated || 0} configs updated</span>
                          <span className="detail-badge">🔍 {opt.patterns_found || 0} patterns</span>
                        </div>
                        {opt.analysis_summary && (
                          <div className="activity-summary">
                            <div className="summary-stat">
                              <strong>Parameter Errors:</strong> {Object.keys(opt.analysis_summary.parameter_errors || {}).length}
                            </div>
                            <div className="summary-stat">
                              <strong>Tool Errors:</strong> {Object.keys(opt.analysis_summary.tool_selection_errors || {}).length}
                            </div>
                            <div className="summary-stat">
                              <strong>Corrections:</strong> {Object.keys(opt.analysis_summary.common_corrections || {}).length}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-activity">
                  <p>No optimization runs yet. Click the button below to run your first feedback-based optimization.</p>
                  <button className="primary-action-btn" onClick={runFeedbackOptimization} disabled={isOptimizing}>
                    {isOptimizing ? '◐ Optimizing...' : '▶ Run First Optimization'}
                  </button>
                </div>
              )}
            </div>

            {/* Feedback Stats Detail */}
            {feedbackStats && (
              <div className="analytics-section">
                <h3>💬 Feedback Collection Status</h3>
                <div className="feedback-detail-grid">
                  <div className="feedback-detail-card">
                    <div className="detail-header">
                      <span className="detail-icon">📥</span>
                      <h4>Total Examples Collected</h4>
                    </div>
                    <div className="detail-value">{feedbackStats.total_examples || 0}</div>
                    <div className="detail-progress">
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${Math.min((feedbackStats.total_examples / 50) * 100, 100)}%` }}
                        ></div>
                      </div>
                      <div className="progress-label">
                        Target: 50+ examples for high confidence
                      </div>
                    </div>
                  </div>

                  <div className="feedback-detail-card">
                    <div className="detail-header">
                      <span className="detail-icon">✓</span>
                      <h4>Ready for Training</h4>
                    </div>
                    <div className="detail-value">{feedbackStats.available_examples || 0}</div>
                    <div className={`readiness-indicator ${feedbackStats.ready_to_optimize ? 'ready' : 'not-ready'}`}>
                      {feedbackStats.ready_to_optimize ? '✓ Ready to Optimize' : '⏳ Collecting More Data'}
                    </div>
                  </div>

                  <div className="feedback-detail-card">
                    <div className="detail-header">
                      <span className="detail-icon">🎯</span>
                      <h4>Data Quality Score</h4>
                    </div>
                    <div className="detail-value">
                      {feedbackStats.total_examples > 0
                        ? Math.round((feedbackStats.available_examples / feedbackStats.total_examples) * 100)
                        : 0}%
                    </div>
                    <div className="detail-sublabel">
                      {feedbackStats.available_examples} usable / {feedbackStats.total_examples} total
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="analytics-section">
              <h3>🚀 Quick Actions</h3>
              <div className="quick-actions-grid">
                <button
                  className="action-card"
                  onClick={runFeedbackOptimization}
                  disabled={isOptimizing || (feedbackStats && !feedbackStats.ready_to_optimize)}
                >
                  <div className="action-icon">🔄</div>
                  <div className="action-label">Run Optimization</div>
                  <div className="action-sublabel">
                    {isOptimizing ? 'Processing...' : feedbackStats?.ready_to_optimize ? 'Ready to run' : 'Need more data'}
                  </div>
                </button>

                <button
                  className="action-card"
                  onClick={() => generateTestSuite(5)}
                  disabled={isGeneratingTests}
                >
                  <div className="action-icon">✓</div>
                  <div className="action-label">Generate Tests</div>
                  <div className="action-sublabel">
                    {isGeneratingTests ? 'Generating...' : 'Create new test suite'}
                  </div>
                </button>

                <button
                  className="action-card"
                  onClick={fetchToolConfigs}
                  disabled={isLoadingConfigs}
                >
                  <div className="action-icon">⚙</div>
                  <div className="action-label">Refresh Configs</div>
                  <div className="action-sublabel">
                    {isLoadingConfigs ? 'Loading...' : 'Reload tool configs'}
                  </div>
                </button>

                <button
                  className="action-card"
                  onClick={() => {
                    fetchStatus(true)
                    fetchFeedbackStats()
                    fetchTestSuites()
                    fetchToolConfigs()
                  }}
                >
                  <div className="action-icon">🔃</div>
                  <div className="action-label">Refresh All</div>
                  <div className="action-sublabel">Update all data</div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="dspy-overview">
            <div className="overview-section">
              <h2>◈ System Status</h2>
              <div className="status-grid">
                <div className="status-card">
                  <div className="status-card-icon">⚡</div>
                  <div className="status-card-content">
                    <h3>LLM Provider</h3>
                    <p className="status-value">{status?.llm_provider || 'Not configured'}</p>
                  </div>
                </div>
                <div className="status-card">
                  <div className="status-card-icon">◆</div>
                  <div className="status-card-content">
                    <h3>Optimizations</h3>
                    <p className="status-value">
                      {status?.optimizations ? Object.keys(status.optimizations).length : 0}
                    </p>
                  </div>
                </div>
                <div className="status-card">
                  <div className="status-card-icon">⚙</div>
                  <div className="status-card-content">
                    <h3>Available Types</h3>
                    <p className="status-value">
                      {status?.available_types?.length || 0}
                    </p>
                  </div>
                </div>
              </div>

              {/* Show LLM status warnings/errors */}
              {status?.status === 'rate_limited' && (
                <div className="status-alert warning">
                  <div className="alert-icon">⚠</div>
                  <div className="alert-content">
                    <h4>Rate Limited</h4>
                    <p>{status.error || 'GitHub API rate limit exceeded. Please wait before making more requests.'}</p>
                  </div>
                </div>
              )}
              {status?.status === 'timeout' && (
                <div className="status-alert error">
                  <div className="alert-icon">⏱</div>
                  <div className="alert-content">
                    <h4>Connection Timeout</h4>
                    <p>{status.error || 'LLM request timed out. Please check your connection.'}</p>
                  </div>
                </div>
              )}
              {status?.status === 'connection_error' && (
                <div className="status-alert error">
                  <div className="alert-icon">✗</div>
                  <div className="alert-content">
                    <h4>Connection Error</h4>
                    <p>{status.error || 'Could not connect to LLM service.'}</p>
                  </div>
                </div>
              )}
              {status?.status === 'error' && (
                <div className="status-alert error">
                  <div className="alert-icon">✗</div>
                  <div className="alert-content">
                    <h4>LLM Error</h4>
                    <p>{status.error || 'An error occurred while checking LLM availability.'}</p>
                  </div>
                </div>
              )}
            </div>

            <div className="overview-section">
              <h2>◎ Optimization Types</h2>
              <div className="optimization-types-grid">
                {optimizationTypes.map(type => (
                  <div key={type.id} className={`optimization-type-card ${type.color}`}>
                    <div className="opt-type-header">
                      <span className="opt-type-icon">{type.icon}</span>
                      <h3>{type.name}</h3>
                    </div>
                    <p className="opt-type-description">{type.description}</p>
                    <div className="opt-type-status">
                      {status?.optimizations?.[type.id] ? (
                        <span className="opt-status-badge optimized">✓ Optimized</span>
                      ) : (
                        <span className="opt-status-badge not-optimized">○ Not Optimized</span>
                      )}
                    </div>
                    {/* Examples for each optimization type */}
                    {type.id === 'param_enhance' && (
                      <div className="opt-type-examples">
                        <h4>Example Parameter Fixes:</h4>
                        <div className="example-workflows">
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              User: "Get weather in New York"
                            </div>
                            <div className="workflow-plan">
                              ❌ weather(place: "New York")<br/>
                              ✅ weather(location: "New York", units: "celsius")
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              User: "Translate 'hello' to Spanish"
                            </div>
                            <div className="workflow-plan">
                              ❌ translate(sentence: "hello", lang: "es")<br/>
                              ✅ translate(text: "hello", target_language: "spanish")
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              User: "Calculate 2 + 2"
                            </div>
                            <div className="workflow-plan">
                              ❌ calculate(formula: "2 + 2")<br/>
                              ✅ calculate(expression: "2 + 2")
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {type.id === 'param_recovery' && (
                      <div className="opt-type-examples">
                        <h4>Example Error Recovery:</h4>
                        <div className="example-workflows">
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              Error: Missing required 'location'
                            </div>
                            <div className="workflow-plan">
                              ❌ Fail: "Missing parameter"<br/>
                              ✅ Extract "Paris" from context:<br/>
                              "What's the weather like?"
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              Error: Invalid JSON format
                            </div>
                            <div className="workflow-plan">
                              ❌ Fail: "Invalid JSON"<br/>
                              ✅ Auto-fix: Escape quotes, add commas
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              Error: Invalid language code "es"
                            </div>
                            <div className="workflow-plan">
                              ❌ Fail: "Unknown language"<br/>
                              ✅ Normalize: "es" → "spanish"
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {type.id === 'tool_select' && (
                      <div className="opt-type-examples">
                        <h4>Example Tool Selection:</h4>
                        <div className="example-workflows">
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "What's the temperature in London?"
                            </div>
                            <div className="workflow-plan">
                              ❌ search_tool (slow, inaccurate)<br/>
                              ✅ weather_tool (fast, accurate)
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "Convert this to French"
                            </div>
                            <div className="workflow-plan">
                              ❌ echo_tool (no translation)<br/>
                              ✅ translate_tool (native support)
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "Save this cat fact"
                            </div>
                            <div className="workflow-plan">
                              ❌ echo_tool (doesn't persist)<br/>
                              ✅ save_fact_tool (stores permanently)
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                    {type.id === 'plan_gen' && (
                      <div className="opt-type-examples">
                        <h4>Example Workflows:</h4>
                        <div className="example-workflows">
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "Get weather in Paris and translate to Spanish"
                            </div>
                            <div className="workflow-plan">
                              1. weather_tool(location: "Paris") <br/>
                              2. translate_tool(text: result, target: "spanish")
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "Calculate 15% tip on $85.50"
                            </div>
                            <div className="workflow-plan">
                              1. calculate_tool(expression: "85.50 * 0.15") <br/>
                              2. format_json_tool(data: result)
                            </div>
                          </div>
                          <div className="workflow-example">
                            <div className="workflow-goal">
                              "Search for Python tutorials and save"
                            </div>
                            <div className="workflow-plan">
                              1. search_tool(query: "Python tutorials") <br/>
                              2. save_fact_tool(fact_text: result[0])
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="overview-section">
              <h2>◆ Feedback-Based Optimization</h2>
              <div className="bulk-optimize-panel">
                <p>Learn from actual usage to improve tool calls and parameter handling</p>

                {/* Feedback Stats */}
                {feedbackStats && (
                  <div className="feedback-stats">
                    <div className="feedback-stat-card">
                      <div className="stat-value">{feedbackStats.total_examples || 0}</div>
                      <div className="stat-label">Collected Examples</div>
                    </div>
                    <div className="feedback-stat-card">
                      <div className="stat-value">{feedbackStats.available_examples || 0}</div>
                      <div className="stat-label">Ready for Training</div>
                    </div>
                    <div className={`feedback-stat-card ${feedbackStats.ready_to_optimize ? 'ready' : 'not-ready'}`}>
                      <div className="stat-icon">
                        {feedbackStats.ready_to_optimize ? '✓' : '⏳'}
                      </div>
                      <div className="stat-label">
                        {feedbackStats.ready_to_optimize ? 'Ready to Optimize' : 'Collecting feedback...'}
                      </div>
                    </div>
                  </div>
                )}

                <button
                  className="dspy-bulk-optimize-btn"
                  onClick={runFeedbackOptimization}
                  disabled={isOptimizing || (feedbackStats && !feedbackStats.ready_to_optimize)}
                >
                  {isOptimizing ? '◐ Optimizing from Feedback...' : '▶ Run Feedback Optimization'}
                </button>

                {optimizeResult && (
                  <div className={`bulk-optimize-result ${optimizeResult.status}`}>
                    {optimizeResult.status === 'success' ? (
                      <>
                        <div className="bulk-result-header">
                          <h4>✅ Feedback Optimization Complete</h4>
                          <div className="bulk-result-summary">
                            <span className="summary-item">
                              <strong>{optimizeResult.training_examples || 0}</strong> training examples used
                            </span>
                            <span className="summary-item">
                              Source: Real user feedback
                            </span>
                            <span className="summary-item timestamp">
                              {new Date(optimizeResult.timestamp).toLocaleString()}
                            </span>
                          </div>
                        </div>
                        <div className="feedback-success-message">
                          <p>✓ System has learned from real usage patterns</p>
                          <p>✓ Tool calls will be more accurate going forward</p>
                          <p>✓ Continue using the system to collect more feedback</p>
                        </div>
                      </>
                    ) : optimizeResult.status === 'insufficient_data' ? (
                      <div className="bulk-optimize-info">
                        <h4>⏳ Not Enough Data Yet</h4>
                        <p>{optimizeResult.message}</p>
                        <div className="data-progress">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{
                                width: `${(optimizeResult.examples_found / optimizeResult.examples_needed) * 100}%`
                              }}
                            ></div>
                          </div>
                          <div className="progress-text">
                            {optimizeResult.examples_found} / {optimizeResult.examples_needed} examples collected
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="bulk-optimize-error">
                        <h4>❌ Optimization Failed</h4>
                        <p>{optimizeResult.error || optimizeResult.message}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Optimization History Tab */}
        {activeTab === 'optimizations' && (
          <div className="dspy-optimizations">
            <div className="optimizations-header">
              <h2>🔄 Optimization History</h2>
              <p>Detailed history of all optimization runs with complete analysis</p>
            </div>

            {optimizationHistory.length > 0 ? (
              <div className="optimizations-list">
                {optimizationHistory.map((opt, idx) => (
                  <div key={opt.id} className={`optimization-entry ${opt.status}`}>
                    <div className="opt-entry-header">
                      <div className="opt-header-left">
                        <span className={`opt-status-icon ${opt.status}`}>
                          {opt.status === 'success' ? '✓' : opt.status === 'insufficient_data' ? '⏳' : '✗'}
                        </span>
                        <div className="opt-title-group">
                          <h3>Optimization Run #{optimizationHistory.length - idx}</h3>
                          <div className="opt-timestamp">{new Date(opt.timestamp).toLocaleString()}</div>
                        </div>
                      </div>
                      <div className="opt-header-right">
                        <button
                          className="expand-btn"
                          onClick={() => setExpandedHistory(prev => ({...prev, [opt.id]: !prev[opt.id]}))}
                        >
                          {expandedHistory[opt.id] ? '▼ Collapse' : '▶ Expand'}
                        </button>
                      </div>
                    </div>

                    <div className="opt-summary-stats">
                      <div className="summary-stat-item">
                        <span className="stat-icon">📝</span>
                        <span className="stat-value">{opt.examples_analyzed || 0}</span>
                        <span className="stat-label">Examples Analyzed</span>
                      </div>
                      <div className="summary-stat-item">
                        <span className="stat-icon">🔍</span>
                        <span className="stat-value">{opt.patterns_found || 0}</span>
                        <span className="stat-label">Patterns Found</span>
                      </div>
                      <div className="summary-stat-item">
                        <span className="stat-icon">⚙</span>
                        <span className="stat-value">{opt.configs_updated || 0}</span>
                        <span className="stat-label">Configs Updated</span>
                      </div>
                    </div>

                    {expandedHistory[opt.id] && (
                      <div className="opt-details">
                        {opt.analysis_summary && (
                          <>
                            <div className="opt-detail-section">
                              <h4>📊 Analysis Summary</h4>
                              <div className="analysis-grid">
                                <div className="analysis-item">
                                  <strong>Parameter Errors:</strong>
                                  <span>{Object.keys(opt.analysis_summary.parameter_errors || {}).length} tools affected</span>
                                </div>
                                <div className="analysis-item">
                                  <strong>Tool Selection Errors:</strong>
                                  <span>{Object.keys(opt.analysis_summary.tool_selection_errors || {}).length} issues</span>
                                </div>
                                <div className="analysis-item">
                                  <strong>Common Corrections:</strong>
                                  <span>{Object.keys(opt.analysis_summary.common_corrections || {}).length} patterns</span>
                                </div>
                              </div>
                            </div>

                            {opt.updates && opt.updates.length > 0 && (
                              <div className="opt-detail-section">
                                <h4>✓ Applied Updates</h4>
                                <div className="updates-list">
                                  {opt.updates.map((update, updateIdx) => (
                                    <div key={updateIdx} className="update-item">
                                      <div className="update-tool-name">
                                        <strong>{update.tool}</strong>
                                        <span className="confidence-badge">
                                          Confidence: {(update.confidence * 100).toFixed(0)}%
                                        </span>
                                      </div>
                                      {update.changes && (
                                        <div className="update-changes">
                                          {update.changes.default_values && Object.keys(update.changes.default_values).length > 0 && (
                                            <div className="change-group">
                                              <strong>Default Values Added:</strong>
                                              <ul>
                                                {Object.entries(update.changes.default_values).map(([param, value]) => (
                                                  <li key={param}>
                                                    <code>{param}</code> = <code>{value}</code>
                                                  </li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                          {update.changes.parameter_mappings && Object.keys(update.changes.parameter_mappings).length > 0 && (
                                            <div className="change-group">
                                              <strong>Parameter Mappings:</strong>
                                              <ul>
                                                {Object.entries(update.changes.parameter_mappings).map(([from, to]) => (
                                                  <li key={from}>
                                                    <code>{from}</code> → <code>{to}</code>
                                                  </li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        )}

                        {opt.status === 'insufficient_data' && (
                          <div className="opt-insufficient-data">
                            <p>{opt.message}</p>
                            <div className="data-requirement">
                              Need {opt.examples_needed || 5} examples, found {opt.examples_analyzed || 0}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-optimizations">
                <div className="no-data-icon">🔄</div>
                <h3>No Optimization History</h3>
                <p>Run your first feedback-based optimization to start tracking improvements.</p>
                <button className="primary-action-btn" onClick={runFeedbackOptimization} disabled={isOptimizing}>
                  {isOptimizing ? '◐ Optimizing...' : '▶ Run First Optimization'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Pattern Analysis Tab */}
        {activeTab === 'patterns' && (
          <div className="dspy-patterns">
            <div className="patterns-header">
              <h2>🔍 Pattern Analysis</h2>
              <p>Detected patterns from user feedback and their confidence scores</p>
            </div>

            {patterns.length > 0 ? (
              <div className="patterns-list">
                {patterns
                  .sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
                  .map((pattern, idx) => (
                    <div key={idx} className="pattern-card">
                      <div className="pattern-header">
                        <div className="pattern-title">
                          <h3>{pattern.tool}</h3>
                          <span className="pattern-type">{pattern.type}</span>
                        </div>
                        <div className="pattern-metrics">
                          <div className={`confidence-badge ${pattern.confidence >= 0.7 ? 'high' : pattern.confidence >= 0.4 ? 'medium' : 'low'}`}>
                            {(pattern.confidence * 100).toFixed(0)}% Confidence
                          </div>
                          <div className="frequency-badge">
                            {pattern.frequency} occurrences
                          </div>
                        </div>
                      </div>

                      <div className="pattern-details">
                        <div className="confidence-bar">
                          <div
                            className="confidence-fill"
                            style={{ width: `${pattern.confidence * 100}%` }}
                          ></div>
                        </div>

                        {pattern.examples && pattern.examples.length > 0 && (
                          <div className="pattern-examples">
                            <h4>Examples:</h4>
                            {pattern.examples.map((example, exIdx) => (
                              <div key={exIdx} className="example-pair">
                                <div className="example-before">
                                  <strong>Before:</strong>
                                  <pre>{JSON.stringify(example.before, null, 2)}</pre>
                                </div>
                                <div className="example-arrow">→</div>
                                <div className="example-after">
                                  <strong>After:</strong>
                                  <pre>{JSON.stringify(example.after, null, 2)}</pre>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            ) : (
              <div className="no-patterns">
                <div className="no-data-icon">🔍</div>
                <h3>No Patterns Detected Yet</h3>
                <p>Run feedback optimization to start detecting usage patterns.</p>
              </div>
            )}
          </div>
        )}

        {/* Test Suites Tab */}
        {activeTab === 'tests' && (
          <div className="dspy-tests">
            <div className="tests-header">
              <h2>✓ Test Suites</h2>
              <p>LLM-generated test cases for validating MCP tool improvements</p>
              <div className="tests-actions">
                <button
                  className="generate-tests-btn"
                  onClick={() => generateTestSuite(5)}
                  disabled={isGeneratingTests}
                >
                  {isGeneratingTests ? '◐ Generating...' : '➕ Generate New Test Suite'}
                </button>
              </div>
            </div>

            {testSuites.length > 0 ? (
              <div className="test-suites-list">
                {testSuites.map((suite) => (
                  <div key={suite.suite_id} className="test-suite-card">
                    <div className="suite-header">
                      <div className="suite-info">
                        <h3>{suite.suite_id}</h3>
                        <div className="suite-meta">
                          <span className="suite-date">
                            Generated: {new Date(suite.generated_at).toLocaleString()}
                          </span>
                          <span className="suite-count">{suite.test_count} tests</span>
                        </div>
                      </div>
                      <div className="suite-actions">
                        {suite.has_results && (
                          <button
                            className="view-results-btn"
                            onClick={() => getTestResults(suite.suite_id)}
                          >
                            📊 View Results
                          </button>
                        )}
                        <button
                          className="run-suite-btn"
                          onClick={() => runTestSuite(suite.suite_id)}
                          disabled={isRunningTests && selectedTestSuite === suite.suite_id}
                        >
                          {isRunningTests && selectedTestSuite === suite.suite_id ? '◐ Running...' : '▶ Run Suite'}
                        </button>
                      </div>
                    </div>

                    {testResults && selectedTestSuite === suite.suite_id && (
                      <div className="test-results">
                        <div className="results-summary">
                          <div className="result-stat success">
                            <span className="result-icon">✓</span>
                            <span className="result-count">{testResults.passed}</span>
                            <span className="result-label">Passed</span>
                          </div>
                          <div className="result-stat failed">
                            <span className="result-icon">✗</span>
                            <span className="result-count">{testResults.failed}</span>
                            <span className="result-label">Failed</span>
                          </div>
                          <div className="result-stat error">
                            <span className="result-icon">⚠</span>
                            <span className="result-count">{testResults.errors}</span>
                            <span className="result-label">Errors</span>
                          </div>
                          <div className="result-stat rate">
                            <span className="result-value">{testResults.success_rate?.toFixed(1)}%</span>
                            <span className="result-label">Success Rate</span>
                          </div>
                        </div>

                        {testResults.test_results && testResults.test_results.length > 0 && (
                          <div className="test-cases">
                            <h4>Test Case Results:</h4>
                            {testResults.test_results.map((testCase, idx) => (
                              <div key={idx} className={`test-case ${testCase.status}`}>
                                <div className="test-case-header">
                                  <span className={`status-icon ${testCase.status}`}>
                                    {testCase.status === 'passed' ? '✓' : testCase.status === 'failed' ? '✗' : '⚠'}
                                  </span>
                                  <div className="test-case-info">
                                    <strong>{testCase.task}</strong>
                                    <span className="test-tool">{testCase.tool}</span>
                                  </div>
                                  <span className="test-time">{testCase.execution_time_ms}ms</span>
                                </div>
                                <div className="test-case-details">
                                  <div className="test-detail">
                                    <strong>Expected:</strong> {testCase.expected_output}
                                  </div>
                                  {testCase.actual_output && (
                                    <div className="test-detail">
                                      <strong>Actual:</strong> {JSON.stringify(testCase.actual_output).substring(0, 200)}
                                    </div>
                                  )}
                                  {testCase.validation_details && (
                                    <div className="test-validation">
                                      <strong>Validation:</strong>
                                      <div>Confidence: {((testCase.validation_details.confidence || 0) * 100).toFixed(0)}%</div>
                                      {testCase.validation_details.details && (
                                        <div className="validation-details">
                                          {testCase.validation_details.details.map((detail, dIdx) => (
                                            <div key={dIdx} className="validation-detail">{detail}</div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="no-test-suites">
                <div className="no-data-icon">✓</div>
                <h3>No Test Suites Generated</h3>
                <p>Generate your first LLM-driven test suite to validate tool improvements.</p>
                <button
                  className="primary-action-btn"
                  onClick={() => generateTestSuite(5)}
                  disabled={isGeneratingTests}
                >
                  {isGeneratingTests ? '◐ Generating...' : '➕ Generate Test Suite'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Tool Configs Tab */}
        {activeTab === 'configs' && (
          <div className="dspy-configs">
            <div className="configs-header">
              <div className="configs-header-text">
                <h2>⚙ Tool Configurations</h2>
                <p>View and manage YAML configurations stored with MCP tools</p>
              </div>
              <div className="configs-header-actions">
                <button
                  className="dspy-export-btn"
                  onClick={exportAllToolConfigs}
                  disabled={!toolConfigs || Object.keys(toolConfigs).length === 0}
                  title="Export all tool configs as separate YAML files"
                >
                  ⬇ Export All YAMLs
                </button>
                <button
                  className="dspy-export-btn"
                  onClick={exportOrchestratorConfig}
                  title="Export orchestrator config"
                >
                  ⬇ Export Orchestrator
                </button>
                <button className="dspy-refresh-btn" onClick={fetchToolConfigs} title="Refresh configs">
                  <span className="refresh-icon">⟳</span> Refresh
                </button>
              </div>
            </div>

            {isLoadingConfigs ? (
              <div className="configs-loading">
                <div className="loading-spinner-dspy"></div>
                <p>Loading tool configurations...</p>
              </div>
            ) : toolConfigs ? (
              <div className="configs-content">
                <div className="configs-list">
                  {Object.entries(toolConfigs).map(([toolName, config]) => (
                    <div key={toolName} className="config-card">
                      <div className="config-card-header">
                        <div className="config-tool-info" onClick={() => setSelectedToolConfig(selectedToolConfig === toolName ? null : toolName)}>
                          <h3>{config.tool?.name || toolName}</h3>
                          <p className="config-description">{config.tool?.description || 'No description'}</p>
                        </div>
                        <div className="config-header-actions">
                          <button
                            className="config-export-btn"
                            onClick={(e) => {
                              e.stopPropagation()
                              exportSingleToolConfig(toolName, config)
                            }}
                            title={`Export ${toolName}.yaml`}
                          >
                            ⬇ YAML
                          </button>
                          <div className="config-expand-icon" onClick={() => setSelectedToolConfig(selectedToolConfig === toolName ? null : toolName)}>
                            {selectedToolConfig === toolName ? '▼' : '▶'}
                          </div>
                        </div>
                      </div>

                      {selectedToolConfig === toolName && (
                        <div className="config-card-details">
                          {/* Parameter Mappings */}
                          {config.parameters?.name_mappings && Object.keys(config.parameters.name_mappings).length > 0 && (
                            <div className="config-section">
                              <h4>📝 Parameter Mappings</h4>
                              <div className="mappings-grid">
                                {Object.entries(config.parameters.name_mappings).map(([wrong, correct]) => (
                                  <div key={wrong} className="mapping-item">
                                    <span className="mapping-wrong">{wrong}</span>
                                    <span className="mapping-arrow">→</span>
                                    <span className="mapping-correct">{correct}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Optimization Metrics */}
                          {config.optimization?.accuracy_metrics && (
                            <div className="config-section">
                              <h4>◫ Optimization Metrics</h4>
                              <div className="metrics-grid">
                                <div className="metric-item">
                                  <span className="metric-label">Successful Calls:</span>
                                  <span className="metric-value">{config.optimization.accuracy_metrics.successful_calls || 0}</span>
                                </div>
                                <div className="metric-item">
                                  <span className="metric-label">Failed Calls:</span>
                                  <span className="metric-value">{config.optimization.accuracy_metrics.failed_calls || 0}</span>
                                </div>
                                <div className="metric-item">
                                  <span className="metric-label">Correction Rate:</span>
                                  <span className="metric-value">
                                    {((config.optimization.accuracy_metrics.parameter_correction_rate || 0) * 100).toFixed(1)}%
                                  </span>
                                </div>
                                <div className="metric-item">
                                  <span className="metric-label">Recovery Rate:</span>
                                  <span className="metric-value">
                                    {((config.optimization.accuracy_metrics.error_recovery_rate || 0) * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                              {config.optimization.last_updated && (
                                <div className="last-updated">
                                  Last updated: {new Date(config.optimization.last_updated).toLocaleString()}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Examples */}
                          {config.examples && config.examples.length > 0 && (
                            <div className="config-section">
                              <h4>📚 Training Examples ({config.examples.length})</h4>
                              <div className="examples-list">
                                {config.examples.slice(0, 3).map((example, idx) => (
                                  <div key={idx} className="example-card">
                                    <div className="example-description">{example.description || `Example ${idx + 1}`}</div>
                                    {example.input && (
                                      <div className="example-details">
                                        <div className="example-row">
                                          <span className="example-label">Input:</span>
                                          <code className="example-code">{JSON.stringify(example.input.raw_params || {}, null, 2)}</code>
                                        </div>
                                        {example.expected_output && (
                                          <div className="example-row">
                                            <span className="example-label">Expected:</span>
                                            <code className="example-code">{JSON.stringify(example.expected_output, null, 2)}</code>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                ))}
                                {config.examples.length > 3 && (
                                  <div className="examples-more">+ {config.examples.length - 3} more examples</div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Smart Defaults */}
                          {config.parameters?.smart_defaults && Object.keys(config.parameters.smart_defaults).length > 0 && (
                            <div className="config-section">
                              <h4>◉ Smart Defaults</h4>
                              <div className="defaults-list">
                                {Object.entries(config.parameters.smart_defaults).map(([param, defaults]) => (
                                  <div key={param} className="default-item">
                                    <span className="default-param">{param}:</span>
                                    <span className="default-strategy">{defaults.strategy || 'default'}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Error Recovery Strategies */}
                          {config.error_recovery?.strategies && config.error_recovery.strategies.length > 0 && (
                            <div className="config-section">
                              <h4>🔧 Error Recovery Strategies</h4>
                              <div className="strategies-list">
                                {config.error_recovery.strategies.map((strategy, idx) => (
                                  <div key={idx} className="strategy-item">
                                    <div className="strategy-pattern">{strategy.error_pattern}</div>
                                    <div className="strategy-action">→ {strategy.recovery_action}</div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {Object.keys(toolConfigs).length === 0 && (
                  <div className="no-configs">
                    <div className="no-configs-icon">⚙</div>
                    <h4>No Tool Configurations Found</h4>
                    <p>Run bulk optimization to generate YAML configurations for your tools.</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="configs-empty">
                <p>Click the refresh button to load tool configurations</p>
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="dspy-history">
            <div className="history-header">
              <h2>◇ Optimization History & Detailed Analytics</h2>
              <p>Track optimization progress, system performance, and detailed metrics over time</p>
              <div className="history-header-actions">
                <button
                  className="history-refresh-btn"
                  onClick={() => {
                    fetchStatus(true)
                    if (callLogs) fetchCallLogs()
                  }}
                >
                  <span className="refresh-icon">⟳</span> Refresh All
                </button>
              </div>
            </div>

            <div className="history-content">
              {/* Overall System Summary */}
              <div className="history-section">
                <h3>◫ System Performance Summary</h3>
                <div className="system-summary-grid">
                  <div className="summary-card">
                    <div className="summary-icon">◉</div>
                    <div className="summary-content">
                      <div className="summary-value">{Object.keys(status?.optimizations || {}).length}</div>
                      <div className="summary-label">Active Optimizations</div>
                      <div className="summary-sublabel">
                        {status?.available_types?.length || 0} types available
                      </div>
                    </div>
                  </div>
                  <div className="summary-card">
                    <div className="summary-icon">🔧</div>
                    <div className="summary-content">
                      <div className="summary-value">
                        {Object.values(status?.optimizations || {}).reduce(
                          (sum, opt) => sum + (opt.training_examples_count || 0), 0
                        )}
                      </div>
                      <div className="summary-label">Training Examples</div>
                      <div className="summary-sublabel">
                        Across {Object.keys(toolConfigs || {}).length} tools
                      </div>
                    </div>
                  </div>
                  <div className="summary-card">
                    <div className="summary-icon">⚡</div>
                    <div className="summary-content">
                      <div className="summary-value">{status?.llm_provider || 'Not Set'}</div>
                      <div className="summary-label">LLM Provider</div>
                      <div className="summary-sublabel">
                        Status: {status?.status || 'unknown'}
                      </div>
                    </div>
                  </div>
                  <div className="summary-card">
                    <div className="summary-icon">✓</div>
                    <div className="summary-content">
                      <div className="summary-value">
                        {Object.values(status?.optimizations || {})
                          .filter(opt => opt.status === 'optimized').length}
                        /
                        {Object.keys(status?.optimizations || {}).length}
                      </div>
                      <div className="summary-label">Optimized Modules</div>
                      <div className="summary-sublabel">
                        {Object.keys(status?.optimizations || {}).length > 0
                          ? Math.round((Object.values(status?.optimizations || {})
                              .filter(opt => opt.status === 'optimized').length /
                              Object.keys(status?.optimizations || {}).length) * 100)
                          : 0}% complete
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Detailed Optimization Breakdown */}
              <div className="history-section">
                <h3>◇ Optimization Module Details</h3>
                <div className="history-filters">
                  <div className="filter-group">
                    <label>Filter:</label>
                    <select
                      value={historyFilter}
                      onChange={(e) => setHistoryFilter(e.target.value)}
                      className="filter-select"
                    >
                      <option value="all">All Modules</option>
                      <option value="optimized">Optimized Only</option>
                      <option value="pending">Pending Only</option>
                    </select>
                  </div>
                  <div className="filter-group">
                    <input
                      type="text"
                      placeholder="Search modules..."
                      value={historySearch}
                      onChange={(e) => setHistorySearch(e.target.value)}
                      className="filter-search"
                    />
                  </div>
                </div>

                {status?.optimizations && Object.keys(status.optimizations).length > 0 ? (
                  <div className="history-modules">
                    {Object.entries(status.optimizations)
                      .filter(([key, value]) => {
                        // Apply filters
                        if (historyFilter === 'optimized' && value.status !== 'optimized') return false
                        if (historyFilter === 'pending' && value.status === 'optimized') return false
                        if (historySearch && !key.toLowerCase().includes(historySearch.toLowerCase())) return false
                        return true
                      })
                      .sort((a, b) => {
                        const timeA = new Date(a[1].timestamp || 0)
                        const timeB = new Date(b[1].timestamp || 0)
                        return timeB - timeA
                      })
                      .map(([key, value]) => {
                        const type = optimizationTypes.find(t => t.id === key)
                        const isExpanded = expandedHistory[key]

                        return (
                          <div key={key} className={`history-module-card ${value.status}`}>
                            <div
                              className="module-card-header"
                              onClick={() => setExpandedHistory(prev => ({
                                ...prev,
                                [key]: !prev[key]
                              }))}
                            >
                              <div className="module-header-left">
                                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
                                <span className="module-icon">{type?.icon || '◆'}</span>
                                <div className="module-title-group">
                                  <h4>{type?.name || key}</h4>
                                  <span className="module-description">{type?.description || 'N/A'}</span>
                                </div>
                              </div>
                              <div className="module-header-right">
                                <span className={`status-badge ${value.status}`}>
                                  {value.status || 'Unknown'}
                                </span>
                                <span className="module-timestamp">
                                  {value.timestamp
                                    ? new Date(value.timestamp).toLocaleString('en-US', {
                                        month: 'short',
                                        day: 'numeric',
                                        hour: '2-digit',
                                        minute: '2-digit'
                                      })
                                    : 'No timestamp'}
                                </span>
                              </div>
                            </div>

                            {isExpanded && (
                              <div className="module-card-details">
                                <div className="module-metrics-row">
                                  <div className="metric-box">
                                    <div className="metric-label">Training Examples</div>
                                    <div className="metric-value">{value.training_examples_count || 0}</div>
                                  </div>
                                  <div className="metric-box">
                                    <div className="metric-label">Module Type</div>
                                    <div className="metric-value">{key}</div>
                                  </div>
                                  <div className="metric-box">
                                    <div className="metric-label">Last Updated</div>
                                    <div className="metric-value">
                                      {value.timestamp
                                        ? new Date(value.timestamp).toLocaleDateString()
                                        : 'Never'}
                                    </div>
                                  </div>
                                  <div className="metric-box">
                                    <div className="metric-label">Status</div>
                                    <div className="metric-value">{value.status || 'Unknown'}</div>
                                  </div>
                                </div>

                                {value.metrics && (
                                  <div className="module-performance">
                                    <h5>Performance Metrics</h5>
                                    <div className="performance-grid">
                                      {Object.entries(value.metrics).map(([metricKey, metricValue]) => (
                                        <div key={metricKey} className="performance-item">
                                          <span className="performance-label">
                                            {metricKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                                          </span>
                                          <span className="performance-value">
                                            {typeof metricValue === 'number'
                                              ? metricValue.toFixed(2)
                                              : metricValue}
                                          </span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {value.config_path && (
                                  <div className="module-config-info">
                                    <strong>Config Path:</strong> <code>{value.config_path}</code>
                                  </div>
                                )}

                                {value.description && (
                                  <div className="module-full-description">
                                    <strong>Description:</strong> {value.description}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                  </div>
                ) : (
                  <div className="no-modules">
                    <div className="no-modules-icon">◇</div>
                    <h4>No Optimization Modules</h4>
                    <p>No optimization events have been recorded yet. Run bulk optimization to start collecting metrics.</p>
                  </div>
                )}
              </div>

              {/* Detailed Call Logs Per Tool */}
              <div className="history-section">
                <h3>◫ Detailed Call Logs by Tool</h3>
                <button
                  className="load-call-logs-btn"
                  onClick={fetchCallLogs}
                >
                  {callLogs ? '⟳ Refresh Call Logs' : '◈ Load Call Logs'}
                </button>

                {callLogs && Object.keys(callLogs).length > 0 && (
                  <div className="call-logs-container">
                    {Object.entries(callLogs).map(([toolName, log]) => (
                      <div key={toolName} className="call-log-tool-card">
                        <div
                          className="call-log-tool-header"
                          onClick={() => toggleToolExpanded(toolName)}
                        >
                          <div className="tool-header-left">
                            <span className="expand-icon">{expandedTools[toolName] ? '▼' : '▶'}</span>
                            <h4>{log.tool_name}</h4>
                            <span className="tool-description-brief">{log.description}</span>
                          </div>
                          <div className="tool-header-right">
                            <span className="call-count success">✓ {log.successful_calls?.length || 0}</span>
                            <span className="call-count failed">✗ {log.failed_calls?.length || 0}</span>
                            <span className="call-count corrections">⚡ {log.corrections?.length || 0}</span>
                          </div>
                        </div>

                        {expandedTools[toolName] && (
                          <div className="call-log-tool-details">
                            {/* Successful Calls */}
                            {log.successful_calls && log.successful_calls.length > 0 && (
                              <div className="call-log-section">
                                <h5>✓ Successful Calls ({log.successful_calls.length})</h5>
                                <div className="call-log-entries">
                                  {log.successful_calls.map((call, idx) => (
                                    <div key={idx} className="call-log-entry success">
                                      <div className="call-log-description">{call.description}</div>
                                      <div className="call-log-details">
                                        <div className="call-log-detail">
                                          <strong>Input:</strong>
                                          <pre>{JSON.stringify(call.input, null, 2)}</pre>
                                        </div>
                                        {call.expected_output && (
                                          <div className="call-log-detail">
                                            <strong>Output:</strong>
                                            <pre>{JSON.stringify(call.expected_output, null, 2)}</pre>
                                          </div>
                                        )}
                                      </div>
                                      {call.timestamp && (
                                        <div className="call-log-timestamp">
                                          {new Date(call.timestamp).toLocaleString()}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Failed Calls */}
                            {log.failed_calls && log.failed_calls.length > 0 && (
                              <div className="call-log-section">
                                <h5>✗ Failed Calls ({log.failed_calls.length})</h5>
                                <div className="call-log-entries">
                                  {log.failed_calls.map((call, idx) => (
                                    <div key={idx} className="call-log-entry failed">
                                      <div className="call-log-description">{call.error}</div>
                                      <div className="call-log-details">
                                        <div className="call-log-detail">
                                          <strong>Attempted Input:</strong>
                                          <pre>{JSON.stringify(call.input || {}, null, 2)}</pre>
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Corrections */}
                            {log.corrections && log.corrections.length > 0 && (
                              <div className="call-log-section">
                                <h5>⚡ Parameter Corrections ({log.corrections.length})</h5>
                                <div className="call-log-entries">
                                  {log.corrections.map((correction, idx) => (
                                    <div key={idx} className="call-log-entry correction">
                                      <div className="correction-parameter">
                                        <strong>{correction.parameter}</strong>
                                      </div>
                                      <div className="correction-change">
                                        <span className="correction-before">Before: {correction.before}</span>
                                        <span className="correction-arrow">→</span>
                                        <span className="correction-after">After: {correction.after}</span>
                                      </div>
                                      <div className="correction-meta">
                                        <span className="correction-reason">{correction.reason}</span>
                                        <span className="correction-frequency">Frequency: {correction.frequency}</span>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Metrics Summary */}
                            {log.metrics && Object.keys(log.metrics).length > 0 && (
                              <div className="call-log-section">
                                <h5>◫ Metrics</h5>
                                <div className="metrics-summary">
                                  <div className="metric-item">
                                    <span className="metric-label">Successful Calls:</span>
                                    <span className="metric-value">{log.metrics.successful_calls || 0}</span>
                                  </div>
                                  <div className="metric-item">
                                    <span className="metric-label">Failed Calls:</span>
                                    <span className="metric-value">{log.metrics.failed_calls || 0}</span>
                                  </div>
                                  <div className="metric-item">
                                    <span className="metric-label">Correction Rate:</span>
                                    <span className="metric-value">
                                      {((log.metrics.parameter_correction_rate || 0) * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                  <div className="metric-item">
                                    <span className="metric-label">Recovery Rate:</span>
                                    <span className="metric-value">
                                      {((log.metrics.error_recovery_rate || 0) * 100).toFixed(1)}%
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {!callLogs && (
                  <div className="no-call-logs">
                    <p>Click "◈ Load Call Logs" to view detailed call history for each tool</p>
                  </div>
                )}

                {callLogs && Object.keys(callLogs).length === 0 && (
                  <div className="no-call-logs">
                    <p>No tool calls have been recorded yet. Execute some workflows in AgentFlow to generate call logs.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
