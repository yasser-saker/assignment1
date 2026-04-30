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
  const pollRef = useRef(null);

  useEffect(() => {
    listProjects().then(setProjects);
    loadJobs();
  }, []);

  const loadJobs = () => listJobs(10).then(setJobs);

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
    runPipeline(projectId, projectPath, ['ingestion', 'extraction', 'output', 'evaluation'], true)
      .then(res => { if (res.job_id) setActiveJob(res.job_id); else setIsRunning(false); })
      .catch(() => setIsRunning(false));
  };

  const currentJob = jobs.find(j => j.id === activeJob);
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

      {isRunning && currentJob && (
        <div className="card" style={{ marginBottom: 24, borderColor: 'var(--primary)' }}>
          <div className="card-title">Progress</div>
          <div className="progress-bar" style={{ marginBottom: 12 }}>
            <div className="progress-fill" style={{ width: `${Math.round((currentJob.progress || 0) * 100)}%` }} />
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {stages.map(s => {
              const stage = currentJob.stages?.find(st => st.name === s);
              const status = stage?.status || 'pending';
              return (
                <span key={s} className={`badge badge-${status === 'completed' ? 'success' : status === 'running' ? 'warning' : 'danger'}`} style={{ textTransform: 'capitalize' }}>
                  {status === 'running' && <span className="status-dot status-running" style={{ marginRight: 4 }} />}
                  {s}
                </span>
              );
            })}
          </div>
          {currentJob.logs?.length > 0 && (
            <div className="logs" style={{ marginTop: 12, maxHeight: 200 }}>
              {currentJob.logs.slice(-10).map((log, i) => (
                <div key={i} className="log-entry">{log.message}</div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="card">
        <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>History</span>
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
                <th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id}>
                  <td><strong>{job.project_id}</strong></td>
                  <td>
                    <span className={`badge badge-${job.status === 'completed' ? 'success' : job.status === 'running' ? 'warning' : 'danger'}`}>
                      {job.status}
                    </span>
                  </td>
                  <td>{Math.round((job.progress || 0) * 100)}%</td>
                  <td>
                    <button className="btn btn-sm btn-secondary" onClick={() => deleteJob(job.id).then(loadJobs)}>
                      Delete
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
