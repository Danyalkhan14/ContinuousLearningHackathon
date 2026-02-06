import { useState } from 'react';

const FileIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 1H3a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L8 1Z" />
    <path d="M8 1v4h4" />
  </svg>
);

const ImageIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="1" y="1" width="12" height="12" rx="1" />
    <circle cx="4.5" cy="4.5" r="1.5" />
    <path d="M1 10l3-3 3 2 4-4 2 2" />
  </svg>
);

const ChevronDown = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M3 4.5L6 7.5L9 4.5" />
  </svg>
);

const files = [
  { id: 'main', name: 'main.tex', icon: FileIcon, active: true },
  { id: 'diagram', name: 'diagram.jpg', icon: ImageIcon, active: false },
];

const outlineItems = ['What is CliniRepGen?', 'Features', 'Collaboration'];

type View = 'editor' | 'agent';

interface SidebarProps {
  activeView?: View;
  onViewChange?: (view: View) => void;
}

export default function Sidebar({ activeView = 'editor', onViewChange }: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'chats' | 'agent'>('files');
  const [outlineOpen, setOutlineOpen] = useState(true);
  const tabForDisplay = activeView === 'agent' ? 'agent' : activeTab;

  const setTab = (tab: 'files' | 'chats' | 'agent') => {
    setActiveTab(tab);
    if (tab === 'agent' && onViewChange) onViewChange('agent');
    else if (tab !== 'agent' && onViewChange) onViewChange('editor');
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <select defaultValue="new">
          <option value="new">New Proj...</option>
        </select>
        <button type="button">Duplicate</button>
      </div>
      <div className="sidebar-tabs">
        <button
          type="button"
          className={`sidebar-tab ${tabForDisplay === 'files' ? 'active' : ''}`}
          onClick={() => setTab('files')}
        >
          Files
        </button>
        <button
          type="button"
          className={`sidebar-tab ${tabForDisplay === 'chats' ? 'active' : ''}`}
          onClick={() => setTab('chats')}
        >
          Chats
        </button>
        <button
          type="button"
          className={`sidebar-tab ${tabForDisplay === 'agent' ? 'active' : ''}`}
          onClick={() => setTab('agent')}
        >
          Agent
        </button>
      </div>
      {tabForDisplay === 'files' && (
        <div className="file-list">
          {files.map((f) => (
            <div key={f.id} className={`file-item ${f.active ? 'active' : ''}`}>
              <f.icon />
              <span>{f.name}</span>
            </div>
          ))}
        </div>
      )}
      {tabForDisplay === 'chats' && (
        <div className="file-list">
          <div style={{ padding: 16, color: 'var(--text-secondary)', fontSize: 13 }}>
            No chats yet. Use the input below to ask anything about your document.
          </div>
        </div>
      )}
      {tabForDisplay === 'agent' && (
        <div className="file-list">
          <div style={{ padding: 16, color: 'var(--text-secondary)', fontSize: 13 }}>
            Upload CSV/text files in the main area and run the agent to store embeddings in Qdrant and get You.com research summaries.
          </div>
        </div>
      )}
      <div className="login-card">
        <div className="login-card-header">
          <span>⚠</span>
          <span>Don&apos;t lose access</span>
        </div>
        <p>You are not logged in. Sign In or Sign Up to save projects and preview from other devices.</p>
        <a href="#signin">Sign In or Sign Up</a>
      </div>
      <div className="outline-section">
        <div className="outline-header" onClick={() => setOutlineOpen(!outlineOpen)} role="button" tabIndex={0}>
          <span>Outline</span>
          <span style={{ transform: outlineOpen ? 'rotate(180deg)' : 'none', display: 'inline-flex' }}>
            <ChevronDown />
          </span>
        </div>
        {outlineOpen && (
          <ul className="outline-list">
            {outlineItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
