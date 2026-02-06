import { useState } from 'react';
import Sidebar from './components/Sidebar';
import EditorPane, { DEFAULT_LATEX } from './components/EditorPane';
import PreviewPane from './components/PreviewPane';
import AgentPane from './components/AgentPane';
import './index.css';

type View = 'editor' | 'agent';

function App() {
  const [latex, setLatex] = useState(DEFAULT_LATEX);
  const [view, setView] = useState<View>('editor');

  return (
    <div className="app-layout">
      <Sidebar activeView={view} onViewChange={setView} />
      {view === 'editor' && (
        <>
          <EditorPane value={latex} onChange={setLatex} />
          <PreviewPane latex={latex} />
        </>
      )}
      {view === 'agent' && <AgentPane />}
    </div>
  );
}

export default App;
