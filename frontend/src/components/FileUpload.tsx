import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, Archive } from 'lucide-react';

interface FileUploadProps {
  onUpload: (file: File) => void;
  isLoading: boolean;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUpload, isLoading }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files[0]);
    }
  };

  const loadSampleFixture = async (type: 'bengaluru' | 'parcels') => {
    const filename = type === 'bengaluru' ? 'survey_bengaluru.kml' : 'cadastral_parcels.zip';
    const sampleUrl = `/sample_data/${filename}`;
    try {
      const response = await fetch(sampleUrl);
      if (!response.ok) {
        throw new Error(`Failed to load fixture ${filename}`);
      }
      const blob = await response.blob();
      const file = new File([blob], filename, {
        type: type === 'bengaluru' ? 'application/vnd.google-earth.kml+xml' : 'application/zip'
      });
      onUpload(file);
    } catch (err: any) {
      alert(`Error loading sample: ${err.message}`);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      <div
        className={`dropzone ${isDragOver ? 'active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <UploadCloud className="dropzone-icon" />
        <div className="dropzone-title">
          {isLoading ? 'Processing Spatial Features...' : 'Upload Shapefile ZIP or KML'}
        </div>
        <div className="dropzone-subtitle">
          Drag & drop .zip or .kml, or click to browse
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".kml,.zip"
          style={{ display: 'none' }}
          onChange={handleFileInputChange}
          disabled={isLoading}
        />
      </div>

      <div className="sample-bar">
        <span className="sample-title">Or test with verified fixtures:</span>
        <div className="sample-btn-group">
          <button
            type="button"
            className="btn-sample"
            onClick={() => loadSampleFixture('bengaluru')}
            disabled={isLoading}
          >
            <FileText size={13} color="#60a5fa" />
            <span>Bengaluru (KML)</span>
          </button>
          <button
            type="button"
            className="btn-sample"
            onClick={() => loadSampleFixture('parcels')}
            disabled={isLoading}
          >
            <Archive size={13} color="#34d399" />
            <span>Parcels (ZIP)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
