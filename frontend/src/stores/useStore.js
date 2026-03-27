import { create } from 'zustand';
import * as api from '../api/client.js';

export const useStore = create((set, get) => ({
  // State
  currentProject: null,
  boxes: [],
  prompt: '',
  editPlan: null,
  suggestions: [],
  matrix: {},
  renderJobs: [],
  outputCount: 0,
  activeView: 'prompt',
  selectedBox: null,
  isInterpreting: false,
  isRendering: false,
  ws: null,

  // Initialize project
  initProject: async (name) => {
    try {
      const project = await api.createProject(name);
      set({
        currentProject: project,
        boxes: [],
        prompt: '',
        editPlan: null,
        suggestions: [],
        matrix: {},
        renderJobs: [],
        outputCount: 0,
      });
      return project;
    } catch (error) {
      console.error('Failed to create project', error);
      throw error;
    }
  },

  // Load project
  loadProject: async (id) => {
    try {
      const project = await api.getProject(id);
      set({
        currentProject: project,
        boxes: project.boxes || [],
        matrix: project.matrix || {},
      });
      get().calculateOutputCount();
      return project;
    } catch (error) {
      console.error('Failed to load project', error);
      throw error;
    }
  },

  // Add box
  addBox: async (name) => {
    const project = get().currentProject;
    if (!project) return;

    try {
      const box = await api.createBox(project.id, name, '');
      set((state) => ({
        boxes: [...state.boxes, box],
      }));
      return box;
    } catch (error) {
      console.error('Failed to create box', error);
      throw error;
    }
  },

  // Rename box
  renameBox: async (boxId, newName) => {
    const project = get().currentProject;
    if (!project) return;

    try {
      const updated = await api.updateBox(project.id, boxId, { name: newName });
      set((state) => ({
        boxes: state.boxes.map((b) =>
          b.id === boxId ? { ...b, name: updated.name } : b
        ),
      }));
      return updated;
    } catch (error) {
      console.error('Failed to rename box', error);
      throw error;
    }
  },

  // Upload clips to box
  uploadClipsToBox: async (boxId, files, onProgress) => {
    const project = get().currentProject;
    if (!project) return;

    try {
      await api.uploadClips(project.id, boxId, files, onProgress);
      const updated = await api.getProject(project.id);
      set({
        currentProject: updated,
        boxes: updated.boxes || [],
      });
    } catch (error) {
      console.error('Failed to upload clips', error);
      throw error;
    }
  },

  // Remove clip
  removeClip: async (boxId, clipId) => {
    const project = get().currentProject;
    if (!project) return;

    try {
      await api.deleteClip(project.id, boxId, clipId);
      const updated = await api.getProject(project.id);
      set({
        currentProject: updated,
        boxes: updated.boxes || [],
      });
    } catch (error) {
      console.error('Failed to remove clip', error);
      throw error;
    }
  },

  // Set prompt
  setPrompt: (text) => {
    set({ prompt: text });
  },

  // Interpret prompt
  interpret: async () => {
    const project = get().currentProject;
    const prompt = get().prompt;
    if (!project || !prompt) return;

    set({ isInterpreting: true });
    try {
      const result = await api.interpretPrompt(project.id, prompt);
      set({
        editPlan: result.edit_plan || [],
        suggestions: result.suggestions || [],
        isInterpreting: false,
      });
    } catch (error) {
      console.error('Failed to interpret prompt', error);
      set({ isInterpreting: false });
      throw error;
    }
  },

  // Update matrix
  updateMatrix: (variableKey, boxId, mode, params) => {
    set((state) => {
      const newMatrix = { ...state.matrix };
      if (!newMatrix[variableKey]) {
        newMatrix[variableKey] = {};
      }
      newMatrix[variableKey][boxId] = { mode, params };
      return { matrix: newMatrix };
    });
    get().calculateOutputCount();
  },

  // Calculate output count
  calculateOutputCount: () => {
    const matrix = get().matrix;
    if (Object.keys(matrix).length === 0) {
      set({ outputCount: 0 });
      return;
    }

    let count = 1;
    for (const variable of Object.values(matrix)) {
      let variableCount = 0;
      for (const config of Object.values(variable)) {
        if (config.mode === 'each') {
          variableCount = Math.max(variableCount, config.params?.count || 1);
        } else if (config.mode === 'random') {
          variableCount = Math.max(variableCount, config.params?.count || 1);
        } else if (config.mode === 'sequential') {
          variableCount = Math.max(variableCount, config.params?.count || 1);
        }
      }
      count *= Math.max(variableCount, 1);
    }

    set({ outputCount: Math.max(count, 1) });
  },

  // Start render
  startRender: async () => {
    const project = get().currentProject;
    if (!project) return;

    set({ isRendering: true });
    try {
      await api.startRender(project.id);
      get().connectWS();
      set({ activeView: 'outputs' });
    } catch (error) {
      console.error('Failed to start render', error);
      set({ isRendering: false });
      throw error;
    }
  },

  // Cancel render
  cancelRender: async () => {
    const project = get().currentProject;
    if (!project) return;

    try {
      await api.cancelRender(project.id);
      set({ isRendering: false });
      const ws = get().ws;
      if (ws) ws.close();
      set({ ws: null });
    } catch (error) {
      console.error('Failed to cancel render', error);
      throw error;
    }
  },

  // Connect WebSocket
  connectWS: () => {
    const project = get().currentProject;
    if (!project) return;

    const ws = api.connectWebSocket(project.id, (data) => {
      if (data.type === 'progress') {
        set((state) => ({
          renderJobs: data.jobs || state.renderJobs,
        }));
      } else if (data.type === 'complete') {
        set({ isRendering: false });
      }
    });

    set({ ws });
  },

  // Set active view
  setActiveView: (view) => {
    set({ activeView: view });
  },

  // Set selected box
  setSelectedBox: (boxId) => {
    set({ selectedBox: boxId });
  },
}));
