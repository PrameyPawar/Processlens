/**
 * ProcessLens Typed API Client.
 * Connects directly to FastAPI backend endpoints through the configured Vite proxy.
 * Includes session cookie support (credentials: 'include') and Bearer token management.
 */

import {
  DataQualityReport,
  ProcessAnalyticsResult,
  ProblemDetectionResult,
  PrioritisationResponse,
  ExplanationResponse,
  EvidenceAuditResponse,
  LoginResponse,
  UserResponse,
  DevStatusResponse,
  DevAuditEventsResponse,
} from '../types/api';

const API_HOST = (
  (typeof import.meta !== 'undefined' && import.meta.env && (import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL)) || ''
).replace(/\/+$/, '');

const API_BASE = `${API_HOST}/api/v1`;

// In-memory token management for Authorization Bearer header
let inMemoryToken: string | null = null;

export function setApiAuthToken(token: string | null): void {
  inMemoryToken = token;
}

export function getApiAuthToken(): string | null {
  return inMemoryToken;
}

function getAuthHeaders(extraHeaders: Record<string, string> = {}): Record<string, string> {
  const headers: Record<string, string> = { ...extraHeaders };
  if (inMemoryToken) {
    headers['Authorization'] = `Bearer ${inMemoryToken}`;
  }
  return headers;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Body not JSON
    }
    throw new Error(errorDetail);
  }
  return response.json() as Promise<T>;
}

export async function checkBackendHealth(): Promise<{ status: string; service: string; version: string }> {
  const resp = await fetch(`${API_HOST}/health`, {
    credentials: 'include',
  });
  return handleResponse(resp);
}

// ==========================================
// Authentication APIs
// ==========================================

export async function loginApi(credentials: { email: string; password: string }): Promise<LoginResponse> {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
    credentials: 'include',
  });
  const data = await handleResponse<LoginResponse>(resp);
  setApiAuthToken(data.access_token);
  return data;
}

export async function registerApi(data: { email: string; name: string; password: string }): Promise<LoginResponse> {
  const resp = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    credentials: 'include',
  });
  const result = await handleResponse<LoginResponse>(resp);
  setApiAuthToken(result.access_token);
  return result;
}

export async function getMeApi(): Promise<UserResponse> {
  const resp = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  return handleResponse<UserResponse>(resp);
}

export async function logoutApi(): Promise<{ message: string }> {
  try {
    const resp = await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'include',
    });
    return await handleResponse<{ message: string }>(resp);
  } finally {
    setApiAuthToken(null);
  }
}

export async function forgotPasswordApi(email: string): Promise<{ message: string }> {
  const resp = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
    credentials: 'include',
  });
  return handleResponse<{ message: string }>(resp);
}

// ==========================================
// Developer Diagnostic APIs
// ==========================================

export async function getDevStatusApi(): Promise<DevStatusResponse> {
  const resp = await fetch(`${API_BASE}/dev/status`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  return handleResponse<DevStatusResponse>(resp);
}

export async function getDevAuditEventsApi(): Promise<DevAuditEventsResponse> {
  const resp = await fetch(`${API_BASE}/dev/audit-events`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  return handleResponse<DevAuditEventsResponse>(resp);
}

// ==========================================
// Analytics & Operations APIs
// ==========================================

export async function uploadAndValidateCsv(file: File): Promise<DataQualityReport> {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${API_BASE}/ingestion/upload`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<DataQualityReport>(resp);
}

export async function fetchProcessAnalytics(file: File): Promise<ProcessAnalyticsResult> {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${API_BASE}/analytics/process`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<ProcessAnalyticsResult>(resp);
}

export async function fetchProblemDetection(file: File): Promise<ProblemDetectionResult> {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${API_BASE}/problems/detect`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<ProblemDetectionResult>(resp);
}

export async function fetchPrioritisation(file: File): Promise<PrioritisationResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`${API_BASE}/prioritisation/rank`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<PrioritisationResponse>(resp);
}

export async function fetchExplanations(file: File, enableLlm: boolean = false): Promise<ExplanationResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('enable_llm', enableLlm ? 'true' : 'false');
  const resp = await fetch(`${API_BASE}/explanation/generate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<ExplanationResponse>(resp);
}

export async function fetchEvidenceAudit(file: File, opportunityId?: string): Promise<EvidenceAuditResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (opportunityId) {
    formData.append('opportunity_id', opportunityId);
  }
  const resp = await fetch(`${API_BASE}/evidence/audit`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
    credentials: 'include',
  });
  return handleResponse<EvidenceAuditResponse>(resp);
}
