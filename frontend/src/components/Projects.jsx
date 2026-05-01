import { useEffect, useState } from 'react';
import { listProjects, getProjectOutput, deleteProject, restoreProject, listHiddenProjects, projectFromFolder, listDirectory } from '../api';

function Projects() {
  const [projects, setProjects] = useState([]);
  const [hidden, setHidden] = useState([]);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(null);
  const [output, setOutput] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleteMsg, setDeleteMsg] = useState('');
  const [deleteError, setDeleteError] = useState('');
  const [customPath, setCustomPath] = useState('');
  const [addingFolder, setAddingFolder] = useState(false);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [browsePath, setBrowsePath] = useState('/app/client_files');
  const [browseItems, setBrowseItems] = useState([]);
  const [browsing, setBrowsing] = useState(false);
  const [browseError, setBrowseError] = useState('');

  const refreshAll = () => {
    listProjects().then(data => {
      setProjects(data);
      if (selected) {
        const stillThere = data.find(p => p.id === selected.id);
        if (!stillThere) {
          setSelected(null);
          setOutput(null);
        }
      }
    });
    listHiddenProjects().then(setHidden);
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleSelect = (project) => {
    setSelected(project);
    if (project.has_output) {
      getProjectOutput(project.id).then(setOutput);
    } else {
      setOutput(null);
    }
  };

  const handleDelete = async (projectId) => {
    setDeleteMsg('');
    setDeleteError('');
    try {
      const res = await deleteProject(projectId);
      if (res.success) {
        setDeleteMsg(`Project ${projectId} removed from list`);
        refreshAll();
        if (selected?.id === projectId) {
          setSelected(null);
          setOutput(null);
        }
      } else {
        setDeleteError(res.errors?.join(', ') || 'Failed to remove');
      }
    } catch (e) {
      setDeleteError(e.message || 'Failed to remove');
    }
    setConfirmDelete(null);
  };

  const handleRestore = async (projectId) => {
    setDeleteMsg('');
    setDeleteError('');
    try {
      const res = await restoreProject(projectId);
      if (res.success) {
        setDeleteMsg(res.message);
        refreshAll();
      } else {
        setDeleteError(res.message || 'Failed to restore');
      }
    } catch (e) {
      setDeleteError(e.message || 'Failed to restore');
    }
  };

  const handleAddCustomFolder = async () => {
    if (!customPath.trim()) return;
    setAddingFolder(true);
    setDeleteMsg('');
    setDeleteError('');
    try {
      const res = await projectFromFolder(customPath.trim());
      if (res.id) {
        setDeleteMsg(`Added project: ${res.id}`);
        setCustomPath('');
        refreshAll();
      } else {
        setDeleteError('Folder not found or invalid');
      }
    } catch (e) {
      setDeleteError(e.message || 'Failed to add folder');
    }
    setAddingFolder(false);
  };

  const handleOpenBrowse = async () => {
    setBrowseOpen(true);
    setBrowseError('');
    await loadBrowsePath('/app/client_files');
  };

  const loadBrowsePath = async (path) => {
    setBrowsing(true);
    setBrowseError('');
    try {
      const data = await listDirectory(path);
      if (data.error) {
        setBrowseError(data.error);
      } else {
        setBrowsePath(data.path);
        setBrowseItems(data.items || []);
      }
    } catch (e) {
      setBrowseError(e.message || 'Failed to load directory');
    }
    setBrowsing(false);
  };

  const handleAddBrowseFolder = async () => {
    if (!browsePath) return;
    setDeleteMsg('');
    setDeleteError('');
    try {
      const res = await projectFromFolder(browsePath);
      if (res.id) {
        setDeleteMsg(`Added project: ${res.id}`);
        setBrowseOpen(false);
        refreshAll();
      } else {
        setDeleteError('Folder not found or invalid');
      }
    } catch (e) {
      setDeleteError(e.message || 'Failed to add project');
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

      {deleteMsg && (
        <div className="badge badge-success" style={{ marginBottom: 12, display: 'inline-flex', padding: '8px 12px' }}>
          {deleteMsg}
        </div>
      )}
      {deleteError && (
        <div className="badge badge-danger" style={{ marginBottom: 12, display: 'inline-flex', padding: '8px 12px' }}>
          {deleteError}
        </div>
      )}

      {/* Add Custom Folder */}
      <div className="card" style={{ marginBottom: 24, background: '#f8fafc' }}>
        <div className="card-title">📁 Add Custom Project Folder</div>
        <div style={{ color: 'var(--text-light)', marginBottom: 12, fontSize: 13 }}>
          Browse available folders or enter a path manually. The folder will be scanned and added as a project.
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            className="form-input"
            placeholder="e.g. /app/client_files/my-project or /data/projects/site-a"
            value={customPath}
            onChange={e => setCustomPath(e.target.value)}
            style={{ flex: 1, minWidth: 300 }}
            onKeyDown={e => e.key === 'Enter' && handleAddCustomFolder()}
          />
          <button
            className="btn btn-primary"
            onClick={handleAddCustomFolder}
            disabled={addingFolder || !customPath.trim()}
          >
            {addingFolder ? 'Scanning...' : 'Add Folder'}
          </button>
          <button
            className="btn btn-secondary"
            onClick={handleOpenBrowse}
            disabled={browsing}
          >
            {browsing ? 'Loading...' : '🔍 Browse'}
          </button>
        </div>
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
            {['all', 'sample', 'challenge', 'custom'].map(f => (
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
              <thead><tr><th>ID</th><th>Type</th><th>Files</th><th>Status</th><th style={{ width: 40 }}></th></tr></thead>
              <tbody>
                {filtered.map(p => (
                  <tr key={p.id} onClick={() => handleSelect(p)} style={{ cursor: 'pointer', background: selected?.id === p.id ? '#eff6ff' : undefined }}>
                    <td><strong>{p.id}</strong><div style={{ fontSize: 12, color: 'var(--text-light)' }}>{p.name}</div></td>
                    <td><span className={`badge badge-${p.type}`}>{p.type}</span></td>
                    <td>{p.files_count}</td>
                    <td>{p.has_output ? <span className="badge badge-success">Done</span> : <span className="badge badge-secondary">No Output</span>}</td>
                    <td>
                      <button
                        className="btn btn-sm btn-danger"
                        style={{ padding: '4px 8px' }}
                        onClick={e => {
                          e.stopPropagation();
                          setConfirmDelete(p);
                        }}
                        title="Remove from list"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          {selected ? (
            <div className="card">
              <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>{selected.id}</span>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={() => setConfirmDelete(selected)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 4 }}><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
                  Remove
                </button>
              </div>
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

      {/* Hidden Projects Section */}
      {hidden.length > 0 && (
        <div className="card" style={{ marginTop: 24, opacity: 0.8 }}>
          <div className="card-title" style={{ color: 'var(--text-light)' }}>
            Hidden Projects ({hidden.length})
          </div>
          <p style={{ color: 'var(--text-light)', fontSize: 13, marginBottom: 12 }}>
            These projects are hidden from the main list. Their source files are preserved.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {hidden.map(id => (
              <span key={id} className="badge badge-secondary" style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                {id}
                <button
                  className="btn btn-sm btn-primary"
                  style={{ padding: '2px 6px', fontSize: 11 }}
                  onClick={() => handleRestore(id)}
                >
                  Restore
                </button>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Browse Modal - Full Filesystem Browser */}
      {browseOpen && (
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
              <span>📂 Browse Filesystem</span>
              <button className="btn btn-sm btn-secondary" onClick={() => setBrowseOpen(false)}>Close</button>
            </div>

            {/* Current path bar */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => loadBrowsePath('/app')}
                title="Go to /app"
              >
                /app
              </button>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => loadBrowsePath('/app/client_files')}
                title="Go to client_files"
              >
                client_files
              </button>
              <button
                className="btn btn-sm btn-secondary"
                onClick={() => loadBrowsePath('/app/data')}
                title="Go to data"
              >
                data
              </button>
              {browsePath !== '/' && (
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={() => {
                    const parent = browsePath.substring(0, browsePath.lastIndexOf('/')) || '/';
                    loadBrowsePath(parent);
                  }}
                  title="Go up"
                >
                  ⬆ Up
                </button>
              )}
            </div>

            <div className="form-input" style={{ fontSize: 12, marginBottom: 12, background: 'var(--bg)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {browsePath}
            </div>

            {browseError && (
              <div className="badge badge-danger" style={{ marginBottom: 12, display: 'inline-flex' }}>
                {browseError}
              </div>
            )}

            {/* Select current folder button */}
            <div style={{ marginBottom: 12 }}>
              <button
                className="btn btn-primary"
                onClick={handleAddBrowseFolder}
                disabled={browsing}
              >
                ✅ Select Current Folder: {browsePath.split('/').pop() || '/'}
              </button>
            </div>

            <div style={{ overflowY: 'auto', flex: 1, border: '1px solid var(--border)', borderRadius: 8 }}>
              {browsing ? (
                <p style={{ color: 'var(--text-light)', textAlign: 'center', padding: 32 }}>Loading...</p>
              ) : browseItems.length === 0 ? (
                <p style={{ color: 'var(--text-light)', textAlign: 'center', padding: 32 }}>Empty directory</p>
              ) : (
                <div>
                  {browseItems.map(item => (
                    <div
                      key={item.path}
                      onClick={() => {
                        if (item.type === 'dir') {
                          loadBrowsePath(item.path);
                        }
                      }}
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
                        {item.type === 'dir' ? '📁' : item.extension === '.pdf' ? '📄' : '📎'}
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

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
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
              Remove Project {confirmDelete.id}
            </div>
            <p style={{ marginBottom: 20 }}>
              This will hide <strong>{confirmDelete.id}</strong> from the list, delete its outputs, and remove related job history. The original PDF files will be preserved.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
              <button
                className="btn btn-secondary"
                onClick={() => setConfirmDelete(null)}
              >
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleDelete(confirmDelete.id)}
              >
                Yes, Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Projects;
