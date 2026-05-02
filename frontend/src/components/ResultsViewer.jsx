import { useEffect, useState } from 'react';
import { listProjects, getProjectOutput, getProjectEvaluation, evaluateProject, listDirectory, clearProjectOutput, exportXLSX, exportMarkedPDF } from '../api';

function ResultsViewer() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [output, setOutput] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [activeTab, setActiveTab] = useState('output');
  const [tradeFilter, setTradeFilter] = useState('all');
  const [expectedBrowserOpen, setExpectedBrowserOpen] = useState(false);
  const [expectedPath, setExpectedPath] = useState('');
  const [browseExpPath, setBrowseExpPath] = useState('/app/client_files');
  const [browseExpItems, setBrowseExpItems] = useState([]);
  const [browseExpLoading, setBrowseExpLoading] = useState(false);
  const [browseExpError, setBrowseExpError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);
  const [clearMsg, setClearMsg] = useState('');

  useEffect(() => {
    listProjects().then(data => {
      setProjects(data);
      const withOutput = data.find(p => p.has_output);
      if (withOutput) setSelectedProject(withOutput.id);
    });
  }, []);

  const loadOutput = () => {
    if (!selectedProject) return;
    setOutput(null);
    setEvaluation(null);
    getProjectOutput(selectedProject).then(setOutput);
    getProjectEvaluation(selectedProject).then(res => { if (!res.error) setEvaluation(res); });
  };

  useEffect(() => {
    loadOutput();
  }, [selectedProject, refreshKey]);

  const handleEvaluate = () => {
    setEvaluating(true);
    evaluateProject(selectedProject, expectedPath || null).then(res => {
      if (!res.error) setEvaluation(res);
      setEvaluating(false);
    }).catch(() => setEvaluating(false));
  };

  const loadExpBrowse = async (path) => {
    setBrowseExpLoading(true);
    setBrowseExpError('');
    try {
      const data = await listDirectory(path);
      if (data.error) {
        setBrowseExpError(data.error);
      } else {
        setBrowseExpPath(data.path);
        setBrowseExpItems(data.items || []);
      }
    } catch (e) {
      setBrowseExpError(e.message || 'Failed to load directory');
    }
    setBrowseExpLoading(false);
  };

  const handleOpenExpectedBrowser = async () => {
    setExpectedBrowserOpen(true);
    await loadExpBrowse('/app/client_files');
  };

  const handleSelectExpectedFolder = (path) => {
    setExpectedPath(path);
    setExpectedBrowserOpen(false);
  };

  const handleClearOutput = async () => {
    if (!selectedProject) return;
    if (!confirm(`Clear all results for ${selectedProject}?`)) return;
    setClearMsg('');
    try {
      const res = await clearProjectOutput(selectedProject);
      if (res.success) {
        setClearMsg(`Cleared ${res.count} files`);
        setOutput(null);
        setEvaluation(null);
        // Refresh projects list to update has_output
        listProjects().then(setProjects);
      } else {
        setClearMsg('Failed to clear: ' + (res.errors?.join(', ') || 'Unknown error'));
      }
    } catch (e) {
      setClearMsg('Error: ' + (e.message || 'Failed to clear'));
    }
    setTimeout(() => setClearMsg(''), 3000);
  };

  const handleExportXLSX = async (projectId) => {
    try {
      const blob = await exportXLSX(projectId);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${projectId}_takeoff.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Export failed: ' + (e.message || 'Unknown error'));
    }
  };

  const handleExportPDF = async (projectId) => {
    try {
      const blob = await exportMarkedPDF(projectId);
      const url = window.URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${projectId}_marked.pdf`);
      link.setAttribute('target', '_blank');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert('Marked PDF export failed: ' + (e.message || 'Unknown error'));
    }
  };

  const filteredItems = output?.line_items?.filter(item => tradeFilter === 'all' || item.trade === tradeFilter) || [];
  
  // Handle both old and new evaluation report formats
  const matchedCount = typeof evaluation?.matched_items === 'number' ? evaluation.matched_items : (evaluation?.matched_count || 0);
  const missingCount = Array.isArray(evaluation?.missing_items) ? evaluation.missing_items.length : (evaluation?.missing_count || 0);
  const extraCount = Array.isArray(evaluation?.extra_items) ? evaluation.extra_items.length : (evaluation?.extra_count || 0);
  const totalPredicted = evaluation?.total_predicted || matchedCount + extraCount;
  const totalExpected = evaluation?.total_expected || matchedCount + missingCount;
  const matchRate = totalExpected > 0 ? (matchedCount / totalExpected) * 100 : 0;
  const avgQtyDiff = evaluation?.avg_qty_pct_diff || 0;
  const quantityDiffs = evaluation?.quantity_differences || [];

  return (
    <div>
      <div className="page-header">
        <h2>Results</h2>
        <p>View predictions and accuracy</p>
      </div>

      {clearMsg && (
        <div className="card" style={{ marginBottom: 16, background: '#f0fdf4', borderColor: 'var(--success)' }}>
          <p style={{ color: 'var(--success)', margin: 0 }}>{clearMsg}</p>
        </div>
      )}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <select className="form-select" value={selectedProject} onChange={e => setSelectedProject(e.target.value)} style={{ width: 260 }}>
            <option value="">Select project...</option>
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.id} {p.has_output ? '✓' : ''}</option>
            ))}
          </select>
          <div className="tabs" style={{ margin: 0, border: 'none' }}>
            <button className={`tab ${activeTab === 'output' ? 'active' : ''}`} onClick={() => setActiveTab('output')}>Output</button>
            <button className={`tab ${activeTab === 'evaluation' ? 'active' : ''}`} onClick={() => setActiveTab('evaluation')}>Evaluation</button>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={() => setRefreshKey(k => k + 1)} title="Refresh results">
            🔄 Refresh
          </button>
          {selectedProject && (
            <button className="btn btn-sm btn-danger" onClick={handleClearOutput} title="Clear results for this project">
              🗑️ Clear
            </button>
          )}
          {activeTab === 'evaluation' && selectedProject && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn btn-sm btn-primary" onClick={handleEvaluate} disabled={evaluating}>
                {evaluating ? 'Running...' : 'Run Evaluation'}
              </button>
              <button className="btn btn-sm btn-secondary" onClick={handleOpenExpectedBrowser}>
                📂 Browse Expected Output
              </button>
            </div>
          )}
          {output && selectedProject && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button className="btn btn-sm btn-success" onClick={() => handleExportXLSX(selectedProject)}>
                📊 Export Excel
              </button>
              <button className="btn btn-sm btn-success" onClick={() => handleExportPDF(selectedProject)}>
                📄 Marked PDF
              </button>
            </div>
          )}
        </div>
      </div>

      {activeTab === 'output' && output && (
        <div>
          <div className="grid grid-4" style={{ marginBottom: 16 }}>
            <div className="stat-card"><div className="stat-value">{output.total_line_items}</div><div className="stat-label">Items</div></div>
            <div className="stat-card"><div className="stat-value" style={{ color: 'var(--success)' }}>{output.confidence_summary?.high || 0}</div><div className="stat-label">High Conf</div></div>
            <div className="stat-card"><div className="stat-value" style={{ color: 'var(--warning)' }}>{output.confidence_summary?.medium || 0}</div><div className="stat-label">Medium Conf</div></div>
            <div className="stat-card"><div className="stat-value">{output.trades?.length || 0}</div><div className="stat-label">Trades</div></div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button className={`btn btn-sm ${tradeFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTradeFilter('all')}>All</button>
              {output.trades?.map(t => (
                <button key={t} className={`btn btn-sm ${tradeFilter === t ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTradeFilter(t)}>{t}</button>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Line Items ({filteredItems.length})</div>
            <div className="table-container" style={{ maxHeight: 500, overflow: 'auto' }}>
              <table>
                <thead style={{ position: 'sticky', top: 0 }}>
                  <tr><th>#</th><th>Description</th><th>Trade</th><th>Qty</th><th>Unit</th><th>Conf</th></tr>
                </thead>
                <tbody>
                  {filteredItems.map((item, idx) => (
                    <tr key={idx}>
                      <td style={{ fontSize: 12, color: 'var(--text-light)' }}>{idx + 1}</td>
                      <td style={{ maxWidth: 400 }}>{item.description}</td>
                      <td><span className="badge badge-sample">{item.trade}</span></td>
                      <td style={{ textAlign: 'right' }}>{item.quantity?.toLocaleString() ?? '—'}</td>
                      <td>{item.unit ?? '—'}</td>
                      <td><span className={`badge badge-${item.confidence === 'high' ? 'success' : item.confidence === 'medium' ? 'warning' : 'danger'}`}>{item.confidence}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'evaluation' && evaluation && !evaluation.error && (
        <div>
          <div className="card" style={{ marginBottom: 24, textAlign: 'center', padding: 32 }}>
            <div style={{ fontSize: 14, color: 'var(--text-light)', marginBottom: 8 }}>Match Rate</div>
            <div style={{ fontSize: 56, fontWeight: 700, color: matchRate > 50 ? 'var(--success)' : matchRate > 30 ? 'var(--warning)' : 'var(--danger)' }}>
              {matchRate.toFixed(1)}%
            </div>
            <div style={{ marginTop: 12 }}>
              <span className="badge badge-success">{matchedCount} Matched</span>
              <span className="badge badge-warning" style={{ marginLeft: 8 }}>{missingCount} Missing</span>
              <span className="badge badge-danger" style={{ marginLeft: 8 }}>{extraCount} Extra</span>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <div className="card-title">Summary</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { label: 'Predicted', value: totalPredicted },
                  { label: 'Expected', value: totalExpected },
                  { label: 'Matched', value: matchedCount },
                  { label: 'Missing', value: missingCount },
                  { label: 'Extra', value: extraCount },
                  { label: 'Avg Qty Diff', value: `${avgQtyDiff.toFixed(1)}%` },
                ].map(s => (
                  <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <span>{s.label}</span><strong>{s.value}</strong>
                  </div>
                ))}
              </div>
            </div>

            {quantityDiffs.length > 0 && (
              <div className="card">
                <div className="card-title">Quantity Differences ({quantityDiffs.length})</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th><th>Predicted</th><th>Expected</th><th>Diff %</th></tr></thead>
                    <tbody>
                      {quantityDiffs.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{item.description || '—'}</td>
                          <td style={{ fontSize: 12, textAlign: 'right' }}>{item.predicted?.toLocaleString() ?? '—'}</td>
                          <td style={{ fontSize: 12, textAlign: 'right' }}>{item.expected?.toLocaleString() ?? '—'}</td>
                          <td style={{ fontSize: 12, textAlign: 'right', color: Math.abs(item.pct_diff || 0) > 10 ? 'var(--danger)' : 'var(--success)' }}>
                            {(item.pct_diff || 0).toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {evaluation.missing_items && evaluation.missing_items.length > 0 && (
              <div className="card">
                <div className="card-title">Missing Items ({evaluation.missing_items.length})</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th></tr></thead>
                    <tbody>
                      {evaluation.missing_items.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{typeof item === 'string' ? item : (item.description || '—')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {evaluation.extra_items && evaluation.extra_items.length > 0 && (
              <div className="card">
                <div className="card-title">Extra Items ({evaluation.extra_items.length})</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th></tr></thead>
                    <tbody>
                      {evaluation.extra_items.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{typeof item === 'string' ? item : (item.description || '—')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'output' && !output && selectedProject && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <p style={{ color: 'var(--text-light)' }}>No output yet. Run the pipeline first.</p>
        </div>
      )}

      {/* Expected Output Browser Modal */}
      {expectedBrowserOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div className="card" style={{ maxWidth: 700, width: '92%', maxHeight: '85vh', display: 'flex', flexDirection: 'column' }}>
            <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>📂 Select Expected Output Folder</span>
              <button className="btn btn-sm btn-secondary" onClick={() => setExpectedBrowserOpen(false)}>Close</button>
            </div>

            {expectedPath && (
              <div className="badge badge-success" style={{ marginBottom: 12, display: 'inline-flex' }}>
                Selected: {expectedPath}
              </div>
            )}

            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
              <button className="btn btn-sm btn-secondary" onClick={() => loadExpBrowse('/app')}> /app </button>
              <button className="btn btn-sm btn-secondary" onClick={() => loadExpBrowse('/app/client_files')}> client_files </button>
              {browseExpPath !== '/' && (
                <button className="btn btn-sm btn-secondary" onClick={() => {
                  const parent = browseExpPath.substring(0, browseExpPath.lastIndexOf('/')) || '/';
                  loadExpBrowse(parent);
                }}> ⬆ Up </button>
              )}
            </div>

            <div className="form-input" style={{ fontSize: 12, marginBottom: 12, background: 'var(--bg)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {browseExpPath}
            </div>

            {browseExpError && (
              <div className="badge badge-danger" style={{ marginBottom: 12, display: 'inline-flex' }}>
                {browseExpError}
              </div>
            )}

            <div style={{ marginBottom: 12 }}>
              <button className="btn btn-primary" onClick={() => handleSelectExpectedFolder(browseExpPath)}>
                ✅ Select Current Folder
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, border: '1px solid var(--border)', borderRadius: 8 }}>
              {browseExpLoading ? (
                <p style={{ color: 'var(--text-light)', textAlign: 'center', padding: 32 }}>Loading...</p>
              ) : browseExpItems.length === 0 ? (
                <p style={{ color: 'var(--text-light)', textAlign: 'center', padding: 32 }}>Empty directory</p>
              ) : (
                <div>
                  {browseExpItems.map(item => (
                    <div
                      key={item.path}
                      onClick={() => { if (item.type === 'dir') loadExpBrowse(item.path); }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 12px',
                        borderBottom: '1px solid var(--border)',
                        cursor: item.type === 'dir' ? 'pointer' : 'default',
                        background: item.type === 'dir' ? '#f8fafc' : '#fff',
                      }}
                      onMouseEnter={e => { if (item.type === 'dir') e.currentTarget.style.background = '#eff6ff'; }}
                      onMouseLeave={e => { if (item.type === 'dir') e.currentTarget.style.background = '#f8fafc'; }}
                    >
                      <span style={{ fontSize: 18, flexShrink: 0 }}>
                        {item.type === 'dir' ? '📁' : item.extension === '.xlsx' ? '📊' : item.extension === '.pdf' ? '📄' : '📎'}
                      </span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: item.type === 'dir' ? 600 : 400, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {item.name}
                        </div>
                        {item.type === 'file' && (
                          <div style={{ fontSize: 11, color: 'var(--text-light)' }}>
                            {item.extension} · {(item.size / 1024).toFixed(1)} KB
                          </div>
                        )}
                      </div>
                      {item.type === 'dir' && (
                        <span style={{ fontSize: 11, color: 'var(--primary)', flexShrink: 0 }}>Open →</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ResultsViewer;
