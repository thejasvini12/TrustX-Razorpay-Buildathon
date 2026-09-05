import React, { useState } from 'react';
import { AccountNodeInput } from '../../types/api';
import { Users, Plus, Trash2, Edit3, Copy, Check, X } from 'lucide-react';

interface AccountNodeEditorProps {
  accounts: AccountNodeInput[];
  onChange: (accounts: AccountNodeInput[]) => void;
  selectedAccountId?: string | null;
  onSelectAccount?: (accountId: string | null) => void;
  disabled?: boolean;
}

const DEFAULT_NEW_ACCOUNT: AccountNodeInput = {
  account_id: 'ACC_CUSTOM_901',
  created_at: new Date().toISOString(),
  average_order_value: 120.0,
  return_rate: 0.25,
  suspicious_activity_score: 0.50,
  order_count: 10,
  total_spend: 1200.0,
  device_type: 'desktop_chrome',
  primary_payment_method: 'credit_card',
};

export const AccountNodeEditor: React.FC<AccountNodeEditorProps> = ({
  accounts,
  onChange,
  selectedAccountId,
  onSelectAccount,
  disabled = false,
}) => {
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<AccountNodeInput>(DEFAULT_NEW_ACCOUNT);
  const [isAdding, setIsAdding] = useState<boolean>(false);

  const handleStartAdd = () => {
    const nextId = `ACC_CUSTOM_${accounts.length + 101}`;
    setEditForm({ ...DEFAULT_NEW_ACCOUNT, account_id: nextId });
    setIsAdding(true);
    setEditingIndex(null);
  };

  const handleStartEdit = (index: number) => {
    setEditForm({ ...accounts[index] });
    setEditingIndex(index);
    setIsAdding(false);
  };

  const handleSaveEdit = () => {
    if (!editForm.account_id.trim()) return;

    if (isAdding) {
      onChange([...accounts, editForm]);
      setIsAdding(false);
    } else if (editingIndex !== null) {
      const updated = [...accounts];
      updated[editingIndex] = editForm;
      onChange(updated);
      setEditingIndex(null);
    }
  };

  const handleCancel = () => {
    setIsAdding(false);
    setEditingIndex(null);
  };

  const handleDelete = (index: number) => {
    const deletedId = accounts[index].account_id;
    const updated = accounts.filter((_, idx) => idx !== index);
    onChange(updated);
    if (selectedAccountId === deletedId && onSelectAccount) {
      onSelectAccount(null);
    }
  };

  const handleDuplicate = (index: number) => {
    const orig = accounts[index];
    const dup: AccountNodeInput = {
      ...orig,
      account_id: `${orig.account_id}_COPY`,
    };
    onChange([...accounts, dup]);
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
          <Users size={16} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>
            Account Nodes ({accounts.length})
          </h3>
        </div>

        <button
          type="button"
          disabled={disabled || isAdding}
          onClick={handleStartAdd}
          className="btn btn-secondary"
          style={{ fontSize: '11px', padding: '4px 10px', gap: '4px' }}
        >
          <Plus size={12} />
          <span>Add Account</span>
        </button>
      </div>

      {/* Add / Edit Form Modal/Drawer */}
      {(isAdding || editingIndex !== null) && (
        <div
          style={{
            padding: '14px',
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--accent-cyan)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--accent-cyan)' }}>
            {isAdding ? 'Add New Account Node' : `Edit Account: ${editForm.account_id}`}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Account ID</label>
              <input
                type="text"
                className="font-mono"
                value={editForm.account_id}
                onChange={(e) => setEditForm({ ...editForm, account_id: e.target.value })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>AOV ($)</label>
              <input
                type="number"
                min="0"
                value={editForm.average_order_value ?? 0}
                onChange={(e) => setEditForm({ ...editForm, average_order_value: parseFloat(e.target.value) || 0 })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Order Count</label>
              <input
                type="number"
                min="0"
                value={editForm.order_count ?? 0}
                onChange={(e) => setEditForm({ ...editForm, order_count: parseInt(e.target.value) || 0 })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Return Rate (0-1)</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={editForm.return_rate ?? 0}
                onChange={(e) => setEditForm({ ...editForm, return_rate: parseFloat(e.target.value) || 0 })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Anomaly Score (0-1)</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.05"
                value={editForm.suspicious_activity_score ?? 0}
                onChange={(e) => setEditForm({ ...editForm, suspicious_activity_score: parseFloat(e.target.value) || 0 })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Device Type</label>
              <select
                value={editForm.device_type ?? 'desktop_chrome'}
                onChange={(e) => setEditForm({ ...editForm, device_type: e.target.value })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              >
                <option value="desktop_chrome">desktop_chrome</option>
                <option value="desktop_firefox">desktop_firefox</option>
                <option value="mobile_ios">mobile_ios</option>
                <option value="mobile_android">mobile_android</option>
                <option value="emulator_bot">emulator_bot</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Payment Method</label>
              <select
                value={editForm.primary_payment_method ?? 'credit_card'}
                onChange={(e) => setEditForm({ ...editForm, primary_payment_method: e.target.value })}
                style={{ padding: '6px 8px', fontSize: '12px', backgroundColor: 'var(--bg-input)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}
              >
                <option value="credit_card">credit_card</option>
                <option value="debit_card">debit_card</option>
                <option value="paypal">paypal</option>
                <option value="apple_pay">apple_pay</option>
                <option value="google_pay">google_pay</option>
                <option value="virtual_card">virtual_card</option>
                <option value="crypto_gift_card">crypto_gift_card</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button type="button" onClick={handleCancel} className="btn btn-secondary" style={{ fontSize: '11px', padding: '4px 10px' }}>
              <X size={12} />
              <span>Cancel</span>
            </button>
            <button type="button" onClick={handleSaveEdit} className="btn btn-primary" style={{ fontSize: '11px', padding: '4px 12px' }}>
              <Check size={12} />
              <span>Save Node</span>
            </button>
          </div>
        </div>
      )}

      {/* Account Nodes List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '260px', overflowY: 'auto' }}>
        {accounts.map((acc, idx) => {
          const isSelected = selectedAccountId === acc.account_id;
          const isHighSusp = (acc.suspicious_activity_score ?? 0) >= 0.70;

          return (
            <div
              key={idx}
              onClick={() => onSelectAccount && onSelectAccount(isSelected ? null : acc.account_id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: isSelected ? 'var(--bg-elevated)' : 'var(--bg-card)',
                border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius-sm)',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: isHighSusp ? 'var(--risk-high)' : 'var(--risk-low)',
                  }}
                />
                <div>
                  <span className="font-mono" style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-primary)' }}>
                    {acc.account_id}
                  </span>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    AOV: ${acc.average_order_value} • Orders: {acc.order_count} • Susp: {acc.suspicious_activity_score} • {acc.device_type}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => handleStartEdit(idx)}
                  style={{ color: 'var(--text-secondary)', cursor: 'pointer', padding: '3px' }}
                  title="Edit Account"
                >
                  <Edit3 size={13} />
                </button>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => handleDuplicate(idx)}
                  style={{ color: 'var(--text-secondary)', cursor: 'pointer', padding: '3px' }}
                  title="Duplicate Account"
                >
                  <Copy size={13} />
                </button>
                <button
                  type="button"
                  disabled={disabled || accounts.length <= 1}
                  onClick={() => handleDelete(idx)}
                  style={{ color: 'var(--status-offline)', cursor: 'pointer', padding: '3px' }}
                  title="Delete Account"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
