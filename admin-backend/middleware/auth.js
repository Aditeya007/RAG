// Blocks unauthenticated users from accessing protected endpoints
// Checks that user is logged in:

// Looks for a JWT token in HTTP requests.

// If token is present and valid, the request continues (user has access).

// If not, sends an error and blocks access.

// Protects routes:

// Any route using this (router.get('/private', auth, ...)) will require a valid login
const jwt = require('jsonwebtoken');

// Middleware to verify JWT and attach user info to req
const auth = (req, res, next) => {
  // JWT is sent in 'Authorization: Bearer <token>' header
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token, authorization denied' });

  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded; // Attach user info to request
    next();
  } catch (err) {
    res.status(401).json({ error: 'Token is not valid' });
  }
};

module.exports = auth;
