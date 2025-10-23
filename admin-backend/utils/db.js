// admin-backend/utils/db.js

const mongoose = require('mongoose');

// Read MongoDB URI from env (use dotenv in server.js)
const MONGO_URI = process.env.MONGO_URI;

if (!MONGO_URI) {
  throw new Error('MongoDB URI not found in environment variables!');
}

// Use this for async/await connection in your server
const dbConnect = async () => {
  try {
    // Detailed logs for startup and error
    console.log('🔗 Connecting to MongoDB...');
    await mongoose.connect(MONGO_URI, {
      useNewUrlParser: true,
      useUnifiedTopology: true,
      // Optional for production: tuning poolSize
      maxPoolSize: 20,
    });
    console.log('✅ MongoDB connection established!');
  } catch (err) {
    console.error('❌ Failed to connect to MongoDB:', err.message);
    process.exit(1); // Fatal exit if DB connection fails
  }
};

// Clean shutdown (optional, good for production clusters)
process.on('SIGINT', async () => {
  await mongoose.connection.close();
  console.log('🛑 MongoDB connection closed due to app termination');
  process.exit(0);
});

module.exports = dbConnect;
