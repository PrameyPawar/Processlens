/**
 * Formatting utilities for ProcessLens analytics metrics.
 * Strictly preserves backward-compatible duration formatting.
 */

export function formatDuration(seconds: number): string {
  if (seconds === 0) return '0.0s';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = seconds / 60;
  if (minutes < 60) return `${minutes.toFixed(1)}m (${Math.round(seconds)}s)`;
  const hours = seconds / 3600;
  if (hours < 48) return `${hours.toFixed(1)}h (${Math.round(seconds)}s)`;
  const days = hours / 24;
  return `${days.toFixed(1)}d (${Math.round(hours)}h)`;
}

export function formatHoursOnly(seconds: number): string {
  if (seconds <= 0) return '0h';
  const hours = seconds / 3600;
  if (hours < 1) return `${(seconds / 60).toFixed(0)}m`;
  return `${hours.toFixed(1)}h`;
}

export function formatNumber(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—';
  return val.toLocaleString('en-US');
}

export function formatScorePercent(score: number | null | undefined): string {
  if (score === null || score === undefined || isNaN(score)) return '—';
  // Canonical normalization: if score <= 1.0 (e.g. 0.75, 0.95), treat as ratio (x 100).
  // If score > 1.0 (e.g. 75.0, 95.0), it is already on the 0-100 score scale.
  const pct = score <= 1.0 ? score * 100 : score;
  return `${Math.round(pct)}%`;
}

export function normalizeScoreTo100(score: number | null | undefined): number {
  if (score === null || score === undefined || isNaN(score)) return 0;
  const pct = score <= 1.0 ? score * 100 : score;
  return Math.min(Math.max(pct, 0), 100);
}

export function formatRatioPercent(ratio: number | null | undefined, decimals: number = 1): string {
  if (ratio === null || ratio === undefined || isNaN(ratio)) return '—';
  return `${(ratio * 100).toFixed(decimals)}%`;
}

export const formatPercentage = formatRatioPercent;

export function formatCurrency(
  amount: number | null | undefined,
  fallback: string = 'Unknown (Missing Financial Parameters)'
): string {
  if (amount === null || amount === undefined) {
    return fallback;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

