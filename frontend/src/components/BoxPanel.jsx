import React, { useCallback, useState, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Plus,
  Upload,
  ChevronDown,
  ChevronRight,
  Trash2,
  Film,
  Pencil,
} from 'lucide-react';
import { useStore } from '../stores/useStore';
import { C, BOX_COLORS } from '../styles/tokens';

export default function BoxPanel() {
  const {
    boxes,
    addBox,
    renameBox,
    uploadClipsToBox,
    removeClip,
    selectedBox,
    setSelectedBox,
  } = useStore();

  const [expandedBoxes, setExpandedBoxes] = useState({});
  const [uploadProgress, setUploadProgress] = useState({});

  const totalClips = useMemo(
    () => boxes.reduce((sum, box) => sum + (box.clips?.length || 0), 0),
    [boxes]
  );

  const handleAddBox = useCallback(async () => {
    const name = `Box ${boxes.length + 1}`;
    await addBox(name);
  }, [addBox, boxes.length]);

  const toggleExpanded = useCallback((boxId) => {
    setExpandedBoxes((prev) => ({
      ...prev,
      [boxId]: !prev[boxId],
    }));
  }, []);

  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px',
          borderBottom: `1px solid ${C.border}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <div
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: C.text,
            }}
          >
            Boxes
          </div>
          <div
            style={{
              fontSize: '11px',
              color: C.textMuted,
              marginTop: '4px',
            }}
          >
            {totalClips} clips total
          </div>
        </div>
        <button
          onClick={handleAddBox}
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
            transition: 'all 200ms ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = C.bgActive;
            e.target.style.borderColor = C.accent;
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = C.bgHover;
            e.target.style.borderColor = C.border;
          }}
        >
          <Plus size={16} />
        </button>
      </div>

      {/* Boxes List */}
      <div
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '8px',
        }}
      >
        {boxes.length === 0 ? (
          <div
            style={{
              padding: '24px 16px',
              textAlign: 'center',
              color: C.textDim,
              fontSize: '13px',
            }}
          >
            No boxes yet. Click + to create one.
          </div>
        ) : (
          boxes.map((box) => (
            <BoxCard
              key={box.id}
              box={box}
              isSelected={selectedBox === box.id}
              onSelect={() => setSelectedBox(box.id)}
              isExpanded={expandedBoxes[box.id]}
              onToggleExpanded={() => toggleExpanded(box.id)}
              onUpload={(files) =>
                uploadClipsToBox(box.id, files, (progress) => {
                  setUploadProgress((prev) => ({
                    ...prev,
                    [box.id]: progress,
                  }));
                })
              }
              uploadProgress={uploadProgress[box.id]}
              onRemoveClip={(clipId) => removeClip(box.id, clipId)}
              onRename={(newName) => renameBox(box.id, newName)}
              formatDuration={formatDuration}
            />
          ))
        )}
      </div>

      {/* Add Box Button */}
      <div style={{ padding: '8px' }}>
        <button
          onClick={handleAddBox}
          style={{
            width: '100%',
            padding: '12px',
            borderRadius: '8px',
            border: `2px dashed ${C.border}`,
            backgroundColor: 'transparent',
            color: C.textMuted,
            fontSize: '13px',
            fontWeight: 500,
            transition: 'all 200ms ease',
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.target.style.borderColor = C.accent;
            e.target.style.color = C.accent;
          }}
          onMouseLeave={(e) => {
            e.target.style.borderColor = C.border;
            e.target.style.color = C.textMuted;
          }}
        >
          <Plus size={16} style={{ display: 'inline', marginRight: '4px' }} />
          Add Box
        </button>
      </div>
    </div>
  );
}

function BoxCard({
  box,
  isSelected,
  onSelect,
  isExpanded,
  onToggleExpanded,
  onUpload,
  uploadProgress,
  onRemoveClip,
  onRename,
  formatDuration,
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(box.name);
  const inputRef = React.useRef(null);

  const startEditing = (e) => {
    e.stopPropagation();
    setEditName(box.name);
    setIsEditing(true);
    setTimeout(() => inputRef.current?.select(), 0);
  };

  const commitRename = () => {
    const trimmed = editName.trim();
    if (trimmed && trimmed !== box.name) {
      onRename(trimmed);
    }
    setIsEditing(false);
  };

  const cancelEditing = () => {
    setEditName(box.name);
    setIsEditing(false);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (files) => onUpload(files),
  });

  const totalDuration = useMemo(() => {
    return (box.clips || []).reduce((sum, clip) => sum + (clip.duration || 0), 0);
  }, [box.clips]);

  const boxColor = box.color || C.accent;

  return (
    <div
      style={{
        marginBottom: '8px',
        borderRadius: '8px',
        border: `1px solid ${
          isSelected ? C.accent + '60' : C.border
        }`,
        backgroundColor: isSelected ? C.bgActive + '40' : C.bgSurface,
        overflow: 'hidden',
        transition: 'all 200ms ease',
      }}
    >
      {/* Box Header */}
      <div
        onClick={onSelect}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 12px',
          cursor: 'pointer',
          backgroundColor: isSelected ? C.bgActive : 'transparent',
          transition: 'background-color 200ms ease',
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = C.bgHover;
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'transparent';
          }
        }}
      >
        {/* Expand Toggle */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleExpanded();
          }}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            borderRadius: '4px',
            backgroundColor: 'transparent',
            color: C.textMuted,
            transition: 'color 200ms ease',
          }}
          onMouseEnter={(e) => {
            e.target.style.color = C.text;
          }}
          onMouseLeave={(e) => {
            e.target.style.color = C.textMuted;
          }}
        >
          {isExpanded ? (
            <ChevronDown size={16} />
          ) : (
            <ChevronRight size={16} />
          )}
        </button>

        {/* Color Dot */}
        <div
          style={{
            width: '12px',
            height: '12px',
            borderRadius: '3px',
            backgroundColor: boxColor,
          }}
        />

        {/* Box Name */}
        {isEditing ? (
          <input
            ref={inputRef}
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename();
              if (e.key === 'Escape') cancelEditing();
            }}
            onClick={(e) => e.stopPropagation()}
            style={{
              flex: 1,
              fontSize: '13px',
              fontWeight: 500,
              color: C.text,
              backgroundColor: C.bgHover,
              border: `1px solid ${C.accent}`,
              borderRadius: '4px',
              padding: '2px 6px',
              outline: 'none',
            }}
            autoFocus
          />
        ) : (
          <span
            onDoubleClick={startEditing}
            style={{
              flex: 1,
              fontSize: '13px',
              fontWeight: 500,
              color: C.text,
              cursor: 'text',
            }}
            title="Double-click to rename"
          >
            {box.name}
          </span>
        )}

        {/* Clip Count Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            borderRadius: '4px',
            backgroundColor: boxColor + '25',
            color: boxColor,
            fontSize: '11px',
            fontWeight: 600,
          }}
        >
          {box.clips?.length || 0}
        </div>

        {/* Duration */}
        <div
          style={{
            fontSize: '11px',
            color: C.textMuted,
          }}
        >
          {formatDuration(totalDuration)}
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div style={{ borderTop: `1px solid ${C.border}` }}>
          {/* Clips Grid or Dropzone */}
          {box.clips && box.clips.length > 0 ? (
            <div
              style={{
                padding: '8px',
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '6px',
              }}
            >
              {box.clips.map((clip) => (
                <ClipThumbnail
                  key={clip.id}
                  clip={clip}
                  onRemove={() => onRemoveClip(clip.id)}
                  formatDuration={formatDuration}
                />
              ))}
            </div>
          ) : null}

          {/* Upload Dropzone */}
          <div {...getRootProps()}>
            <input {...getInputProps()} />
            <div
              style={{
                padding: '12px',
                margin: '0 8px 8px',
                borderRadius: '6px',
                border: `2px dashed ${
                  isDragActive ? C.accent : C.border
                }`,
                backgroundColor: isDragActive
                  ? C.accent + '10'
                  : 'transparent',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 200ms ease',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  color: isDragActive ? C.accent : C.textMuted,
                  transition: 'color 200ms ease',
                }}
              >
                <Upload size={14} />
                <span>
                  {isDragActive ? 'Drop clips here' : 'Drag clips here'}
                </span>
              </div>
            </div>
          </div>

          {/* Upload Progress */}
          {uploadProgress !== undefined && uploadProgress < 100 && (
            <div style={{ padding: '0 8px 8px' }}>
              <div
                style={{
                  height: '4px',
                  borderRadius: '2px',
                  backgroundColor: C.bgHover,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    height: '100%',
                    backgroundColor: C.accent,
                    width: `${uploadProgress}%`,
                    transition: 'width 100ms ease',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ClipThumbnail({ clip, onRemove, formatDuration }) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div
      style={{
        position: 'relative',
        borderRadius: '6px',
        overflow: 'hidden',
        backgroundColor: C.bgHover,
        border: `1px solid ${C.border}`,
        aspectRatio: '16 / 9',
        cursor: 'grab',
      }}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      {/* Placeholder or Thumbnail */}
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: C.bgActive,
        }}
      >
        <Film size={24} color={C.textMuted} />
      </div>

      {/* Duration Overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: '4px',
          right: '4px',
          fontSize: '10px',
          fontWeight: 600,
          backgroundColor: C.bg + 'DD',
          color: C.text,
          padding: '2px 6px',
          borderRadius: '3px',
        }}
      >
        {formatDuration(clip.duration)}
      </div>

      {/* Delete Button */}
      {showDelete && (
        <button
          onClick={() => onRemove()}
          style={{
            position: 'absolute',
            top: '4px',
            right: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            borderRadius: '4px',
            backgroundColor: C.red,
            color: C.bg,
            transition: 'opacity 200ms ease',
          }}
        >
          <Trash2 size={12} />
        </button>
      )}
    </div>
  );
}
