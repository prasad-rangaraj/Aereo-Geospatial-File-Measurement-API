import React from 'react';
import { Activity, FileCode } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="brand-badge">AEREO</div>
        <div className="header-title-group">
          <h1>Geospatial File Measurement Platform</h1>
          <p>Automated Vector Feature Extraction & Projected Coordinate Metric Calculations</p>
        </div>
      </div>
      <div className="header-actions">
        <a 
          href="/docs" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="btn-link"
          title="Open interactive Swagger REST API documentation"
        >
          <FileCode size={14} />
          <span>Swagger API</span>
        </a>
        <a 
          href="/api/health" 
          target="_blank" 
          rel="noopener noreferrer" 
          className="btn-link"
          title="Check backend health status"
        >
          <Activity size={14} />
          <span>Health</span>
        </a>
      </div>
    </header>
  );
};
