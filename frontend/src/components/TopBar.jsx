import React, { useCallback } from 'react';
import {
  Scissors,
  MessageSquare,
  Table2,
  LayoutGrid,
  RotateCcw,
  Settings,
  Zap,
} from 'lucide-react';
import { useStore } from '../stores/useStore';
import { C } from '../styles/tokens';

export default function TopBar() {
  const {
    activeView,
    setActiveView,
    outputCount,
    startRender,
    isRendering,
  } = useStore();

  const handleRender = useCallback(() => {
    startRender();
  }, [startRender]);

  const views = [
    { id: 'prompt', label: 'Prompt', icon: MessageSquare },
    { id: 'matrix', label: 'Matrix', icon: Table2 },
    { id: 'outputs', label: 'Outputs', icon: LayoutGrid },
  ];

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 24px',
        borderBottom: `1px solid ${C.border}`,
        backgroundColor: C.bgElevated,
        height: '72px',
      }}
    >
      {/* Logo and Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            background: `linear-gradient(135deg, ${C.accent} 0%, ${C.pink} 100%)`,
            borderRadius: '8px',
          }}
        >
          <Scissors size={24} color={C.bg} />
        </div>
        <div>
          <div
            style={{
              fontSize: '18px',
              fontWeight: 600,
              letterSpacing: '-0.5px',
            }}
          >
            MassEdit
          </div>
          <div style={{ fontSize: '11px', color: C.textMuted }}>
            Prompt-Driven Video Assembly
          </div>
        </div>
      </div>

      {/* View Switcher */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          backgroundColor: C.bgSurface,
          padding: '6px',
          borderRadius: '10px',
          border: `1px solid ${C.border}`,
        }}
      >
        {views.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveView(id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 12px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
              transition: 'all 200ms ease',
              backgroundColor:
                activeView === id ? C.bgActive : 'transparent',
              color: activeView === id ? C.accent : C.textMuted,
              border: `1px solid ${
                activeView === id ? C.accent + '40' : 'transparent'
              }`,
            }}
            onMouseEnter={(e) => {
              if (activeView !== id) {
                e.target.style.backgroundColor = C.bgHover;
              }
            }}
            onMouseLeave={(e) => {
              if (activeView !== id) {
                e.target.style.backgroundColor = 'transparent';
              }
            }}
          >
            <Icon size={16} />
            <span>{label}</span>
            {id === 'outputs' && (
              <span
                style={{
                  marginLeft: '4px',
                  fontSize: '11px',
                  color: C.textMuted,
                }}
              >
                {outputCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Right Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button
          title="Undo"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            backgroundColor: C.bgSurface,
            border: `1px solid ${C.border}`,
            color: C.textMuted,
            transition: 'all 200ms ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = C.bgHover;
            e.target.style.color = C.text;
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = C.bgSurface;
            e.target.style.color = C.textMuted;
          }}
        >
          <RotateCcw size={18} />
        </button>

        <button
          title="Settings"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '40px',
            height: '40px',
            borderRadius: '8px',
            backgroundColor: C.bgSurface,
            border: `1px solid ${C.border}`,
            color: C.textMuted,
            transition: 'all 200ms ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = C.bgHover;
            e.target.style.color = C.text;
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = C.bgSurface;
            e.target.style.color = C.textMuted;
          }}
        >
          <Settings size={18} />
        </button>

        <button
          onClick={handleRender}
          disabled={isRendering}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '10px 20px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: 600,
            background: isRendering
              ? C.greenMuted
              : `linear-gradient(135deg, ${C.green} 0%, #22c55e 100%)`,
            color: isRendering ? C.textMuted : C.bg,
            border: 'none',
            transition: 'all 200ms ease',
            cursor: isRendering ? 'not-allowed' : 'pointer',
            opacity: isRendering ? 0.7 : 1,
          }}
          onMouseEnter={(e) => {
            if (!isRendering) {
              e.target.style.transform = 'translateY(-2px)';
              e.target.style.boxShadow = `0 8px 16px ${C.green}40`;
            }
          }}
          onMouseLeave={(e) => {
            e.target.style.transform = 'translateY(0)';
            e.target.style.boxShadow = 'none';
          }}
        >
          <Zap size={16} />
          <span>
            Render {outputCount > 0 ? `(${outputCount})` : ''}
          </span>
        </button>
      </div>
    </div>
  );
}
