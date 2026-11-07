import React, { useState, useEffect, useRef } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CustomerLogin } from './components/auth/CustomerLogin';
import { DevLogin } from './components/auth/DevLogin';
import { DeveloperDashboard } from './components/dev/DeveloperDashboard';
import { Header } from './components/Header';
import { WorkflowStepper, StepId } from './components/WorkflowStepper';
import { FileUpload } from './components/FileUpload';
import { OverviewDashboard } from './components/OverviewDashboard';
import { DataQualityCard } from './components/DataQualityCard';
import { ProcessOverview } from './components/ProcessOverview';
import { ProblemsView } from './components/ProblemsView';
import { OpportunitiesView } from './components/OpportunitiesView';
import { ExplanationsView } from './components/ExplanationsView';
import { ReportsView } from './components/ReportsView';
import { EvidenceDossierModal } from './components/EvidenceDossierModal';
import { MarketingLandingPage } from './components/marketing/MarketingLandingPage';

import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
  ExplanationResponse,
  OpportunityEvidenceDossier,
  EvidenceAuditManifest,
} from './types/api';

import {
  uploadAndValidateCsv,
  fetchProcessAnalytics,
  fetchProblemDetection,
  fetchPrioritisation,
  fetchExplanations,
  fetchEvidenceAudit,
} from './services/api';

import { AlertCircle, Terminal, ArrowRight } from 'lucide-react';

