// Defines API endpoints for users to manage their info.

// Protected by auth middleware (must be logged in).

// Uses controllers for business logic.

// /api/user/me gives the profile of the currently logged-in user.


const express = require('express');
const router = express.Router();
const auth = require('../middleware/auth');
const userController = require('../controllers/userController');
const { validateProfileUpdate } = require('../middleware/validate');

/**
 * @route   GET /api/user/me
 * @desc    Get current user's profile
 * @access  Protected (requires JWT)
 */
router.get('/me', auth, userController.getMe);

/**
 * @route   PUT /api/user/me
 * @desc    Update current user's profile
 * @access  Protected (requires JWT)
 * @body    { name?, email?, username?, password? }
 */
router.put('/me', auth, validateProfileUpdate, userController.updateMe);

// (Optionally, add more later: delete account, view other stats, etc.)

module.exports = router;
