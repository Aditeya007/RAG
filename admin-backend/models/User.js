// admin-backend/models/User.js

const mongoose = require('mongoose');

// User Schema
const UserSchema = new mongoose.Schema(
  {
    name: { type: String },
    email: { type: String, required: true, unique: true, lowercase: true },
    username: { type: String, required: true, unique: true },
    password: { type: String, required: true }, // Store only hashed (bcrypt) passwords!
    // You can add more later: roles, isAdmin, bot config, etc.
  },
  {
    timestamps: true, // Auto-manages createdAt/updatedAt
  }
);

// Export for use everywhere (routes, controllers)
module.exports = mongoose.model('User', UserSchema);
