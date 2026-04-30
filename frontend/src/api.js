import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export const healthCheck = () => api.get('/health').then(r => r.data);

// Config
export const getConfig = () => api.get('/config/').then(r => r.data);
export const updateConfig = (path, value) => api.post('/config/', { path, value }).then(r => r.data);
export const resetConfig = () => api.post('/config/reset').then(r => r.data);

// Projects
export const listProjects = () => api.get('/projects/').then(r => r.data);
export const projectFromFolder = (folderPath) => api.post('/projects/from-folder', { folder_path: folderPath }).then(r => r.data);
export const getProject = (id) => api.get(`/projects/${id}`).then(r => r.data);
export const getProjectOutput = (id) => api.get(`/projects/${id}/output`).then(r => r.data);
export const getProjectEvaluation = (id) => api.get(`/projects/${id}/evaluation`).then(r => r.data);
export const evaluateProject = (id) => api.post(`/projects/${id}/evaluate`).then(r => r.data);

// System
export const browseFolder = () => api.post('/system/browse-folder').then(r => r.data);

// Pipeline & Jobs
export const runPipeline = (projectId, projectPath, stages, force = false) =>
  api.post('/pipeline/run', { project_id: projectId, project_path: projectPath, stages, force }).then(r => r.data);
export const getJobStatus = (jobId) =>
  api.get(`/pipeline/status/${jobId}`).then(r => r.data);
export const listJobs = (limit = 50) =>
  api.get(`/pipeline/jobs?limit=${limit}`).then(r => r.data);
export const deleteJob = (jobId) =>
  api.delete(`/pipeline/jobs/${jobId}`).then(r => r.data);
export const runScript = (script, args = []) =>
  api.post('/pipeline/run-script', { script, args }).then(r => r.data);

export default api;
