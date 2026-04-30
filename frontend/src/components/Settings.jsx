import { useEffect, useState } from 'react';
import { getConfig, updateConfig, resetConfig } from '../api';

function Settings() {
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getConfig().then(data => { setConfig(data); setLoading(false); });
  }, []);

  const handleChange = (section, key, value) => {
    setConfig(prev => ({ ...prev, [section]: { ...prev[section], [key]: value } }));
  };

  const handleSave = async () => {
    setSaving(true);
    for (const [section, values] of Object.entries(config)) {
      for (const [key, value] of Object.entries(values)) {
        await updateConfig(`${section}.${key}`, value);
      }
    }
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = async () => {
    if (!confirm('Reset all settings to defaults?')) return;
    const data = await resetConfig();
    setConfig(data);
  };

  const renderField = (section, key, value) => {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    if (typeof value === 'boolean') {
      return (
        <label key={key} className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={value} onChange={e => handleChange(section, key, e.target.checked)} style={{ width: 16, height: 16 }} />
          {label}
        </label>
      );
    }
    if (typeof value === 'number') {
      return (
        <div className="form-group" key={key}>
          <label className="form-label">{label}</label>
          <input type="number" className="form-input" value={value} onChange={e => handleChange(section, key, parseFloat(e.target.value))} step={key.includes('threshold') ? 1 : 0.1} />
        </div>
      );
    }
    if (key.includes('key')) {
      return (
        <div className="form-group" key={key}>
          <label className="form-label">{label}</label>
          <input type="password" className="form-input" value={value} onChange={e => handleChange(section, key, e.target.value)} />
        </div>
      );
    }
    if (key === 'provider') {
      return (
        <div className="form-group" key={key}>
          <label className="form-label">{label}</label>
          <select className="form-select" value={value} onChange={e => handleChange(section, key, e.target.value)}>
            <option value="kimi">Kimi</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </div>
      );
    }
    return (
      <div className="form-group" key={key}>
        <label className="form-label">{label}</label>
        <input type="text" className="form-input" value={value} onChange={e => handleChange(section, key, e.target.value)} />
      </div>
    );
  };

  if (loading) return <div className="card" style={{ textAlign: 'center', padding: 48 }}><p>Loading...</p></div>;

  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure the system</p>
      </div>

      {saved && (
        <div className="card" style={{ marginBottom: 16, background: '#f0fdf4', borderColor: 'var(--success)' }}>
          <p style={{ color: 'var(--success)', margin: 0 }}>Settings saved!</p>
        </div>
      )}

      {Object.entries(config).map(([section, values]) => (
        <div className="card" key={section} style={{ marginBottom: 16 }}>
          <div className="card-title" style={{ textTransform: 'capitalize' }}>{section}</div>
          {Object.entries(values).map(([key, value]) => renderField(section, key, value))}
        </div>
      ))}

      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
        <button className="btn btn-secondary" onClick={handleReset}>Reset Defaults</button>
      </div>
    </div>
  );
}

export default Settings;
