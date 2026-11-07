import React, { useState, useRef } from 'react';
import { UploadCloud, FileSpreadsheet, Sparkles, Database } from 'lucide-react';

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  isUploading?: boolean;
}

const FALLBACK_QUICKSTART_CSV = `case_id,activity,timestamp,resource,department,order_value,quantity,product_type,priority,event_type
ORD-00001,Order Received,2026-02-20 07:13:00.000000000,Sales-02,Sales,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Order Verification,2026-02-20 09:03:50.651268903,Sales-03,Sales,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Inventory Check,2026-02-22 00:27:54.099501169,Warehouse-01,Warehouse,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Production Planning,2026-02-22 03:48:59.144865877,Planner-01,Planning,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Production,2026-02-22 07:46:24.690823881,Prod-01,Production,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Quality Inspection,2026-02-22 18:29:03.399351255,QC-02,Quality,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Dispatch,2026-02-22 20:47:23.472887540,Warehouse-01,Warehouse,91257.49,237,Motor Housing,Urgent,complete
ORD-00001,Invoice,2026-02-22 22:54:08.701549102,Finance-01,Finance,91257.49,237,Motor Housing,Urgent,complete
ORD-00002,Order Received,2026-02-16 06:55:00.000000000,Sales-02,Sales,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Order Verification,2026-02-16 07:31:37.829163098,Sales-01,Sales,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Inventory Check,2026-02-16 15:33:23.030769283,Warehouse-01,Warehouse,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Production Planning,2026-02-16 19:13:16.040572525,Planner-01,Planning,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Production,2026-02-16 21:33:48.887553264,Prod-04,Production,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Quality Inspection,2026-02-17 10:50:30.330077185,QC-01,Quality,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Dispatch,2026-02-17 13:42:46.459164315,Warehouse-01,Warehouse,31198.99,241,Industrial Pump,Normal,complete
ORD-00002,Invoice,2026-02-17 15:35:32.238891221,Finance-01,Finance,31198.99,241,Industrial Pump,Normal,complete`;

export const FileUpload: React.FC<FileUploadProps> = ({ onFileSelected, isUploading = false }) => {
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isLoadingSample, setIsLoadingSample] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = (file: File) => {
    onFileSelected(file);
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

  const handleLoadSample = async () => {
    if (isUploading || isLoadingSample) return;
    setIsLoadingSample(true);
    try {
      const response = await fetch('/samples/quickstart.csv');
      if (response.ok) {
        const text = await response.text();
        const blob = new Blob([text], { type: 'text/csv' });
        const file = new File([blob], 'manufacturing_orders_quickstart.csv', { type: 'text/csv' });
        processFile(file);
        return;
      }
    } catch {
      // Fallback to inline sample if network fetch fails
    } finally {
      setIsLoadingSample(false);
    }

    const blob = new Blob([FALLBACK_QUICKSTART_CSV], { type: 'text/csv' });
    const file = new File([blob], 'manufacturing_orders_quickstart.csv', { type: 'text/csv' });
    processFile(file);
  };

  return (
    <div className="pl-upload-wrapper">
      <div className="pl-upload-container">
        <div className="pl-upload-header-intro">
          <div className="pl-upload-tag">
            <Database size={13} className="text-cyan" />
            <span>OPERATIONAL DATA INGESTION</span>
          </div>
          <h2 className="pl-upload-title">Import Operational Event Log</h2>
          <p className="pl-upload-subtitle">
            ProcessLens reconstructs deterministic end-to-end execution paths, isolates cycle-time bottlenecks,
            and calculates automation potential backed by transparent evidence.
          </p>
        </div>

        <div
          className={`pl-dropzone ${isDragging ? 'is-dragging' : ''} ${isUploading ? 'is-uploading' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload CSV Event Log"
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv"
            style={{ display: 'none' }}
            disabled={isUploading}
          />

          <div className="pl-dropzone-icon-box">
            {isUploading ? (
              <span className="pl-spinner-lg" />
            ) : (
              <UploadCloud size={36} className="text-cyan" />
            )}
          </div>

          <div className="pl-dropzone-text">
            <h3 className="pl-dropzone-heading">
              {isUploading ? 'Executing Analysis Pipeline...' : 'Drop your CSV event log here, or browse files'}
            </h3>
            <p className="pl-dropzone-sub">
              Canonical schema columns: <code className="font-mono text-cyan">case_id</code>, <code className="font-mono text-cyan">activity</code>, <code className="font-mono text-cyan">timestamp</code>
            </p>
            <p className="pl-dropzone-limits">
              Maximum file size: 10MB. UTF-8 or ASCII encoded CSV format.
            </p>
          </div>
        </div>

        {/* Quick Sample Dataset Action */}
        <div className="pl-quick-samples-card">
          <div className="pl-quick-samples-info">
            <div className="pl-quick-samples-title">
              <Sparkles size={14} className="text-cyan" />
              <span>Explore ProcessLens with Pilot Demonstration Data</span>
            </div>
            <p className="pl-quick-samples-desc">
              Load a verified manufacturing order fulfillment log with 100 cases, multi-stage rework, and bottleneck transitions.
            </p>
          </div>

          <button
            type="button"
            className="pl-btn pl-btn-primary pl-btn-sm"
            disabled={isUploading || isLoadingSample}
            onClick={handleLoadSample}
          >
            {isLoadingSample ? (
              <span className="pl-btn-spinner" />
            ) : (
              <FileSpreadsheet size={14} />
            )}
            <span>Load Quickstart Log</span>
          </button>
        </div>

        {/* Analytical Chain Badges */}
        <div className="pl-chain-banner">
          <div className="pl-chain-step">
            <span className="pl-chain-dot" />
            <span className="pl-chain-label">Operational Data</span>
          </div>
          <span className="pl-chain-arrow">&rarr;</span>
          <div className="pl-chain-step">
            <span className="pl-chain-dot dot-teal" />
            <span className="pl-chain-label">Evidence</span>
          </div>
          <span className="pl-chain-arrow">&rarr;</span>
          <div className="pl-chain-step">
            <span className="pl-chain-dot dot-amber" />
            <span className="pl-chain-label">Economics</span>
          </div>
          <span className="pl-chain-arrow">&rarr;</span>
          <div className="pl-chain-step">
            <span className="pl-chain-dot dot-cyan" />
            <span className="pl-chain-label">Decision</span>
          </div>
        </div>
      </div>
    </div>
  );
};
