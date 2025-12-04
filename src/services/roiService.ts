// ROI Service for Advanced ROI Editor - Backend API Integration
import { Roi, RoiType, ROI_SHAPES } from '@/types/roi';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export class RoiService {
  /**
   * Get ROIs for a specific camera
   * @param cameraId Camera ID
   * @returns Array of ROIs
   */
  static async getRois(cameraId: string): Promise<Roi[]> {
    try {
      const response = await fetch(
        `${API_BASE}/api/roi?camera_id=${encodeURIComponent(cameraId)}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch ROIs: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      // Convert backend format to frontend format
      if (data.items && Array.isArray(data.items)) {
        return data.items.map((item: any) => this.convertFromBackend(item));
      }

      return [];
    } catch (error) {
      console.error('Error fetching ROIs:', error);
      throw error;
    }
  }

  /**
   * Save ROIs for a specific camera
   * @param cameraId Camera ID
   * @param rois Array of ROIs to save
   */
  static async saveRois(cameraId: string, rois: Roi[]): Promise<void> {
    try {
      const payload = {
        camera_id: cameraId,
        items: rois.map((roi) => this.convertToBackend(roi)),
      };

      const response = await fetch(`${API_BASE}/api/roi`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Failed to save ROIs: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error saving ROIs:', error);
      throw error;
    }
  }

  /**
   * Validate ROI before saving
   * @param roi ROI to validate
   * @returns Array of error messages (empty if valid)
   */
  static validateRoi(roi: Omit<Roi, 'id' | 'created_at' | 'updated_at'>): string[] {
    const errors: string[] = [];

    // Validate name
    if (!roi.name || roi.name.trim().length === 0) {
      errors.push('Name is required');
    }

    if (roi.name && roi.name.trim().length < 3) {
      errors.push('Name must be at least 3 characters');
    }

    // Validate shape vs coordinates
    const pointCount = roi.coordinates.length;

    if (roi.shape === 'line' && pointCount !== 2) {
      errors.push('Line must have exactly 2 points');
    }

    if (roi.shape === 'rectangle' && pointCount !== 2) {
      errors.push('Rectangle must have exactly 2 points (will be converted to 4)');
    }

    if (roi.shape === 'polygon' && pointCount < 3) {
      errors.push('Polygon must have at least 3 points');
    }

    // Validate coordinates
    if (roi.coordinates.some((p) => typeof p.x !== 'number' || typeof p.y !== 'number')) {
      errors.push('All coordinates must have valid x and y values');
    }

    // Validate metadata for specific types
    if (
      (roi.roi_type === 'direction_zone' || roi.roi_type === 'wrong_direction') &&
      roi.metadata?.allowed_heading
    ) {
      const [min, max] = roi.metadata.allowed_heading;
      if (min < 0 || min > 360 || max < 0 || max > 360) {
        errors.push('Heading must be between 0 and 360 degrees');
      }
    }

    return errors;
  }

  /**
   * Export ROIs to JSON format
   * @param cameraId Camera ID
   * @param rois Array of ROIs
   * @returns JSON string
   */
  static exportToJson(cameraId: string, rois: Roi[]): string {
    const data = {
      camera_id: cameraId,
      rois: rois.map((roi) => ({
        roi_type: roi.roi_type,
        coordinates: roi.coordinates.map((p) => [p.x, p.y]),
        color: roi.color,
        name: roi.name,
        metadata: roi.metadata || {},
      })),
    };

    return JSON.stringify(data, null, 2);
  }

  /**
   * Import ROIs from JSON
   * @param json JSON string
   * @returns Object with cameraId and rois array
   */
  static importFromJson(json: string): { cameraId: string; rois: Roi[] } {
    try {
      const data = JSON.parse(json);

      if (!data.camera_id) {
        throw new Error('Missing camera_id in JSON');
      }

      if (!Array.isArray(data.rois)) {
        throw new Error('Invalid rois array in JSON');
      }

      const rois: Roi[] = data.rois.map((r: any) => {
        const roiType = r.roi_type as RoiType;
        const shape = ROI_SHAPES[roiType];

        if (!shape) {
          throw new Error(`Invalid roi_type: ${r.roi_type}`);
        }

        return {
          id: crypto.randomUUID(),
          roi_type: roiType,
          name: r.name || 'Unnamed ROI',
          shape: shape,
          coordinates: r.coordinates.map(([x, y]: [number, number]) => ({ x, y })),
          color: r.color,
          metadata: r.metadata,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
      });

      return {
        cameraId: data.camera_id,
        rois,
      };
    } catch (error) {
      console.error('Error importing JSON:', error);
      throw new Error(
        `Failed to import JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  }

  /**
   * Convert backend format to frontend Roi format
   * @param item Backend ROI item
   * @returns Frontend Roi object
   */
  private static convertFromBackend(item: any): Roi {
    const roiType = item.roi_type as RoiType;
    const shape = ROI_SHAPES[roiType] || 'polygon';

    return {
      id: item.id || crypto.randomUUID(),
      roi_type: roiType,
      name: item.name || 'Unnamed ROI',
      shape: shape,
      coordinates: Array.isArray(item.coordinates)
        ? item.coordinates.map((coord: any) => {
            if (Array.isArray(coord)) {
              return { x: coord[0], y: coord[1] };
            }
            return coord;
          })
        : [],
      color: item.color,
      metadata: item.metadata,
      created_at: item.created_at || new Date().toISOString(),
      updated_at: item.updated_at || new Date().toISOString(),
    };
  }

  /**
   * Convert frontend Roi format to backend format
   * @param roi Frontend Roi object
   * @returns Backend ROI item
   */
  private static convertToBackend(roi: Roi): any {
    return {
      id: roi.id,
      roi_type: roi.roi_type,
      name: roi.name,
      coordinates: roi.coordinates.map((p) => [p.x, p.y]),
      color: roi.color,
      metadata: roi.metadata || {},
      created_at: roi.created_at,
      updated_at: roi.updated_at,
    };
  }
}
