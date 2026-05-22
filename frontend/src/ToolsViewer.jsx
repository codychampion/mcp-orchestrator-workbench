import React, { useState, useEffect } from 'react'
import { API_BASE } from './utils/api'
import CopyButton from './components/CopyButton'
import './ToolsViewer.css'

export default function ToolsViewer() {
  const [tools, setTools] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedTool, setSelectedTool] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    fetchTools()
  }, [])

  const fetchTools = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_BASE}/tools`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      setTools(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching tools:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const filteredTools = tools.filter(tool =>
    tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tool.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const renderParamsSchema = (schema) => {
    if (!schema || typeof schema !== 'object') {
      return <span className="no-params">No parameters</span>
    }

    const properties = schema.properties || {}
    const required = schema.required || []

    if (Object.keys(properties).length === 0) {
      return <span className="no-params">No parameters</span>
    }

    return (
      <div className="params-list">
        {Object.entries(properties).map(([paramName, paramDetails]) => (
          <div key={paramName} className="param-item">
            <div className="param-header">
              <span className="param-name">{paramName}</span>
              {required.includes(paramName) && (
                <span className="param-required">required</span>
              )}
              {paramDetails.type && (
                <span className="param-type">{paramDetails.type}</span>
              )}
            </div>
            {paramDetails.description && (
              <div className="param-description">{paramDetails.description}</div>
            )}
            {paramDetails.enum && (
              <div className="param-enum">
                <strong>Allowed values:</strong> {paramDetails.enum.join(', ')}
              </div>
            )}
            {paramDetails.default !== undefined && (
              <div className="param-default">
                <strong>Default:</strong> {JSON.stringify(paramDetails.default)}
              </div>
            )}
          </div>
        ))}
      </div>
    )
  }

  if (loading) {
    return (
      <div className="tools-viewer-container">
        <div className="tools-loading">
          <div className="loading-spinner"></div>
          <p>Loading tools...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="tools-viewer-container">
        <div className="tools-error">
          <h2>Error Loading Tools</h2>
          <p>{error}</p>
          <button onClick={fetchTools} className="retry-btn">
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="tools-viewer-container">
      <div className="tools-search-bar">
        <div className="tools-stats-inline">
          <div className="stat-badge">
            <span className="stat-value">{tools.length}</span>
            <span className="stat-label">Total</span>
          </div>
          <div className="stat-badge">
            <span className="stat-value">{filteredTools.length}</span>
            <span className="stat-label">Filtered</span>
          </div>
        </div>
        <input
          type="text"
          placeholder="Search tools by name or description..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="tools-search-input"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="clear-search-btn"
            title="Clear search"
            aria-label="Clear search query"
          >
            ✕
          </button>
        )}
      </div>

      <div className="tools-content">
        <div className="tools-grid">
          {filteredTools.map((tool) => (
            <div
              key={tool.name}
              className={`tool-card ${selectedTool?.name === tool.name ? 'selected' : ''}`}
              onClick={() => setSelectedTool(tool)}
            >
              <div className="tool-card-header">
                <h3 className="tool-card-name">{tool.name}</h3>
              </div>
              <p className="tool-card-description">{tool.description}</p>
              <div className="tool-card-footer">
                {tool.params_schema?.properties && (
                  <span className="tool-param-count">
                    {Object.keys(tool.params_schema.properties).length} parameter(s)
                  </span>
                )}
                <span className="view-details-link">View details →</span>
              </div>
            </div>
          ))}
        </div>

        {selectedTool && (
          <div className="tool-details-panel">
            <div className="tool-details-header">
              <h2>{selectedTool.name}</h2>
              <button
                onClick={() => setSelectedTool(null)}
                className="close-details-btn"
                title="Close details"
                aria-label="Close tool details panel"
              >
                ✕
              </button>
            </div>
            <div className="tool-details-body">
              <div className="detail-section">
                <h3>Description</h3>
                <p className="detail-description">{selectedTool.description}</p>
              </div>

              <div className="detail-section">
                <h3>Parameters</h3>
                {renderParamsSchema(selectedTool.params_schema)}
              </div>

              <div className="detail-section">
                <h3>JSON Schema</h3>
                <div style={{ position: 'relative' }}>
                  <CopyButton
                    text={JSON.stringify(selectedTool.params_schema, null, 2)}
                    className="copy-btn-top-right"
                  />
                  <pre className="json-schema">
                    {JSON.stringify(selectedTool.params_schema, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="detail-section">
                <h3>Full Metadata</h3>
                <div style={{ position: 'relative' }}>
                  <CopyButton
                    text={JSON.stringify(selectedTool, null, 2)}
                    className="copy-btn-top-right"
                  />
                  <pre className="json-schema">
                    {JSON.stringify(selectedTool, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {filteredTools.length === 0 && searchQuery && (
        <div className="no-results">
          <h3>No tools found</h3>
          <p>No tools match your search query "{searchQuery}"</p>
        </div>
      )}
    </div>
  )
}
