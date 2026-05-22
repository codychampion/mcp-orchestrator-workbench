import React, { useState, useRef, useEffect } from 'react'
import { API_BASE } from './utils/api'
import { useToast } from './components/Toast'
import CopyButton from './components/CopyButton'
import './WorkflowBuilder.css'

export default function WorkflowBuilder() {
  const { success, error, warning, info } = useToast()
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [tools, setTools] = useState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [workflowId, setWorkflowId] = useState(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [executionUpdates, setExecutionUpdates] = useState([])
  const [finalOutput, setFinalOutput] = useState(null)
  const [showExecutionLog, setShowExecutionLog] = useState(false)
  const [logExpanded, setLogExpanded] = useState(false)
  const [webSocket, setWebSocket] = useState(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [toolsExpanded, setToolsExpanded] = useState(true)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(null)
  const canvasRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    // Fetch available tools
    const fetchTools = async () => {
      try {
        const response = await fetch(`${API_BASE}/tools`)
        const toolsData = await response.json()
        const userTools = toolsData.filter(tool =>
          !['validate_dag', 'smart_dag_builder', 'generate_node_id'].includes(tool.name)
        )
        setTools(userTools)
      } catch (error) {
        console.error('Failed to fetch tools:', error)
      }
    }
    fetchTools()
  }, [])

  const addToolNode = (toolName) => {
    const newNode = {
      id: `node_${Date.now()}`,
      type: 'tool',
      config: {
        tool: toolName,
        params: {}
      },
      position: { x: 100 + nodes.length * 50, y: 100 + nodes.length * 50 }
    }
    setNodes([...nodes, newNode])
  }


  const removeNode = (nodeId) => {
    setNodes(nodes.filter(n => n.id !== nodeId))
    setEdges(edges.filter(e => e.from !== nodeId && e.to !== nodeId))
    if (selectedNode?.id === nodeId) {
      setSelectedNode(null)
    }
  }

  const addEdge = (fromId, toId) => {
    // Prevent duplicate edges
    if (edges.some(e => e.from === fromId && e.to === toId)) {
      return
    }
    setEdges([...edges, { from: fromId, to: toId }])
  }

  const removeEdge = (fromId, toId) => {
    setEdges(edges.filter(e => !(e.from === fromId && e.to === toId)))
  }

  const updateNodeConfig = (nodeId, config) => {
    setNodes(nodes.map(n =>
      n.id === nodeId ? { ...n, config: { ...n.config, ...config } } : n
    ))
  }

  const createWorkflow = async () => {
    try {
      const response = await fetch(`${API_BASE}/workflow/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges })
      })

      const data = await response.json()
      setWorkflowId(data.workflow_id)
      return data.workflow_id
    } catch (error) {
      console.error('Error creating workflow:', error)
      return null
    }
  }

  const executeWorkflow = async () => {
    if (nodes.length === 0) {
      warning('Please add at least one node to the workflow')
      return
    }

    setIsExecuting(true)
    setExecutionUpdates([])

    try {
      let wfId = workflowId
      if (!wfId) {
        wfId = await createWorkflow()
        if (!wfId) return
      }

      // Start execution
      await fetch(`${API_BASE}/workflow/${wfId}/execute`, {
        method: 'POST'
      })

      // Connect to WebSocket for updates
      const wsUrl = API_BASE.replace('http', 'ws')
      const ws = new WebSocket(`${wsUrl}/ws/workflow/${wfId}`)

      ws.onmessage = (event) => {
        const update = JSON.parse(event.data)
        setExecutionUpdates(prev => [...prev, update])

        if (update.type === 'workflow_complete') {
          setIsExecuting(false)
          // Extract final output from completed workflow
          if (update.state) {
            const nodeStates = Object.values(update.state)
            const successfulNodes = nodeStates.filter(n => n.status === 'success' && n.result)
            if (successfulNodes.length > 0) {
              // Use the last successful node's result as final output
              const lastNode = successfulNodes[successfulNodes.length - 1]
              setFinalOutput(lastNode.result)
            }
          }
          setShowExecutionLog(true)
          ws.close()
        } else if (update.type === 'workflow_error') {
          setIsExecuting(false)
          setFinalOutput({ error: true, message: 'Workflow execution failed' })
          setShowExecutionLog(true)
          ws.close()
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsExecuting(false)
      }

      setWebSocket(ws)

    } catch (error) {
      console.error('Error executing workflow:', error)
      setIsExecuting(false)
    }
  }

  const saveWorkflowToFile = async () => {
    if (!workflowId) {
      const newWorkflowId = await createWorkflow()
      if (!newWorkflowId) return
    }

    setIsSaving(true)
    try {
      const response = await fetch(`${API_BASE}/workflow/${workflowId}/save`, {
        method: 'POST'
      })

      const data = await response.json()
      if (data.status === 'success') {
        // Download as JSON file
        const blob = new Blob([JSON.stringify(data.workflow, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `workflow-${workflowId}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        success('Workflow saved successfully!')
      }
    } catch (err) {
      console.error('Error saving workflow:', err)
      error('Failed to save workflow')
    } finally {
      setIsSaving(false)
    }
  }

  const loadWorkflowFromFile = (event) => {
    const file = event.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (e) => {
      try {
        const workflowData = JSON.parse(e.target.result)
        await loadWorkflow(workflowData)
      } catch (err) {
        console.error('Error loading workflow:', err)
        error('Failed to load workflow file')
      }
    }
    reader.readAsText(file)
  }

  const loadWorkflow = async (workflowData) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/workflow/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workflow: workflowData })
      })

      const data = await response.json()
      if (data.status === 'success') {
        setWorkflowId(data.workflow_id)

        // Load nodes and edges from the workflow
        const loadedNodes = workflowData.nodes.map((node, idx) => ({
          ...node,
          position: node.position || { x: 100 + idx * 50, y: 100 + idx * 50 }
        }))
        const loadedEdges = workflowData.edges || []

        setNodes(loadedNodes)
        setEdges(loadedEdges)
        success('Workflow loaded successfully!')
      }
    } catch (err) {
      console.error('Error loading workflow:', err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const clearWorkflow = () => {
    if (nodes.length > 0) {
      if (!window.confirm('Clear the entire workflow? This action cannot be undone.')) {
        return
      }
    }
    setNodes([])
    setEdges([])
    setSelectedNode(null)
    setWorkflowId(null)
    setExecutionUpdates([])
    setFinalOutput(null)
    setShowExecutionLog(false)
    setLogExpanded(false)
    setIsExecuting(false)
    setFeedbackSubmitted(null)
  }

  const organizeLayout = () => {
    if (nodes.length === 0) return

    // Build adjacency map
    const inDegree = {}
    const outgoing = {}
    nodes.forEach(node => {
      inDegree[node.id] = 0
      outgoing[node.id] = []
    })
    edges.forEach(edge => {
      inDegree[edge.to]++
      outgoing[edge.from].push(edge.to)
    })

    // Topological sort to determine layers
    const layers = []
    const nodeLayer = {}
    const queue = nodes.filter(node => inDegree[node.id] === 0).map(n => n.id)

    let currentLayer = 0
    while (queue.length > 0) {
      const layerSize = queue.length
      layers[currentLayer] = []

      for (let i = 0; i < layerSize; i++) {
        const nodeId = queue.shift()
        layers[currentLayer].push(nodeId)
        nodeLayer[nodeId] = currentLayer

        outgoing[nodeId].forEach(nextId => {
          inDegree[nextId]--
          if (inDegree[nextId] === 0) {
            queue.push(nextId)
          }
        })
      }
      currentLayer++
    }

    // Handle cycles - put remaining nodes in final layer
    const unplaced = nodes.filter(n => nodeLayer[n.id] === undefined)
    if (unplaced.length > 0) {
      layers[currentLayer] = unplaced.map(n => n.id)
      unplaced.forEach(n => nodeLayer[n.id] = currentLayer)
    }

    // Position nodes
    const LAYER_SPACING = 200
    const NODE_SPACING = 250
    const START_X = 100
    const START_Y = 100

    const updatedNodes = nodes.map(node => {
      const layer = nodeLayer[node.id]
      const layerNodes = layers[layer]
      const indexInLayer = layerNodes.indexOf(node.id)
      const layerWidth = (layerNodes.length - 1) * NODE_SPACING
      const startX = START_X - layerWidth / 2

      return {
        ...node,
        position: {
          x: startX + indexInLayer * NODE_SPACING + layer * 150,
          y: START_Y + layer * LAYER_SPACING
        }
      }
    })

    setNodes(updatedNodes)
    success('Workflow organized!')
  }

  const getNodeStyle = (node) => {
    const baseStyle = {
      position: 'absolute',
      left: `${node.position.x}px`,
      top: `${node.position.y}px`
    }
    return baseStyle
  }

  const exportLogsAsJSON = () => {
    const logsData = {
      workflow_id: workflowId,
      timestamp: new Date().toISOString(),
      execution_updates: executionUpdates,
      nodes,
      edges
    }

    const blob = new Blob([JSON.stringify(logsData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `execution-log-${workflowId || Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const submitFeedback = async (rating) => {
    try {
      // Extract workflow execution data for learning
      const feedbackData = {
        workflow_id: workflowId,
        rating: rating,
        timestamp: new Date().toISOString(),
        execution_summary: {
          nodes: nodes,
          edges: edges,
          updates: executionUpdates,
          final_output: finalOutput
        }
      }

      // Submit feedback to backend
      const response = await fetch(`${API_BASE}/dspy/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback_type: 'workflow',
          rating: rating,
          data: feedbackData
        })
      })

      if (response.ok) {
        setFeedbackSubmitted(rating)
        success(`Feedback submitted! This helps improve workflow optimization.`)
        console.log('Workflow feedback submitted successfully')
      } else {
        error('Failed to submit feedback')
      }
    } catch (err) {
      console.error('Error submitting feedback:', err)
      error('Error submitting feedback')
    }
  }

  return (
    <div className="workflow-builder-container">
      <div className="workflow-header">
        <h2>⟁ Workflow Builder</h2>
        <p>Create custom workflows by connecting agents and tools</p>
      </div>

      <div className="workflow-content">
        {/* Toolbox Sidebar */}
        <div className="toolbox-sidebar">
          <div className="toolbox-header">
            <h3>⚙ Toolbox</h3>
            <button
              className="collapse-tools-btn"
              onClick={() => setToolsExpanded(!toolsExpanded)}
              title={toolsExpanded ? 'Collapse tools' : 'Expand tools'}
              aria-label={toolsExpanded ? 'Collapse tools' : 'Expand tools'}
            >
              {toolsExpanded ? '⌃' : '⌄'}
            </button>
          </div>

          {toolsExpanded && (
            <div className="toolbox-section">
              <h4>Tools</h4>
              <div className="toolbox-items">
              {tools.slice(0, 10).map(tool => (
                <div
                  key={tool.name}
                  className="toolbox-item"
                  onClick={() => addToolNode(tool.name)}
                  title={tool.description}
                >
                  <span className="toolbox-icon">⬡</span>
                  <span className="toolbox-label">{tool.name}</span>
                </div>
              ))}
              </div>
            </div>
          )}

          <div className="toolbox-actions">
            <button onClick={executeWorkflow} disabled={isExecuting || nodes.length === 0} className="execute-workflow-btn">
              {isExecuting ? '◐ Running...' : '▶ Execute'}
            </button>
            <button onClick={organizeLayout} disabled={nodes.length === 0} className="organize-workflow-btn" title="Auto-organize workflow layout">
              ⚏ Organize
            </button>
            <button onClick={saveWorkflowToFile} disabled={isSaving || nodes.length === 0} className="save-workflow-btn">
              {isSaving ? '◐ Saving...' : '▼ Save'}
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={loadWorkflowFromFile}
              accept=".json"
              style={{ display: 'none' }}
            />
            <button onClick={() => fileInputRef.current?.click()} disabled={isLoading} className="load-file-btn">
              {isLoading ? '◐ Loading...' : '▲ Load'}
            </button>
            <button onClick={clearWorkflow} disabled={isExecuting} className="clear-workflow-btn">
              ✕ Clear
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div className="workflow-canvas" ref={canvasRef}>
          {nodes.length === 0 ? (
            <div className="canvas-placeholder">
              <div className="placeholder-icon">⬚</div>
              <h3>Start Building</h3>
              <p>Add tools from the toolbox to create your workflow</p>
            </div>
          ) : (
            <>
              <svg className="workflow-edges">
                {edges.map((edge, idx) => {
                  const fromNode = nodes.find(n => n.id === edge.from)
                  const toNode = nodes.find(n => n.id === edge.to)
                  if (!fromNode || !toNode) return null

                  const x1 = fromNode.position.x + 100
                  const y1 = fromNode.position.y + 40
                  const x2 = toNode.position.x + 100
                  const y2 = toNode.position.y + 40

                  return (
                    <g key={idx}>
                      <line
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke="#9ca3af"
                        strokeWidth="2"
                        markerEnd="url(#arrowhead)"
                      />
                    </g>
                  )
                })}
                <defs>
                  <marker
                    id="arrowhead"
                    markerWidth="10"
                    markerHeight="7"
                    refX="9"
                    refY="3.5"
                    orient="auto"
                  >
                    <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
                  </marker>
                </defs>
              </svg>

              {nodes.map(node => (
                <div
                  key={node.id}
                  className={`workflow-node ${node.type} ${selectedNode?.id === node.id ? 'selected' : ''}`}
                  style={getNodeStyle(node)}
                  onClick={() => setSelectedNode(node)}
                  draggable
                  onDragEnd={(e) => {
                    const canvas = canvasRef.current
                    if (canvas) {
                      const rect = canvas.getBoundingClientRect()
                      const x = e.clientX - rect.left - 100
                      const y = e.clientY - rect.top - 40
                      setNodes(nodes.map(n =>
                        n.id === node.id ? { ...n, position: { x, y } } : n
                      ))
                    }
                  }}
                >
                  <div className="node-header">
                    <span className="node-icon">
                      {node.type === 'agent' ? '◉' : '▢'}
                    </span>
                    <span className="node-title">
                      {node.type === 'agent'
                        ? 'Executor Agent'
                        : node.config.tool}
                    </span>
                    <button
                      className="node-remove-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        removeNode(node.id)
                      }}
                    >
                      ×
                    </button>
                  </div>
                  <div className="node-body">
                    {node.type === 'agent' && (
                      <div className="node-goal">{node.config.goal?.substring(0, 40)}...</div>
                    )}
                    {node.type === 'tool' && (
                      <div className="node-params">{Object.keys(node.config.params || {}).length} params</div>
                    )}
                  </div>
                </div>
              ))}
            </>
          )}
        </div>

        {/* Properties Panel */}
        {nodes.length > 0 && !selectedNode && (
          <div className="properties-panel">
            <div className="properties-header">
              <h3>Properties</h3>
            </div>
            <div className="properties-content">
              <div className="properties-empty">
                <div className="empty-icon">◇</div>
                <h4>No Node Selected</h4>
                <p>Click on a node in the canvas to view and edit its properties</p>
              </div>
            </div>
          </div>
        )}
        {selectedNode && (
          <div className="properties-panel">
            <div className="properties-header">
              <h3>Properties</h3>
              <button onClick={() => setSelectedNode(null)} className="close-properties-btn" aria-label="Close properties panel">
                ×
              </button>
            </div>

            <div className="properties-content">
              <div className="property-group">
                <label>Node ID</label>
                <input type="text" value={selectedNode.id} disabled className="property-input" />
              </div>

              <div className="property-group">
                <label>Type</label>
                <input type="text" value={selectedNode.type} disabled className="property-input" />
              </div>

              {selectedNode.type === 'agent' && (
                <>
                  <div className="property-group">
                    <label>Agent Type</label>
                    <input type="text" value="Executor" disabled className="property-input" />
                  </div>

                  <div className="property-group">
                    <label>Goal</label>
                    <textarea
                      value={selectedNode.config.goal}
                      onChange={(e) => updateNodeConfig(selectedNode.id, { goal: e.target.value })}
                      className="property-textarea"
                      rows={3}
                    />
                  </div>
                </>
              )}

              {selectedNode.type === 'tool' && (
                <>
                  <div className="property-group">
                    <label>Tool</label>
                    <select
                      value={selectedNode.config.tool}
                      onChange={(e) => updateNodeConfig(selectedNode.id, { tool: e.target.value })}
                      className="property-input"
                    >
                      {tools.map(tool => (
                        <option key={tool.name} value={tool.name}>
                          {tool.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="property-group">
                    <label>Parameters (JSON)</label>
                    <textarea
                      value={JSON.stringify(selectedNode.config.params || {}, null, 2)}
                      onChange={(e) => {
                        try {
                          const params = JSON.parse(e.target.value)
                          updateNodeConfig(selectedNode.id, { params })
                        } catch (err) {
                          // Invalid JSON, don't update
                        }
                      }}
                      className="property-textarea"
                      rows={4}
                    />
                  </div>
                </>
              )}

              <div className="property-group">
                <label>Connections</label>
                <div className="connections-section">
                  <div className="connection-controls">
                    <select
                      className="connect-select"
                      onChange={(e) => {
                        if (e.target.value) {
                          addEdge(selectedNode.id, e.target.value)
                          e.target.value = ''
                        }
                      }}
                    >
                      <option value="">Connect to...</option>
                      {nodes
                        .filter(n => n.id !== selectedNode.id)
                        .map(n => (
                          <option key={n.id} value={n.id}>
                            {n.type === 'agent'
                              ? 'Executor Agent'
                              : n.config.tool}
                          </option>
                        ))}
                    </select>
                  </div>

                  <div className="current-connections">
                    <div className="connection-list">
                      <strong>Outgoing:</strong>
                      {edges.filter(e => e.from === selectedNode.id).length === 0 ? (
                        <div className="connection-empty">No outgoing connections</div>
                      ) : (
                        edges
                          .filter(e => e.from === selectedNode.id)
                          .map(e => {
                            const toNode = nodes.find(n => n.id === e.to)
                            return (
                              <div key={e.to} className="connection-item">
                                <span>→ {toNode?.type === 'agent' ? 'Executor Agent' : toNode?.config.tool}</span>
                                <button onClick={() => removeEdge(e.from, e.to)} className="remove-connection-btn">
                                  ×
                                </button>
                              </div>
                            )
                          })
                      )}
                    </div>

                    <div className="connection-list">
                      <strong>Incoming:</strong>
                      {edges.filter(e => e.to === selectedNode.id).length === 0 ? (
                        <div className="connection-empty">No incoming connections</div>
                      ) : (
                        edges
                          .filter(e => e.to === selectedNode.id)
                          .map(e => {
                            const fromNode = nodes.find(n => n.id === e.from)
                            return (
                              <div key={e.from} className="connection-item">
                                <span>← {fromNode?.type === 'agent' ? 'Executor Agent' : fromNode?.config.tool}</span>
                                <button onClick={() => removeEdge(e.from, e.to)} className="remove-connection-btn">
                                  ×
                                </button>
                              </div>
                            )
                          })
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Final Output */}
      {finalOutput && (
        <div className="workflow-final-output">
          <div className="final-output-header">
            <h3>✓ Final Output</h3>
            <button onClick={() => setFinalOutput(null)} className="close-output-btn" aria-label="Close final output">×</button>
          </div>
          <div className="final-output-content">
            {finalOutput.error ? (
              <div className="output-error">
                <span className="error-icon">⚠</span>
                <span>{finalOutput.message}</span>
              </div>
            ) : (
              <div className="output-success">
                <div style={{ position: 'relative' }}>
                  <CopyButton
                    text={typeof finalOutput === 'object' ? JSON.stringify(finalOutput, null, 2) : finalOutput}
                    className="copy-btn-top-right"
                  />
                  <pre>{typeof finalOutput === 'object' ? JSON.stringify(finalOutput, null, 2) : finalOutput}</pre>
                </div>
              </div>
            )}
          </div>
          {!finalOutput.error && (
            <div className="workflow-feedback">
              <span className="feedback-label">Was this workflow helpful?</span>
              {feedbackSubmitted ? (
                <span className="feedback-submitted">
                  {feedbackSubmitted === 'positive' ? '✓ Thanks for your feedback!' : '✓ Feedback submitted'}
                </span>
              ) : (
                <div className="feedback-buttons">
                  <button
                    className="feedback-btn thumbs-up"
                    onClick={() => submitFeedback('positive')}
                    title="Helpful"
                  >
                    👍
                  </button>
                  <button
                    className="feedback-btn thumbs-down"
                    onClick={() => submitFeedback('negative')}
                    title="Not helpful"
                  >
                    👎
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Execution Log Tray */}
      {showExecutionLog && executionUpdates.length > 0 && (
        <div className={`execution-log ${logExpanded ? 'expanded' : ''}`}>
          <div className="execution-log-header">
            <h3>▭ Execution Log</h3>
            <div className="header-actions">
              <button
                onClick={exportLogsAsJSON}
                className="export-log-btn"
                title="Export logs as JSON"
              >
                ⬇
              </button>
              <button
                onClick={() => setLogExpanded(!logExpanded)}
                className="expand-log-btn"
                title={logExpanded ? 'Collapse' : 'Expand'}
              >
                {logExpanded ? '⇤' : '⇥'}
              </button>
              <button onClick={() => setShowExecutionLog(false)} className="close-log-btn" aria-label="Close execution log">×</button>
            </div>
          </div>
          <div className="log-content">
            <div className="log-section">
              <h4>◈ Workflow Events</h4>
              <div className="log-entries">
                {executionUpdates.map((update, idx) => {
                  // Determine event icon and color based on type
                  let eventIcon = '○'
                  let eventClass = ''

                  if (update.type === 'optimization_start') {
                    eventIcon = '⚡'
                    eventClass = 'optimization'
                  } else if (update.type === 'parameters_corrected') {
                    eventIcon = '✓'
                    eventClass = 'success'
                  } else if (update.type === 'error_recovery_start') {
                    eventIcon = '⟲'
                    eventClass = 'recovery'
                  } else if (update.type === 'error_recovered') {
                    eventIcon = '✓'
                    eventClass = 'recovered'
                  } else if (update.type === 'tool_call_success') {
                    eventIcon = '✓'
                    eventClass = 'success'
                  } else if (update.type === 'tool_call_failed') {
                    eventIcon = '✗'
                    eventClass = 'error'
                  } else if (update.type === 'node_complete') {
                    eventIcon = '✓'
                    eventClass = 'success'
                  } else if (update.type === 'node_error') {
                    eventIcon = '✗'
                    eventClass = 'error'
                  }

                  return (
                    <div key={idx} className={`log-entry ${eventClass}`}>
                      <div className="log-entry-header">
                        <span className="log-entry-icon">{eventIcon}</span>
                        <strong>{update.type.replace(/_/g, ' ').toUpperCase()}</strong>
                        {update.node_id && <span className="log-entry-node">Node: {update.node_id}</span>}
                        {update.tool && <span className="log-entry-tool">Tool: {update.tool}</span>}
                      </div>
                      <div className="log-entry-content">
                        {/* Optimization Start */}
                        {update.type === 'optimization_start' && (
                          <div className="log-field">
                            <span className="log-label">Original Parameters:</span>
                            <pre>{JSON.stringify(update.original_params, null, 2)}</pre>
                          </div>
                        )}

                        {/* Parameters Corrected */}
                        {update.type === 'parameters_corrected' && update.corrections && (
                          <div className="log-field corrections">
                            <span className="log-label">Parameter Corrections:</span>
                            {Object.entries(update.corrections).map(([key, correction]) => (
                              <div key={key} className="correction-detail">
                                <strong>{key}:</strong>
                                <div className="correction-comparison">
                                  <span className="before">❌ {JSON.stringify(correction.before)}</span>
                                  <span className="arrow">→</span>
                                  <span className="after">✓ {JSON.stringify(correction.after)}</span>
                                </div>
                                <div className="correction-reason">{correction.reason}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Tool Call Attempt */}
                        {update.type === 'tool_call_attempt' && (
                          <div className="log-field">
                            <span className="log-label">Attempt {update.attempt} with parameters:</span>
                            <pre>{JSON.stringify(update.params, null, 2)}</pre>
                          </div>
                        )}

                        {/* Error Recovery Start */}
                        {update.type === 'error_recovery_start' && (
                          <div className="log-field recovery">
                            <span className="log-label">Attempting recovery from error:</span>
                            <span className="error-message">{update.error}</span>
                          </div>
                        )}

                        {/* Error Recovered */}
                        {update.type === 'error_recovered' && (
                          <div className="log-field recovered">
                            <span className="log-label">Recovery Action:</span>
                            <span>{update.recovery_action}</span>
                            <div className="recovery-comparison">
                              <div><strong>Original:</strong> <pre>{JSON.stringify(update.original_params, null, 2)}</pre></div>
                              <div><strong>Recovered:</strong> <pre>{JSON.stringify(update.recovered_params, null, 2)}</pre></div>
                            </div>
                          </div>
                        )}

                        {/* Tool Call Failed */}
                        {update.type === 'tool_call_failed' && (
                          <div className="log-field error">
                            <span className="log-label">Attempt {update.attempt} failed:</span>
                            <span className="error-message">{update.error}</span>
                          </div>
                        )}

                        {/* Node Complete */}
                        {update.type === 'node_complete' && update.result && (
                          <div className="log-field">
                            <span className="log-label">Result:</span>
                            <div className="log-result">{update.result}</div>
                          </div>
                        )}

                        {/* Node Error */}
                        {update.type === 'node_error' && update.error && (
                          <div className="log-field error">
                            <span className="log-label">Error:</span>
                            <span>{update.error}</span>
                          </div>
                        )}

                        {/* Workflow Complete */}
                        {update.type === 'workflow_complete' && update.state && (
                          <div className="log-field">
                            <span className="log-label">Final State:</span>
                            <div style={{ position: 'relative' }}>
                              <CopyButton
                                text={JSON.stringify(update.state, null, 2)}
                                className="copy-btn-top-right"
                              />
                              <pre>{JSON.stringify(update.state, null, 2)}</pre>
                            </div>
                          </div>
                        )}

                        {/* Generic fallback for other types */}
                        {!['optimization_start', 'parameters_corrected', 'tool_call_attempt', 'error_recovery_start', 'error_recovered', 'tool_call_failed', 'node_complete', 'node_error', 'workflow_complete'].includes(update.type) && (
                          <pre>{JSON.stringify(update, null, 2)}</pre>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
