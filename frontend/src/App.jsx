import React, { useEffect } from 'react';
import { useStore } from './stores/useStore';
import TopBar from './components/TopBar';
import BoxPanel from './components/BoxPanel';
import PromptPanel from './components/PromptPanel';
import MatrixPanel from './components/MatrixPanel';
import OutputGrid from './components/OutputGrid';
import StatusBar from './components/StatusBar';
import { C } from './styles/tokens';

export default function App() {
  const store = useStore();

  // Initialize app with default project
  useEffect(() => {
    if (!store.currentProject) {
      store.initProject('Default Project');
    }
  }, []);

  const renderView = () => {
    switch (store.activeView) {
      case 'matrix':
        return <MatrixPanel />;
      case 'outputs':
        return <OutputGrid />;
      case 'prompt':
      default:
        return <PromptPanel />;
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        backgroundColor: C.bg,
        color: C.text,
        fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
      }}
    >
      <style>{`
        * {
          margin: 0;
          padding: 0;
          box-sizing: border-box;
        }

        html, body, #root {
          height: 100%;
        }

        ::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: ${C.border};
          border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: ${C.borderLight};
        }

        button {
          font-family: inherit;
          cursor: pointer;
          border: none;
          background: none;
          color: inherit;
        }

        input, textarea, select {
          font-family: inherit;
          color: inherit;
          background: inherit;
          border: none;
          padding: 0;
          margin: 0;
        }

        textarea:focus, input:focus, select:focus {
          outline: none;
        }
      `}</style>

      {/* Top Bar */}
      <TopBar />

      {/* Main Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Left Sidebar - Boxes */}
        <div
          style={{
            width: '320px',
            borderRight: `1px solid ${C.border}`,
            display: 'flex',
            flexDirection: 'column',
            backgroundColor: C.bgSurface,
          }}
        >
          <BoxPanel />
        </div>

        {/* Center Panel - View Content */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {renderView()}
        </div>
      </div>

      {/* Status Bar */}
      <StatusBar />
    </div>
  );
}
