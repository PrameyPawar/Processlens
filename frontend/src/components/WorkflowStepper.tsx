import React from 'react';
import {
  LayoutDashboard,
  BarChart2,
  AlertTriangle,
  Target,
  BookOpen,
  FileText,
  FileSpreadsheet,
} from 'lucide-react';

export type StepId =
  | 'overview'
  | 'quality'
  | 'analytics'
  | 'problems'
  | 'opportunities'
  | 'explanations'
  | 'reports';

interface WorkflowStepperProps {
  currentStep: StepId;
  completedSteps: Set<StepId>;
  loadingStep: StepId | null;
  onSelectStep: (step: StepId) => void;
  canNavigate: boolean;
}

interface StepDef {
  id: StepId;
  label: string;
  ariaLabel: string;
  icon: React.ReactNode;
}

const PRIMARY_WORKSPACES: StepDef[] = [
  { id: 'overview', label: 'Overview', ariaLabel: 'Overview', icon: <LayoutDashboard size={15} /> },
  { id: 'analytics', label: 'Process Explorer', ariaLabel: '2. Process Overview (Process Explorer)', icon: <BarChart2 size={15} /> },
  { id: 'problems', label: 'Findings', ariaLabel: '3. Problems & Signals (Findings)', icon: <AlertTriangle size={15} /> },
  { id: 'opportunities', label: 'Opportunities', ariaLabel: '4. Opportunities & Roadmap', icon: <Target size={15} /> },
  { id: 'explanations', label: 'Evidence & Explanations', ariaLabel: '5. Grounded Explanations (Evidence & Explanations)', icon: <BookOpen size={15} /> },
  { id: 'reports', label: 'Reports', ariaLabel: '6. Reports & Export', icon: <FileText size={15} /> },
];

const QUALITY_STEP: StepDef = {
  id: 'quality',
  label: 'Data Quality Audit',
  ariaLabel: 'Schema Integrity & Quality Audit',
  icon: <FileSpreadsheet size={15} />,
};

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({
  currentStep,
  completedSteps,
  loadingStep,
  onSelectStep,
  canNavigate,
}) => {
  // If user is actively inspecting Data Quality, surface it in navigation
  const stepsToShow = currentStep === 'quality'
    ? [QUALITY_STEP, ...PRIMARY_WORKSPACES]
    : PRIMARY_WORKSPACES;

  return (
    <nav className="pl-primary-nav" aria-label="Primary Application Navigation">
      <div className="pl-nav-scroll-container">
        {stepsToShow.map((step) => {
          const isCurrent = currentStep === step.id;
          const isCompleted = completedSteps.has(step.id);
          const isLoading = loadingStep === step.id;
          const isOverviewOrReports = step.id === 'overview' || step.id === 'reports';
          const isClickable =
            canNavigate &&
            (isCompleted || isCurrent || (isOverviewOrReports && completedSteps.has('quality')));

          return (
            <button
              key={step.id}
              type="button"
              className={`pl-nav-item ${isCurrent ? 'is-active' : ''} ${isClickable ? 'is-clickable' : 'is-disabled'}`}
              onClick={() => isClickable && onSelectStep(step.id)}
              disabled={!isClickable}
              aria-current={isCurrent ? 'page' : undefined}
              aria-label={step.ariaLabel}
            >
              <span className="pl-nav-icon">
                {isLoading ? <span className="pl-nav-spinner" /> : step.icon}
              </span>
              <span className="pl-nav-label">{step.label}</span>
              {isCompleted && !isCurrent && (
                <span className="pl-nav-status-dot" title="Analysis ready" />
              )}
            </button>
          );
        })}
      </div>
    </nav>
  );
};
