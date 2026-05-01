import { useEffect, useState } from 'react';
import { listProjects, healthCheck, listJobs, clearAllJobs, clearAllOutputs } from '../api';

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');
  const [clearMsg, setClearMsg] = useState('');
  const [clearError, setClearError] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'));
    listProjects().then(setProjects);
    listJobs(50).then(setJobs);
  }, []);

  const refreshData = () => {
    listProjects().then(setProjects);
    listJobs(5).then(setJobs);
  };

  const handleClearJobs = async () => {
    setClearMsg('');
    setClearError('');
    try {
      const res = await clearAllJobs();
      if (res.success) {
        setClearMsg('Jobs history cleared successfully');
        refreshData();
      } else {
        setClearError(res.error || 'Failed to clear jobs');
      }
    } catch (e) {
      setClearError(e.message || 'Failed to clear jobs');
    }
    setConfirmAction(null);
  };

  const handleClearOutputs = async () => {
    setClearMsg('');
    setClearError('');
    try {
      const res = await clearAllOutputs();
      if (res.success) {
        setClearMsg(`Outputs cleared: ${res.count} items deleted`);
        refreshData();
      } else {
        setClearError(res.errors?.join(', ') || 'Failed to clear outputs');
      }
    } catch (e) {
      setClearError(e.message || 'Failed to clear outputs');
    }
    setConfirmAction(null);
  };

  const handleClearAll = async () => {
    setClearMsg('');
    setClearError('');
    try {
      const jobsRes = await clearAllJobs();
      const outputsRes = await clearAllOutputs();
      if (jobsRes.success && outputsRes.success) {
        setClearMsg(`All data cleared: ${outputsRes.count} outputs + all jobs removed`);
        refreshData();
      } else {
        setClearError('Some items failed to clear');
      }
    } catch (e) {
      setClearError(e.message || 'Failed to clear data');
    }
    setConfirmAction(null);
  };

  const stats = {
    total: projects.length,
    withOutput: projects.filter(p => p.has_output).length,
    running: jobs.filter(j => j.status === 'running').length,
    completed: jobs.filter(j => j.status === 'completed').length,
  };

  const confirmLabels = {
    jobs: { title: 'Clear Jobs History', desc: 'This will delete all pipeline job records. This action cannot be undone.', action: handleClearJobs },
    outputs: { title: 'Clear All Outputs', desc: 'This will delete all prediction.json and evaluation_report.json files. This action cannot be undone.', action: handleClearOutputs },
    all: { title: 'Clear All Data', desc: 'This will delete all jobs history AND all output files. This action cannot be undone.', action: handleClearAll },
  };

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>System overview and recent activity</p>
      </div>

      <div className="grid grid-4" style={{ marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Projects</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--success)' }}>{stats.withOutput}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--primary)' }}>{stats.running}</div>
          <div className="stat-label">Running</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: apiStatus === 'ok' ? 'var(--success)' : 'var(--danger)' }}>
            {apiStatus === 'ok' ? 'Online' : 'Error'}
          </div>
          <div className="stat-label">API Status</div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Recent Jobs</div>
          {jobs.length === 0 ? (
            <p style={{ color: 'var(--text-light)' }}>No jobs yet. Go to Pipeline to start one.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Status</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => (
                  <tr key={j.id}>
                    <td><strong>{j.project_id}</strong></td>
                    <td>
                      <span className={`badge badge-${j.status === 'completed' ? 'success' : j.status === 'running' ? 'warning' : 'danger'}`}>
                        {j.status}
                      </span>
                    </td>
                    <td>{Math.round((j.progress || 0) * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="card">
          <div className="card-title">Quick Start</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <a href="#/pipeline" className="btn btn-primary" style={{ justifyContent: 'center' }}>
              Run Pipeline
            </a>
            <a href="#/projects" className="btn btn-secondary" style={{ justifyContent: 'center' }}>
              Browse Projects
            </a>
            <a href="#/results" className="btn btn-secondary" style={{ justifyContent: 'center' }}>
              View Results
            </a>
          </div>
        </div>
      </div>

      {/* Data Management Section */}
      <div className="card" style={{ marginTop: 24, borderColor: 'var(--danger)' }}>
        <div className="card-title" style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 8 }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
          Data Management
        </div>
        <p style={{ color: 'var(--text-light)', marginBottom: 16 }}>
          Manage stored data. These actions are permanent and cannot be undone.
        </p>

        <div className="grid grid-3" style={{ gap: 12 }}>
          <button
            className="btn btn-danger"
            style={{ justifyContent: 'center' }}
            onClick={() => setConfirmAction('jobs')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            Clear Jobs History
          </button>
          <button
            className="btn btn-danger"
            style={{ justifyContent: 'center' }}
            onClick={() => setConfirmAction('outputs')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            Clear All Outputs
          </button>
          <button
            className="btn btn-danger"
            style={{ justifyContent: 'center' }}
            onClick={() => setConfirmAction('all')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            Clear All Data
          </button>
        </div>

        {clearMsg && (
          <div className="badge badge-success" style={{ marginTop: 12, display: 'inline-flex', padding: '8px 12px' }}>
            {clearMsg}
          </div>
        )}
        {clearError && (
          <div className="badge badge-danger" style={{ marginTop: 12, display: 'inline-flex', padding: '8px 12px' }}>
            {clearError}
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {confirmAction && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: 420, width: '90%' }}>
            <div className="card-title" style={{ color: 'var(--danger)' }}>
              {confirmLabels[confirmAction].title}
            </div>
            <p style={{ marginBottom: 20 }}>
              {confirmLabels[confirmAction].desc}
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setConfirmAction(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={confirmLabels[confirmAction].action}
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Dashboard;
