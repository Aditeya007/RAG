// runBotForUser:

// Lets your Express backend call the Python RAG bot (or scraper) for a specific user by making an HTTP API request.

// Passes user ID, input, or other parameters so the Python backend knows which user's data to use.

// Returns the bot output (answer, stats, etc.) for use in your dashboard or API.

const axios = require('axios');

/**
 * Launch the RAG bot for a user by calling your Python FastAPI backend
 * @param {string} userId - The MongoDB user ID
 * @param {string} userInput - The user's query/input
 * @returns {Promise<Object>} - Bot's response data
 */
exports.runBotForUser = async (userId, userInput) => {
  try {
    // Get FastAPI endpoint from environment or use default
    const botApiUrl = process.env.FASTAPI_BOT_URL || 'http://localhost:8000';
    
    // Create a session ID that includes the user ID for tracking
    const sessionId = `user_${userId}_${Date.now()}`;
    
    console.log(`🤖 Calling FastAPI bot at ${botApiUrl}/chat`);
    console.log(`   Session ID: ${sessionId}`);
    console.log(`   Query: ${userInput}`);
    
    // API call to your FastAPI bot (matches the QuestionRequest Pydantic model)
    const response = await axios.post(
      `${botApiUrl}/chat`,
      {
        query: userInput,
        session_id: sessionId, // Pass session_id as expected by FastAPI
      },
      {
        timeout: 30000, // 30 second timeout
        headers: {
          'Content-Type': 'application/json',
        }
      }
    );
    
    console.log('✅ Bot response received successfully');
    return response.data; // Bot's answer (AnswerResponse: { answer: string })
  } catch (err) {
    console.error('❌ Bot job execution failed:', err.message);
    
    // Provide more specific error messages
    if (err.code === 'ECONNREFUSED') {
      throw new Error('Cannot connect to FastAPI bot - is it running?');
    } else if (err.response) {
      // FastAPI returned an error response
      throw new Error(`Bot API error: ${err.response.data?.detail || err.message}`);
    } else if (err.request) {
      // Request was made but no response received
      throw new Error('No response from bot API - request timeout');
    } else {
      throw new Error(`Bot job failed: ${err.message}`);
    }
  }
};
