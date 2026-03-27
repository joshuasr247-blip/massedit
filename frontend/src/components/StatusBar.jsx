import React, { useMemo } from 'react';
import { Film, LayoutGrid, CheckCircle2, Clock, Zap } from 'lucide-react';
import { useStore } from '../stores/useStore';
import { C } from '../styles/tokens';

export default function StatusBar() {
  const { boxes, outputCount, renderJobs } = useStore();

  const stats = useMemo(() => {
    const totalClips = boxes.reduce((sum, box) => sum + (box.clips?.length || 0), 0);
    const renderDone = renderJobs.filter((j) => j.status === 'done').length;
    const renderInProgress = renderJobs.filter(
      (j) => j.status === 'rendering'
    ).length;

    return {
      totalClips,
      outputCount,
      renderDone,
      renderInProgress,
    };
  }, [boxes, outputCount, renderJobs]);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 24px',
        borderTop: `1px solid ${C.border}`,
        backgroundColor: C.bgElevated,
        height: '48px',
        fontSize: '12px',
        color: C.textMuted,
      }}
    >
      {/* Left Stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Film size={14} color={C.text} />
          <span>{stats.totalClips} clips loaded</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <LayoutGrid size={14} color={C.text} />
          <span>{stats.outputCount} outputs configured</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <CheckCircle2 size={14} color={C.green} />
          <span style={{ color: C.green }}>{stats.renderDone} rendered</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Clock size={14} color={C.orange} />
          <span style={{ color: C.orange }}>
            {stats.renderInProgress} in progress
          </span>
        </div>
      </div>

      {/* Right Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          color: C.textMuted,
        }}
      >
        <Zap size={12} color={C.cyan} />
        <span style={{ color: C.cyan }}>
          Hybrid mode: preview in-browser · render on server
        </span>
      </div>
    </div>
  );
}
