import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

interface MapViewerProps {
  geojsonData: any | null;
  selectedFeatureIndex: number | null;
  onFeatureClick: (index: number) => void;
}

export const MapViewer: React.FC<MapViewerProps> = ({
  geojsonData,
  selectedFeatureIndex,
  onFeatureClick
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const geojsonLayerRef = useRef<L.GeoJSON | null>(null);
  const featureLayersMap = useRef<Map<number, L.Layer>>(new Map());

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      zoomControl: true,
      attributionControl: true
    }).setView([12.9716, 77.5946], 13); // Default to Bengaluru

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update GeoJSON Layer
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (geojsonLayerRef.current) {
      map.removeLayer(geojsonLayerRef.current);
      geojsonLayerRef.current = null;
      featureLayersMap.current.clear();
    }

    if (!geojsonData || !geojsonData.features || geojsonData.features.length === 0) {
      return;
    }

    let currentIndex = 0;
    const geoLayer = L.geoJSON(geojsonData, {
      style: (feature) => {
        const type = feature?.geometry?.type || '';
        if (type.includes('Polygon')) {
          return {
            color: '#10b981',
            weight: 2,
            fillColor: '#34d399',
            fillOpacity: 0.35
          };
        }
        return {
          color: '#3b82f6',
          weight: 4,
          opacity: 0.85
        };
      },
      pointToLayer: (_feature, latlng) => {
        return L.circleMarker(latlng, {
          radius: 7,
          fillColor: '#f59e0b',
          color: '#ffffff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9
        });
      },
      onEachFeature: (feature, layer) => {
        const idx = currentIndex;
        featureLayersMap.current.set(idx, layer);

        const props = feature.properties || {};
        const meas = props._measurement || {};

        let popupHtml = `
          <div style="font-family: sans-serif; font-size: 12px; color: #1e293b;">
            <div style="font-weight: 700; font-size: 13px; margin-bottom: 4px;">
              ${feature.id || 'Feature #' + idx}
            </div>
            <div>Type: <b>${meas.geometry_type || 'Unknown'}</b></div>
        `;

        if (meas.area_sq_m) {
          popupHtml += `<div>Area: <b>${meas.area_sq_m.toLocaleString()} m²</b> (${meas.area_hectares} ha)</div>`;
          popupHtml += `<div>Perimeter: <b>${meas.perimeter_m?.toLocaleString() || 0} m</b></div>`;
        }

        if (meas.length_m) {
          popupHtml += `<div>Length: <b>${meas.length_m.toLocaleString()} m</b> (${meas.length_km} km)</div>`;
        }

        popupHtml += `</div>`;
        layer.bindPopup(popupHtml);

        layer.on('click', () => {
          onFeatureClick(idx);
        });

        currentIndex++;
      }
    }).addTo(map);

    geojsonLayerRef.current = geoLayer;

    // Fit map bounds to loaded data
    if (geoLayer.getBounds().isValid()) {
      map.fitBounds(geoLayer.getBounds(), { padding: [50, 50] });
    }
  }, [geojsonData]);

  // Handle selected feature focus
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || selectedFeatureIndex === null) return;

    const layer = featureLayersMap.current.get(selectedFeatureIndex);
    if (layer) {
      if ((layer as any).getBounds) {
        map.fitBounds((layer as any).getBounds(), { padding: [80, 80], maxZoom: 17 });
      } else if ((layer as any).getLatLng) {
        map.setView((layer as any).getLatLng(), 16);
      }
      layer.openPopup();
    }
  }, [selectedFeatureIndex]);

  return <div ref={mapContainerRef} className="map-container" />;
};
