import { HashRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import Projects from './components/Projects';
import PipelineRunner from './components/PipelineRunner';
import ResultsViewer from './components/ResultsViewer';
import SettingsPage from './components/Settings';
import './App.css';

function App() {
  return (
    <HashRouter>
      <div className="app">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/pipeline" element={<PipelineRunner />} />
            <Route path="/results" element={<ResultsViewer />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}

export default App;
