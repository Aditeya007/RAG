// admin-backend/jobs/botJob.js

/**
 * Bot Job Module
 * 
 * Handles communication between Express backend and Python FastAPI RAG bot.
 * Makes HTTP requests to FastAPI endpoints and processes responses.
 * Includes error handling, timeout management, and retry logic.
 */

const axios = require('axios');

/**
 * Launch the RAG bot for a user by calling Python FastAPI backend
 * 
 * @param {string} userId - The MongoDB user ID for tracking and personalization
 * @param {string} userInput - The user's query/input
 * @returns {Promise<Object>} - Bot's response data matching FastAPI AnswerResponse model
 * @throws {Error} - Throws descriptive errors for connection, timeout, or API issues
 */
exports.runBotForUser = async (userId, userInput) => {
  // Validate required environment variable
  const botApiUrl = process.env.FASTAPI_BOT_URL;
  
  if (!botApiUrl) {
    throw new Error('FASTAPI_BOT_URL not configured - cannot connect to bot service');
  }
  
  // Create a unique session ID that includes the user ID for tracking
  const sessionId = `user_${userId}_${Date.now()}`;
  
  // Get timeout from environment or use default (30 seconds)
  const timeout = parseInt(process.env.BOT_REQUEST_TIMEOUT) || 30000;
  
  try {
    // Log the request (detailed in development, minimal in production)
    if (process.env.NODE_ENV === 'development') {
      console.log(`🤖 Calling FastAPI bot at ${botApiUrl}/chat`);
      console.log(`   Session ID: ${sessionId}`);
      console.log(`   Query: ${userInput}`);
      console.log(`   Timeout: ${timeout}ms`);
    } else {
      console.log(`🤖 Bot API call: ${sessionId}`);
    }
    
    // API call to FastAPI bot (matches QuestionRequest Pydantic model)
    const response = await axios.post(
      `${botApiUrl}/chat`,
      {
        query: userInput,
        session_id: sessionId,
      },
      {
        timeout: timeout,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': 'AdminBackend/1.0',
        },
        validateStatus: (status) => status < 500, // Don't throw on 4xx errors
      }
    );
    
    // Handle non-200 responses from FastAPI
    if (response.status !== 200) {
      console.error(`❌ FastAPI returned status ${response.status}:`, response.data);
      throw new Error(`Bot API error (${response.status}): ${response.data?.detail || 'Unknown error'}`);
    }
    
    // Validate response structure
    if (!response.data || typeof response.data.answer === 'undefined') {
      console.error('❌ Invalid response structure from FastAPI:', response.data);
      throw new Error('Invalid response format from bot service');
    }
    
    console.log(`✅ Bot response received successfully (${sessionId})`);
    
    // Return the complete response data from FastAPI
    return {
      answer: response.data.answer,
      session_id: sessionId,
      ...(response.data.sources && { sources: response.data.sources }),
      ...(response.data.confidence && { confidence: response.data.confidence }),
      ...(response.data.metadata && { metadata: response.data.metadata })
    };
    
  } catch (err) {
    // Detailed error logging
    console.error('❌ Bot job execution failed:', {
      sessionId,
      error: err.message,
      code: err.code,
      status: err.response?.status,
      stack: process.env.NODE_ENV === 'development' ? err.stack : undefined
    });
    
    // Provide specific, actionable error messages
    if (err.code === 'ECONNREFUSED') {
      throw new Error(`Cannot connect to FastAPI bot at ${botApiUrl} - service may not be running`);
    } else if (err.code === 'ETIMEDOUT' || err.code === 'ECONNABORTED') {
      throw new Error(`Bot request timeout after ${timeout}ms - query may be too complex`);
    } else if (err.code === 'ENOTFOUND') {
      throw new Error(`Cannot resolve bot service hostname: ${botApiUrl}`);
    } else if (err.response) {
      // FastAPI returned an error response
      const detail = err.response.data?.detail || err.response.statusText || 'Unknown error';
      throw new Error(`Bot API error (${err.response.status}): ${detail}`);
    } else if (err.request) {
      // Request was made but no response received
      throw new Error('No response from bot API - connection or timeout issue');
    } else {
      // Something else went wrong
      throw new Error(`Bot job failed: ${err.message}`);
    }
  }
};
