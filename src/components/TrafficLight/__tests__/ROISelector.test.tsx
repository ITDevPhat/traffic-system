/**
 * Unit Tests for ROI Selector Component
 * Feature: traffic-light-roi-detection
 * Requirements: 1.1, 1.2, 1.3
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { ROISelector, NormalizedROI } from '../ROISelector';

describe('ROISelector - Unit Tests', () => {
  const defaultProps = {
    videoWidth: 1280,
    videoHeight: 720,
    onROISelected: vi.fn(),
  };

  describe('Mouse Event Handlers', () => {
    it('should start drawing on mouse down', () => {
      const { container } = render(<ROISelector {...defaultProps} />);
      const svg = container.querySelector('svg');
      expect(svg).toBeTruthy();

      // Simulate mouse down
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });

      // Check that cursor changes to crosshair (indicates drawing mode)
      expect(svg).toHaveStyle({ cursor: 'crosshair' });
    });

    it('should update preview rectangle on mouse move while drawing', () => {
      const { container } = render(<ROISelector {...defaultProps} />);
      const svg = container.querySelector('svg');

      // Start drawing
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });

      // Move mouse
      fireEvent.mouseMove(svg!, { clientX: 200, clientY: 200 });

      // Check that a preview rectangle is rendered
      const rect = container.querySelector('rect[stroke-dasharray="5,5"]');
      expect(rect).toBeTruthy();
    });

    it('should finalize ROI on mouse up', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector {...defaultProps} onROISelected={onROISelected} />
      );
      const svg = container.querySelector('svg');

      // Draw a rectangle
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 300, clientY: 250 });
      fireEvent.mouseUp(svg!);

      // Verify callback was called
      expect(onROISelected).toHaveBeenCalledTimes(1);

      // Verify the ROI has normalized coordinates
      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;
      expect(roi.x).toBeGreaterThanOrEqual(0);
      expect(roi.x).toBeLessThanOrEqual(1);
      expect(roi.y).toBeGreaterThanOrEqual(0);
      expect(roi.y).toBeLessThanOrEqual(1);
      expect(roi.width).toBeGreaterThanOrEqual(0);
      expect(roi.width).toBeLessThanOrEqual(1);
      expect(roi.height).toBeGreaterThanOrEqual(0);
      expect(roi.height).toBeLessThanOrEqual(1);
    });

    it('should not call onROISelected if mouse up without drawing', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector {...defaultProps} onROISelected={onROISelected} />
      );
      const svg = container.querySelector('svg');

      // Just mouse up without starting to draw
      fireEvent.mouseUp(svg!);

      expect(onROISelected).not.toHaveBeenCalled();
    });
  });

  describe('Coordinate Normalization', () => {
    it('should normalize coordinates correctly for typical case', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector
          videoWidth={1280}
          videoHeight={720}
          onROISelected={onROISelected}
        />
      );
      const svg = container.querySelector('svg');

      // Draw from (100, 100) to (300, 250)
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 300, clientY: 250 });
      fireEvent.mouseUp(svg!);

      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      // Expected normalized values
      // x: 100/1280 ≈ 0.078, y: 100/720 ≈ 0.139
      // width: 200/1280 ≈ 0.156, height: 150/720 ≈ 0.208
      expect(roi.x).toBeCloseTo(100 / 1280, 3);
      expect(roi.y).toBeCloseTo(100 / 720, 3);
      expect(roi.width).toBeCloseTo(200 / 1280, 3);
      expect(roi.height).toBeCloseTo(150 / 720, 3);
    });

    it('should handle negative coordinates (drag from right to left)', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector {...defaultProps} onROISelected={onROISelected} />
      );
      const svg = container.querySelector('svg');

      // Draw from right to left (300, 250) to (100, 100)
      fireEvent.mouseDown(svg!, { clientX: 300, clientY: 250 });
      fireEvent.mouseMove(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseUp(svg!);

      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      // Should still produce valid normalized coordinates
      expect(roi.x).toBeGreaterThanOrEqual(0);
      expect(roi.y).toBeGreaterThanOrEqual(0);
      expect(roi.width).toBeGreaterThan(0);
      expect(roi.height).toBeGreaterThan(0);
    });

    it('should clamp out-of-bounds coordinates to [0, 1]', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector
          videoWidth={100}
          videoHeight={100}
          onROISelected={onROISelected}
        />
      );
      const svg = container.querySelector('svg');

      // Draw with coordinates that would exceed bounds
      fireEvent.mouseDown(svg!, { clientX: -50, clientY: -50 });
      fireEvent.mouseMove(svg!, { clientX: 200, clientY: 200 });
      fireEvent.mouseUp(svg!);

      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      // All values should be clamped to [0, 1]
      expect(roi.x).toBeGreaterThanOrEqual(0);
      expect(roi.x).toBeLessThanOrEqual(1);
      expect(roi.y).toBeGreaterThanOrEqual(0);
      expect(roi.y).toBeLessThanOrEqual(1);
      expect(roi.width).toBeGreaterThanOrEqual(0);
      expect(roi.width).toBeLessThanOrEqual(1);
      expect(roi.height).toBeGreaterThanOrEqual(0);
      expect(roi.height).toBeLessThanOrEqual(1);
    });
  });

  describe('ROI Validation', () => {
    it('should handle minimum size ROI (2% of frame)', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector
          videoWidth={1000}
          videoHeight={1000}
          onROISelected={onROISelected}
        />
      );
      const svg = container.querySelector('svg');

      // Draw a small ROI (20x20 pixels = 2% of 1000x1000)
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 120, clientY: 120 });
      fireEvent.mouseUp(svg!);

      expect(onROISelected).toHaveBeenCalled();
      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      // Should be approximately 0.02 (2%)
      expect(roi.width).toBeCloseTo(0.02, 2);
      expect(roi.height).toBeCloseTo(0.02, 2);
    });

    it('should handle very small ROI (< 2% - edge case)', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector
          videoWidth={1000}
          videoHeight={1000}
          onROISelected={onROISelected}
        />
      );
      const svg = container.querySelector('svg');

      // Draw a very small ROI (5x5 pixels = 0.5%)
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 105, clientY: 105 });
      fireEvent.mouseUp(svg!);

      // Component should still call the callback (validation happens in parent/API)
      expect(onROISelected).toHaveBeenCalled();
      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      expect(roi.width).toBeCloseTo(0.005, 3);
      expect(roi.height).toBeCloseTo(0.005, 3);
    });

    it('should handle zero-size ROI (click without drag)', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector {...defaultProps} onROISelected={onROISelected} />
      );
      const svg = container.querySelector('svg');

      // Click at same position (no drag)
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseUp(svg!);

      // Should still call callback with zero-size ROI
      expect(onROISelected).toHaveBeenCalled();
      const roi = onROISelected.mock.calls[0][0] as NormalizedROI;

      expect(roi.width).toBe(0);
      expect(roi.height).toBe(0);
    });
  });

  describe('Visual Feedback', () => {
    it('should render snap circle at start point while drawing', () => {
      const { container } = render(<ROISelector {...defaultProps} />);
      const svg = container.querySelector('svg');

      // Start drawing
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });

      // Check for snap circle
      const circle = container.querySelector('circle');
      expect(circle).toBeTruthy();
      expect(circle).toHaveAttribute('r', '8');
    });

    it('should show selected ROI with label after finalization', () => {
      const { container } = render(<ROISelector {...defaultProps} />);
      const svg = container.querySelector('svg');

      // Draw and finalize ROI
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 300, clientY: 250 });
      fireEvent.mouseUp(svg!);

      // Check for selected ROI rectangle (solid, not dashed)
      const rects = container.querySelectorAll('rect');
      const selectedRect = Array.from(rects).find(
        (rect) => !rect.getAttribute('stroke-dasharray')
      );
      expect(selectedRect).toBeTruthy();

      // Check for label
      const text = container.querySelector('text');
      expect(text).toBeTruthy();
      expect(text?.textContent).toBe('Traffic Light ROI');
    });

    it('should change cursor to crosshair while drawing', () => {
      const { container } = render(<ROISelector {...defaultProps} />);
      const svg = container.querySelector('svg');

      // Initially default cursor
      expect(svg).toHaveStyle({ cursor: 'default' });

      // Start drawing
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });

      // Should change to crosshair
      expect(svg).toHaveStyle({ cursor: 'crosshair' });

      // Finish drawing
      fireEvent.mouseUp(svg!);

      // Should return to default
      expect(svg).toHaveStyle({ cursor: 'default' });
    });
  });

  describe('ROI Replacement', () => {
    it('should replace old ROI when drawing new one', () => {
      const onROISelected = vi.fn();
      const { container } = render(
        <ROISelector {...defaultProps} onROISelected={onROISelected} />
      );
      const svg = container.querySelector('svg');

      // Draw first ROI
      fireEvent.mouseDown(svg!, { clientX: 100, clientY: 100 });
      fireEvent.mouseMove(svg!, { clientX: 200, clientY: 200 });
      fireEvent.mouseUp(svg!);

      expect(onROISelected).toHaveBeenCalledTimes(1);
      const firstROI = onROISelected.mock.calls[0][0] as NormalizedROI;

      // Draw second ROI
      fireEvent.mouseDown(svg!, { clientX: 300, clientY: 300 });
      fireEvent.mouseMove(svg!, { clientX: 400, clientY: 400 });
      fireEvent.mouseUp(svg!);

      expect(onROISelected).toHaveBeenCalledTimes(2);
      const secondROI = onROISelected.mock.calls[1][0] as NormalizedROI;

      // Verify they are different
      expect(secondROI).not.toEqual(firstROI);

      // Only one selected ROI should be visible (the latest one)
      const selectedRects = container.querySelectorAll(
        'rect:not([stroke-dasharray])'
      );
      expect(selectedRects.length).toBe(1);
    });
  });
});
