// ROI Types and Interfaces for Advanced ROI Editor

// 15 ROI Types
export type RoiType =
  | 'detection_zone'
  | 'lane_car'
  | 'lane_bike'
  | 'lane_bus'
  | 'lane_truck'
  | 'forbidden_area'
  | 'wrong_direction'
  | 'direction_zone'
  | 'stopline'
  | 'solid_line'
  | 'dashed_line'
  | 'crosswalk'
  | 'traffic_light'
  | 'vehicle_entry'
  | 'vehicle_exit';

// Shape types
export type Shape = 'polygon' | 'line' | 'rectangle';

// Point interface
export interface Point {
  x: number;
  y: number;
}

// ROI Metadata for special types
export interface RoiMetadata {
  allowed_heading?: [number, number]; // [min, max] degrees for direction_zone, wrong_direction
  allowed_classes?: string[]; // ['car', 'bus', 'truck', 'motorbike'] for lane types
  related_light?: string; // Traffic light ID for stopline (used in red_light violation)
  description?: string; // Optional description for any ROI type
}

// Main ROI interface
export interface Roi {
  id: string;
  roi_type: RoiType;
  name: string;
  shape: Shape;
  coordinates: Point[]; // Array of {x, y} points
  color: string;
  metadata?: RoiMetadata;
  created_at: string;
  updated_at: string;
}

// Color mapping for each ROI type
export const ROI_COLORS: Record<RoiType, string> = {
  detection_zone: '#00FFFF',    // Cyan
  lane_car: '#4CAF50',          // Green
  lane_bike: '#2196F3',         // Blue
  lane_bus: '#673AB7',          // Deep Purple
  lane_truck: '#3F51B5',        // Indigo
  forbidden_area: '#FF1744',    // Red
  wrong_direction: '#FF9100',   // Orange
  direction_zone: '#FFC400',    // Amber
  stopline: '#FF0000',          // Red
  solid_line: '#880E4F',        // Pink Dark
  dashed_line: '#BDBDBD',       // Grey
  crosswalk: '#FFD600',         // Yellow
  traffic_light: '#FFFFFF',     // White
  vehicle_entry: '#00E676',     // Green Light
  vehicle_exit: '#00BFA5',      // Teal
};

// Shape mapping for each ROI type
export const ROI_SHAPES: Record<RoiType, Shape> = {
  detection_zone: 'polygon',
  lane_car: 'polygon',
  lane_bike: 'polygon',
  lane_bus: 'polygon',
  lane_truck: 'polygon',
  forbidden_area: 'polygon',
  wrong_direction: 'polygon',
  direction_zone: 'polygon',
  stopline: 'line',
  solid_line: 'line',
  dashed_line: 'line',
  crosswalk: 'polygon',
  traffic_light: 'rectangle',
  vehicle_entry: 'polygon',
  vehicle_exit: 'polygon',
};

// Helper to get ROI type display name
export const ROI_TYPE_LABELS: Record<RoiType, string> = {
  detection_zone: 'Detection Zone',
  lane_car: 'Lane Car',
  lane_bike: 'Lane Bike',
  lane_bus: 'Lane Bus',
  lane_truck: 'Lane Truck',
  forbidden_area: 'Forbidden Area',
  wrong_direction: 'Wrong Direction',
  direction_zone: 'Direction Zone',
  stopline: 'Stop Line',
  solid_line: 'Solid Line',
  dashed_line: 'Dashed Line',
  crosswalk: 'Crosswalk',
  traffic_light: 'Traffic Light',
  vehicle_entry: 'Vehicle Entry',
  vehicle_exit: 'Vehicle Exit',
};
