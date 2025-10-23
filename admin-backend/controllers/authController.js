// admin-backend/controllers/authController.js

const User = require('../models/User');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

/**
 * Register a new user
 * @route   POST /api/auth/register
 * @access  Public
 * @param   {Object} req.body - { name, email, username, password }
 * @returns {Object} { message: string }
 */
exports.registerUser = async (req, res) => {
  const { name, email, username, password } = req.body;
  
  try {
    // Check if email or username already exists
    const existingEmail = await User.findOne({ email: email.toLowerCase() });
    const existingUsername = await User.findOne({ username });
    
    if (existingEmail) {
      return res.status(400).json({ 
        error: 'Email already in use',
        field: 'email'
      });
    }
    
    if (existingUsername) {
      return res.status(400).json({ 
        error: 'Username already in use',
        field: 'username'
      });
    }

    // Hash the password securely
    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    // Create and save user
    const user = new User({ 
      name: name.trim(), 
      email: email.toLowerCase().trim(), 
      username: username.trim(), 
      password: hashedPassword 
    });
    
    await user.save();

    console.log(`✅ New user registered: ${username} (${email})`);
    
    res.status(201).json({ 
      message: 'User registered successfully',
      user: {
        id: user._id,
        name: user.name,
        username: user.username,
        email: user.email
      }
    });
  } catch (err) {
    console.error('❌ Register error:', err);
    
    // Handle mongoose validation errors
    if (err.name === 'ValidationError') {
      const messages = Object.values(err.errors).map(e => e.message);
      return res.status(400).json({ error: messages.join(', ') });
    }
    
    res.status(500).json({ error: 'Server error during registration' });
  }
};

/**
 * Login a user and return JWT token
 * @route   POST /api/auth/login
 * @access  Public
 * @param   {Object} req.body - { username, password }
 * @returns {Object} { token: string, user: Object }
 */
exports.loginUser = async (req, res) => {
  const { username, password } = req.body;
  
  try {
    // Find user by username (case-insensitive)
    const user = await User.findOne({ username: username.trim() });
    
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Compare password hash
    const isMatch = await bcrypt.compare(password, user.password);
    
    if (!isMatch) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    // Sign JWT token (expires in 1 day)
    const token = jwt.sign(
      { 
        userId: user._id, 
        username: user.username, 
        email: user.email 
      },
      process.env.JWT_SECRET,
      { expiresIn: '1d' }
    );
    
    console.log(`✅ User logged in: ${username}`);
    
    res.json({
      token,
      user: { 
        id: user._id, 
        name: user.name, 
        username: user.username, 
        email: user.email 
      }
    });
  } catch (err) {
    console.error('❌ Login error:', err);
    res.status(500).json({ error: 'Server error during login' });
  }
};
