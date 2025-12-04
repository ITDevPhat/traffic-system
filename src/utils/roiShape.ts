// Shape conversion and utility functions for ROI Editor

import { Point } from '@/types/roi';

export class ShapeUtils {
  /**
   * Convert 2 points (rectangle) to 4 points (clockwise order)
   * @param p1 First point (any corner)
   * @param p2 Second point (opposite corner)
   * @returns Array of 4 points in clockwise order: [TL, TR, BR, BL]
   */
  static rectangleTo4Points(p1: Point, p2: Point): Point[] {
    const x1 = Math.min(p1.x, p2.x);
    const y1 = Math.min(p1.y, p2.y);
    const x2 = Math.max(p1.x, p2.x);
    const y2 = Math.max(p1.y, p2.y);
    
    return [
      { x: x1, y: y1 }, // Top-left
      { x: x2, y: y1 }, // Top-right
      { x: x2, y: y2 }, // Bottom-right
      { x: x1, y: y2 }, // Bottom-left
    ];
  }

  /**
   * Check if two points are close to each other (for snap functionality)
   * @param p1 First point
   * @param p2 Second point
   * @param threshold Distance threshold in pixels (default: 12)
   * @returns true if points are within threshold distance
   */
  static isNear(p1: Point, p2: Point, threshold: number = 12): boolean {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    return distance < threshold;
  }

  /**
   * Calculate the center point of a polygon
   * @param points Array of points
   * @returns Center point
   */
  static getCenter(points: Point[]): Point {
    if (points.length === 0) {
      return { x: 0, y: 0 };
    }
    
    const sum = points.reduce(
      (acc, p) => ({ x: acc.x + p.x, y: acc.y + p.y }),
      { x: 0, y: 0 }
    );
    
    return {
      x: sum.x / points.length,
      y: sum.y / points.length,
    };
  }

  /**
   * Check if polygon is closed (first and last points match)
   * @param points Array of points
   * @returns true if polygon is closed
   */
  static isPolygonClosed(points: Point[]): boolean {
    if (points.length < 3) {
      return false;
    }
    
    const firstPoint = points[0];
    const lastPoint = points[points.length - 1];
    
    return this.isNear(firstPoint, lastPoint, 1); // Very small threshold for exact match
  }

  /**
   * Close polygon by adding first point to end if not already closed
   * @param points Array of points
   * @returns Array of points with polygon closed
   */
  static closePolygon(points: Point[]): Point[] {
    if (points.length < 3) {
      return points;
    }
    
    if (this.isPolygonClosed(points)) {
      return points;
    }
    
    return [...points, points[0]];
  }

  /**
   * Calculate distance between two points
   * @param p1 First point
   * @param p2 Second point
   * @returns Distance in pixels
   */
  static distance(p1: Point, p2: Point): number {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  /**
   * Get bounding box of points
   * @param points Array of points
   * @returns Bounding box {minX, minY, maxX, maxY}
   */
  static getBoundingBox(points: Point[]): {
    minX: number;
    minY: number;
    maxX: number;
    maxY: number;
  } {
    if (points.length === 0) {
      return { minX: 0, minY: 0, maxX: 0, maxY: 0 };
    }

    const xs = points.map(p => p.x);
    const ys = points.map(p => p.y);

    return {
      minX: Math.min(...xs),
      minY: Math.min(...ys),
      maxX: Math.max(...xs),
      maxY: Math.max(...ys),
    };
  }

  /**
   * Check if a point is inside a polygon (ray casting algorithm)
   * @param point Point to check
   * @param polygon Array of polygon points
   * @returns true if point is inside polygon
   */
  static isPointInPolygon(point: Point, polygon: Point[]): boolean {
    let inside = false;
    
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].x;
      const yi = polygon[i].y;
      const xj = polygon[j].x;
      const yj = polygon[j].y;
      
      const intersect =
        yi > point.y !== yj > point.y &&
        point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
      
      if (intersect) {
        inside = !inside;
      }
    }
    
    return inside;
  }
}
