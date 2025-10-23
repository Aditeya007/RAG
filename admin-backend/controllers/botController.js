// admin-backend/controllers/botController.js

const botJob = require('../jobs/botJob');

/**
 * Run the RAG bot with user's query
 * @route   POST /api/bot/run
 * @access  Protected (requires JWT)
 * @param   {Object} req.body - { input: string }
 * @returns {Object} { answer: string } - The bot's response from FastAPI
 */
exports.runBot = async (req, res) => {
  // Get user info from JWT (set by auth middleware)
  const userId = req.user.userId;
  const username = req.user.username;
  const { input } = req.body;
  
  try {
    console.log(`🤖 Bot request from user: ${username} (${userId})`);
    console.log(`   Query: "${input}"`);
    
    // Call the bot job to interact with FastAPI backend
    const botResult = await botJob.runBotForUser(userId, input.trim());
    
    // FastAPI returns { answer: string } as per AnswerResponse model
    console.log(`✅ Bot response received for user: ${username}`);
    
    res.json({
      ...botResult,
      user_id: userId // Include user ID in response for frontend tracking
    });
  } catch (err) {
    console.error(`❌ Bot error for user ${username}:`, err.message);
    
    // Determine appropriate status code based on error
    let statusCode = 500;
    let errorMessage = err.message || 'Failed to run bot';
    
    if (err.message.includes('Cannot connect')) {
      statusCode = 503; // Service unavailable
      errorMessage = 'Bot service is currently unavailable. Please try again later.';
    } else if (err.message.includes('timeout')) {
      statusCode = 504; // Gateway timeout
      errorMessage = 'Bot request timed out. Please try again.';
    }
    
    res.status(statusCode).json({ 
      error: errorMessage,
      details: process.env.NODE_ENV === 'development' ? err.message : undefined
    });
  }
};
