const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const botController = require('../controllers/botController');
const { validateBotRun } = require('../middleware/validate');

/**
 * @route   POST /api/bot/run
 * @desc    Run the RAG bot with user's query
 * @access  Protected (requires JWT)
 * @body    { input: string }
 * @returns { answer: string } - The bot's response
 */
router.post('/run', auth, validateBotRun, botController.runBot);

module.exports = router;
