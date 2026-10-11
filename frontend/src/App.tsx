import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { FileUpload } from './components/FileUpload';
import { MetricsSummary } from './components/MetricsSummary';
import { FeatureList } from './components/FeatureList';
import { MapViewer } from './components/MapViewer';
import type { FileMeasurementsResponse } from './types/geospatial';

export const App: React.FC = () => {
  const [measurementsData, setMeasurementsData] = useState<FileMeasurementsResponse | null>(null);
  const [geojsonData, setGeojsonData] = useState<any | null>(null);
  const [selectedFeatureIndex, setSelectedFeatureIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFileUpload = async (file: File) => {
    setIsLoading(true);
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const uploadRes = await fetch('/api/files/', {
        method: 'POST',
        body: formData,
      });

      if (!uploadRes.ok) {
        const errJson = await uploadRes.json().catch(() => ({}));
        throw new Error(errJson.detail || `Upload failed with HTTP ${uploadRes.status}`);
      }

      const fileInfo = await uploadRes.json();
      const fileId = fileInfo.id;

      // Fetch measurements and GeoJSON in parallel
      const [measRes, geoRes] = await Promise.all([
        fetch(`/api/files/${fileId}/measurements/`),
        fetch(`/api/files/${fileId}/geojson/`),
      ]);

      if (!measRes.ok || !geoRes.ok) {
        throw new Error('Failed to retrieve computed measurements from backend.');
      }

      const measData = await measRes.json();
      const gData = await geoRes.json();

      setMeasurementsData(measData);
      setGeojsonData(gData);
      setSelectedFeatureIndex(null);
    } catch (err: any) {
      console.error('Error handling file:', err);
      setErrorMessage(err.message || 'An unexpected error occurred during processing.');
    } finally {
      setIsLoading(false);
    }
  };

  // Automatically load the Bengaluru survey fixture on initial launch for immediate wow factor!
  useEffect(() => {
    const loadDefault = async () => {
      try {
        const res = await fetch('/sample_data/survey_bengaluru.kml');
        if (res.ok) {
          const blob = await res.blob();
          const defaultFile = new File([blob], 'survey_bengaluru.kml', {
            type: 'application/vnd.google-earth.kml+xml',
          });
          handleFileUpload(defaultFile);
        }
      } catch (e) {
        // Fallback silently if dev server not yet connected
      }
    };
    loadDefault();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <Header />

      <div className="app-layout">
        <aside className="sidebar">
          <FileUpload onUpload={handleFileUpload} isLoading={isLoading} />

          {errorMessage && (
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#f87171',
                borderRadius: '8px',
                padding: '12px',
                fontSize: '12px',
              }}
            >
              <b>Error:</b> {errorMessage}
            </div>
          )}

          {measurementsData && (
            <>
              <MetricsSummary
                summary={measurementsData.summary}
                sourceCrs={measurementsData.source_crs}
                projectedCrs={measurementsData.projected_crs}
                status={measurementsData.status}
              />

              <FeatureList
                features={measurementsData.features}
                selectedIndex={selectedFeatureIndex}
                onSelectFeature={(idx) => setSelectedFeatureIndex(idx)}
              />
            </>
          )}
        </aside>

        <main className="map-container">
          <MapViewer
            geojsonData={geojsonData}
            selectedFeatureIndex={selectedFeatureIndex}
            onFeatureClick={(idx) => setSelectedFeatureIndex(idx)}
          />

          {isLoading && (
            <div className="loading-box">
              <div className="spin-loader" />
              <div style={{ fontSize: '14px', fontWeight: 600 }}>
                Transforming CRS & Calculating Metric Geometries...
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
