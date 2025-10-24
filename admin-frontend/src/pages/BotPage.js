// src/pages/BotPage.js

import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import Loader from '../components/Loader';

import '../styles/index.css';

function BotPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const botEndpoint = user?.botEndpoint || '';

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    if (!input.trim()) return;

    if (!botEndpoint) {
      setError('Bot endpoint not provisioned for your account.');
      return;
    }

    const userMessage = input.trim();
    
    // Display user message
    setMessages(msgs => [...msgs, { sender: 'user', text: userMessage }]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      const response = await fetch(botEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query: userMessage }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();

      setMessages(msgs => [
        ...msgs,
        { sender: 'bot', text: data.answer || data.response || 'No response received' }
      ]);
    } catch (err) {
      console.error('Bot communication error:', err);
      setMessages(msgs => [
        ...msgs,
        { sender: 'error', text: 'Failed to communicate with bot. Please try again.' }
      ]);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleClearChat() {
    if (window.confirm('Clear chat history?')) {
      setMessages([]);
      setError('');
    }
  }

  return (
    <div className="bot-container">
      <header className="bot-header">
        <h2 className="bot-heading">🤖 Bot Interaction</h2>
        <div className="bot-header-actions">
          {messages.length > 0 && (
            <button className="bot-clear-btn" onClick={handleClearChat}>
              Clear Chat
            </button>
          )}
          <button className="bot-back-btn" onClick={() => navigate('/dashboard')}>
            ← Dashboard
          </button>
        </div>
      </header>

      {!botEndpoint ? (
        <div className="bot-error-banner">
          <strong>⚠️ Bot Not Available</strong>
          <p>No bot endpoint has been provisioned for your account yet.</p>
          <p>Please contact your administrator.</p>
        </div>
      ) : (
        <>
          <div className="bot-messages">
            {messages.length === 0 && (
              <div className="bot-welcome">
                <p>👋 Hello! Ask me anything about your RAG system.</p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`bot-message bot-message-${msg.sender}`}
              >
                <span>{msg.text}</span>
              </div>
            ))}
            {loading && (
              <div className="bot-message bot-message-bot bot-typing">
                <span>Thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="bot-error-inline">
              {error}
            </div>
          )}

          <form className="bot-form" onSubmit={handleSend}>
            <input
              className="bot-input"
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={loading}
              placeholder="Type your message here..."
              autoFocus
            />
            <button
              className="bot-send-btn"
              type="submit"
              disabled={loading || !input.trim()}
            >
              {loading ? '...' : 'Send'}
            </button>
          </form>
        </>
      )}
    </div>
  );
}

export default BotPage;
