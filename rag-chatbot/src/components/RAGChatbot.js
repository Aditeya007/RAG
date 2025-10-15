import React, { useState, useRef, useEffect } from 'react';

const RAGChatbot = () => {
  const [messages, setMessages] = useState([
    { id: 0, sender: 'bot', text: "Welcome! I'm your AI-powered assistant. How may I assist you today?" }
  ]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [status, setStatus] = useState('Online');
  const [leadCollectionActive, setLeadCollectionActive] = useState(false);

  const sessionId = useRef('react_user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9));
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (text, sender) => {
    setMessages((prev) => [...prev, { id: prev.length, sender, text }]);
  };

  const sendMessage = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isSending) return;

    addMessage(trimmedInput, 'user');
    setInput('');
    setIsSending(true);
    setStatus('Processing...');
    addMessage('', 'bot-typing');

    // 🔍 DEBUG LINES - Check what's being sent
    console.log('🔍 REACT DEBUG - Sending session_id:', sessionId.current);
    console.log('🔍 REACT DEBUG - Full request body:', JSON.stringify({ 
      question: trimmedInput, 
      session_id: sessionId.current 
    }));

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmedInput, session_id: sessionId.current })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setMessages((prev) => prev.filter(msg => msg.sender !== 'bot-typing'));
      addMessage(data.answer, 'bot');

      if (data.answer.includes('provide your details') || data.answer.includes('name , email and phone')) {
        setLeadCollectionActive(true);
        setStatus('Contact Form Active');
      } else if (leadCollectionActive && data.answer.includes('Perfect')) {
        setLeadCollectionActive(false);
        setStatus('Information Saved');
        setTimeout(() => setStatus('Online'), 3000);
      } else {
        setStatus('Online');
      }
    } catch (error) {
      setMessages((prev) => prev.filter(msg => msg.sender !== 'bot-typing'));
      addMessage(`Connection error. Please ensure the service is running or try again later.`, 'bot');
      setStatus('Connection Error');
      setTimeout(() => setStatus('Online'), 5000);
    }
    setIsSending(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div style={styles.outerContainer}>
      <div style={styles.container}>
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <div style={styles.logo}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="3" stroke="#1e40af" strokeWidth="2"/>
                <circle cx="9" cy="9" r="2" fill="#1e40af"/>
                <circle cx="15" cy="9" r="2" fill="#1e40af"/>
                <path d="M8 15 Q12 18 16 15" stroke="#1e40af" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <h3 style={styles.headerTitle}>Assistant</h3>
              <p style={styles.headerSubtitle}>Knowledge Base & Support</p>
            </div>
          </div>
          <div style={styles.statusIndicator}>
            <span style={styles.statusDot(status)}></span>
            <span style={styles.statusText}>{status}</span>
          </div>
        </div>

        <div style={styles.chatContainer}>
          <div style={styles.chatMessages}>
            {messages.map(({ id, sender, text }) =>
              sender === 'bot-typing' ? (
                <div key={id} style={styles.messageWrapper('bot')}>
                  <div style={styles.avatar('bot')}>AI</div>
                  <div style={styles.typingIndicator}>
                    <span style={styles.typingDot}></span>
                    <span style={styles.typingDot}></span>
                    <span style={styles.typingDot}></span>
                  </div>
                </div>
              ) : (
                <div key={id} style={styles.messageWrapper(sender)}>
                  {sender === 'bot' && <div style={styles.avatar('bot')}>AI</div>}
                  <div style={styles.messageContent}>
                    <div style={styles.message(sender)}>
                      {text}
                    </div>
                    <div style={styles.messageTime}>{formatTime()}</div>
                  </div>
                  {sender === 'user' && <div style={styles.avatar('user')}>You</div>}
                </div>
              )
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={styles.inputContainer}>
            <textarea
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isSending}
              style={styles.textInput}
              rows="1"
            />
            <button
              onClick={sendMessage}
              disabled={isSending || !input.trim()}
              style={{
                ...styles.sendButton,
                ...(isSending || !input.trim() ? styles.sendButtonDisabled : {})
              }}
              aria-label="Send message"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>

        <div style={styles.footer}>
          <p style={styles.footerText}>
            Powered by Aditeya Mitra • Type your question or request pricing information
          </p>
        </div>
      </div>
    </div>
  );
};