const AppContent: React.FC = () => {
  const { user, role, isAuthenticated, isLoading } = useAuth();

  // Navigation Routing State (supports direct URL access, refresh, and history navigation)
  const [currentPath, setCurrentPath] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return window.location.pathname || '/';
    }
    return '/';
  });

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigate = (path: string) => {
    if (typeof window !== 'undefined' && path !== window.location.pathname) {
      window.history.pushState({}, '', path);
      setCurrentPath(path);
    }
  };

  // Customer Operational Workspace State
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [currentStep, setCurrentStep] = useState<StepId>('quality');
  const [completedSteps, setCompletedSteps] = useState<Set<StepId>>(new Set());
  const [loadingStep, setLoadingStep] = useState<StepId | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Analytical State
  const [qualityReport, setQualityReport] = useState<DataQualityReport | null>(null);
  const [analytics, setAnalytics] = useState<ProcessAnalyticsResult | null>(null);
  const [problems, setProblems] = useState<ProblemDetectionResult | null>(null);
  const [prioritisation, setPrioritisation] = useState<PrioritisationResponse | null>(null);
  const [explanations, setExplanations] = useState<ExplanationResponse | null>(null);

  // Evidence Dossier Modal
  const [activeDossier, setActiveDossier] = useState<OpportunityEvidenceDossier | null>(null);
  const [dossierManifest, setDossierManifest] = useState<EvidenceAuditManifest | undefined>(undefined);
  const [, setLoadingDossier] = useState<boolean>(false);
  const activeRunId = useRef(0);

  // Data isolation reset on logout or dataset switch
  const handleReset = () => {
    activeRunId.current += 1;
    setFile(null);
    setIsProcessing(false);
    setCurrentStep('quality');
    setCompletedSteps(new Set());
    setLoadingStep(null);
    setError(null);
    setQualityReport(null);
    setAnalytics(null);
    setProblems(null);
    setPrioritisation(null);
    setExplanations(null);
    setActiveDossier(null);
    setDossierManifest(undefined);
    setLoadingDossier(false);
  };

  const handleFileSelected = async (selectedFile: File) => {
    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      setError('Invalid file type. Only CSV event logs (.csv) are accepted.');
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size exceeds maximum allowed limit of 10MB.');
      return;
    }

    // Reset previous run to prevent data leakage
    handleReset();
    const runId = activeRunId.current;
    setFile(selectedFile);
    setIsProcessing(true);
    const newCompleted = new Set<StepId>();

    try {
      // Step 1: Ingestion & Data Quality
      setLoadingStep('quality');
      const qualityData = await uploadAndValidateCsv(selectedFile);
      if (runId !== activeRunId.current) return;
      setQualityReport(qualityData);
      newCompleted.add('quality');
      setCompletedSteps(new Set(newCompleted));
      setCurrentStep('quality');

      if (qualityData.valid_rows === 0) {
        setError('No valid rows found in CSV file. Check data quality report for exact defects.');
        setIsProcessing(false);
        setLoadingStep(null);
        return;
      }

      // Step 2: Reconstruction & Analytics
      setLoadingStep('analytics');
      const analyticsData = await fetchProcessAnalytics(selectedFile);
      if (runId !== activeRunId.current) return;
      setAnalytics(analyticsData);
      newCompleted.add('analytics');
      setCompletedSteps(new Set(newCompleted));

      // Step 3: Neutral Problem Detection
      setLoadingStep('problems');
      const problemsData = await fetchProblemDetection(selectedFile);
      if (runId !== activeRunId.current) return;
      setProblems(problemsData);
      newCompleted.add('problems');
      setCompletedSteps(new Set(newCompleted));

      // Step 4: Opportunities & Economics Prioritisation
      setLoadingStep('opportunities');
      const prioritisationData = await fetchPrioritisation(selectedFile);
      if (runId !== activeRunId.current) return;
      setPrioritisation(prioritisationData);
      newCompleted.add('opportunities');
      setCompletedSteps(new Set(newCompleted));

      // Step 5: Explanations & Evidence Audit
      setLoadingStep('explanations');
      const explanationsData = await fetchExplanations(selectedFile);
      if (runId !== activeRunId.current) return;
      setExplanations(explanationsData);
      newCompleted.add('explanations');
      newCompleted.add('reports');
      newCompleted.add('overview');
      setCompletedSteps(new Set(newCompleted));

      // Pipeline complete: default to Executive Overview Dashboard
      setCurrentStep('overview');
    } catch (err: any) {
      if (runId === activeRunId.current) {
        setError(err.message || 'An error occurred while executing the operational pipeline.');
      }
    } finally {
      if (runId === activeRunId.current) {
        setIsProcessing(false);
        setLoadingStep(null);
      }
    }
  };

  const handleStepClick = (stepId: StepId) => {
    if (completedSteps.has(stepId) || stepId === 'overview') {
      setCurrentStep(stepId);
    }
  };

  const handleSelectDossier = async (opportunityId: string) => {
    if (!file) return;
    const runId = activeRunId.current;
    setLoadingDossier(true);
    try {
      const auditResp = await fetchEvidenceAudit(file, opportunityId);
      if (runId !== activeRunId.current) return;
      const dossier = auditResp.dossiers.find((d) => d.opportunity_id === opportunityId);
      if (dossier) {
        setActiveDossier(dossier);
        setDossierManifest(auditResp.manifest);
      }
    } catch (err: any) {
      if (runId === activeRunId.current) {
        setError(`Failed to load evidence dossier: ${err.message}`);
      }
    } finally {
      if (runId === activeRunId.current) setLoadingDossier(false);
    }
  };

  // -------------------------------------------------------------
  // ROUTING & AUTHENTICATION ENFORCEMENT
  // -------------------------------------------------------------

  // Show loading skeleton while restoring session
  if (isLoading) {
    return (
      <div className="login-page-container">
        <div className="session-restore-box">
          <div className="spinner"></div>
          <p>Verifying ProcessLens session...</p>
        </div>
      </div>
    );
  }

  // Developer Login Route (/dev/login)
  if (currentPath === '/dev/login') {
    return <DevLogin onNavigate={navigate} />;
  }

  // Developer Dashboard Route (/dev/dashboard)
  if (currentPath === '/dev/dashboard') {
    if (!isAuthenticated || role !== 'developer') {
      return <DevLogin onNavigate={navigate} />;
    }
    return <DeveloperDashboard onNavigate={navigate} />;
  }

  // Customer Login Route (/login)
  if (currentPath === '/login') {
    if (isAuthenticated) {
      if (role === 'developer') {
        return <DeveloperDashboard onNavigate={navigate} />;
      }
      // Redirect authenticated customer to workspace
      navigate('/');
    }
    return <CustomerLogin onNavigate={navigate} />;
  }

  // Explicit Marketing Landing Page Route (/landing or /home)
  if (currentPath === '/landing' || currentPath === '/home') {
    return <MarketingLandingPage onNavigate={navigate} isAuthenticated={isAuthenticated} />;
  }

  // Public Landing Page: Unauthenticated visitors at '/' see the Marketing Landing Page
  if (!isAuthenticated) {
    return <MarketingLandingPage onNavigate={navigate} isAuthenticated={false} />;
  }

  // Authenticated Workspace (Customer or Developer inspecting customer view)
  return (
    <div className="app-container">
      {/* Developer Banner if viewing customer operations workspace */}
      {role === 'developer' && (
        <div className="dev-preview-banner">
          <div className="dev-preview-content">
            <Terminal size={16} />
            <span>
              <strong>Developer Mode:</strong> Viewing Customer Operations Workspace as <code>{user?.email}</code>
            </span>
          </div>
          <button
            type="button"
            className="dev-preview-btn"
            onClick={() => navigate('/dev/dashboard')}
          >
            Return to Dev Console <ArrowRight size={14} />
          </button>
        </div>
      )}

      <Header
        hasActiveData={!!file}
        onReset={handleReset}
        onNavigate={navigate}
        datasetName={file?.name}
        dataQualityReport={qualityReport}
        onOpenQuality={() => handleStepClick('quality')}
      />


      <main className="main-content">
        {/* Error Alert Banner */}
        {error && (
          <div className="alert-card error" role="alert">
            <AlertCircle size={20} className="alert-icon" />
            <div className="alert-body">
              <span className="alert-title">Operational Warning</span>
              <p className="alert-message">{error}</p>
            </div>
            <button
              type="button"
              className="alert-close"
              onClick={() => setError(null)}
              aria-label="Dismiss message"
            >
              ×
            </button>
          </div>
        )}

        {/* Initial Empty Upload State */}
        {!file && (
          <FileUpload
            onFileSelected={handleFileSelected}
            isUploading={isProcessing}
          />
        )}

        {/* Pipeline Execution / Workspace Navigation State */}
        {file && (
          <div className="dashboard-content">
            <WorkflowStepper
              currentStep={currentStep}
              completedSteps={completedSteps}
              loadingStep={loadingStep}
              onSelectStep={handleStepClick}
              canNavigate={!isProcessing}
            />

            <div className="step-content-area">
              {currentStep === 'overview' && qualityReport && analytics && problems && prioritisation && (
                <OverviewDashboard
                  qualityReport={qualityReport}
                  analytics={analytics}
                  problems={problems}
                  prioritisation={prioritisation}
                  explanations={explanations}
                  onNavigateToStep={(stepId: StepId) => handleStepClick(stepId)}
                  onSelectDossier={handleSelectDossier}
                />
              )}

              {currentStep === 'quality' && (
                qualityReport ? (
                  <DataQualityCard report={qualityReport} />
                ) : (
                  <div className="loading-card glass-panel">
                    <span className="spinner" />
                    <p>Auditing dataset structure & validating schema integrity...</p>
                  </div>
                )
              )}

              {currentStep === 'analytics' && (
                analytics ? (
                  <ProcessOverview analytics={analytics} />
                ) : (
                  <div className="loading-card glass-panel">
                    <span className="spinner" />
                    <p>Reconstructing process event paths & cycle times...</p>
                  </div>
                )
              )}

              {currentStep === 'problems' && (
                problems ? (
                  <ProblemsView problems={problems} />
                ) : (
                  <div className="loading-card glass-panel">
                    <span className="spinner" />
                    <p>Scanning for bottlenecks, rework loops, and operational signals...</p>
                  </div>
                )
              )}

              {currentStep === 'opportunities' && (
                prioritisation ? (
                  <OpportunitiesView
                    prioritisation={prioritisation}
                    onSelectDossier={handleSelectDossier}
                  />
                ) : (
                  <div className="loading-card glass-panel">
                    <span className="spinner" />
                    <p>Prioritising opportunity portfolio roadmap & readiness...</p>
                  </div>
                )
              )}

              {currentStep === 'explanations' && (
                explanations ? (
                  <ExplanationsView
                    explanations={explanations}
                    onSelectDossier={handleSelectDossier}
                  />
                ) : (
                  <div className="loading-card glass-panel">
                    <span className="spinner" />
                    <p>Generating evidence-backed executive explanations...</p>
                  </div>
                )
              )}

              {currentStep === 'reports' && qualityReport && analytics && problems && prioritisation && (
                <ReportsView
                  qualityReport={qualityReport}
                  analytics={analytics}
                  problems={problems}
                  prioritisation={prioritisation}
                  explanations={explanations}
                />
              )}
            </div>
          </div>
        )}

        {/* Detail-on-Demand Evidence Dossier Modal */}
        {activeDossier && (
          <EvidenceDossierModal
            dossier={activeDossier}
            manifest={dossierManifest}
            onClose={() => setActiveDossier(null)}
          />
        )}
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;
