import { useEffect, useState } from 'react';
import { getConfig, updateConfig, resetConfig } from '../api';

function Settings() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeTab, setActiveTab] = useState('llm');

  useEffect(() => {
    getConfig().then(data => {
      setConfig(data);
      setLoading(false);
    });
  }, []);

  const setValue = (section, key, value) => {
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

  if (loading || !config) return (
    <div className="card" style={{ textAlign: 'center', padding: 48 }}>
      <p>Loading settings...</p>
    </div>
  );

  const tabs = [
    { id: 'llm', label: 'LLM & AI', icon: '🤖' },
    { id: 'ocr', label: 'OCR Engine', icon: '🔍' },
    { id: 'pipeline', label: 'Pipeline', icon: '⚙️' },
    { id: 'evaluation', label: 'Evaluation', icon: '📊' },
    { id: 'output', label: 'Output', icon: '📝' },
  ];

  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure system behavior and engine preferences</p>
      </div>

      {saved && (
        <div className="card" style={{ marginBottom: 16, background: '#f0fdf4', borderColor: 'var(--success)' }}>
          <p style={{ color: 'var(--success)', margin: 0 }}>✓ Settings saved successfully</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`btn ${activeTab === tab.id ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span style={{ marginRight: 6 }}>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        {/* LLM Tab */}
        {activeTab === 'llm' && (
          <div>
            <div className="card-title">🤖 LLM & AI Configuration</div>
            <div style={{ color: 'var(--text-light)', marginBottom: 20, fontSize: 14 }}>
              Choose the AI model and parameters used for extraction.
            </div>
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Provider</label>
                <select
                  className="form-input"
                  value={config.llm?.provider || 'openai'}
                  onChange={e => setValue('llm', 'provider', e.target.value)}
                >
                  <option value="openai">OpenAI</option>
                  <option value="kimi">Kimi (Moonshot)</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Model</label>
                <input
                  type="text"
                  className="form-input"
                  value={config.llm?.model || 'gpt-4o'}
                  onChange={e => setValue('llm', 'model', e.target.value)}
                  placeholder="e.g. gpt-4o, kimi-k2.5"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Temperature ({config.llm?.temperature ?? 0.1})</label>
                <input
                  type="range"
                  className="form-input"
                  min="0"
                  max="1"
                  step="0.1"
                  value={config.llm?.temperature ?? 0.1}
                  onChange={e => setValue('llm', 'temperature', parseFloat(e.target.value))}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-light)' }}>
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Max Tokens</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.llm?.max_tokens || 4000}
                  onChange={e => setValue('llm', 'max_tokens', parseInt(e.target.value))}
                  min="500"
                  max="8000"
                  step="500"
                />
              </div>
            </div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 12 }}>
              <input
                type="checkbox"
                checked={config.llm?.use_llm_in_pipeline || false}
                onChange={e => setValue('llm', 'use_llm_in_pipeline', e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <span>Use LLM in pipeline (requires API key)</span>
            </label>
          </div>
        )}

        {/* OCR Tab */}
        {activeTab === 'ocr' && (
          <div>
            <div className="card-title">🔍 OCR Engine</div>
            <div style={{ color: 'var(--text-light)', marginBottom: 20, fontSize: 14 }}>
              Choose between local Tesseract OCR or online vision APIs.
            </div>

            <div className="form-group" style={{ marginBottom: 20 }}>
              <label className="form-label">OCR Mode</label>
              <div style={{ display: 'flex', gap: 12 }}>
                <label
                  className="card"
                  style={{
                    flex: 1,
                    cursor: 'pointer',
                    border: config.ocr?.mode === 'local' ? '2px solid var(--primary)' : '2px solid transparent',
                    background: config.ocr?.mode === 'local' ? '#eff6ff' : undefined,
                  }}
                >
                  <input
                    type="radio"
                    name="ocr_mode"
                    value="local"
                    checked={config.ocr?.mode === 'local'}
                    onChange={e => setValue('ocr', 'mode', e.target.value)}
                    style={{ marginRight: 8 }}
                  />
                  <strong>Local Tesseract</strong>
                  <div style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 4 }}>
                    Free, private, runs on this server. No API costs.
                  </div>
                </label>
                <label
                  className="card"
                  style={{
                    flex: 1,
                    cursor: 'pointer',
                    border: config.ocr?.mode === 'online' ? '2px solid var(--primary)' : '2px solid transparent',
                    background: config.ocr?.mode === 'online' ? '#eff6ff' : undefined,
                  }}
                >
                  <input
                    type="radio"
                    name="ocr_mode"
                    value="online"
                    checked={config.ocr?.mode === 'online'}
                    onChange={e => setValue('ocr', 'mode', e.target.value)}
                    style={{ marginRight: 8 }}
                  />
                  <strong>Online Vision API</strong>
                  <div style={{ fontSize: 13, color: 'var(--text-light)', marginTop: 4 }}>
                    GPT-4o Vision. Higher accuracy, costs per image.
                  </div>
                </label>
              </div>
            </div>

            <div className="grid grid-3">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.ocr?.enabled !== false}
                  onChange={e => setValue('ocr', 'enabled', e.target.checked)}
                  style={{ width: 18, height: 18 }}
                />
                Enable OCR
              </label>
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.ocr?.preprocess !== false}
                  onChange={e => setValue('ocr', 'preprocess', e.target.checked)}
                  style={{ width: 18, height: 18 }}
                />
                Preprocess Images
              </label>
            </div>

            <div className="grid grid-3" style={{ marginTop: 16 }}>
              <div className="form-group">
                <label className="form-label">DPI</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.ocr?.dpi || 300}
                  onChange={e => setValue('ocr', 'dpi', parseInt(e.target.value))}
                  min="150"
                  max="600"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Language</label>
                <input
                  type="text"
                  className="form-input"
                  value={config.ocr?.lang || 'eng'}
                  onChange={e => setValue('ocr', 'lang', e.target.value)}
                  placeholder="eng, eng+ara, ..."
                />
              </div>
              <div className="form-group">
                <label className="form-label">Confidence Threshold</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.ocr?.confidence_threshold || 50}
                  onChange={e => setValue('ocr', 'confidence_threshold', parseInt(e.target.value))}
                  min="0"
                  max="100"
                />
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Tab */}
        {activeTab === 'pipeline' && (
          <div>
            <div className="card-title">⚙️ Pipeline Settings</div>
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Max Retries</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.pipeline?.max_retries || 3}
                  onChange={e => setValue('pipeline', 'max_retries', parseInt(e.target.value))}
                  min="0"
                  max="10"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Retry Delay (seconds)</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.pipeline?.retry_delay || 2}
                  onChange={e => setValue('pipeline', 'retry_delay', parseInt(e.target.value))}
                  min="1"
                  max="60"
                />
              </div>
            </div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 12 }}>
              <input
                type="checkbox"
                checked={config.pipeline?.cache_enabled !== false}
                onChange={e => setValue('pipeline', 'cache_enabled', e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <span>Enable LLM response caching</span>
            </label>
          </div>
        )}

        {/* Evaluation Tab */}
        {activeTab === 'evaluation' && (
          <div>
            <div className="card-title">📊 Evaluation Thresholds</div>
            <div style={{ color: 'var(--text-light)', marginBottom: 20, fontSize: 14 }}>
              Controls how predicted line items are matched against expected outputs.
            </div>
            <div className="grid grid-3">
              <div className="form-group">
                <label className="form-label">Fuzzy Match %</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.evaluation?.fuzzy_match_threshold || 80}
                  onChange={e => setValue('evaluation', 'fuzzy_match_threshold', parseFloat(e.target.value))}
                  min="0"
                  max="100"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Qty Exact %</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.evaluation?.qty_exact_threshold || 5}
                  onChange={e => setValue('evaluation', 'qty_exact_threshold', parseFloat(e.target.value))}
                  min="0"
                  max="100"
                />
              </div>
              <div className="form-group">
                <label className="form-label">Qty Close %</label>
                <input
                  type="number"
                  className="form-input"
                  value={config.evaluation?.qty_close_threshold || 10}
                  onChange={e => setValue('evaluation', 'qty_close_threshold', parseFloat(e.target.value))}
                  min="0"
                  max="100"
                />
              </div>
            </div>
          </div>
        )}

        {/* Output Tab */}
        {activeTab === 'output' && (
          <div>
            <div className="card-title">📝 Output Format</div>
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Format</label>
                <select
                  className="form-input"
                  value={config.output?.format || 'json'}
                  onChange={e => setValue('output', 'format', e.target.value)}
                >
                  <option value="json">JSON</option>
                  <option value="jsonl">JSON Lines</option>
                </select>
              </div>
            </div>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 12 }}>
              <input
                type="checkbox"
                checked={config.output?.include_confidence_summary !== false}
                onChange={e => setValue('output', 'include_confidence_summary', e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <span>Include confidence summary</span>
            </label>
            <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 8 }}>
              <input
                type="checkbox"
                checked={config.output?.include_processing_stats !== false}
                onChange={e => setValue('output', 'include_processing_stats', e.target.checked)}
                style={{ width: 18, height: 18 }}
              />
              <span>Include processing stats</span>
            </label>
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : '💾 Save Changes'}
        </button>
        <button className="btn btn-secondary" onClick={handleReset}>
          ↺ Reset Defaults
        </button>
      </div>
    </div>
  );
}

export default Settings;
