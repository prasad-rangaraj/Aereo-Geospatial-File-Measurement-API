import React, { useState } from 'react';
import type { FeatureItem } from '../types/geospatial';

interface FeatureListProps {
  features: FeatureItem[];
  selectedIndex: number | null;
  onSelectFeature: (index: number) => void;
}

export const FeatureList: React.FC<FeatureListProps> = ({
  features,
  selectedIndex,
  onSelectFeature
}) => {
  const [filterType, setFilterType] = useState<string>('ALL');

  const filtered = features.filter(f => {
    if (filterType === 'ALL') return true;
    if (filterType === 'POLYGON') return f.geometry_type.includes('Polygon');
    if (filterType === 'LINE') return f.geometry_type.includes('Line');
    if (filterType === 'POINT') return f.geometry_type.includes('Point');
    return true;
  });

  return (
    <div className="features-section">
      <div className="features-header">
        <span className="features-title">Extracted Vector Features</span>
        <span className="badge-count mono">{features.length} items</span>
      </div>

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
        {['ALL', 'POLYGON', 'LINE', 'POINT'].map(type => (
          <button
            key={type}
            type="button"
            onClick={() => setFilterType(type)}
            style={{
              background: filterType === type ? 'var(--primary)' : 'var(--bg-card)',
              color: filterType === type ? '#ffffff' : 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
              padding: '4px 8px',
              borderRadius: '6px',
              fontSize: '10px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s'
            }}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="feature-cards-container">
        {filtered.map(feat => {
          const isSelected = selectedIndex === feat.feature_index;
          const isPoly = feat.geometry_type.includes('Polygon');
          const isLine = feat.geometry_type.includes('Line');
          const isPoint = feat.geometry_type.includes('Point');

          return (
            <div
              key={feat.feature_index}
              className={`feature-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectFeature(feat.feature_index)}
            >
              <div className="feature-card-top">
                <span className="feature-title">
                  {feat.feature_id || `Feature #${feat.feature_index}`}
                </span>
                <span
                  className={`type-pill ${
                    isPoly
                      ? 'pill-polygon'
                      : isLine
                      ? 'pill-line'
                      : 'pill-point'
                  }`}
                >
                  {feat.geometry_type}
                </span>
              </div>

              <div className="feature-measurement-text mono">
                {isPoly && (
                  <div>
                    Area: <b>{feat.measurement.area_sq_m?.toLocaleString() || 0} m²</b>
                    <span style={{ color: 'var(--text-muted)', marginLeft: '6px', fontSize: '11px' }}>
                      ({feat.measurement.area_hectares || 0} ha)
                    </span>
                    <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '2px' }}>
                      Perimeter: {feat.measurement.perimeter_m?.toLocaleString() || 0} m
                    </div>
                  </div>
                )}

                {isLine && (
                  <div>
                    Length: <b>{feat.measurement.length_m?.toLocaleString() || 0} m</b>
                    <span style={{ color: 'var(--text-muted)', marginLeft: '6px', fontSize: '11px' }}>
                      ({feat.measurement.length_km || 0} km)
                    </span>
                  </div>
                )}

                {isPoint && (
                  <div style={{ color: 'var(--text-dim)', fontSize: '11px' }}>
                    {feat.measurement.note || 'Point geometry: zero planar area & length'}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
