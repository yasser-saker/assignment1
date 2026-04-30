import { useEffect, useState } from 'react';
import { listProjects, getProjectOutput } from '../api';

function Projects() {
  const [projects, setProjects] = useState([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [output, setOutput] = useState(null);

  useEffect(() => {
    listProjects().then(setProjects);
  }, []);

  const handleSelect = (project) => {
    setSelected(project);
    if (project.has_output) {
      getProjectOutput(project.id).then(setOutput);
    } else {
      setOutput(null);
    }
  };

  const filtered = projects.filter(p => {
    const matchesType = filter === 'all' || p.type === filter;
    const matchesSearch = search === '' || p.id.toLowerCase().includes(search.toLowerCase()) || p.name.toLowerCase().includes(search.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div>
      <div className="page-header">
        <h2>Projects</h2>
        <p>All construction takeoff projects</p>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            className="form-input"
            placeholder="Search..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            {['all', 'sample', 'challenge'].map(f => (
              <button key={f} className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter(f)}>
                {f === 'all' ? 'All' : f}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-title">Projects ({filtered.length})</div>
          <div className="table-container">
            <table>
              <thead><tr><th>ID</th><th>Type</th><th>Files</th><th>Status</th></tr></thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id} onClick={() => handleSelect(p)} style={{ cursor: 'pointer', background: selected?.id === p.id ? '#eff6ff' : undefined }}>
                    <td><strong>{p.id}</strong><div style={{ fontSize: 12, color: 'var(--text-light)' }}>{p.name}</div></td>
                    <td><span className={`badge badge-${p.type}`}>{p.type}</span></td>
                    <td>{p.files_count}</td>
                    <td>{p.has_output ? <span className="badge badge-success">Done</span> : <span className="badge badge-warning">Pending</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          {selected ? (
            <div className="card">
              <div className="card-title">{selected.id}</div>
              <div className="form-group">
                <label className="form-label">Path</label>
                <div className="form-input" style={{ background: 'var(--bg)', fontSize: 12 }}>{selected.path}</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div className="form-group"><label className="form-label">Type</label><div className="form-input" style={{ background: 'var(--bg)' }}>{selected.type}</div></div>
                <div className="form-group"><label className="form-label">Files</label><div className="form-input" style={{ background: 'var(--bg)' }}>{selected.files_count}</div></div>
              </div>

              {output ? (
                <div style={{ marginTop: 16 }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                    <div className="stat-card" style={{ padding: 12 }}><div className="stat-value" style={{ fontSize: 24 }}>{output.total_line_items}</div><div className="stat-label">Items</div></div>
                    <div className="stat-card" style={{ padding: 12 }}><div className="stat-value" style={{ fontSize: 24 }}>{output.trades?.length || 0}</div><div className="stat-label">Trades</div></div>
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {output.trades?.map(t => <span key={t} className="badge badge-sample">{t}</span>)}
                  </div>
                </div>
              ) : (
                <p style={{ color: 'var(--text-light)', marginTop: 16 }}>No output yet.</p>
              )}
            </div>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: 48, color: 'var(--text-light)' }}>
              <p>Select a project to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Projects;
