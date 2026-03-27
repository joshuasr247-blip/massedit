const BACKEND_URL = import.meta.env.VITE_API_URL || '';
const API_BASE = `${BACKEND_URL}/api`;

// Helper for making authenticated requests
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response
}

// Projects
export async function createProject(name) {
  return request('/projects', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
}

export async function getProject(id) {
  return request(`/projects/${id}`);
}

export async function listProjects() {
  return request('/projects');
}

// Boxes
export async function createBox(projectId, name, color) {
  return request(`/projects/${projectId}/boxes`, {
    method: 'POST',
    body: JSON.stringify({ name, color }),
  });
}

export async function updateBox(projectId, boxId, updates) {
  return request(`/projects/${projectId}/boxes/${boxId}`, {
    method: 'PUT',
    body: JSON.stringify(updates),
  });
}

export async function deleteBox(projectId, boxId) {
  return request(`/projects/${projectId}/boxes/${boxId}`, {
    method: 'DELETE',
  });
}

// Clips
export async function uploadClips(projectId, boxId, files, onProgress) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const xhr = new XMLHttpRequest();

  return new Promise((resolve, reject) => {
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          resolve({});
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('POST', `${API_BASE}/projects/${projectId}/boxes/${boxId}/clips`);
    xhr.send(formData);
  });
}

export async function deleteClip(projectId, boxId, clipId) {
  return request(`/projects/${projectId}/boxes/${boxId}/clips/${clipId}`, {
    method: 'DELETE',
  });
}

// AI Interpretation
export async function interpretPrompt(projectId, prompt) {
  return request(`/projects/${projectId}/interpret`, {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  });
}

export async function refinePrompt(projectId, refinement) {
  return request(`/projects/${projectId}/refine`, {
    method: 'POST',
    body: JSON.stringify({ refinement }),
  });
}

// Rendering
export async function startRender(projectId) {
  return request(`/projects/${projectId}/render`, {
    method: 'POST',
  });
}

export async function cancelRender(projectId) {
  return request(`/projects/${projectId}/render`, {
    method: 'DELETE',
  });
}

export async function getRenderStatus(projectId) {
  return request(`/projects/${projectId}/render/status`);
}

export async function getOutputs(projectId) {
  return request(`/projects/${projectId}/outputs`);
}

export async function previewRender(projectId) {
  return request(`/projects/${projectId}/render/preview`, {
    method: 'POST',
  });
}

// WebSocket
export function connectWebSocket(projectId, onMessage) {
  const wsBase = BACKEND_URL
    ? BACKEND_URL.replace(/^http/, 'ws')
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
  const wsUrl = `${wsBase}/ws/${projectId}`;

  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('WebSocket connected');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message', e);
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error', error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
  };

  return ws;
}
