import React from 'react';
import { Compass, CheckCircle2, AlertTriangle } from 'lucide-react';
import type { MeasurementSummary } from '../types/geospatial';

interface MetricsSummaryProps {
  summary: MeasurementSummary;
  sourceCrs?: string;
  projectedCrs?: string;
  status: string;
}

export const MetricsSummary: React.FC<MetricsSummaryProps> = ({
  summary,
  sourceCrs,
  projectedCrs,
  status
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Projection details banner */}
      <div className="crs-banner">
        <div className="crs-tag">
          <Compass size={13} />
          <span>Metric Projected CRS</span>
        </div>
        <div className="crs-value mono">
          {projectedCrs || 'N/A'}
        </div>
        <div className="crs-source">
          Source Coordinate System: <span className="mono">{sourceCrs || 'Unknown'}</span>
        </div>
      </div>

      {/* Numerical metric cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Polygon Area</div>
          <div className="metric-value mono">
            {summary.total_area_sq_m.toLocaleString()} m²
          </div>
          <div className="metric-sub mono">
            {summary.total_area_hectares.toFixed(4)} ha
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Total Line Length</div>
          <div className="metric-value mono">
            {summary.total_length_m.toLocaleString()} m
          </div>
          <div className="metric-sub mono">
            {summary.total_length_km.toFixed(3)} km
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Extracted Features</div>
          <div className="metric-value mono">
            {summary.total_features}
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {summary.polygon_count} poly · {summary.linestring_count} lines · {summary.point_count} pts
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-label">Processing Status</div>
          <div 
            className="metric-value" 
            style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: '6px', 
              fontSize: '14px', 
              color: status === 'COMPLETED' ? '#34d399' : '#f59e0b' 
            }}
          >
            {status === 'COMPLETED' ? (
              <>
                <CheckCircle2 size={16} />
                <span>COMPLETED</span>
              </>
            ) : (
              <>
                <AlertTriangle size={16} />
                <span>{status}</span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
