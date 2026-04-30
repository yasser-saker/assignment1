import { useEffect, useState } from 'react';
import { listProjects, getProjectOutput, getProjectEvaluation, evaluateProject } from '../api';

function ResultsViewer() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [output, setOutput] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [evaluating, setEvaluating] = useState(false);
  const [activeTab, setActiveTab] = useState('output');
  const [tradeFilter, setTradeFilter] = useState('all');

  useEffect(() => {
    listProjects().then(data => {
      setProjects(data);
      const withOutput = data.find(p => p.has_output);
      if (withOutput) setSelectedProject(withOutput.id);
    });
  }, []);

  useEffect(() => {
    if (!selectedProject) return;
    setOutput(null);
    setEvaluation(null);
    getProjectOutput(selectedProject).then(setOutput);
    getProjectEvaluation(selectedProject).then(res => { if (!res.error) setEvaluation(res); });
  }, [selectedProject]);

  const handleEvaluate = () => {
    setEvaluating(true);
    evaluateProject(selectedProject).then(res => {
      if (!res.error) setEvaluation(res);
      setEvaluating(false);
    }).catch(() => setEvaluating(false));
  };

  const filteredItems = output?.line_items?.filter(item => tradeFilter === 'all' || item.trade === tradeFilter) || [];
  const matchRate = evaluation?.match_rate || 0;

  return (
    <div>
      <div className="page-header">
        <h2>Results</h2>
        <p>View predictions and accuracy</p>
      </div>

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
          {activeTab === 'evaluation' && selectedProject && (
            <button className="btn btn-sm btn-primary" onClick={handleEvaluate} disabled={evaluating}>
              {evaluating ? 'Running...' : 'Run Evaluation'}
            </button>
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
              <span className="badge badge-success">{evaluation.matched_count} Matched</span>
              <span className="badge badge-warning" style={{ marginLeft: 8 }}>{evaluation.missing_count} Missing</span>
              <span className="badge badge-danger" style={{ marginLeft: 8 }}>{evaluation.extra_count} Extra</span>
            </div>
          </div>

          <div className="grid grid-2">
            <div className="card">
              <div className="card-title">Summary</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { label: 'Predicted', value: evaluation.total_predicted },
                  { label: 'Expected', value: evaluation.total_expected },
                  { label: 'Matched', value: evaluation.matched_count },
                  { label: 'Missing', value: evaluation.missing_count },
                  { label: 'Extra', value: evaluation.extra_count },
                  { label: 'Avg Qty Diff', value: `${evaluation.avg_qty_pct_diff?.toFixed(1) || 0}%` },
                ].map(s => (
                  <div key={s.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <span>{s.label}</span><strong>{s.value}</strong>
                  </div>
                ))}
              </div>
            </div>

            {evaluation.matched_items && evaluation.matched_items.length > 0 && (
              <div className="card">
                <div className="card-title">Matched Items</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th><th>Diff %</th></tr></thead>
                    <tbody>
                      {evaluation.matched_items.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{item.description || item.predicted?.description || '—'}</td>
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
                <div className="card-title">Missing Items</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th><th>Qty</th></tr></thead>
                    <tbody>
                      {evaluation.missing_items.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{item.description || '—'}</td>
                          <td style={{ fontSize: 12, textAlign: 'right' }}>{item.quantity ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {evaluation.extra_items && evaluation.extra_items.length > 0 && (
              <div className="card">
                <div className="card-title">Extra Items</div>
                <div className="table-container" style={{ maxHeight: 350, overflow: 'auto' }}>
                  <table>
                    <thead><tr><th>Description</th><th>Qty</th></tr></thead>
                    <tbody>
                      {evaluation.extra_items.slice(0, 30).map((item, idx) => (
                        <tr key={idx}>
                          <td style={{ fontSize: 12 }}>{item.description || '—'}</td>
                          <td style={{ fontSize: 12, textAlign: 'right' }}>{item.quantity ?? '—'}</td>
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
    </div>
  );
}

export default ResultsViewer;
