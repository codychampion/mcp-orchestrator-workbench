import React, {useState, useEffect} from 'react'
import { API_BASE } from './utils/api'
import ChatInterface from './ChatInterface'
import AgentFlow from './AgentFlow'
import WorkflowBuilder from './WorkflowBuilder'
import ToolsViewer from './ToolsViewer'
import DSpyOptimizer from './DSpyOptimizer'
import { ToastProvider } from './components/Toast'
import './App.css'
import './DSpyOptimizerAboutStyles.css'

export default function App(){
  const [mode, setMode] = useState('agent')
  const [mcpStatus, setMcpStatus] = useState(null)
  const [llmStatus, setLlmStatus] = useState(null)
  const [showTooltip, setShowTooltip] = useState(false)
  const [selectedModel, setSelectedModel] = useState('github/gpt-4o-mini')
  const [darkMode, setDarkMode] = useState(false)
  const [showAboutModal, setShowAboutModal] = useState(false)

  // Apply dark mode class to body
  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode')
    } else {
      document.body.classList.remove('dark-mode')
    }
  }, [darkMode])

  // Available models (GitHub and Azure)
  const availableModels = [
    { id: 'github/gpt-4o-mini', name: 'GitHub GPT-4o Mini', description: 'Fast and efficient', provider: 'GitHub' },
    { id: 'github/gpt-4o', name: 'GitHub GPT-4o', description: 'Most capable model', provider: 'GitHub' },
    { id: 'azure/gpt-35-turbo', name: 'Azure GPT-3.5 Turbo', description: 'Fast and reliable', provider: 'Azure' },
    { id: 'azure/gpt-4', name: 'Azure GPT-4', description: 'Advanced reasoning', provider: 'Azure' }
  ]

  const modes = [
    { id: 'agent', label: 'AgentFlow', icon: '◉', description: 'Autonomous agent execution' },
    { id: 'workflow', label: 'Workflow', icon: '⟁', description: 'Visual workflow builder' },
    { id: 'tools', label: 'Tools', icon: '⚙', description: 'Browse available MCP tools' },
    { id: 'dspy', label: 'DSPy Optimizer', icon: '◈', description: 'Optimize MCP with machine learning' }
  ]

  // Test LLM model connectivity
  const testLLMModel = async (model) => {
    try {
      setLlmStatus({ status: 'testing', model })
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: 'test',
          chat_history: [],
          model: model
        }),
        signal: AbortSignal.timeout(30000)
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()
      if (data.error) {
        throw new Error(data.error)
      }

      setLlmStatus({
        status: 'connected',
        model,
        model_used: data.model_used,
        timestamp: new Date().toISOString()
      })
    } catch (error) {
      console.error('LLM test failed:', error)
      setLlmStatus({
        status: 'error',
        model,
        error: error.message,
        timestamp: new Date().toISOString()
      })
    }
  }

  // Test LLM on model change
  useEffect(() => {
    testLLMModel(selectedModel)
  }, [selectedModel])

  useEffect(() => {
    const fetchMcpStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/mcp/status`)
        const data = await response.json()
        setMcpStatus(data)
      } catch (error) {
        console.error('Failed to fetch MCP status:', error)
        setMcpStatus({ status: 'error', error: error.message })
      }
    }

    // Fetch immediately
    fetchMcpStatus()

    // Poll every 10 seconds
    const interval = setInterval(fetchMcpStatus, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <ToastProvider>
      {/* About MCP Modal */}
      {showAboutModal && (
        <div className="about-modal-overlay" onClick={() => setShowAboutModal(false)}>
          <div className="about-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="about-modal-close" onClick={() => setShowAboutModal(false)}>×</button>

            <div className="about-modal-scroll">
              <div className="about-hero">
                <h1 className="about-hero-title">The Model Context Protocol</h1>
                <p className="about-hero-subtitle">
                  The missing piece that makes AI truly useful
                </p>
                <div className="hero-stats">
                  <div className="hero-stat">
                    <div className="stat-number">∞</div>
                    <div className="stat-label">AI Models</div>
                  </div>
                  <div className="hero-stat-divider">×</div>
                  <div className="hero-stat">
                    <div className="stat-number">∞</div>
                    <div className="stat-label">Tools</div>
                  </div>
                  <div className="hero-stat-divider">=</div>
                  <div className="hero-stat highlight">
                    <div className="stat-number">1</div>
                    <div className="stat-label">Standard</div>
                  </div>
                </div>
              </div>

              <div className="about-section">
                <h2 className="about-section-title">The Problem MCP Solves</h2>
                <div className="problem-solution">
                  <div className="problem-card">
                    <h3>Before MCP</h3>
                    <ul className="problem-list">
                      <li>Every AI needs custom code for each tool</li>
                      <li>Same tool, different implementation for each AI</li>
                      <li>Tools break when AI providers update</li>
                      <li>Can't switch between AI models easily</li>
                      <li>Massive development overhead</li>
                    </ul>
                  </div>
                  <div className="arrow-divider">→</div>
                  <div className="solution-card">
                    <h3>With MCP</h3>
                    <ul className="solution-list">
                      <li>Write once, works with any AI</li>
                      <li>One standard protocol for all tools</li>
                      <li>Tools stay compatible forever</li>
                      <li>Switch AIs without changing code</li>
                      <li>Build 10x faster</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="about-section">
                <h2 className="about-section-title">Think of It Like...</h2>
                <div className="analogies-enhanced">
                  <div className="analogy-enhanced">
                    <div className="analogy-visual">
                      <div className="analogy-before">
                        <div className="device">Phone</div>
                        <div className="connector">—</div>
                        <div className="charger">Charger 1</div>
                      </div>
                      <div className="analogy-before">
                        <div className="device">Laptop</div>
                        <div className="connector">—</div>
                        <div className="charger">Charger 2</div>
                      </div>
                      <div className="analogy-before">
                        <div className="device">Watch</div>
                        <div className="connector">—</div>
                        <div className="charger">Charger 3</div>
                      </div>
                    </div>
                    <p className="analogy-label bad">Different charger for every device</p>
                  </div>
                  <div className="analogy-divider">VS</div>
                  <div className="analogy-enhanced">
                    <div className="analogy-visual">
                      <div className="analogy-after">
                        <div className="devices-group">
                          <div className="device">Phone</div>
                          <div className="device">Laptop</div>
                          <div className="device">Watch</div>
                        </div>
                        <div className="connector-unified">⟶</div>
                        <div className="universal-port">USB-C</div>
                      </div>
                    </div>
                    <p className="analogy-label good">One universal standard</p>
                  </div>
                </div>
                <div className="analogy-explanation">
                  <strong>MCP is the "USB-C" for AI.</strong> Just like USB-C works with any device,
                  MCP lets any AI work with any tool through one universal protocol.
                </div>
              </div>

              <div className="about-section">
                <h2 className="about-section-title">Why Should You Care?</h2>
                <div className="about-benefits-grid">
                  <div className="benefit-card">
                    <h3>Faster Development</h3>
                    <p>Build AI applications 10x faster by reusing existing tools instead of reinventing the wheel.</p>
                  </div>
                  <div className="benefit-card">
                    <h3>Better Security</h3>
                    <p>Control exactly what your AI can access. No more giving AI unlimited access to everything.</p>
                  </div>
                  <div className="benefit-card">
                    <h3>True Interoperability</h3>
                    <p>Your tools work with ANY AI - Claude, ChatGPT, local models, and future AIs not yet invented.</p>
                  </div>
                  <div className="benefit-card">
                    <h3>Portable Tools</h3>
                    <p>Move your AI tools between projects, teams, and companies. They just work everywhere.</p>
                  </div>
                </div>
              </div>

              <div className="about-section">
                <h2 className="about-section-title">For Developers: How It Works</h2>
                <div className="tech-comparison">
                  <div className="comparison-side">
                    <h3 className="comparison-title old">Traditional Approach</h3>
                    <div className="code-block">
                      <div className="code-header">Hardcoded for each AI</div>
                      <pre>{`// For Claude
anthropic.messages.create({
  tools: [customClaudeTool]
})

// For OpenAI
openai.chat.completions.create({
  functions: [customGPTFunction]
})

// Different code for every AI!`}</pre>
                    </div>
                  </div>

                  <div className="comparison-side">
                    <h3 className="comparison-title new">MCP Way</h3>
                    <div className="code-block">
                      <div className="code-header">Universal standard</div>
                      <pre>{`// Works with ANY AI!
const mcp = new MCPClient()
await mcp.connect("http://tools:8000")

// That's it!
// Claude, GPT, Gemini, local models
// All use the same tools`}</pre>
                    </div>
                  </div>
                </div>

                <div className="tech-stack">
                  <h3>The MCP Stack</h3>
                  <div className="stack-layers">
                    <div className="stack-layer layer-1">
                      <div className="layer-content">
                        <h4>Any AI Model</h4>
                        <p>Claude · GPT-4 · Gemini · Llama · Your Custom Model</p>
                      </div>
                    </div>
                    <div className="stack-connector">↕</div>
                    <div className="stack-layer layer-2">
                      <div className="layer-content">
                        <h4>MCP Protocol</h4>
                        <p>JSON-RPC 2.0 · Server-Sent Events · Schema Discovery</p>
                      </div>
                    </div>
                    <div className="stack-connector">↕</div>
                    <div className="stack-layer layer-3">
                      <div className="layer-content">
                        <h4>MCP Tools</h4>
                        <p>Database · APIs · Files · Your Custom Tools</p>
                      </div>
                    </div>
                    <div className="stack-connector">↕</div>
                    <div className="stack-layer layer-4">
                      <div className="layer-content">
                        <h4>DSPy Optimization (This System!)</h4>
                        <p>Auto-fixes · Smart defaults · Error recovery · Continuous learning</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="tech-features">
                  <h3>Key Technical Features</h3>
                  <div className="features-grid">
                    <div className="feature-item">
                      <h4>Real-time Streaming</h4>
                      <p>Server-Sent Events enable streaming responses for long-running operations</p>
                    </div>
                    <div className="feature-item">
                      <h4>Auto-Discovery</h4>
                      <p>JSON Schema lets AIs understand tools without hardcoded knowledge</p>
                    </div>
                    <div className="feature-item">
                      <h4>Secure by Design</h4>
                      <p>Granular permissions control exactly what each AI can access</p>
                    </div>
                    <div className="feature-item">
                      <h4>Language Agnostic</h4>
                      <p>Implement in Python, TypeScript, Go, Rust - it just works</p>
                    </div>
                  </div>
                </div>

                <div className="dspy-enhancement">
                  <h3>DSPy Makes MCP Smarter</h3>
                  <p className="enhancement-intro">
                    This system adds <strong>machine learning optimization</strong> on top of standard MCP:
                  </p>
                  <div className="enhancement-features">
                    <div className="enhancement-item">
                      <div className="enhancement-content">
                        <h4>Auto-Fix Parameters</h4>
                        <p>User says "place" but tool expects "location"? DSPy learns the mapping and fixes it automatically.</p>
                        <div className="enhancement-example">
                          <code>{"place: 'Paris' → location: 'Paris'"}</code>
                        </div>
                      </div>
                    </div>
                    <div className="enhancement-item">
                      <div className="enhancement-content">
                        <h4>Smart Error Recovery</h4>
                        <p>When calls fail, DSPy predicts the fix based on learned patterns instead of generic retry logic.</p>
                        <div className="enhancement-example">
                          <code>Error: Missing param → Generate from context</code>
                        </div>
                      </div>
                    </div>
                    <div className="enhancement-item">
                      <div className="enhancement-content">
                        <h4>Portable Configs</h4>
                        <p>All optimizations saved as YAML files that travel with each tool. Copy tool = copy optimizations!</p>
                        <div className="enhancement-example">
                          <code>weather_tool.yaml → 95% accuracy</code>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="about-section">
                <h2 className="about-section-title">Real-World Examples</h2>
                <div className="examples-grid">
                  <div className="example-card-about">
                    <div className="example-header-about">
                      <h4>Enterprise Integration</h4>
                    </div>
                    <p>
                      A company builds one MCP server for their internal tools (CRM, inventory, analytics).
                      Now ANY AI - their custom chatbot, third-party agents, or future AI assistants - can
                      access these tools without new integration work.
                    </p>
                  </div>

                  <div className="example-card-about">
                    <div className="example-header-about">
                      <h4>Open Source Community</h4>
                    </div>
                    <p>
                      Developers publish MCP tools for databases, APIs, and services. Anyone can download and use them
                      with their preferred AI, creating a thriving ecosystem of reusable AI tools.
                    </p>
                  </div>

                  <div className="example-card-about">
                    <div className="example-header-about">
                      <h4>Healthcare & Privacy</h4>
                    </div>
                    <p>
                      Medical AI assistants can access patient records through local MCP servers that never send data
                      to the cloud, maintaining HIPAA compliance while still benefiting from powerful AI capabilities.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="app">
        <header className="app-header">
          <div className="header-content">
            <h1 className="app-title">
              <span className="logo">⌘</span>
              MCP Orchestrator
            </h1>

            <div className="mode-selector-container">
              {modes.map(m => (
                <button
                  key={m.id}
                  className={`mode-selector-btn ${mode === m.id ? 'active' : ''}`}
                  onClick={() => setMode(m.id)}
                  title={m.description}
                >
                  <span className="mode-icon">{m.icon}</span>
                  <span className="mode-label">{m.label}</span>
                </button>
              ))}
            </div>

            <div className="header-right-controls">
              <div className="model-selector">
                <label className="model-label">Model:</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="model-select"
                  title={availableModels.find(m => m.id === selectedModel)?.description}
                >
                  {availableModels.map(model => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>

              <button
                onClick={() => setShowAboutModal(true)}
                className="about-mcp-btn"
                title="About MCP"
              >
                ℹ About MCP
              </button>

              <button
                onClick={() => setDarkMode(!darkMode)}
                className="theme-toggle-btn"
                title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {darkMode ? '○' : '◐'}
              </button>

              <div
                className="status-indicator"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
              >
                <span className={`status-dot ${
                  llmStatus?.status === 'connected' ? 'connected' :
                  llmStatus?.status === 'testing' ? 'testing' :
                  'disconnected'
                }`}></span>
                <span className="status-text">
                  {llmStatus?.status === 'connected' ? 'LLM Ready' :
                   llmStatus?.status === 'testing' ? 'Testing LLM...' :
                   llmStatus?.status === 'error' ? 'LLM Error' :
                   'Checking...'}
                </span>
                {showTooltip && (llmStatus || mcpStatus) && (
                  <div className="status-tooltip">
                    <div className="tooltip-header">System Status</div>

                    {/* LLM Status */}
                    {llmStatus && (
                      <>
                        <div className="tooltip-section-title">LLM Model</div>
                        <div className="tooltip-row">
                          <span className="tooltip-label">Status:</span>
                          <span className={`tooltip-value ${
                            llmStatus.status === 'connected' ? 'connected' :
                            llmStatus.status === 'testing' ? 'testing' :
                            'disconnected'
                          }`}>
                            {llmStatus.status === 'connected' ? '✓ Ready' :
                             llmStatus.status === 'testing' ? '◐ Testing...' :
                             '✗ Error'}
                          </span>
                        </div>
                        <div className="tooltip-row">
                          <span className="tooltip-label">Model:</span>
                          <span className="tooltip-value small">{llmStatus.model}</span>
                        </div>
                        {llmStatus.model_used && (
                          <div className="tooltip-row">
                            <span className="tooltip-label">Used:</span>
                            <span className="tooltip-value small">{llmStatus.model_used}</span>
                          </div>
                        )}
                        {llmStatus.error && (
                          <div className="tooltip-row">
                            <span className="tooltip-label">Error:</span>
                            <span className="tooltip-value error">{llmStatus.error}</span>
                          </div>
                        )}
                      </>
                    )}

                    {/* MCP Status */}
                    {mcpStatus && (
                      <>
                        <div className="tooltip-section-title">MCP Server</div>
                        {mcpStatus.status === 'connected' ? (
                          <>
                            <div className="tooltip-row">
                              <span className="tooltip-label">Status:</span>
                              <span className="tooltip-value connected">✓ Connected</span>
                            </div>
                            <div className="tooltip-row">
                              <span className="tooltip-label">Tools:</span>
                              <span className="tooltip-value">{mcpStatus.tools_count}</span>
                            </div>
                            <div className="tooltip-row">
                              <span className="tooltip-label">Response:</span>
                              <span className="tooltip-value">{mcpStatus.response_time_ms}ms</span>
                            </div>
                          </>
                        ) : (
                          <div className="tooltip-row">
                            <span className="tooltip-label">Status:</span>
                            <span className="tooltip-value disconnected">✗ Disconnected</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        <main className="app-main">
          {mode === 'agent' && <AgentFlow selectedModel={selectedModel} />}
          {mode === 'workflow' && <WorkflowBuilder selectedModel={selectedModel} />}
          {mode === 'tools' && <ToolsViewer />}
          {mode === 'dspy' && <DSpyOptimizer />}
        </main>
      </div>
    </ToastProvider>
  )
}
