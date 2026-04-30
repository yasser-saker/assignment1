import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  PlayCircle,
  Settings,
  FileText,
  Cpu,
} from 'lucide-react';

function Sidebar() {
  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/projects', icon: FolderOpen, label: 'Projects' },
    { to: '/pipeline', icon: PlayCircle, label: 'Pipeline' },
    { to: '/results', icon: FileText, label: 'Results' },
    { to: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1>AI Takeoff Builder</h1>
        <p>Construction Takeoff Automation</p>
      </div>
      <nav className="nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <Cpu size={14} style={{ display: 'inline', marginRight: 6 }} />
        v1.0.0 — Backend Ready
      </div>
    </aside>
  );
}

export default Sidebar;
