import { useState, useEffect, useCallback } from 'react';
import { listProjectFiles, runFiles, getJobStatus, listV2Outputs } from '../api';

function FileBrowser({ projectId }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(new Set());
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [v2Outputs, setV2Outputs] = useState([]);
  const [polling, setPolling] = useState(false);

  const loadFiles = useCallback(async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await listProjectFiles(projectId);
      setFiles(data);
      // Auto-select non-scanned files by default
      const autoSelect = new Set();
      data.forEach(f => {
        if (f.scanned_pages === 0) autoSelect.add(f.path);
      });
      setSelectedFiles(autoSelect);
    } catch (e) {
      console.error('Failed to load files:', e);
    }
    setLoading(false);
  }, [projectId]);

  const loadV2Outputs = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await listV2Outputs(projectId);
      setV2Outputs(data);
    } catch (e) {
      console.error('Failed to load v2 outputs:', e);
    }
  }, [projectId]);

  useEffect(() => {
    loadFiles();
    loadV2Outputs();
  }, [loadFiles, loadV2Outputs]);

  // Poll job status
  useEffect(() => {
    if (!jobId || !polling) return;
    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId);
        setJobStatus(status);
        if (status.status === 'completed' || status.status === 'failed') {
          setPolling(false);
          loadV2Outputs();
        }
      } catch (e) {
        console.error('Poll error:', e);
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [jobId, polling, loadV2Outputs]);

  const toggleFile = (path) => {
    setSelectedFiles(prev => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const toggleAll = () => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map(f => f.path)));
    }
  };

  const handleRun = async () => {
    if (selectedFiles.size === 0) return;
    setJobStatus({ status: 'running', message: 'Starting...' });
    setPolling(true);
    try {
      const result = await runFiles(projectId, Array.from(selectedFiles), 'v2');
      setJobId(result.job_id);
    } catch (e) {
      setJobStatus({ status: 'failed', message: e.message });
      setPolling(false);
    }
  };

  const formatSize = (mb) => mb < 1 ? `${(mb * 1024).toFixed(0)}KB` : `${mb.toFixed(1)}MB`;

  const getFileIcon = (fileType) => {
    switch (fileType) {
      case 'drawing': return '📐';
      case 'spec': return '📋';
      case 'sow': return '📝';
      case 'addendum': return '📎';
      default: return '📄';
    }
  };

  return (
    <div className="file-browser">
      <div className="file-browser-header">
        <h3>📁 Project Files</h3>
        <div className="file-actions">
          <button className="btn btn-sm" onClick={toggleAll}>
            {selectedFiles.size === files.length ? 'Deselect All' : 'Select All'}
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={handleRun}
            disabled={selectedFiles.size === 0 || polling}
          >
            {polling ? '⏳ Running...' : `▶️ Process Selected (${selectedFiles.size})`}
          </button>
          <button className="btn btn-sm" onClick={loadFiles}>🔄 Refresh</button>
        </div>
      </div>

      {loading && <div className="loading">Loading files...</div>}

      {!loading && files.length === 0 && (
        <div className="empty-state">No PDF files found in project directory.</div>
      )}

      {files.length > 0 && (
        <div className="file-list">
          <div className="file-list-header">
            <span style={{ width: 30 }}></span>
            <span style={{ flex: 2 }}>File</span>
            <span style={{ width: 80 }}>Size</span>
            <span style={{ width: 80 }}>Pages</span>
            <span style={{ width: 80 }}>Scanned</span>
            <span style={{ width: 80 }}>Type</span>
            <span style={{ width: 60 }}>v2</span>
          </div>
          {files.map(file => (
            <div key={file.path} className={`file-row ${file.scanned_pages > 0 ? 'scanned' : ''}`}>
              <input
                type="checkbox"
                checked={selectedFiles.has(file.path)}
                onChange={() => toggleFile(file.path)}
                style={{ width: 30 }}
              />
              <span style={{ flex: 2 }} className="file-name" title={file.path}>
                {getFileIcon(file.file_type)} {file.name}
              </span>
              <span style={{ width: 80 }}>{formatSize(file.size_mb)}</span>
              <span style={{ width: 80 }}>{file.total_pages}</span>
              <span style={{ width: 80, color: file.scanned_pages > 0 ? '#f59e0b' : '#10b981' }}>
                {file.scanned_pages > 0 ? `⚠️ ${file.scanned_pages}` : '✓ Text'}
              </span>
              <span style={{ width: 80 }}>
                <span className={`badge badge-${file.file_type}`}>{file.file_type}</span>
              </span>
              <span style={{ width: 60 }}>
                {file.has_output_v2 ? '✅' : '—'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Live Processing Status */}
      {jobStatus && (
        <div className={`job-status job-status-${jobStatus.status}`}>
          <h4>🔄 Live Processing</h4>
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${(jobStatus.progress || 0) * 100}%` }}
            />
          </div>
          <div className="job-meta">
            <span>Status: <strong>{jobStatus.status}</strong></span>
            <span>Progress: {Math.round((jobStatus.progress || 0) * 100)}%</span>
          </div>
          {jobStatus.message && (
            <div className="job-message">{jobStatus.message}</div>
          )}
          {jobStatus.logs && jobStatus.logs.length > 0 && (
            <div className="job-logs">
              {jobStatus.logs.slice(-20).map((log, i) => (
                <div key={i} className="log-line">{log}</div>
              ))}
            </div>
          )}
          {jobStatus.status === 'completed' && jobStatus.output_path && (
            <div className="job-output">
              ✅ Output saved to: <code>{jobStatus.output_path}</code>
            </div>
          )}
          {jobStatus.error && (
            <div className="job-error">❌ {jobStatus.error}</div>
          )}
        </div>
      )}

      {/* v2 Outputs */}
      {v2Outputs.length > 0 && (
        <div className="v2-outputs">
          <h4>📦 v2 Outputs</h4>
          <div className="v2-list">
            {v2Outputs.map(out => (
              <div key={out.file} className="v2-item">
                <span className="v2-name">{out.file}</span>
                <span className="v2-meta">
                  {out.line_items_count} items · {(out.size / 1024).toFixed(1)}KB
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default FileBrowser;
