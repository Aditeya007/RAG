// admin-backend/models/User.js

const mongoose = require('mongoose');

/**
 * User Schema
 * Represents a user in the RAG Admin system
 * 
 * Security notes:
 * - Passwords are never stored in plain text (hashed with bcrypt in controller)
 * - Email is stored in lowercase for case-insensitive lookups
 * - Unique indexes prevent duplicate usernames/emails
 */
const UserSchema = new mongoose.Schema(
  {
    name: { 
      type: String, 
      required: [true, 'Name is required'],
      trim: true,
      minlength: [2, 'Name must be at least 2 characters'],
      maxlength: [100, 'Name cannot exceed 100 characters']
    },
    email: { 
      type: String, 
      required: [true, 'Email is required'], 
      unique: true, 
      lowercase: true,
      trim: true,
      match: [/^[^\s@]+@[^\s@]+\.[^\s@]+$/, 'Please provide a valid email address']
    },
    username: { 
      type: String, 
      required: [true, 'Username is required'], 
      unique: true,
      trim: true,
      minlength: [3, 'Username must be at least 3 characters'],
      maxlength: [30, 'Username cannot exceed 30 characters'],
      match: [/^[a-zA-Z0-9_]+$/, 'Username can only contain letters, numbers, and underscores']
    },
    password: { 
      type: String, 
      required: [true, 'Password is required'],
      minlength: [6, 'Password must be at least 6 characters']
      // Note: Stored as bcrypt hash, never plain text!
    },
    // Future extensions (uncomment when needed):
    // role: { 
    //   type: String, 
    //   enum: ['user', 'admin', 'moderator'], 
    //   default: 'user' 
    // },
    // isActive: { 
    //   type: Boolean, 
    //   default: true 
    // },
    // lastLogin: { 
    //   type: Date 
    // },
    // botPreferences: {
    //   type: mongoose.Schema.Types.Mixed,
    //   default: {}
    // }
  },
  {
    timestamps: true, // Auto-manages createdAt/updatedAt fields
    collection: 'users' // Explicit collection name
  }
);

// Indexes for performance
UserSchema.index({ email: 1 });
UserSchema.index({ username: 1 });
UserSchema.index({ createdAt: -1 });

// Instance method to get public profile (exclude password)
UserSchema.methods.toPublicProfile = function() {
  return {
    id: this._id,
    name: this.name,
    username: this.username,
    email: this.email,
    createdAt: this.createdAt,
    updatedAt: this.updatedAt
  };
};

// Static method to find user by email or username
UserSchema.statics.findByEmailOrUsername = function(identifier) {
  return this.findOne({
    $or: [
      { email: identifier.toLowerCase() },
      { username: identifier }
    ]
  });
};

// Export for use everywhere (routes, controllers)
module.exports = mongoose.model('User', UserSchema);
