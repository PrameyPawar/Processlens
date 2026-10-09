import React, { useState, useRef } from 'react';

interface FileUploadProps {
  onUploadSuccess: (data: any) => void;
  onUploadError: (errorMsg: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess, onUploadError }) => {
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      onUploadError('Invalid file type. Please upload a valid CSV event log.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      onUploadError('File size exceeds maximum allowed limit of 10MB.');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/v1/ingestion/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (response.ok) {
        onUploadSuccess(result);
      } else {
        onUploadError(result.detail || 'Failed to parse CSV file.');
      }
    } catch (err: any) {
      onUploadError('Network error connecting to backend API.');
    } finally {
      setUploading(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  return (
    <div
      className={`dropzone ${isDragging ? 'active' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".csv"
        style={{ display: 'none' }}
      />
      <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📄</div>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
        {uploading ? 'Processing CSV file...' : 'Drop your CSV Event Log here, or Click to Browse'}
      </h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
        Accepts canonical CSV schema with <code>case_id</code>, <code>activity</code>, and <code>timestamp</code> (Max 10MB)
      </p>
    </div>
  );
};
