import axios from 'axios';

// Use relative path so requests go through nginx proxy in Docker,
// and through Vite proxy during local development.
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,  // 5 minutes for long-running pipeline operations
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
export const evaluateProject = (id, expectedOutputPath = null) =>
  api.post(`/projects/${id}/evaluate`, { project_id: id, expected_output_path: expectedOutputPath }).then(r => r.data);
export const deleteProject = (id) => api.post(`/projects/${id}/delete`).then(r => r.data);
export const clearProjectOutput = (id) => api.post(`/projects/${id}/clear-output`).then(r => r.data);
export const restoreProject = (id) => api.post(`/projects/${id}/restore`).then(r => r.data);
export const listHiddenProjects = () => api.get('/projects/hidden').then(r => r.data);
export const discoverProjects = (search = '') => api.get(`/projects/discover?search=${encodeURIComponent(search)}`).then(r => r.data);

// System
export const browseFolder = () => api.post('/system/browse-folder').then(r => r.data);
export const listDirectory = (path) => api.post('/system/list-directory', { path }).then(r => r.data);

// Pipeline & Jobs
export const runPipeline = (projectId, projectPath, stages, force = false) =>
  api.post('/pipeline/run', { project_id: projectId, project_path: projectPath, stages, force }).then(r => r.data);
export const getJobStatus = (jobId) =>
  api.get(`/pipeline/status/${jobId}`).then(r => r.data);
export const listJobs = (limit = 50) =>
  api.get(`/pipeline/jobs?limit=${limit}`).then(r => r.data);
export const deleteJob = (jobId) =>
  api.delete(`/pipeline/jobs/${jobId}`).then(r => r.data);
export const clearAllJobs = () =>
  api.post('/pipeline/clear-jobs').then(r => r.data);
export const clearAllOutputs = () =>
  api.post('/projects/clear-outputs').then(r => r.data);
export const runScript = (script, args = []) =>
  api.post('/pipeline/run-script', { script, args }).then(r => r.data);

// Files
export const listProjectFiles = (projectId) => api.get(`/files/${projectId}/list`).then(r => r.data);
export const getFileInfo = (projectId, filePath) => api.get(`/files/${projectId}/info/${encodeURIComponent(filePath)}`).then(r => r.data);
export const runFiles = (projectId, files, outputVersion = 'v2', evaluate = false, expectedDir = null) =>
  api.post('/files/run', { project_id: projectId, files, output_version: outputVersion, evaluate, expected_dir: expectedDir }).then(r => r.data);
export const listV2Outputs = (projectId) => api.get(`/files/${projectId}/v2-outputs`).then(r => r.data);

export default api;
