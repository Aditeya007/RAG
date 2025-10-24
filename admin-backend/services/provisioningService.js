// admin-backend/services/provisioningService.js

const crypto = require('crypto');

/**
 * Normalize usernames into safe slugs for resource identifiers.
 * Ensures generated URIs remain filesystem and URL friendly.
 */
const toSlug = (value) => {
  if (!value) {
    return 'user';
  }

  return value
    .toString()
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    || 'user';
};

/**
 * Small helper to join base URLs with paths without double slashes.
 */
const joinUrl = (base, path) => {
  const sanitizedBase = base.replace(/\/+$/, '');
  const sanitizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${sanitizedBase}${sanitizedPath}`;
};

/**
 * Build deterministic resource identifiers so that repeated provisioning
 * for the same user yields the same endpoints, enabling idempotency.
 */
const buildResourceId = ({ userId, username }) => {
  const slug = toSlug(username);
  const hash = crypto
    .createHash('sha1')
    .update(`${userId}:${username}`)
    .digest('hex')
    .slice(0, 10);
  return `${slug}-${hash}`;
};

/**
 * Generate resource locations for a user. Values can be overridden via env.
 */
const provisionResourcesForUser = ({ userId, username }) => {
  if (!userId || !username) {
    const error = new Error('Cannot provision resources without userId and username');
    error.statusCode = 500;
    throw error;
  }

  const resourceId = buildResourceId({ userId, username });
  const slug = toSlug(username);

  const databaseBase = process.env.DEFAULT_DATABASE_URI_BASE || 'mongodb://localhost:27017';
  const botBase = process.env.DEFAULT_BOT_BASE_URL || 'http://localhost:8000';
  const schedulerBase = process.env.DEFAULT_SCHEDULER_BASE_URL || 'http://localhost:9000';
  const scraperBase = process.env.DEFAULT_SCRAPER_BASE_URL || 'http://localhost:7000';

  const databaseName = `rag_${slug}_${resourceId.slice(-6)}`;

  return {
    databaseUri: `${databaseBase.replace(/\/+$/, '')}/${databaseName}`,
    botEndpoint: joinUrl(botBase, `/api/bots/${resourceId}`),
    schedulerEndpoint: joinUrl(schedulerBase, `/api/schedules/${resourceId}`),
    scraperEndpoint: joinUrl(scraperBase, `/api/scrape/${resourceId}`)
  };
};

/**
 * Ensure a user document always carries provisioned resources.
 */
const ensureUserResources = async (userDoc) => {
  if (!userDoc) {
    return null;
  }

  const needsProvisioning = [
    userDoc.databaseUri,
    userDoc.botEndpoint,
    userDoc.schedulerEndpoint,
    userDoc.scraperEndpoint
  ].some((value) => !value);

  if (!needsProvisioning) {
    return userDoc;
  }

  const resources = provisionResourcesForUser({
    userId: userDoc._id.toString(),
    username: userDoc.username
  });

  userDoc.set(resources);
  await userDoc.save();
  return userDoc;
};

module.exports = {
  provisionResourcesForUser,
  ensureUserResources
};
