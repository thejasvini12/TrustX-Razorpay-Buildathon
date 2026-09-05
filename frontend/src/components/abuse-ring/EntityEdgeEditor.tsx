import React, { useState } from 'react';
import { EntityEdgeInput, AccountNodeInput } from '../../types/api';
import { Link2, Plus, Trash2, Smartphone, Globe, CreditCard, MapPin, Check, X } from 'lucide-react';

interface EntityEdgeEditorProps {
  edges: EntityEdgeInput[];
  accounts: AccountNodeInput[];
  onChange: (edges: EntityEdgeInput[]) => void;
  selectedEntityId?: string | null;
  onSelectEntity?: (entityId: string | null) => void;
  disabled?: boolean;
}

export const EntityEdgeEditor: React.FC<EntityEdgeEditorProps> = ({
  edges,
  accounts,
  onChange,
  selectedEntityId,
  onSelectEntity,
  disabled = false,
}) => {
  const [isAdding, setIsAdding] = useState<boolean>(false);
  const [newAccountId, setNewAccountId] = useState<string>(accounts[0]?.account_id || '');
  const [newEntityType, setNewEntityType] = useState<'DEVICE' | 'IP' | 'PAYMENT' | 'ADDRESS'>('DEVICE');
  const [newEntityId, setNewEntityId] = useState<string>('DEV_SHARED_01');

  // Count degree of each entity
  const entityDegrees = edges.reduce((acc, edge) => {
    acc[edge.entity_id] = (acc[edge.entity_id] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const handleAddEdge = () => {
    if (!newAccountId || !newEntityId.trim()) return;

    // Check duplicate
    const exists = edges.some(
      (e) => e.account_id === newAccountId && e.entity_id === newEntityId.trim() && e.entity_type === newEntityType
    );
    if (!exists) {
      onChange([
        ...edges,
        {
          account_id: newAccountId,
          entity_type: newEntityType,
          entity_id: newEntityId.trim(),
        },
      ]);
    }
    setIsAdding(false);
  };

  const handleRemoveEdge = (index: number) => {
    const updated = edges.filter((_, idx) => idx !== index);
    onChange(updated);
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'DEVICE':
        return <Smartphone size={13} color="var(--accent-cyan)" />;
      case 'IP':
        return <Globe size={13} color="var(--accent-purple)" />;
      case 'PAYMENT':
        return <CreditCard size={13} color="var(--risk-medium)" />;
      case 'ADDRESS':
        return <MapPin size={13} color="var(--risk-high)" />;
      default:
        return <Link2 size={13} color="var(--text-muted)" />;
    }
  };

  return (
    <div
      style={{
        padding: '16px',
        backgroundColor: 'var(--bg-app)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '14px',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Link2 size={16} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Entity Link Edges ({edges.length})
          </h3>
        </div>

        <button
          type="button"
          disabled={disabled || isAdding || accounts.length === 0}
          onClick={() => {
            setNewAccountId(accounts[0]?.account_id || '');
            setIsAdding(true);
          }}
          className="btn btn-secondary"
          style={{ fontSize: '11px', padding: '4px 10px', gap: '4px' }}
        >
          <Plus size={12} />
          <span>Add Link</span>
        </button>
      </div>

      {/* Add Edge Form */}
      {isAdding && (
        <div
          style={{
            padding: '12px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--accent-purple)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--accent-purple)' }}>
            Link Account to Infrastructure Entity
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Account</label>
              <select
                value={newAccountId}
                onChange={(e) => setNewAccountId(e.target.value)}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              >
                {accounts.map((a) => (
                  <option key={a.account_id} value={a.account_id}>
                    {a.account_id}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Entity Type</label>
              <select
                value={newEntityType}
                onChange={(e) => setNewEntityType(e.target.value as any)}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              >
                <option value="DEVICE">DEVICE</option>
                <option value="IP">IP</option>
                <option value="PAYMENT">PAYMENT</option>
                <option value="ADDRESS">ADDRESS</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Entity ID</label>
              <input
                type="text"
                className="font-mono"
                value={newEntityId}
                onChange={(e) => setNewEntityId(e.target.value)}
                placeholder="DEV_SHARED_01"
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
            <button type="button" onClick={() => setIsAdding(false)} className="btn btn-secondary" style={{ fontSize: '11px', padding: '3px 8px' }}>
              <X size={12} />
              <span>Cancel</span>
            </button>
            <button type="button" onClick={handleAddEdge} className="btn btn-primary" style={{ fontSize: '11px', padding: '3px 10px' }}>
              <Check size={12} />
              <span>Add Link</span>
            </button>
          </div>
        </div>
      )}

      {/* Edges List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '260px', overflowY: 'auto' }}>
        {edges.map((edge, idx) => {
          const degree = entityDegrees[edge.entity_id] || 1;
          const isShared = degree >= 2;
          const isSelected = selectedEntityId === edge.entity_id;

          return (
            <div
              key={idx}
              onClick={() => onSelectEntity && onSelectEntity(isSelected ? null : edge.entity_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '7px 10px',
                backgroundColor: isSelected ? 'var(--bg-elevated)' : 'var(--bg-card)',
                border: `1px solid ${isSelected ? 'var(--accent-purple)' : isShared ? 'var(--border-muted)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ padding: '4px', backgroundColor: 'var(--bg-app)', borderRadius: 'var(--radius-sm)' }}>
                  {getEntityIcon(edge.entity_type)}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="font-mono" style={{ fontSize: '11px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
                    {edge.account_id}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>─</span>
                  <span className="font-mono" style={{ fontSize: '11px', color: 'var(--text-primary)' }}>
                    {edge.entity_id}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} onClick={(e) => e.stopPropagation()}>
                {isShared && (
                  <span
                    style={{
                      fontSize: '9px',
                      fontWeight: '700',
                      padding: '2px 6px',
                      backgroundColor: 'rgba(168, 85, 247, 0.15)',
                      color: 'var(--accent-purple)',
                      borderRadius: 'var(--radius-pill)',
                    }}
                  >
                    Shared ({degree}x)
                  </span>
                )}

                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => handleRemoveEdge(idx)}
                  style={{ color: 'var(--status-offline)', cursor: 'pointer', padding: '2px' }}
                  title="Remove Link"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
