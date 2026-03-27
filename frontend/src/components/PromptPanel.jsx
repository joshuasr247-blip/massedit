import React, { useCallback, useState } from 'react';
import {
  Send,
  Lightbulb,
  Settings,
  Loader,
  Copy,
  Check,
} from 'lucide-react';
import { useStore } from '../stores/useStore';
import { C } from '../styles/tokens';

const EXAMPLE_PROMPT = `Create 3 variations:
- Variation 1: Use only Hooks clips with fade transitions
- Variation 2: Use Content with zoom effect, 2x speed
- Variation 3: Use CTAs with bold titles and increase volume on Music track`;

export default function PromptPanel() {
  const {
    boxes,
    prompt,
    setPrompt,
    interpret,
    isInterpreting,
    editPlan,
    suggestions,
  } = useStore();

  const [copied, setCopied] = useState(null);

  const handleInterpret = useCallback(async () => {
    if (prompt.trim()) {
      await interpret();
    }
  }, [prompt, interpret]);

  const insertBoxName = useCallback((boxName) => {
    const textarea = document.getElementById('prompt-textarea');
    if (textarea) {
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newPrompt =
        prompt.substring(0, start) +
        `[${boxName}]` +
        prompt.substring(end);
      setPrompt(newPrompt);
      setTimeout(() => {
        textarea.focus();
        textarea.selectionStart = textarea.selectionEnd =
          start + boxName.length + 2;
      }, 0);
    }
  }, [prompt, setPrompt]);

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'auto',
      }}
    >
      {/* Main Content */}
      <div style={{ flex: 1, padding: '32px', maxWidth: '1200px' }}>
        {/* Prompt Section */}
        <div style={{ marginBottom: '48px' }}>
          <div
            style={{
              marginBottom: '12px',
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
              Edit Prompt
            </h2>
            <p
              style={{
                fontSize: '13px',
                color: C.textMuted,
              }}
            >
              Describe how you want your videos edited and combined.
            </p>
          </div>

          {/* Prompt Textarea */}
          <textarea
            id="prompt-textarea"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={EXAMPLE_PROMPT}
            style={{
              width: '100%',
              minHeight: '140px',
              padding: '16px',
              borderRadius: '10px',
              border: `1px solid ${C.border}`,
              backgroundColor: C.bgSurface,
              color: C.text,
              fontSize: '13px',
              lineHeight: '1.6',
              fontFamily: 'inherit',
              resize: 'vertical',
              transition: 'border-color 200ms ease',
            }}
            onFocus={(e) => {
              e.target.style.borderColor = C.accent;
            }}
            onBlur={(e) => {
              e.target.style.borderColor = C.border;
            }}
          />

          {/* Box Name Pills */}
          {boxes.length > 0 && (
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '8px',
                marginTop: '12px',
              }}
            >
              {boxes.map((box) => (
                <button
                  key={box.id}
                  onClick={() => insertBoxName(box.name)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '12px',
                    border: 'none',
                    backgroundColor: box.color || C.accent,
                    color: C.bg,
                    fontSize: '12px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 200ms ease',
                    opacity: 0.85,
                  }}
                  onMouseEnter={(e) => {
                    e.target.style.opacity = '1';
                    e.target.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.opacity = '0.85';
                    e.target.style.transform = 'translateY(0)';
                  }}
                  title={`Insert ${box.name}`}
                >
                  {box.name}
                </button>
              ))}
            </div>
          )}

          {/* Interpret Button */}
          <button
            onClick={handleInterpret}
            disabled={!prompt.trim() || isInterpreting}
            style={{
              marginTop: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              padding: '12px 24px',
              borderRadius: '8px',
              border: 'none',
              background: isInterpreting
                ? C.accentMuted
                : `linear-gradient(135deg, ${C.accent} 0%, ${C.accentHover} 100%)`,
              color: C.bg,
              fontSize: '13px',
              fontWeight: 600,
              cursor: isInterpreting ? 'not-allowed' : 'pointer',
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              if (!isInterpreting) {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = `0 8px 16px ${C.accent}40`;
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = 'none';
            }}
          >
            {isInterpreting ? (
              <>
                <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
                <span>Interpreting...</span>
              </>
            ) : (
              <>
                <Send size={16} />
                <span>Interpret</span>
              </>
            )}
          </button>
        </div>

        {/* Edit Plan */}
        {editPlan && editPlan.length > 0 && (
          <div style={{ marginBottom: '48px' }}>
            <h3
              style={{
                fontSize: '16px',
                fontWeight: 600,
                color: C.text,
                marginBottom: '16px',
              }}
            >
              Edit Plan
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {editPlan.map((step, idx) => (
                <EditPlanStep
                  key={idx}
                  step={step}
                  stepNumber={idx + 1}
                  onCopy={copyToClipboard}
                  copied={copied}
                />
              ))}
            </div>
          </div>
        )}

        {/* Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div style={{ marginBottom: '48px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '16px',
              }}
            >
              <Lightbulb
                size={18}
                color={C.orange}
                style={{ flexShrink: 0 }}
              />
              <h3
                style={{
                  fontSize: '16px',
                  fontWeight: 600,
                  color: C.orange,
                }}
              >
                AI Suggestions
              </h3>
            </div>

            <div
              style={{
                borderRadius: '10px',
                border: `1px solid ${C.orange}40`,
                backgroundColor: C.orange + '08',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              {suggestions.map((suggestion, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    backgroundColor: C.bgSurface,
                    border: `1px solid ${C.border}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '4px',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: C.accent,
                          backgroundColor: C.accent + '20',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                        }}
                      >
                        {suggestion.type || 'suggestion'}
                      </span>
                    </div>
                    <p
                      style={{
                        fontSize: '13px',
                        color: C.text,
                        lineHeight: '1.5',
                      }}
                    >
                      {suggestion.text || suggestion.description}
                    </p>
                  </div>
                  <button
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      border: `1px solid ${C.border}`,
                      backgroundColor: C.bgActive,
                      color: C.accent,
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 200ms ease',
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
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
                    Apply
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}

function EditPlanStep({ step, stepNumber, onCopy, copied }) {
  return (
    <div
      style={{
        padding: '16px',
        borderRadius: '10px',
        border: `1px solid ${C.border}`,
        backgroundColor: C.bgSurface,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}
      >
        <div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '4px',
            }}
          >
            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: C.accent,
                color: C.bg,
                fontSize: '11px',
                fontWeight: 700,
              }}
            >
              {stepNumber}
            </span>
            <span
              style={{
                fontSize: '14px',
                fontWeight: 600,
                color: C.text,
              }}
            >
              {step.label || step.name}
            </span>
          </div>
          <p
            style={{
              fontSize: '13px',
              color: C.textMuted,
              lineHeight: '1.5',
            }}
          >
            {step.description}
          </p>
        </div>
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
            color: C.textMuted,
            transition: 'all 200ms ease',
            flexShrink: 0,
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = C.bgActive;
            e.target.style.color = C.text;
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = C.bgHover;
            e.target.style.color = C.textMuted;
          }}
        >
          <Settings size={16} />
        </button>
      </div>

      {/* FFmpeg Command */}
      {step.ffmpeg_command && (
        <div
          style={{
            marginTop: '12px',
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: C.bg,
            border: `1px solid ${C.border}`,
            position: 'relative',
          }}
        >
          <code
            style={{
              fontSize: '11px',
              color: C.cyan,
              fontFamily: '"Monaco", "Courier New", monospace',
              wordBreak: 'break-all',
              display: 'block',
              lineHeight: '1.4',
            }}
          >
            {step.ffmpeg_command}
          </code>
          <button
            onClick={() =>
              onCopy(step.ffmpeg_command, `cmd-${stepNumber}`)
            }
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '24px',
              height: '24px',
              borderRadius: '4px',
              backgroundColor: C.bgHover,
              border: `1px solid ${C.border}`,
              color: C.textMuted,
              transition: 'all 200ms ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = C.bgActive;
              e.target.style.color = C.text;
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = C.bgHover;
              e.target.style.color = C.textMuted;
            }}
          >
            {copied === `cmd-${stepNumber}` ? (
              <Check size={14} />
            ) : (
              <Copy size={14} />
            )}
          </button>
        </div>
      )}
    </div>
  );
}
