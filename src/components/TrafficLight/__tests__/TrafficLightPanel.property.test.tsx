/**
 * Property-Based Tests for Traffic Light Panel Component
 * Feature: traffic-light-roi-detection
 */

import { describe, it, expect, vi } from 'vitest';
import * as fc from 'fast-check';
import { render } from '@testing-library/react';
import {
  TrafficLightPanel,
  TrafficLightState,
  TrafficLightPanelState,
} from '../TrafficLightPanel';

describe('TrafficLightPanel - Property-Based Tests', () => {
  /**
   * Property 9: State-to-Color Mapping Consistency
   * **Validates: Requirements 4.4, 4.5, 4.6, 4.7**
   *
   * For any traffic light state (GREEN/RED/YELLOW/UNKNOWN), the UI must display
   * the corresponding color: GREEN→#10b981, RED→#ef4444, YELLOW→#f59e0b, UNKNOWN→#6b7280.
   */
  it('Property 9: state-to-color mapping is consistent', () => {
    // Define the expected color mappings
    const expectedColors: Record<TrafficLightState, string> = {
      GREEN: '#10b981',
      RED: '#ef4444',
      YELLOW: '#f59e0b',
      UNKNOWN: '#6b7280',
    };

    fc.assert(
      fc.property(
        // Generate arbitrary traffic light states
        fc.constantFrom<TrafficLightState>('GREEN', 'RED', 'YELLOW', 'UNKNOWN'),
        fc.float({ min: 0, max: 1 }), // confidence
        fc.string(), // lastUpdate
        fc.boolean(), // isDetecting
        (currentState, confidence, lastUpdate, isDetecting) => {
          const state: TrafficLightPanelState = {
            currentState,
            confidence,
            lastUpdate,
            framePreview: null,
            isDetecting,
          };

          const { container, unmount } = render(
            <TrafficLightPanel
              state={state}
              onStartDetection={vi.fn()}
              onStopDetection={vi.fn()}
            />
          );

          // Find the state display element (the one with the colored dot and text)
          const stateDisplay = container.querySelector(
            'span[style*="font-weight: bold"]'
          );
          expect(stateDisplay).toBeTruthy();

          // Extract the color from the style attribute
          const style = stateDisplay?.getAttribute('style') || '';
          const colorMatch = style.match(/color:\s*([^;]+)/);
          expect(colorMatch).toBeTruthy();

          const actualColor = colorMatch![1].trim();
          const expectedColor = expectedColors[currentState];

          // Normalize colors for comparison (browser may convert hex to rgb)
          const normalizeColor = (color: string): string => {
            // If it's already hex, return as is
            if (color.startsWith('#')) return color.toLowerCase();
            
            // If it's rgb, convert to hex
            const rgbMatch = color.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
            if (rgbMatch) {
              const r = parseInt(rgbMatch[1]);
              const g = parseInt(rgbMatch[2]);
              const b = parseInt(rgbMatch[3]);
              return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
            }
            return color;
          };

          // Verify the color matches the expected mapping
          expect(normalizeColor(actualColor)).toBe(normalizeColor(expectedColor));

          // Also verify the colored dot has the same color
          const dot = stateDisplay?.querySelector('span[style*="border-radius: 50%"]');
          expect(dot).toBeTruthy();

          const dotStyle = dot?.getAttribute('style') || '';
          const dotColorMatch = dotStyle.match(/background-color:\s*([^;]+)/);
          expect(dotColorMatch).toBeTruthy();

          const dotColor = dotColorMatch![1].trim();
          expect(normalizeColor(dotColor)).toBe(normalizeColor(expectedColor));

          // Verify the text content matches the state
          expect(stateDisplay?.textContent).toContain(currentState);

          unmount();
        }
      ),
      { numRuns: 100 }
    );
  });

  /**
   * Property 19: UI Component Completeness
   * **Validates: Requirements 8.2**
   *
   * For any rendered Traffic Light Panel, the DOM must contain: an image element
   * (or placeholder), a state label element, and control buttons (Start/Stop).
   */
  it('Property 19: UI contains all required components', () => {
    fc.assert(
      fc.property(
        // Generate arbitrary panel states
        fc.constantFrom<TrafficLightState>('GREEN', 'RED', 'YELLOW', 'UNKNOWN'),
        fc.float({ min: 0, max: 1 }),
        fc.string(),
        fc.option(fc.string(), { nil: null }), // framePreview can be null
        fc.boolean(),
        (currentState, confidence, lastUpdate, framePreview, isDetecting) => {
          const state: TrafficLightPanelState = {
            currentState,
            confidence,
            lastUpdate,
            framePreview,
            isDetecting,
          };

          const { container, unmount } = render(
            <TrafficLightPanel
              state={state}
              onStartDetection={vi.fn()}
              onStopDetection={vi.fn()}
            />
          );

          // 1. Check for image element or placeholder
          if (framePreview) {
            const img = container.querySelector('img');
            expect(img).toBeTruthy();
            expect(img?.getAttribute('alt')).toBe('Traffic Light ROI Preview');
          } else {
            // Should have placeholder text
            const placeholder = Array.from(container.querySelectorAll('div')).find(
              (div) => div.textContent?.includes('No ROI selected')
            );
            expect(placeholder).toBeTruthy();
          }

          // 2. Check for state label element
          const stateLabel = container.querySelector('span[style*="font-weight: bold"]');
          expect(stateLabel).toBeTruthy();
          expect(stateLabel?.textContent).toContain(currentState);

          // 3. Check for control buttons
          const buttons = container.querySelectorAll('button');
          expect(buttons.length).toBe(2);

          // Verify button texts
          const buttonTexts = Array.from(buttons).map((btn) => btn.textContent);
          expect(buttonTexts).toContain('Start Detection');
          expect(buttonTexts).toContain('Stop Detection');

          // 4. Check for panel header
          const header = Array.from(container.querySelectorAll('div')).find(
            (div) => div.textContent === 'Traffic Light ROI'
          );
          expect(header).toBeTruthy();

          unmount();
        }
      ),
      { numRuns: 100 }
    );
  });
});
