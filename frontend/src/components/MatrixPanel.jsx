import React, { useCallback, useMemo } from 'react';
import {
  Zap,
  Layers,
  Wand2,
  Wind,
  Music,
  Clock,
  ChevronDown,
} from 'lucide-react';
import { useStore } from '../stores/useStore';
import { C } from '../styles/tokens';

const VARIABLES = [
  {
    key: 'clips',
    label: 'Clip Selection',
    icon: Layers,
    description: 'Which clips appear in each variation',
  },
  {
    key: 'effects',
    label: 'Effects',
    icon: Wand2,
    description: 'Visual effects applied to clips',
  },
  {
    key: 'transitions',
    label: 'Transitions',
    icon: Wind,
    description: 'Transitions between clips',
  },
  {
    key: 'music',
    label: 'Music Track',
    icon: Music,
    description: 'Background music selection and volume',
  },
  {
    key: 'duration',
    label: 'Duration Target',
    icon: Clock,
    description: 'Total video length',
  },
];

const MODES = ['fixed', 'each', 'random', 'sequential'];

export default function MatrixPanel() {
  const { boxes, matrix, updateMatrix, outputCount } = useStore();

  const calculateFormula = useMemo(() => {
    if (Object.keys(matrix).length === 0) return null;

    const formula = [];
    for (const [varKey, config] of Object.entries(matrix)) {
      const variable = VARIABLES.find((v) => v.key === varKey);
      if (!variable) continue;

      let varCount = 0;
      const modes = [];

      for (const [boxId, setting] of Object.entries(config)) {
        if (setting.mode === 'each') {
          const boxName = boxes.find((b) => b.id === boxId)?.name || 'Unknown';
          const clipsCount = boxes.find((b) => b.id === boxId)?.clips?.length || 1;
          varCount = Math.max(varCount, clipsCount);
          modes.push(`${boxName} (${clipsCount}, iterate)`);
        } else if (setting.mode === 'random' || setting.mode === 'sequential') {
          const count = setting.params?.count || 1;
          varCount = Math.max(varCount, count);
          modes.push(`${setting.mode} ${count}`);
        }
      }

      if (varCount > 0) {
        formula.push({
          variable: variable.label,
          count: varCount,
          modes: modes.join(' × '),
        });
      }
    }

    return formula;
  }, [matrix, boxes]);

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
        <h2
          style={{
            fontSize: '18px',
            fontWeight: 600,
            color: C.text,
            marginBottom: '4px',
          }}
        >
          Variation Matrix
        </h2>
        <p
          style={{
            fontSize: '13px',
            color: C.textMuted,
          }}
        >
          Define how each parameter varies across outputs. {outputCount} total
          videos.
        </p>
      </div>

      {/* Matrix Grid */}
      <div
        style={{
          flex: 1,
          padding: '32px',
          overflow: 'auto',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: `200px repeat(${boxes.length}, 1fr)`,
            gap: '12px',
            marginBottom: '32px',
          }}
        >
          {/* Header Row */}
          <div
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: C.textMuted,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              padding: '12px',
              borderRadius: '8px',
              backgroundColor: C.bgSurface,
            }}
          >
            Variable
          </div>

          {boxes.map((box) => (
            <div
              key={box.id}
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: C.text,
                padding: '12px',
                borderRadius: '8px',
                backgroundColor: (box.color || C.accent) + '20',
                border: `1px solid ${(box.color || C.accent) + '40'}`,
                textAlign: 'center',
              }}
            >
              {box.name}
            </div>
          ))}

          {/* Variable Rows */}
          {VARIABLES.map((variable) => (
            <React.Fragment key={variable.key}>
              {/* Variable Name Cell */}
              <MatrixVariableCell variable={variable} />

              {/* Config Cells */}
              {boxes.map((box) => (
                <MatrixConfigCell
                  key={`${variable.key}-${box.id}`}
                  variable={variable}
                  box={box}
                  config={matrix[variable.key]?.[box.id]}
                  onUpdate={(mode, params) =>
                    updateMatrix(variable.key, box.id, mode, params)
                  }
                />
              ))}
            </React.Fragment>
          ))}
        </div>

        {/* Output Formula */}
        {calculateFormula && calculateFormula.length > 0 && (
          <div
            style={{
              padding: '16px',
              borderRadius: '10px',
              backgroundColor: C.green + '15',
              border: `1px solid ${C.green}40`,
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
            }}
          >
            <Zap
              size={18}
              color={C.green}
              style={{ flexShrink: 0, marginTop: '2px' }}
            />
            <div>
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: C.green,
                  marginBottom: '6px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                }}
              >
                Output Calculation
              </div>
              <div
                style={{
                  fontSize: '13px',
                  color: C.text,
                  lineHeight: '1.6',
                  fontFamily: '"Monaco", "Courier New", monospace',
                }}
              >
                {calculateFormula
                  .map((f) => `${f.variable} (${f.modes})`)
                  .join(' × ')}
                <br />= <strong>{outputCount} videos</strong>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MatrixVariableCell({ variable }) {
  const Icon = variable.icon;

  return (
    <div
      style={{
        padding: '12px',
        borderRadius: '8px',
        backgroundColor: C.bgSurface,
        border: `1px solid ${C.border}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '4px',
        }}
      >
        <Icon size={14} color={C.accent} />
        <span
          style={{
            fontSize: '12px',
            fontWeight: 600,
            color: C.text,
          }}
        >
          {variable.label}
        </span>
      </div>
      <p
        style={{
          fontSize: '10px',
          color: C.textDim,
          lineHeight: '1.3',
        }}
      >
        {variable.description}
      </p>
    </div>
  );
}

function MatrixConfigCell({ variable, box, config, onUpdate }) {
  const currentMode = config?.mode || 'fixed';
  const currentParams = config?.params || {};

  const handleModeChange = (newMode) => {
    let params = { ...currentParams };
    if (newMode === 'each') {
      params.count = box.clips?.length || 1;
    } else if (newMode === 'random' || newMode === 'sequential') {
      params.count = currentParams.count || 3;
    }
    onUpdate(newMode, params);
  };

  const handleCountChange = (newCount) => {
    onUpdate(currentMode, { ...currentParams, count: newCount });
  };

  const renderContent = () => {
    if (currentMode === 'each') {
      const clipsCount = box.clips?.length || 1;
      return (
        <div
          style={{
            fontSize: '12px',
            color: box.color || C.accent,
            fontWeight: 500,
          }}
        >
          ×{clipsCount}
        </div>
      );
    } else if (currentMode === 'random' || currentMode === 'sequential') {
      return (
        <input
          type="number"
          min={1}
          max={100}
          value={currentParams.count || 3}
          onChange={(e) =>
            handleCountChange(parseInt(e.target.value) || 1)
          }
          style={{
            width: '100%',
            padding: '4px',
            textAlign: 'center',
            fontSize: '12px',
            backgroundColor: C.bgSurface,
            border: `1px solid ${C.border}`,
            borderRadius: '4px',
            color: C.text,
          }}
        />
      );
    }
    return null;
  };

  return (
    <div
      style={{
        padding: '8px',
        borderRadius: '8px',
        backgroundColor: C.bgSurface,
        border: `1px solid ${C.border}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <select
        value={currentMode}
        onChange={(e) => handleModeChange(e.target.value)}
        style={{
          padding: '6px 8px',
          fontSize: '11px',
          backgroundColor: C.bgHover,
          border: `1px solid ${C.border}`,
          borderRadius: '4px',
          color: C.text,
          cursor: 'pointer',
          appearance: 'none',
          backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='${encodeURIComponent(C.textMuted)}' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
          backgroundRepeat: 'no-repeat',
          backgroundPosition: 'right 4px center',
          paddingRight: '20px',
        }}
      >
        {MODES.map((mode) => (
          <option key={mode} value={mode}>
            {mode.charAt(0).toUpperCase() + mode.slice(1)}
          </option>
        ))}
      </select>

      {renderContent()}
    </div>
  );
}