const styles = {
  outerContainer: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
  },
  container: {
    width: '100%',
    maxWidth: '900px',
    background: '#ffffff',
    borderRadius: '12px',
    overflow: 'hidden',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05)'
  },
  header: {
    background: 'linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%)',
    padding: '20px 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)'
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px'
  },
  logo: {
    width: '40px',
    height: '40px',
    background: '#ffffff',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  headerTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '600',
    color: '#ffffff',
    letterSpacing: '-0.5px'
  },
  headerSubtitle: {
    margin: 0,
    fontSize: '12px',
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: '2px'
  },
  statusIndicator: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    background: 'rgba(255, 255, 255, 0.15)',
    padding: '6px 12px',
    borderRadius: '20px'
  },
  statusDot: (status) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: status === 'Online' ? '#10b981' : 
                status === 'Processing...' ? '#f59e0b' : 
                status === 'Contact Form Active' ? '#3b82f6' :
                status === 'Information Saved' ? '#10b981' : '#ef4444',
    animation: status === 'Processing...' ? 'pulse 1.5s infinite' : 'none'
  }),
  statusText: {
    fontSize: '12px',
    color: '#ffffff',
    fontWeight: '500'
  },
  chatContainer: {
    height: '500px',
    display: 'flex',
    flexDirection: 'column',
    background: '#fafbfc'
  },
  chatMessages: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px',
    display: 'flex',
    flexDirection: 'column',
    gap: '16px'
  },
  messageWrapper: (sender) => ({
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    flexDirection: sender === 'user' ? 'row-reverse' : 'row'
  }),
  avatar: (sender) => ({
    width: '32px',
    height: '32px',
    borderRadius: '8px',
    background: sender === 'bot' ? '#1e40af' : '#6b7280',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: '600',
    flexShrink: 0
  }),
  messageContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    maxWidth: '70%'
  },
  message: (sender) => ({
    padding: '12px 16px',
    borderRadius: sender === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
    background: sender === 'user' ? '#1e40af' : '#ffffff',
    color: sender === 'user' ? '#ffffff' : '#1f2937',
    fontSize: '14px',
    lineHeight: '1.5',
    boxShadow: sender === 'bot' ? '0 1px 2px rgba(0, 0, 0, 0.05)' : 'none',
    border: sender === 'bot' ? '1px solid #e5e7eb' : 'none'
  }),
  messageTime: {
    fontSize: '11px',
    color: '#9ca3af',
    paddingLeft: '4px'
  },
  typingIndicator: {
    padding: '12px 20px',
    background: '#ffffff',
    borderRadius: '12px',
    display: 'flex',
    gap: '4px',
    alignItems: 'center',
    border: '1px solid #e5e7eb'
  },
  typingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: '#9ca3af',
    animation: 'typing 1.4s infinite'
  },
  inputContainer: {
    padding: '16px 24px',
    background: '#ffffff',
    borderTop: '1px solid #e5e7eb',
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-end'
  },
  textInput: {
    flex: 1,
    padding: '10px 14px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    resize: 'none',
    outline: 'none',
    fontFamily: 'inherit',
    lineHeight: '1.5',
    minHeight: '40px',
    maxHeight: '100px',
    transition: 'border-color 0.2s',
    background: '#f9fafb',
    ':focus': {
      borderColor: '#1e40af',
      background: '#ffffff'
    }
  },
  sendButton: {
    padding: '10px 16px',
    background: '#1e40af',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
    ':hover': {
      background: '#1e3a8a'
    }
  },
  sendButtonDisabled: {
    background: '#9ca3af',
    cursor: 'not-allowed'
  },
  footer: {
    padding: '12px 24px',
    background: '#f9fafb',
    borderTop: '1px solid #e5e7eb'
  },
  footerText: {
    margin: 0,
    fontSize: '12px',
    color: '#6b7280',
    textAlign: 'center'
  }
};

// Add animations
const styleSheet = document.createElement("style");
styleSheet.type = "text/css";
styleSheet.innerText = `
  @keyframes typing {
    0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
    30% { opacity: 1; transform: translateY(-10px); }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  textarea:focus {
    border-color: #1e40af !important;
    background: #ffffff !important;
  }
  button:hover:not(:disabled) {
    background: #1e3a8a !important;
    transform: translateY(-1px);
  }
  button:active:not(:disabled) {
    transform: translateY(0);
  }
  *::-webkit-scrollbar {
    width: 6px;
  }
  *::-webkit-scrollbar-track {
    background: #f1f1f1;
  }
  *::-webkit-scrollbar-thumb {
    background: #cbd5e1;
    border-radius: 3px;
  }
  *::-webkit-scrollbar-thumb:hover {
    background: #94a3b8;
  }
`;
document.head.appendChild(styleSheet);

export default RAGChatbot;
