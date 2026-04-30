import { useEffect, useState } from 'react';
import { listProjects, healthCheck, listJobs } from '../api';

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus('ok'))
      .catch(() => setApiStatus('error'));
    listProjects().then(setProjects);
    listJobs(5).then(setJobs);
  }, []);

  const stats = {
    total: projects.length,
    withOutput: projects.filter(p => p.has_output).length,
    running: jobs.filter(j => j.status === 'running').length,
    completed: jobs.filter(j => j.status === 'completed').length,
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
    </div>
  );
}

export default Dashboard;
