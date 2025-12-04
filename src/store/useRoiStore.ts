// Zustand store for Advanced ROI Editor
import { create } from 'zustand';
import { Roi, Point } from '@/types/roi';

interface RoiStore {
  // State
  rois: Roi[];
  selectedRoiId: string | null;
  currentCamera: string;
  drawingMode: boolean;
  currentPoints: Point[];
  loading: boolean;
  error: string | null;
  filterType: string | null;
  hoveredType: string | null;

  // Basic CRUD actions
  addRoi: (roi: Omit<Roi, 'id' | 'created_at' | 'updated_at'>) => void;
  updateRoi: (id: string, data: Partial<Omit<Roi, 'id' | 'created_at'>>) => void;
  deleteRoi: (id: string) => void;
  cloneRoi: (id: string) => void;
  selectRoi: (id: string | null) => void;

  // Drawing mode actions
  setDrawingMode: (mode: boolean) => void;
  addPoint: (point: Point) => void;
  clearPoints: () => void;
  finishDrawing: () => void;

  // Camera management
  setCurrentCamera: (cameraId: string) => void;

  // Backend sync actions (will be implemented in Phase 3)
  saveToBackend: () => Promise<void>;
  loadFromBackend: (cameraId: string) => Promise<void>;

  // Utility actions
  setError: (error: string | null) => void;
  clearError: () => void;

  // Legend filter actions
  setFilterType: (type: string | null) => void;
  setHoveredType: (type: string | null) => void;
}

export const useRoiStore = create<RoiStore>()((set, get) => ({
  // Initial state
  rois: [],
  selectedRoiId: null,
  currentCamera: '',
  drawingMode: false,
  currentPoints: [],
  loading: false,
  error: null,
  filterType: null,
  hoveredType: null,

  // Add new ROI
  addRoi: (roi) => {
    const newRoi: Roi = {
      ...roi,
      id: crypto.randomUUID(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    // Validate shape
    const shape = roi.shape;
    const pointCount = roi.coordinates.length;

    if (shape === 'line' && pointCount !== 2) {
      set({ error: 'Line must have exactly 2 points' });
      return;
    }

    if (shape === 'rectangle' && pointCount !== 2) {
      set({ error: 'Rectangle must have exactly 2 points' });
      return;
    }

    if (shape === 'polygon' && pointCount < 3) {
      set({ error: 'Polygon must have at least 3 points' });
      return;
    }

    set((state) => ({
      rois: [...state.rois, newRoi],
      error: null,
    }));
  },

  // Update existing ROI
  updateRoi: (id, data) => {
    set((state) => ({
      rois: state.rois.map((roi) =>
        roi.id === id
          ? {
              ...roi,
              ...data,
              updated_at: new Date().toISOString(),
            }
          : roi
      ),
    }));
  },

  // Delete ROI
  deleteRoi: (id) => {
    set((state) => ({
      rois: state.rois.filter((roi) => roi.id !== id),
      selectedRoiId: state.selectedRoiId === id ? null : state.selectedRoiId,
    }));
  },

  // Clone ROI
  cloneRoi: (id) => {
    const state = get();
    const roiToClone = state.rois.find((roi) => roi.id === id);

    if (!roiToClone) {
      set({ error: `ROI with id ${id} not found` });
      return;
    }

    const clonedRoi: Roi = {
      ...roiToClone,
      id: crypto.randomUUID(),
      name: `${roiToClone.name}_copy`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    set((state) => ({
      rois: [...state.rois, clonedRoi],
      error: null,
    }));
  },

  // Select ROI
  selectRoi: (id) => {
    set({ selectedRoiId: id });
  },

  // Set drawing mode
  setDrawingMode: (mode) => {
    set({
      drawingMode: mode,
      currentPoints: mode ? get().currentPoints : [],
    });
  },

  // Add point during drawing
  addPoint: (point) => {
    set((state) => ({
      currentPoints: [...state.currentPoints, point],
    }));
  },

  // Clear current points
  clearPoints: () => {
    set({ currentPoints: [] });
  },

  // Finish drawing and create ROI
  finishDrawing: () => {
    const state = get();
    const points = state.currentPoints;

    if (points.length === 0) {
      set({ error: 'No points to create ROI' });
      return;
    }

    // This will be called from UI with proper ROI data
    // For now, just clear points and exit drawing mode
    set({
      drawingMode: false,
      currentPoints: [],
    });
  },

  // Set current camera
  setCurrentCamera: (cameraId) => {
    set({ currentCamera: cameraId });
  },

  // Save to backend
  saveToBackend: async () => {
    const state = get();
    const { currentCamera, rois } = state;

    if (!currentCamera) {
      set({ error: 'No camera selected' });
      return;
    }

    set({ loading: true, error: null });
    try {
      const { RoiService } = await import('@/services/roiService');
      await RoiService.saveRois(currentCamera, rois);
      
      // Show success notification (will be implemented with toast in Phase 9)
      console.log('ROIs saved successfully');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save ROIs';
      set({ error: errorMessage });
      throw error;
    } finally {
      set({ loading: false });
    }
  },

  // Load from backend
  loadFromBackend: async (cameraId) => {
    set({ loading: true, error: null });
    try {
      const { RoiService } = await import('@/services/roiService');
      const rois = await RoiService.getRois(cameraId);
      
      set({
        currentCamera: cameraId,
        rois,
        selectedRoiId: null,
      });

      // Show success notification (will be implemented with toast in Phase 9)
      console.log(`Loaded ${rois.length} ROIs for camera ${cameraId}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load ROIs';
      set({ error: errorMessage });
      throw error;
    } finally {
      set({ loading: false });
    }
  },

  // Set error
  setError: (error) => {
    set({ error });
  },

  // Clear error
  clearError: () => {
    set({ error: null });
  },

  // Set filter type
  setFilterType: (type) => {
    set({ filterType: type });
  },

  // Set hovered type
  setHoveredType: (type) => {
    set({ hoveredType: type });
  },
}));
