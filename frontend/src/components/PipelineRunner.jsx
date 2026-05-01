import { useEffect, useState, useRef } from 'react';
import { listProjects, runPipeline, getJobStatus, listJobs, deleteJob, browseFolder } from '../api';

function PipelineRunner() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [customPath, setCustomPath] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [activeJob, setActiveJob] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const pollRef = useRef(null);
  const selectedPollRef = useRef(null);

  useEffect(() => {
    listProjects().then(setProjects);
    loadJobs();
  }, []);

  const loadJobs = () => listJobs(20).then(setJobs);

  // Poll active running job
  useEffect(() => {
    if (!activeJob) return;
    pollRef.current = setInterval(() => {
      getJobStatus(activeJob).then(job => {
        setJobs(prev => prev.map(j => j.id === job.id ? job : j));
        if (job.status === 'completed' || job.status === 'failed') {
          setIsRunning(false);
          if (pollRef.current) clearInterval(pollRef.current);
        }
      });
    }, 1500);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeJob]);

  // Poll selected job (for viewing details)
  useEffect(() => {
    if (!selectedJob || selectedJob === activeJob) {
      if (selectedPollRef.current) clearInterval(selectedPollRef.current);
      return;
    }
    selectedPollRef.current = setInterval(() => {
      getJobStatus(selectedJob).then(job => {
        setJobs(prev => prev.map(j => j.id === job.id ? job : j));
      });
    }, 2000);
    return () => { if (selectedPollRef.current) clearInterval(selectedPollRef.current); };
  }, [selectedJob, activeJob]);

  const handleBrowse = () => {
    browseFolder().then(res => {
      if (res.success && res.folder) {
        setCustomPath(res.folder);
        setUseCustom(true);
      }
    });
  };

  const handleRun = () => {
    let projectId = selectedProject;
    let projectPath = null;
    if (useCustom) {
      if (!customPath.trim()) return;
      projectPath = customPath.trim();
      const parts = customPath.split(/[\\\/]/);
      const name = parts.filter(Boolean).pop() || 'custom';
      projectId = name.split(' ')[0];
      if (!projectId.startsWith('TAKEOFF-')) projectId = 'CUSTOM-' + projectId;
    } else {
      if (!selectedProject) return;
    }
    setIsRunning(true);
    setSelectedJob(null);
    runPipeline(projectId, projectPath, ['ingestion', 'extraction', 'output', 'evaluation'], true)
      .then(res => { 
        if (res.job_id) {
          setActiveJob(res.job_id);
          setSelectedJob(res.job_id);
        } else {
          setIsRunning(false);
        }
      })
      .catch(() => setIsRunning(false));
  };

  const handleSelectJob = (jobId) => {
    setSelectedJob(jobId === selectedJob ? null : jobId);
  };

  const handleDeleteJob = (e, jobId) => {
    e.stopPropagation();
    deleteJob(jobId).then(() => {
      if (selectedJob === jobId) setSelectedJob(null);
      if (activeJob === jobId) {
        setActiveJob(null);
        setIsRunning(false);
      }
      loadJobs();
    });
  };

  const currentJob = jobs.find(j => j.id === activeJob);
  const displayJob = jobs.find(j => j.id === selectedJob);
  const stages = ['initialization', 'ingestion', 'extraction', 'output', 'evaluation', 'finalization'];

  return (
    <div>
      <div className="page-header">
        <h2>Pipeline</h2>
        <p>Run extraction on a project</p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">Select Project</div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          <button className={`btn btn-sm ${!useCustom ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setUseCustom(false)}>
            Existing
          </button>
          <button className={`btn btn-sm ${useCustom ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setUseCustom(true)}>
            Custom Folder
          </button>
        </div>

        {!useCustom ? (
          <select className="form-select" value={selectedProject} onChange={e => setSelectedProject(e.target.value)}>
            <option value="">Select project...</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.id} — {p.name}</option>
            ))}
          </select>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              className="form-input"
              value={customPath}
              onChange={e => setCustomPath(e.target.value)}
              placeholder="Full path to project folder"
              style={{ flex: 1 }}
            />
            <button className="btn btn-secondary" onClick={handleBrowse}>
              Browse...
            </button>
          </div>
        )}

        <button
          className="btn btn-primary"
          onClick={handleRun}
          disabled={isRunning || (!useCustom && !selectedProject) || (useCustom && !customPath.trim())}
          style={{ width: '100%', marginTop: 16, justifyContent: 'center' }}
        >
          {isRunning ? 'Running...' : 'Run Pipeline'}
        </button>
      </div>

      {/* Job Details Card - shows for selected job (active or historical) */}
      {displayJob && (
        <div className="card" style={{ marginBottom: 24, borderColor: displayJob.id === activeJob ? 'var(--primary)' : 'var(--border)' }}>
          <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>
              {displayJob.id === activeJob ? '▶️ Current Run' : '📋 Job Details'}
              <span style={{ marginLeft: 12, fontSize: 13, color: 'var(--text-light)', fontWeight: 400 }}>
                {displayJob.project_id} — {new Date(displayJob.created_at || Date.now()).toLocaleString()}
              </span>
            </span>
            <span className={`badge badge-${displayJob.status === 'completed' ? 'success' : displayJob.status === 'running' ? 'warning' : 'danger'}`}>
              {displayJob.status}
            </span>
          </div>

          <div className="progress-bar" style={{ marginBottom: 12 }}>
            <div className="progress-fill" style={{ width: `${Math.round((displayJob.progress || 0) * 100)}%` }} />
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            {stages.map(s => {
              const stage = displayJob.stages?.find(st => st.name === s);
              const status = stage?.status || 'pending';
              return (
                <span key={s} className={`badge badge-${status === 'completed' ? 'success' : status === 'running' ? 'warning' : 'danger'}`} style={{ textTransform: 'capitalize' }}>
                  {status === 'running' && <span className="status-dot status-running" style={{ marginRight: 4 }} />}
                  {s}
                </span>
              );
            })}
          </div>

          {displayJob.logs?.length > 0 && (
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-light)', marginBottom: 4 }}>
                Logs ({displayJob.logs.length} lines)
              </div>
              <div className="logs" style={{ maxHeight: 300 }}>
                {displayJob.logs.map((log, i) => (
                  <div key={i} className="log-entry">{log.message || log}</div>
                ))}
              </div>
            </div>
          )}

          {displayJob.error && (
            <div className="card" style={{ marginTop: 12, background: '#fef2f2', borderColor: 'var(--danger)' }}>
              <div style={{ color: 'var(--danger)', fontSize: 13 }}>
                <strong>Error:</strong> {displayJob.error}
              </div>
            </div>
          )}

          {displayJob.output_path && (
            <div style={{ marginTop: 12, fontSize: 13 }}>
              <span style={{ color: 'var(--text-light)' }}>Output: </span>
              <code style={{ fontSize: 12 }}>{displayJob.output_path}</code>
            </div>
          )}
        </div>
      )}

      <div className="card">
        <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>History ({jobs.length})</span>
          <button className="btn btn-sm btn-secondary" onClick={loadJobs}>Refresh</button>
        </div>
        {jobs.length === 0 ? (
          <p style={{ color: 'var(--text-light)' }}>No jobs yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Project</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Started</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr 
                  key={job.id} 
                  onClick={() => handleSelectJob(job.id)}
                  style={{ 
                    cursor: 'pointer',
                    background: selectedJob === job.id ? '#eff6ff' : undefined,
                    borderLeft: selectedJob === job.id ? '3px solid var(--primary)' : undefined,
                  }}
                  className="job-row"
                >
                  <td>
                    <strong>{job.project_id}</strong>
                    {job.id === activeJob && <span className="badge badge-warning" style={{ marginLeft: 8, fontSize: 10 }}>ACTIVE</span>}
                  </td>
                  <td>
                    <span className={`badge badge-${job.status === 'completed' ? 'success' : job.status === 'running' ? 'warning' : 'danger'}`}>
                      {job.status}
                    </span>
                  </td>
                  <td>{Math.round((job.progress || 0) * 100)}%</td>
                  <td style={{ fontSize: 12, color: 'var(--text-light)' }}>
                    {job.created_at ? new Date(job.created_at).toLocaleTimeString() : '—'}
                  </td>
                  <td>
                    <button 
                      className="btn btn-sm btn-secondary" 
                      onClick={(e) => handleDeleteJob(e, job.id)}
                      title="Delete job"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

export default PipelineRunner;
