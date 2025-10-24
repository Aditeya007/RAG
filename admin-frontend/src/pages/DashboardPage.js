// src/pages/DashboardPage.js

import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

import '../styles/index.css';

function DashboardPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // User resource endpoints, to be filled from backend profile (as you build infra)
  const dbUri = user?.databaseUri || 'Not provisioned yet';
  const botEndpoint = user?.botEndpoint || 'Not provisioned yet';
  const schedulerEndpoint = user?.schedulerEndpoint || 'Not provisioned yet';
  const scraperEndpoint = user?.scraperEndpoint || 'Not provisioned yet';

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <h2>Welcome, {user?.name || user?.username || 'Admin'}!</h2>
        <button className="dashboard-logout-btn" onClick={handleLogout}>
          Logout
        </button>
      </header>

      <section className="dashboard-info">
        <h3>Your Isolated System Resources</h3>
        <p className="dashboard-subtitle">
          Each user has their own dedicated infrastructure for the RAG chatbot system.
        </p>
        <table className="dashboard-table">
          <tbody>
            <tr>
              <td><strong>Database URI:</strong></td>
              <td className="dashboard-value">{dbUri}</td>
            </tr>
            <tr>
              <td><strong>Bot Endpoint:</strong></td>
              <td className="dashboard-value">{botEndpoint}</td>
            </tr>
            <tr>
              <td><strong>Scheduler Endpoint:</strong></td>
              <td className="dashboard-value">{schedulerEndpoint}</td>
            </tr>
            <tr>
              <td><strong>Scraper Endpoint:</strong></td>
              <td className="dashboard-value">{scraperEndpoint}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="dashboard-actions">
        <button
          className="dashboard-action-btn"
          onClick={() => navigate('/bot')}
        >
          🤖 Interact with Bot
        </button>
        <button
          className="dashboard-action-btn"
          onClick={() => navigate('/health')}
        >
          ❤️ System Health Status
        </button>
      </section>
    </div>
  );
}

export default DashboardPage;
