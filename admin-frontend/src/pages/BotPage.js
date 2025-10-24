// src/pages/BotPage.js

import React, { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

import '../styles/index.css';

function BotPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // RAG Chatbot app URL (default port 3001 to avoid conflict with admin frontend on 3000)
  const ragChatbotUrl = process.env.REACT_APP_RAG_CHATBOT_URL || 'http://localhost:3001';

  // Open rag-chatbot in new tab when component mounts
  useEffect(() => {
    const openChatbot = () => {
      window.open(ragChatbotUrl, '_blank', 'noopener,noreferrer');
    };
    
    // Small delay to ensure smooth transition
    const timer = setTimeout(openChatbot, 100);
    
    return () => clearTimeout(timer);
  }, [ragChatbotUrl]);

  const handleOpenChatbot = () => {
    window.open(ragChatbotUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="bot-container">
      <header className="bot-header">
        <h2 className="bot-heading">🤖 RAG AI Assistant</h2>
        <div className="bot-header-actions">
          <button className="bot-back-btn" onClick={() => navigate('/dashboard')}>
            ← Dashboard
          </button>
        </div>
      </header>

      <div className="bot-redirect-content">
        <div className="bot-redirect-card">
          <div className="bot-redirect-icon">💬</div>
          <h3>RAG Chatbot</h3>
          <p className="bot-redirect-message">
            Your chatbot should open in a new tab automatically.
          </p>
          <p className="bot-redirect-info">
            If it didn't open, click the button below:
          </p>
          
          <button className="bot-open-btn" onClick={handleOpenChatbot}>
            🚀 Open RAG Chatbot
          </button>

          <div className="bot-redirect-details">
            <p><strong>Chatbot URL:</strong> {ragChatbotUrl}</p>
            <p><strong>User:</strong> {user?.username || user?.name}</p>
            <p><strong>Status:</strong> <span className="status-active">Active</span></p>
          </div>

          <div className="bot-redirect-note">
            <p>💡 <strong>Note:</strong> The RAG chatbot runs as a standalone React application. 
            Make sure it's running on port 3001 before clicking the button above.</p>
            <pre className="bot-command">cd rag-chatbot && PORT=3001 npm start</pre>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BotPage;
