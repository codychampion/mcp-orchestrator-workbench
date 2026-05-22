import React, {useState, useRef, useEffect} from 'react'
import './ChatInterface.css'
import { API_BASE } from './utils/api'

export default function ChatInterface({ selectedModel }) {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('chatMessages')
    return saved ? JSON.parse(saved) : []
  })
  const [conversationHistory, setConversationHistory] = useState(() => {
    const saved = localStorage.getItem('conversationHistory')
    return saved ? JSON.parse(saved) : []
  })
  const [currentConversationId, setCurrentConversationId] = useState(() => {
    return localStorage.getItem('currentConversationId') || null
  })
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)

  const scrollToBottom = () => {
    if (!isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Detect user scrolling
  useEffect(() => {
    const container = messagesContainerRef.current
    if (!container) return

    let scrollTimer = null

    const handleScroll = () => {
      setIsUserScrolling(true)

      if (scrollTimer) {
        clearTimeout(scrollTimer)
      }

      const isAtBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - 10

      if (isAtBottom) {
        setIsUserScrolling(false)
      } else {
        scrollTimer = setTimeout(() => {
          setIsUserScrolling(false)
        }, 2000)
      }
    }

    container.addEventListener('scroll', handleScroll)
    return () => {
      container.removeEventListener('scroll', handleScroll)
      if (scrollTimer) clearTimeout(scrollTimer)
    }
  }, [])

  // Save messages to localStorage
  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages))
  }, [messages])

  useEffect(() => {
    localStorage.setItem('conversationHistory', JSON.stringify(conversationHistory))
  }, [conversationHistory])

  useEffect(() => {
    if (currentConversationId) {
      localStorage.setItem('currentConversationId', currentConversationId)
    }
  }, [currentConversationId])

  const saveCurrentConversation = () => {
    if (messages.length === 0) return

    const conversationId = currentConversationId || Date.now().toString()
    const conversation = {
      id: conversationId,
      title: messages.find(m => m.type === 'user')?.content?.slice(0, 50) || 'New Conversation',
      messages: [...messages],
      timestamp: new Date().toISOString()
    }

    const updatedHistory = conversationHistory.filter(c => c.id !== conversationId)
    updatedHistory.unshift(conversation)
    setConversationHistory(updatedHistory.slice(0, 20))
  }

  const startNewConversation = () => {
    if (messages.length > 0) {
      if (!window.confirm('Start a new conversation? Your current conversation will be saved to history.')) {
        return
      }
    }
    saveCurrentConversation()
    setMessages([])
    setCurrentConversationId(null)
    localStorage.removeItem('currentConversationId')
  }

  const loadConversation = (conversation) => {
    saveCurrentConversation()
    setMessages(conversation.messages)
    setCurrentConversationId(conversation.id)
    setShowHistory(false)
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    // Set conversation ID if first message
    if (!currentConversationId) {
      setCurrentConversationId(Date.now().toString())
    }

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Create abort controller with 60 second timeout
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          goal: input,
          chat_history: messages,
          model: selectedModel
        }),
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const data = await response.json()

      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: data.content || data.error || 'No response received',
        timestamp: new Date(),
        model_used: data.model_used,
        error: !!data.error
      }

      setMessages(prev => [...prev, assistantMessage])

    } catch (error) {
      clearTimeout(timeoutId)
      console.error('Error:', error)

      let errorMsg = 'Sorry, I encountered an error while processing your request.'
      if (error.name === 'AbortError') {
        errorMsg = 'Request timed out. The server may be experiencing issues or rate limiting. Please try again.'
      } else if (error.message.includes('fetch')) {
        errorMsg = 'Could not connect to the server. Please check your connection.'
      }

      const errorMessage = {
        id: Date.now() + 2,
        type: 'assistant',
        content: errorMsg,
        timestamp: new Date(),
        error: true
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-interface">
      {/* Conversation History Sidebar */}
      {showHistory && (
        <div className="history-sidebar">
          <div className="history-header">
            <h3>▭ Conversation History</h3>
            <button
              className="close-history-btn"
              onClick={() => setShowHistory(false)}
              aria-label="Close conversation history"
            >
              ✕
            </button>
          </div>
          <div className="history-list">
            {conversationHistory.map(conversation => (
              <div
                key={conversation.id}
                className={`history-item ${conversation.id === currentConversationId ? 'active' : ''}`}
                onClick={() => loadConversation(conversation)}
              >
                <div className="history-title">{conversation.title}</div>
                <div className="history-timestamp">
                  {new Date(conversation.timestamp).toLocaleDateString()}
                </div>
              </div>
            ))}
            {conversationHistory.length === 0 && (
              <div className="history-empty">No previous conversations</div>
            )}
          </div>
        </div>
      )}

      <div className="chat-container">
        <div className="chat-header">
          <div className="header-left">
            <button
              className="history-btn"
              onClick={() => setShowHistory(true)}
              title="View conversation history"
            >
              ▭ History
            </button>
            <button
              className="new-chat-btn"
              onClick={startNewConversation}
              title="Start new conversation"
            >
              + New Chat
            </button>
          </div>

          <div className="header-right"></div>
        </div>

        <div className="messages-container" ref={messagesContainerRef}>
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome-message">
                <p>Ask me anything! I'm here to help with questions, ideas, or just to chat.</p>
                <div className="example-prompts">
                  <button onClick={() => setInput('Tell me an interesting fact')}>
                    ● Tell me a fact
                  </button>
                  <button onClick={() => setInput('What can you help me with?')}>
                    ◯ What can you do?
                  </button>
                  <button onClick={() => setInput('Explain quantum computing in simple terms')}>
                    ◐ Explain quantum computing
                  </button>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div key={message.id} className={`message ${message.type}`}>
                <div className="message-content">
                  <div className="message-text">{message.content}</div>
                </div>
                <div className="message-timestamp">
                  {message.timestamp instanceof Date
                    ? message.timestamp.toLocaleTimeString()
                    : new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="message assistant loading">
                <div className="message-content">
                  <div className="loading-message">
                    <div className="loading-spinner"></div>
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              rows={1}
              className="message-input"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="send-button"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
