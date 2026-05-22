import React, { useState, useRef, useEffect } from 'react'
import { API_BASE } from './utils/api'
import './AgentFlow.css'

export default function AgentFlow() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [currentSession, setCurrentSession] = useState(null)
  const [wsConnection, setWsConnection] = useState(null)
  const [executionLog, setExecutionLog] = useState(null)
  const [showLog, setShowLog] = useState(false)
  const [logExpanded, setLogExpanded] = useState(false)
  const [availableTools, setAvailableTools] = useState([])
  const [selectedTools, setSelectedTools] = useState([])
  const [showToolModal, setShowToolModal] = useState(false)
  const [examplePrompts, setExamplePrompts] = useState([
    'Get me a random cat fact',
    'What\'s the weather like?',
    'Tell me a joke'
  ])
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Fetch available tools on mount
  useEffect(() => {
    const fetchTools = async () => {
      try {
        const response = await fetch(`${API_BASE}/tools`)
        const tools = await response.json()
        setAvailableTools(tools)
        // Select all tools by default
        setSelectedTools(tools.map(t => t.name))
      } catch (error) {
        console.error('Error fetching tools:', error)
      }
    }
    fetchTools()

    // Fetch dynamic example prompts from LLM
    const fetchExamples = async () => {
      try {
        const response = await fetch(`${API_BASE}/dspy/generate-examples`, {
          method: 'POST'
        })
        const data = await response.json()
        if (data.status === 'success' && data.examples && data.examples.length > 0) {
          setExamplePrompts(data.examples)
        }
      } catch (error) {
        console.error('Error fetching example prompts:', error)
        // Keep default examples if fetch fails
      }
    }
    fetchExamples()
  }, [])

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsConnection) {
        wsConnection.close()
      }
    }
  }, [wsConnection])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const userGoal = input
    setInput('')
    setIsLoading(true)

    // Create abort controller with 60 second timeout for initial request
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)

    try {
      // Start AgentFlow (always use executor agent)
      const response = await fetch(`${API_BASE}/agent-flow/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_type: 'executor',
          goal: userGoal,
          context: {
            conversation_history: messages.slice(-5).map(m => ({
              role: m.type,
              content: m.content
            }))
          },
          selected_tools: selectedTools // Send selected tools to backend
        }),
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()
      const sessionId = data.session_id
      setCurrentSession(sessionId)

      // Add thinking indicator
      const thinkingMessage = {
        id: Date.now() + 1,
        type: 'agent',
        content: '',
        timestamp: new Date(),
        thinking: true,
        toolCalls: []
      }
      setMessages(prev => [...prev, thinkingMessage])

      // Connect to WebSocket for real-time updates
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.hostname === 'localhost' ? 'localhost:8100' : window.location.hostname + ':8100'
      const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/agent-flow/${sessionId}`)

      setWsConnection(ws)

      let finalResponse = ''
      let toolCalls = []

      ws.onmessage = (event) => {
        const update = JSON.parse(event.data)
        console.log('Agent update:', update)

        if (update.type === 'tools_discovered') {
          // Agent discovered available tools - show subtle indicator
          setMessages(prev => prev.map(msg =>
            msg.thinking
              ? { ...msg, toolsAvailable: update.tools_count }
              : msg
          ))
        } else if (update.type === 'thought') {
          // Agent is thinking - update thinking message
          const thoughts = update.decision?.thoughts || ''
          setMessages(prev => prev.map(msg =>
            msg.thinking
              ? { ...msg, thoughts }
              : msg
          ))
        } else if (update.type === 'tool_call_start') {
          // Agent is calling a tool
          toolCalls.push({
            tool: update.tool,
            status: 'running'
          })
          setMessages(prev => prev.map(msg =>
            msg.thinking
              ? { ...msg, toolCalls: [...toolCalls] }
              : msg
          ))
        } else if (update.type === 'tool_call_complete') {
          // Tool call completed
          toolCalls = toolCalls.map(tc =>
            tc.tool === update.tool
              ? { ...tc, status: 'complete', result: update.result }
              : tc
          )
          setMessages(prev => prev.map(msg =>
            msg.thinking
              ? { ...msg, toolCalls: [...toolCalls] }
              : msg
          ))
        } else if (update.type === 'action_result') {
          // Collect results
          if (update.result && typeof update.result === 'string') {
            finalResponse = update.result
          }
        } else if (update.type === 'complete') {
          // Agent finished - fetch full summary and show results
          fetchExecutionSummary(sessionId, finalResponse, toolCalls, ws)
        } else if (update.type === 'flow_complete') {
          // Flow completed - fetch full summary and show results
          fetchExecutionSummary(sessionId, finalResponse, toolCalls, ws)
        } else if (update.type === 'flow_error') {
          // Error occurred
          setMessages(prev => prev.map(msg =>
            msg.thinking
              ? {
                  ...msg,
                  thinking: false,
                  content: `Error: ${update.error}`,
                  error: true
                }
              : msg
          ))
          setIsLoading(false)
          ws.close()
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setMessages(prev => prev.map(msg =>
          msg.thinking
            ? {
                ...msg,
                thinking: false,
                content: 'Connection error. Please try again.',
                error: true
              }
            : msg
        ))
        setIsLoading(false)
      }

    } catch (error) {
      clearTimeout(timeoutId)
      console.error('Error:', error)

      let errorMsg = 'Sorry, I encountered an error. Please try again.'
      if (error.name === 'AbortError') {
        errorMsg = 'Request timed out. The server may be experiencing issues or rate limiting. Please try again.'
      } else if (error.message.includes('fetch')) {
        errorMsg = 'Could not connect to the server. Please check your connection.'
      } else if (error.message.includes('HTTP error')) {
        errorMsg = `Server error: ${error.message}. The server may be out of API tokens or experiencing issues.`
      }

      setMessages(prev => prev.map(msg =>
        msg.thinking
          ? {
              ...msg,
              thinking: false,
              content: errorMsg,
              error: true
            }
          : msg
      ))
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const fetchExecutionSummary = async (sessionId, finalResponse, toolCalls, ws) => {
    try {
      const response = await fetch(`${API_BASE}/agent-flow/${sessionId}`)
      const data = await response.json()

      // Format comprehensive summary from execution log
      let summaryContent = ''

      // Add result if available
      if (data.result) {
        summaryContent += `${data.result}\n\n`
      } else if (finalResponse) {
        summaryContent += `${finalResponse}\n\n`
      }

      // Add execution summary
      if (data.execution_log) {
        const log = data.execution_log

        // Summary stats
        summaryContent += `📊 Execution Summary:\n`
        summaryContent += `• Iterations: ${data.iterations || 0}\n`
        summaryContent += `• Tool Calls: ${log.tool_calls?.length || 0}\n`
        summaryContent += `• Status: ${data.status || 'completed'}\n\n`

        // Tool calls summary
        if (log.tool_calls && log.tool_calls.length > 0) {
          summaryContent += `⚙️ Tools Used:\n`
          log.tool_calls.forEach((call, idx) => {
            const statusIcon = call.status === 'completed' ? '✓' : call.status === 'failed' ? '✗' : '⏳'
            const retryInfo = call.retry_count > 0 ? ` (${call.retry_count} retries)` : ''
            summaryContent += `${idx + 1}. ${statusIcon} ${call.tool}${retryInfo}\n`

            // Show result if available and successful
            if (call.status === 'completed' && call.result) {
              const resultPreview = typeof call.result === 'string'
                ? call.result.substring(0, 200)
                : JSON.stringify(call.result).substring(0, 200)
              summaryContent += `   → ${resultPreview}${resultPreview.length >= 200 ? '...' : ''}\n`
            }

            // Show error if failed
            if (call.status === 'failed' && call.error) {
              summaryContent += `   ✗ Error: ${call.error}\n`
            }
          })
          summaryContent += `\n`
        }

        // Show key findings from thoughts
        if (log.thoughts && log.thoughts.length > 0) {
          const lastThought = log.thoughts[log.thoughts.length - 1]
          if (lastThought.decision && lastThought.decision !== 'finish') {
            summaryContent += `💭 Final Decision: ${lastThought.decision}\n`
            if (lastThought.thoughts) {
              summaryContent += `   ${lastThought.thoughts}\n\n`
            }
          }
        }

        summaryContent += `\n💡 View detailed execution log for complete analysis`
      }

      // Update message with comprehensive summary
      setMessages(prev => prev.map(msg =>
        msg.thinking
          ? {
              ...msg,
              thinking: false,
              content: summaryContent.trim() || 'Task completed successfully!',
              toolCalls: [...toolCalls],
              fullSummary: data
            }
          : msg
      ))

      setExecutionLog(data.execution_log)
      setShowLog(true) // Auto-show execution log panel when complete
      setIsLoading(false)
      ws.close()

    } catch (error) {
      console.error('Error fetching execution summary:', error)
      // Fallback to simple message
      setMessages(prev => prev.map(msg =>
        msg.thinking
          ? {
              ...msg,
              thinking: false,
              content: finalResponse || 'Task completed!',
              toolCalls: [...toolCalls]
            }
          : msg
      ))
      setIsLoading(false)
      ws.close()
    }
  }

  const fetchExecutionLog = async (sessionId) => {
    try {
      const response = await fetch(`${API_BASE}/agent-flow/${sessionId}`)
      const data = await response.json()
      setExecutionLog(data.execution_log)
      setShowLog(true)
    } catch (error) {
      console.error('Error fetching execution log:', error)
    }
  }

  const startNewConversation = () => {
    setMessages([])
    setCurrentSession(null)
    setExecutionLog(null)
    setShowLog(false)
    setLogExpanded(false)
    if (wsConnection) {
      wsConnection.close()
      setWsConnection(null)
    }
  }

  const toggleTool = (toolName) => {
    setSelectedTools(prev =>
      prev.includes(toolName)
        ? prev.filter(t => t !== toolName)
        : [...prev, toolName]
    )
  }

  const selectAllTools = () => {
    setSelectedTools(availableTools.map(t => t.name))
  }

  const deselectAllTools = () => {
    setSelectedTools([])
  }

  const downloadExecutionLog = () => {
    if (!executionLog) return

    const dataStr = JSON.stringify(executionLog, null, 2)
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr)

    const exportFileDefaultName = `execution-log-${currentSession || Date.now()}.json`

    const linkElement = document.createElement('a')
    linkElement.setAttribute('href', dataUri)
    linkElement.setAttribute('download', exportFileDefaultName)
    linkElement.click()
  }

  const submitFeedback = async (rating, message) => {
    try {
      // Extract tool calls and execution data for learning
      const feedbackData = {
        session_id: currentSession,
        rating: rating,
        timestamp: new Date().toISOString(),
        execution_summary: message.fullSummary
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
        // Update message to show feedback was submitted
        setMessages(prev => prev.map(msg =>
          msg.id === message.id
            ? { ...msg, feedbackSubmitted: rating }
            : msg
        ))
        console.log('Feedback submitted successfully')
      }
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  return (
    <div className="agent-flow-container">
      <div className="agent-chat-header">
        <div className="header-left">
          <button
            className="new-chat-btn"
            onClick={startNewConversation}
            title="Start new conversation"
          >
            + New Chat
          </button>
        </div>
        <div className="header-center">
          <h2>◉ Agent Assistant</h2>
          <p className="agent-subtitle">Autonomous executor agent with access to all tools</p>
        </div>
        <div className="header-right">
          {executionLog && (
            <button
              className="view-log-btn"
              onClick={() => setShowLog(!showLog)}
              title={showLog ? 'Hide execution log' : 'Show execution log'}
            >
              ▭ {showLog ? 'Hide Log' : 'View Log'}
            </button>
          )}
        </div>
      </div>

      <div className="agent-messages-container" ref={messagesContainerRef}>
        <div className="agent-messages">
          {messages.length === 0 && (
            <div className="agent-welcome-message">
              <h3>◆ Welcome to AgentFlow</h3>
              <p>Ask me anything! I'll use all available tools to help you.</p>
              <div className="agent-example-prompts">
                {examplePrompts.map((prompt, idx) => (
                  <button key={idx} onClick={() => setInput(prompt)}>
                    {['◆', '★', '✓', '◉', '◈'][idx % 5]} {prompt.length > 40 ? prompt.substring(0, 40) + '...' : prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} className={`agent-message ${message.type}`}>
              <div className="agent-message-content">
                {message.thinking ? (
                  <div className="agent-thinking">
                    <div className="thinking-indicator">
                      <div className="thinking-spinner"></div>
                      <span>Thinking...</span>
                    </div>
                    {message.toolsAvailable && (
                      <div className="tools-indicator">
                        ⚙ {message.toolsAvailable} tools available
                      </div>
                    )}
                    {message.toolCalls && message.toolCalls.length > 0 && (
                      <div className="tool-calls">
                        {message.toolCalls.map((tc, idx) => (
                          <div key={idx} className={`tool-call ${tc.status}`}>
                            <span className="tool-icon">
                              {tc.status === 'running' ? '⏳' : '✓'}
                            </span>
                            <span className="tool-name">{tc.tool}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <>
                    <div className="agent-message-text">{message.content}</div>
                    {message.toolCalls && message.toolCalls.length > 0 && !message.error && (
                      <div className="tools-used">
                        <span className="tools-label">⚙ Used tools:</span>
                        {message.toolCalls.map((tc, idx) => (
                          <span key={idx} className="tool-badge">{tc.tool}</span>
                        ))}
                      </div>
                    )}
                    {message.type === 'agent' && !message.error && !message.thinking && message.fullSummary && (
                      <div className="message-feedback">
                        <span className="feedback-label">Was this helpful?</span>
                        <button
                          className="feedback-btn thumbs-up"
                          onClick={() => submitFeedback('positive', message)}
                          title="Helpful"
                        >
                          👍
                        </button>
                        <button
                          className="feedback-btn thumbs-down"
                          onClick={() => submitFeedback('negative', message)}
                          title="Not helpful"
                        >
                          👎
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
              <div className="agent-message-timestamp">
                {message.timestamp instanceof Date
                  ? message.timestamp.toLocaleTimeString()
                  : new Date(message.timestamp).toLocaleTimeString()}
              </div>
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="agent-input-container">
        <div className="agent-input-wrapper">
          <button
            className="tools-config-btn-input"
            onClick={() => setShowToolModal(true)}
            title="Configure available tools"
          >
            ⚙ Tools ({selectedTools.length}/{availableTools.length})
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="What would you like me to do?"
            rows={1}
            className="agent-message-input"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="agent-send-button"
          >
            Send
          </button>
        </div>
      </div>

      {/* Execution Log Tray */}
      {showLog && executionLog && (
        <div className={`execution-log ${logExpanded ? 'expanded' : ''}`}>
          <div className="execution-log-header">
            <h3>▭ Execution Log</h3>
            <div className="header-actions">
              <button
                onClick={downloadExecutionLog}
                className="download-log-btn"
                title="Download as JSON"
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
              <button onClick={() => setShowLog(false)} className="close-log-btn" aria-label="Close execution log">×</button>
            </div>
          </div>
          <div className="log-content">
            {/* Thoughts Section */}
            {executionLog.thoughts && executionLog.thoughts.length > 0 && (
              <div className="log-section">
                <h4>◇ Thoughts ({executionLog.thoughts.length} iterations)</h4>
                <div className="log-entries">
                  {executionLog.thoughts.map((thought, idx) => (
                    <div key={idx} className="log-entry">
                      <div className="log-entry-header">
                        <strong>Iteration {thought.iteration}</strong>
                        <span className="log-entry-action">Action: {thought.action}</span>
                      </div>
                      <div className="log-entry-content">
                        <div className="log-field">
                          <span className="log-label">Decision:</span>
                          <span>{thought.decision}</span>
                        </div>
                        {thought.thoughts && (
                          <div className="log-field">
                            <span className="log-label">Thoughts:</span>
                            <span className="log-thoughts">{thought.thoughts}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Tool Calls Section */}
            {executionLog.tool_calls && executionLog.tool_calls.length > 0 && (
              <div className="log-section">
                <h4>⚙ Tool Calls ({executionLog.tool_calls.length})</h4>
                <div className="log-entries">
                  {executionLog.tool_calls.map((call, idx) => (
                    <div key={idx} className={`log-entry tool-call-entry ${call.status}`}>
                      <div className="log-entry-header">
                        <strong>{idx + 1}. {call.tool}</strong>
                        <div className="header-badges">
                          {call.retry_count > 0 && (
                            <span className="retry-badge">
                              ⟲ {call.retry_count} {call.retry_count === 1 ? 'retry' : 'retries'}
                            </span>
                          )}
                          <span className={`log-status ${call.status}`}>
                            {call.status === 'completed' ? '✓' : call.status === 'failed' ? '✗' : '⏳'}
                            {' '}{call.status}
                          </span>
                        </div>
                      </div>
                      <div className="log-entry-content">
                        {/* Show attempts if there are multiple */}
                        {call.attempts && call.attempts.length > 1 && (
                          <div className="log-field attempts-field">
                            <span className="log-label">Attempts:</span>
                            <div className="attempts-list">
                              {call.attempts.map((attempt, attemptIdx) => (
                                <div key={attemptIdx} className={`attempt-item ${attempt.status}`}>
                                  <div className="attempt-header">
                                    <span className="attempt-number">Attempt {attempt.attempt}</span>
                                    <span className={`attempt-status ${attempt.status}`}>
                                      {attempt.status === 'completed' ? '✓' : attempt.status === 'failed' ? '✗' : '⏳'}
                                      {' '}{attempt.status}
                                    </span>
                                  </div>
                                  <div className="attempt-params">
                                    <strong>Params:</strong>
                                    <pre>{JSON.stringify(attempt.params, null, 2)}</pre>
                                  </div>
                                  {attempt.error && (
                                    <div className="attempt-error">
                                      <strong>Error:</strong> {attempt.error}
                                    </div>
                                  )}
                                  {attempt.result && (
                                    <div className="attempt-result">
                                      <strong>Result:</strong> {attempt.result}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Show retries if any */}
                        {call.retries && call.retries.length > 0 && (
                          <div className="log-field retries-field">
                            <span className="log-label">LLM Corrections:</span>
                            <div className="retries-list">
                              {call.retries.map((retry, retryIdx) => (
                                <div key={retryIdx} className="retry-item">
                                  <div className="retry-header">
                                    <span className="retry-number">Correction {retryIdx + 1}</span>
                                    <span className="retry-attempt">Attempt {retry.attempt}</span>
                                  </div>
                                  <div className="retry-error">
                                    <strong>Error:</strong> {retry.error}
                                  </div>
                                  <div className="retry-changes">
                                    <div className="param-change">
                                      <strong>✗ Previous:</strong>
                                      <pre>{JSON.stringify(retry.previous_params, null, 2)}</pre>
                                    </div>
                                    <div className="param-change">
                                      <strong>✓ Corrected:</strong>
                                      <pre>{JSON.stringify(retry.corrected_params, null, 2)}</pre>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Show single attempt info if no retries */}
                        {(!call.attempts || call.attempts.length === 1) && (
                          <>
                            <div className="log-field">
                              <span className="log-label">Params:</span>
                              <pre>{JSON.stringify(call.params, null, 2)}</pre>
                            </div>
                            {call.result && (
                              <div className="log-field">
                                <span className="log-label">Result:</span>
                                <div className="log-result">{call.result}</div>
                              </div>
                            )}
                            {call.error && (
                              <div className="log-field error">
                                <span className="log-label">Error:</span>
                                <span>{call.error}</span>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions Section */}
            {executionLog.actions && executionLog.actions.length > 0 && (
              <div className="log-section">
                <h4>◈ Actions ({executionLog.actions.length})</h4>
                <div className="log-entries">
                  {executionLog.actions.map((action, idx) => (
                    <div key={idx} className="log-entry">
                      <div className="log-entry-header">
                        <strong>Iteration {action.iteration}</strong>
                      </div>
                      <div className="log-entry-content">
                        <div className="log-field">
                          <span className="log-label">Result:</span>
                          <div className="log-result">
                            {typeof action.result === 'object'
                              ? JSON.stringify(action.result, null, 2)
                              : action.result}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tool Selection Modal */}
      {showToolModal && (
        <div
          className="tool-modal-overlay"
          onClick={() => setShowToolModal(false)}
        >
          <div
            className="tool-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="tool-modal-header">
              <h3>⚙ Configure Available Tools</h3>
              <button
                className="modal-close-btn"
                onClick={() => setShowToolModal(false)}
                title="Close"
              >
                ×
              </button>
            </div>
            <div className="tool-modal-body">
              <div className="tool-modal-actions">
                <button onClick={selectAllTools} className="select-all-btn">
                  ✓ Select All
                </button>
                <button onClick={deselectAllTools} className="deselect-all-btn">
                  ✗ Deselect All
                </button>
                <span className="tool-count">
                  {selectedTools.length} of {availableTools.length} selected
                </span>
              </div>
              <div className="tool-list">
                {availableTools.map((tool) => (
                  <div key={tool.name} className="tool-item">
                    <label className="tool-checkbox-label">
                      <input
                        type="checkbox"
                        checked={selectedTools.includes(tool.name)}
                        onChange={() => toggleTool(tool.name)}
                        className="tool-checkbox"
                      />
                      <div className="tool-info">
                        <span className="tool-name">{tool.name}</span>
                        <span className="tool-description">{tool.description}</span>
                      </div>
                    </label>
                  </div>
                ))}
              </div>
            </div>
            <div className="tool-modal-footer">
              <button
                className="apply-tools-btn"
                onClick={() => setShowToolModal(false)}
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
