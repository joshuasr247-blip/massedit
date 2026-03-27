import React, { useCallback, useState, useMemo } from 'react';
import {
  Play,
  Download,
  Grid3x3,
  List,
  Share2,
  RefreshCw,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import { useStore } from '../stores/useStore';
import { BOX_COLORS, C } from '../styles/tokens';

export default function OutputGrid() {
  const { outputCount, boxes, renderJobs, isRendering } = useStore();
  const [viewMode, setViewMode] = useState('grid');

  const renderDone = useMemo(
    () => renderJobs.filter((j) => j.status === 'done').length,
    [renderJobs]
  );

  const renderInProgress = useMemo(
    () => renderJobs.filter((j) => j.status === 'rendering').length,
    [renderJobs]
  );

  const outputs = useMemo(() => {
    // Generate mock outputs for demo
    return Array.from({ length: outputCount }, (_, idx) => ({
      id: idx,
      name: `Output ${idx + 1}`,
      boxes: boxes.slice(0, Math.ceil((idx + 1) / (outputCount / boxes.length))),
      status: idx < renderDone ? 'done' : idx < renderDone + renderInProgress ? 'rendering' : 'queued',
      progress: idx < renderDone ? 100 : idx < renderDone + renderInProgress ? Math.random() * 70 + 30 : 0,
    }));
  }, [outputCount, boxes, renderDone, renderInProgress]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'auto',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '32px',
          borderBottom: `1px solid ${C.border}`,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '16px',
          }}
        >
          <div>
            <h2
              style={{
                fontSize: '18px',
                fontWeight: 600,
                color: C.text,
                marginBottom: '4px',
              }}
            >
              Outputs
            </h2>
            <p
              style={{
                fontSize: '13px',
                color: C.textMuted,
              }}
            >
              Generated videos from your matrix.
            </p>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            {/* Status Badge */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                borderRadius: '6px',
                backgroundColor: C.bgSurface,
                border: `1px solid ${C.border}`,
                fontSize: '12px',
                color: C.textMuted,
              }}
            >
              <CheckCircle2 size={14} color={C.green} />
              <span>{renderDone} done</span>
              <span style={{ color: C.textDim }}>·</span>
              <Clock size={14} color={C.orange} />
              <span>{renderInProgress} rendering</span>
            </div>

            {/* View Toggle */}
            <div
              style={{
                display: 'flex',
                gap: '4px',
                backgroundColor: C.bgSurface,
                padding: '4px',
                borderRadius: '6px',
                border: `1px solid ${C.border}`,
              }}
            >
              <button
                onClick={() => setViewMode('grid')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  borderRadius: '4px',
                  backgroundColor:
                    viewMode === 'grid' ? C.bgActive : 'transparent',
                  color: viewMode === 'grid' ? C.accent : C.textMuted,
                  transition: 'all 200ms ease',
                }}
                title="Grid view"
              >
                <Grid3x3 size={16} />
              </button>
              <button
                onClick={() => setViewMode('list')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '32px',
                  height: '32px',
                  borderRadius: '4px',
                  backgroundColor:
                    viewMode === 'list' ? C.bgActive : 'transparent',
                  color: viewMode === 'list' ? C.accent : C.textMuted,
                  transition: 'all 200ms ease',
                }}
                title="List view"
              >
                <List size={16} />
              </button>
            </div>

            {/* Export Button */}
            <button
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '8px 16px',
                borderRadius: '6px',
                backgroundColor: C.bgActive,
                border: `1px solid ${C.border}`,
                color: C.accent,
                fontSize: '12px',
                fontWeight: 600,
                cursor: renderDone > 0 ? 'pointer' : 'not-allowed',
                transition: 'all 200ms ease',
                opacity: renderDone > 0 ? 1 : 0.5,
              }}
              disabled={renderDone === 0}
              onMouseEnter={(e) => {
                if (renderDone > 0) {
                  e.target.style.backgroundColor = C.bgHover;
                  e.target.style.borderColor = C.accent;
                }
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = C.bgActive;
                e.target.style.borderColor = C.border;
              }}
            >
              <Share2 size={14} />
              Export All
            </button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          padding: '32px',
          overflow: 'auto',
        }}
      >
        {outputCount === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '48px 24px',
              color: C.textDim,
            }}
          >
            <Play size={48} style={{ margin: '0 auto 16px', opacity: 0.5 }} />
            <p style={{ fontSize: '13px', marginBottom: '8px' }}>
              No outputs yet.
            </p>
            <p style={{ fontSize: '12px', color: C.textMuted }}>
              Configure your matrix and click Render to generate videos.
            </p>
          </div>
        ) : viewMode === 'grid' ? (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: '16px',
            }}
          >
            {outputs.map((output) => (
              <OutputCard key={output.id} output={output} boxes={boxes} />
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {outputs.map((output) => (
              <OutputRow key={output.id} output={output} boxes={boxes} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function OutputCard({ output, boxes }) {
  const [showActions, setShowActions] = useState(false);

  const statusColor =
    output.status === 'done'
      ? C.green
      : output.status === 'rendering'
      ? C.orange
      : C.textDim;

  return (
    <div
      style={{
        borderRadius: '10px',
        border: `1px solid ${C.border}`,
        overflow: 'hidden',
        backgroundColor: C.bgSurface,
        transition: 'all 200ms ease',
        cursor: 'pointer',
      }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* Thumbnail */}
      <div
        style={{
          position: 'relative',
          aspectRatio: '16 / 9',
          background: `linear-gradient(135deg, ${output.boxes
            .map((b) => b.color || C.accent)
            .join(', ')})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}
      >
        {/* Play Button */}
        {showActions && output.status === 'done' && (
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: C.bg + 'DD',
              border: `2px solid ${C.text}`,
              color: C.text,
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.transform = 'scale(1.1)';
              e.target.style.backgroundColor = C.bg + 'EE';
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'scale(1)';
              e.target.style.backgroundColor = C.bg + 'DD';
            }}
          >
            <Play size={20} fill="currentColor" />
          </button>
        )}

        {/* Status Indicator */}
        <div
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            backgroundColor: statusColor,
            boxShadow: `0 0 8px ${statusColor}80`,
          }}
        />

        {/* Progress Bar */}
        {output.status === 'rendering' && (
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '3px',
              backgroundColor: C.bgActive,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                backgroundColor: C.orange,
                width: `${output.progress}%`,
                transition: 'width 300ms ease',
              }}
            />
          </div>
        )}
      </div>

      {/* Info */}
      <div style={{ padding: '12px' }}>
        <div
          style={{
            fontSize: '12px',
            fontWeight: 600,
            color: C.text,
            marginBottom: '8px',
          }}
        >
          {output.name}
        </div>

        {/* Box Pills */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '4px',
            marginBottom: '8px',
          }}
        >
          {output.boxes.map((box) => (
            <span
              key={box.id}
              style={{
                fontSize: '10px',
                fontWeight: 500,
                color: C.bg,
                backgroundColor: box.color || C.accent,
                padding: '2px 6px',
                borderRadius: '3px',
              }}
            >
              {box.name}
            </span>
          ))}
        </div>

        {/* Actions */}
        {showActions && output.status === 'done' && (
          <div
            style={{
              display: 'flex',
              gap: '4px',
            }}
          >
            <button
              style={{
                flex: 1,
                padding: '6px',
                borderRadius: '4px',
                backgroundColor: C.bgActive,
                border: `1px solid ${C.border}`,
                color: C.accent,
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 200ms ease',
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = C.accent;
                e.target.style.color = C.bg;
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = C.bgActive;
                e.target.style.color = C.accent;
              }}
            >
              <Play size={12} style={{ display: 'inline', marginRight: '4px' }} />
              Play
            </button>
            <button
              style={{
                flex: 1,
                padding: '6px',
                borderRadius: '4px',
                backgroundColor: C.bgActive,
                border: `1px solid ${C.border}`,
                color: C.text,
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 200ms ease',
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = C.bgHover;
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = C.bgActive;
              }}
            >
              <Download size={12} style={{ display: 'inline', marginRight: '4px' }} />
              Download
            </button>
          </div>
        )}

        {/* Rendering State */}
        {output.status === 'rendering' && (
          <div
            style={{
              fontSize: '11px',
              color: C.orange,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <RefreshCw
              size={12}
              style={{ animation: 'spin 2s linear infinite' }}
            />
            {Math.round(output.progress)}%
          </div>
        )}

        {/* Queued State */}
        {output.status === 'queued' && (
          <div
            style={{
              fontSize: '11px',
              color: C.textMuted,
            }}
          >
            Queued
          </div>
        )}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function OutputRow({ output, boxes }) {
  const statusColor =
    output.status === 'done'
      ? C.green
      : output.status === 'rendering'
      ? C.orange
      : C.textDim;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '12px',
        borderRadius: '8px',
        border: `1px solid ${C.border}`,
        backgroundColor: C.bgSurface,
        transition: 'all 200ms ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = C.bgActive;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = C.bgSurface;
      }}
    >
      {/* Status Dot */}
      <div
        style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: statusColor,
          flexShrink: 0,
        }}
      />

      {/* Name */}
      <div style={{ flex: 1 }}>
        <div
          style={{
            fontSize: '12px',
            fontWeight: 600,
            color: C.text,
            marginBottom: '4px',
          }}
        >
          {output.name}
        </div>
        <div
          style={{
            display: 'flex',
            gap: '6px',
            flexWrap: 'wrap',
          }}
        >
          {output.boxes.map((box) => (
            <span
              key={box.id}
              style={{
                fontSize: '10px',
                color: C.bg,
                backgroundColor: box.color || C.accent,
                padding: '2px 6px',
                borderRadius: '3px',
              }}
            >
              {box.name}
            </span>
          ))}
        </div>
      </div>

      {/* Progress */}
      {output.status === 'rendering' && (
        <div
          style={{
            width: '120px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <div
            style={{
              flex: 1,
              height: '4px',
              borderRadius: '2px',
              backgroundColor: C.bgHover,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                backgroundColor: C.orange,
                width: `${output.progress}%`,
                transition: 'width 300ms ease',
              }}
            />
          </div>
          <div
            style={{
              fontSize: '11px',
              color: C.orange,
              width: '30px',
              textAlign: 'right',
            }}
          >
            {Math.round(output.progress)}%
          </div>
        </div>
      )}

      {/* Actions */}
      {output.status === 'done' && (
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              backgroundColor: C.bgHover,
              border: `1px solid ${C.border}`,
              color: C.accent,
              cursor: 'pointer',
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = C.accent;
              e.target.style.color = C.bg;
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = C.bgHover;
              e.target.style.color = C.accent;
            }}
          >
            <Play size={14} fill="currentColor" />
          </button>
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              borderRadius: '6px',
              backgroundColor: C.bgHover,
              border: `1px solid ${C.border}`,
              color: C.text,
              cursor: 'pointer',
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = C.bgActive;
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = C.bgHover;
            }}
          >
            <Download size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
