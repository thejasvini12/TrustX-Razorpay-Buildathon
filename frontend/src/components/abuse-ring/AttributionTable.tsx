import React from 'react';
import { AccountAttributionItem } from '../../types/api';
import { ShieldAlert, ShieldCheck, AlertTriangle, Users } from 'lucide-react';

interface AttributionTableProps {
  attributionList: AccountAttributionItem[];
  selectedAccountId?: string | null;
  onSelectAccount?: (accountId: string | null) => void;
}

export const AttributionTable: React.FC<AttributionTableProps> = ({
  attributionList,
  selectedAccountId,
  onSelectAccount,
}) => {
  if (!attributionList || attributionList.length === 0) return null;

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'CORE_MEMBER':
        return {
          label: 'Core Member',
          badge: 'badge-critical',
          color: 'var(--risk-critical)',
          icon: ShieldAlert,
          desc: 'High-centrality coordinated operator driving entity links and anomaly signals.',
        };
      case 'PERIPHERAL_MEMBER':
        return {
          label: 'Peripheral Member',
          badge: 'badge-medium',
          color: 'var(--risk-medium)',
          icon: AlertTriangle,
          desc: 'Secondary participant exhibiting moderate connectivity or anomalous attributes.',
        };
      case 'INCIDENTAL_BYSTANDER':
      default:
        return {
          label: 'Incidental Bystander (Protected)',
          badge: 'badge-low',
          color: 'var(--risk-low)',
          icon: ShieldCheck,
          desc: 'Co-located legitimate user on shared IP/campus infrastructure. Fully protected from bulk enforcement.',
        };
    }
  };

  const bystanderCount = attributionList.filter((a) => a.attribution_role === 'INCIDENTAL_BYSTANDER').length;
  const coreCount = attributionList.filter((a) => a.attribution_role === 'CORE_MEMBER').length;

  return (
    <div className="card">
      {/* Header */}
      <div className="card-header" style={{ marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Account Attribution & Role Classification</h3>
          </div>
          <p className="card-description">
            Sub-graph role decomposition isolating malicious syndicate operators from incidental bystanders.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {bystanderCount > 0 && (
            <span className="badge badge-low" style={{ fontSize: '11px' }}>
              {bystanderCount} Protected Bystander{bystanderCount > 1 ? 's' : ''}
            </span>
          )}
          {coreCount > 0 && (
            <span className="badge badge-critical" style={{ fontSize: '11px' }}>
              {coreCount} Core Operator{coreCount > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Attribution Table */}
      <div style={{ overflowX: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: '12px',
            textAlign: 'left',
          }}
        >
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Account ID</th>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Attribution Role</th>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Ring Links</th>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Shared Entities</th>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Risk Contribution</th>
              <th style={{ padding: '8px 10px', fontWeight: '600' }}>Attribution Rationale</th>
            </tr>
          </thead>
          <tbody>
            {attributionList.map((item, idx) => {
              const roleInfo = getRoleBadge(item.attribution_role);
              const isSelected = selectedAccountId === item.account_id;
              const RoleIcon = roleInfo.icon;

              return (
                <tr
                  key={idx}
                  onClick={() => onSelectAccount && onSelectAccount(isSelected ? null : item.account_id)}
                  style={{
                    borderBottom: '1px solid var(--border-subtle)',
                    backgroundColor: isSelected
                      ? 'var(--bg-elevated)'
                      : item.attribution_role === 'INCIDENTAL_BYSTANDER'
                      ? 'rgba(16, 185, 129, 0.03)'
                      : 'transparent',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  {/* Account ID */}
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="font-mono" style={{ fontWeight: '700', color: isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)' }}>
                        {item.account_id}
                      </span>
                    </div>
                  </td>

                  {/* Attribution Role */}
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <RoleIcon size={14} color={roleInfo.color} />
                      <span className={`badge ${roleInfo.badge}`} style={{ fontSize: '10px' }}>
                        {item.attribution_role}
                      </span>
                    </div>
                  </td>

                  {/* Linked Ring Accounts */}
                  <td className="font-mono" style={{ padding: '10px', fontWeight: '700', color: item.linked_ring_accounts_count > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {item.linked_ring_accounts_count} linked accs
                  </td>

                  {/* Shared Entity Types */}
                  <td style={{ padding: '10px' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                      {item.shared_entity_types && item.shared_entity_types.length > 0 ? (
                        item.shared_entity_types.map((type, tIdx) => (
                          <span
                            key={tIdx}
                            className="font-mono"
                            style={{
                              fontSize: '9px',
                              padding: '2px 5px',
                              backgroundColor: 'var(--bg-app)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {type}
                          </span>
                        ))
                      ) : (
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>None</span>
                      )}
                    </div>
                  </td>

                  {/* Risk Contribution */}
                  <td style={{ padding: '10px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: '700',
                        color: item.risk_contribution === 'HIGH' ? 'var(--risk-high)' : item.risk_contribution === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
                      }}
                    >
                      {item.risk_contribution}
                    </span>
                  </td>

                  {/* Reasoning */}
                  <td style={{ padding: '10px', fontSize: '11px', color: 'var(--text-secondary)', maxWidth: '320px', lineHeight: '1.4' }}>
                    {item.attribution_reasoning}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
