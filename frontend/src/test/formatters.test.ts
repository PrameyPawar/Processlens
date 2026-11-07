import { describe, it, expect } from 'vitest';
import {
  formatScorePercent,
  normalizeScoreTo100,
  formatDuration,
  formatHoursOnly,
  formatNumber,
  formatRatioPercent,
  formatCurrency,
} from '../utils/formatters';

describe('formatters utility suite - Phase 11.7 Semantic Audit', () => {
  describe('formatScorePercent (fixes 7500% confidence bug)', () => {
    it('correctly handles 0-100 score scale (real backend output)', () => {
      expect(formatScorePercent(75.0)).toBe('75%');
      expect(formatScorePercent(90.0)).toBe('90%');
      expect(formatScorePercent(10.0)).toBe('10%');
      expect(formatScorePercent(100.0)).toBe('100%');
    });

    it('correctly handles 0.0-1.0 fraction scale (mocked / normalized ratios)', () => {
      expect(formatScorePercent(0.75)).toBe('75%');
      expect(formatScorePercent(0.95)).toBe('95%');
      expect(formatScorePercent(0.1)).toBe('10%');
      expect(formatScorePercent(1.0)).toBe('100%');
    });

    it('handles zero score cleanly', () => {
      expect(formatScorePercent(0)).toBe('0%');
      expect(formatScorePercent(0.0)).toBe('0%');
    });

    it('handles null, undefined, and NaN gracefully', () => {
      expect(formatScorePercent(null)).toBe('—');
      expect(formatScorePercent(undefined)).toBe('—');
      expect(formatScorePercent(NaN)).toBe('—');
    });
  });

  describe('normalizeScoreTo100', () => {
    it('normalizes fractions to 0-100 range', () => {
      expect(normalizeScoreTo100(0.85)).toBe(85);
      expect(normalizeScoreTo100(0.05)).toBe(5);
    });

    it('preserves already-scaled scores in 0-100 range', () => {
      expect(normalizeScoreTo100(75)).toBe(75);
      expect(normalizeScoreTo100(92.4)).toBe(92.4);
    });

    it('clamps values beyond boundaries', () => {
      expect(normalizeScoreTo100(120)).toBe(100);
      expect(normalizeScoreTo100(-10)).toBe(0);
    });

    it('returns 0 for null/undefined', () => {
      expect(normalizeScoreTo100(null)).toBe(0);
      expect(normalizeScoreTo100(undefined)).toBe(0);
    });
  });

  describe('formatCurrency with epistemic safeguards', () => {
    it('formats valid dollar amounts without decimals', () => {
      expect(formatCurrency(125000)).toBe('$125,000');
      expect(formatCurrency(0)).toBe('$0');
    });

    it('returns explicit unmonetized/unknown state when financial params are missing', () => {
      expect(formatCurrency(null)).toBe('Unknown (Missing Financial Parameters)');
      expect(formatCurrency(undefined)).toBe('Unknown (Missing Financial Parameters)');
      expect(formatCurrency(null, 'Not monetised (inputs required)')).toBe('Not monetised (inputs required)');
    });
  });

  describe('formatDuration and formatHoursOnly', () => {
    it('formats seconds correctly', () => {
      expect(formatDuration(0)).toBe('0.0s');
      expect(formatDuration(45)).toBe('45.0s');
    });

    it('formats minutes with exact seconds context', () => {
      expect(formatDuration(150)).toBe('2.5m (150s)');
    });

    it('formats hours with exact seconds context', () => {
      expect(formatDuration(3600)).toBe('1.0h (3600s)');
    });

    it('formats hours only concisely', () => {
      expect(formatHoursOnly(0)).toBe('0h');
      expect(formatHoursOnly(1800)).toBe('30m');
      expect(formatHoursOnly(7200)).toBe('2.0h');
    });
  });

  describe('formatRatioPercent', () => {
    it('formats decimal ratios as percentages', () => {
      expect(formatRatioPercent(1.0)).toBe('100.0%');
      expect(formatRatioPercent(0.9845, 1)).toBe('98.5%');
      expect(formatRatioPercent(0.9845, 2)).toBe('98.45%');
      expect(formatRatioPercent(null)).toBe('—');
    });
  });

  describe('formatNumber', () => {
    it('formats numbers with comma separators', () => {
      expect(formatNumber(1250000)).toBe('1,250,000');
      expect(formatNumber(0)).toBe('0');
      expect(formatNumber(null)).toBe('—');
    });
  });
});
