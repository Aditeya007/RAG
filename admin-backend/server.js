// admin-backend/server.js

require('dotenv').config();                // Loads secrets from .env

const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');              // Allow frontend calls (React dev server)
const dbConnect = require('./utils/db');   // Your MongoDB connection utility

const authRoutes = require('./routes/auth');
const userRoutes = require('./routes/user');
const botRoutes = require('./routes/bot');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',  // Configure allowed origins
  credentials: true
}));
app.use(express.json());                   // Parse JSON requests
app.use(express.urlencoded({ extended: true })); // Parse URL-encoded bodies

// Request logging middleware (simple version)
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Connect to MongoDB
dbConnect();

// API Routes
app.use('/api/auth', authRoutes);          // Register, login
app.use('/api/user', userRoutes);          // User info, CRUD
app.use('/api/bot', botRoutes);            // Bot interaction endpoints

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'OK',
    timestamp: new Date().toISOString(),
    service: 'admin-backend',
    mongodb: mongoose.connection.readyState === 1 ? 'connected' : 'disconnected'
  });
});

// Root endpoint
app.get('/', (req, res) => {
  res.json({ 
    message: 'Admin Backend API',
    version: '1.0.0',
    endpoints: [
      'POST /api/auth/register',
      'POST /api/auth/login',
      'GET /api/user/me',
      'PUT /api/user/me',
      'POST /api/bot/run',
      'GET /api/health'
    ]
  });
});

// 404 handler for undefined routes
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('❌ Unhandled error:', err);
  res.status(err.status || 500).json({ 
    error: err.message || 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
});

// Start server
app.listen(PORT, () => {
  console.log('='.repeat(60));
  console.log(`🚀 Admin Backend Server Started`);
  console.log(`📡 Port: ${PORT}`);
  console.log(`🌐 Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 MongoDB: ${mongoose.connection.readyState === 1 ? '✅ Connected' : '⏳ Connecting...'}`);
  console.log(`🤖 FastAPI Bot URL: ${process.env.FASTAPI_BOT_URL || 'http://localhost:8000'}`);
  console.log('='.repeat(60));
});


