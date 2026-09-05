import React, { useState } from 'react';
import { AccountNodeInput, EntityEdgeInput } from '../../types/api';
import { Network, Info } from 'lucide-react';

interface AbuseRingGraphProps {
  accounts: AccountNodeInput[];
  edges: EntityEdgeInput[];
  selectedAccountId?: string | null;
  selectedEntityId?: string | null;
  onSelectAccount?: (accountId: string | null) => void;
  onSelectEntity?: (entityId: string | null) => void;
}

export const AbuseRingGraph: React.FC<AbuseRingGraphProps> = ({
  accounts,
  edges,
  selectedAccountId,
  selectedEntityId,
  onSelectAccount,
  onSelectEntity,
}) => {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // Group unique entities with their type and degree
  const entitiesMap = edges.reduce((acc, edge) => {
    if (!acc[edge.entity_id]) {
      acc[edge.entity_id] = {
        entity_id: edge.entity_id,
        entity_type: edge.entity_type,
        accounts: new Set<string>(),
      };
    }
    acc[edge.entity_id].accounts.add(edge.account_id);
    return acc;
  }, {} as Record<string, { entity_id: string; entity_type: string; accounts: Set<string> }>);

  const uniqueEntities = Object.values(entitiesMap);

  // Layout parameters for clean bipartite layout
  const width = 640;
  const height = Math.max(340, Math.max(accounts.length, uniqueEntities.length) * 60 + 60);

  const accountYSpacing = (height - 60) / Math.max(1, accounts.length);
  const entityYSpacing = (height - 60) / Math.max(1, uniqueEntities.length);

  const accountNodes = accounts.map((acc, idx) => ({
    id: acc.account_id,
    label: acc.account_id,
    x: 100,
    y: 40 + idx * accountYSpacing + accountYSpacing / 2,
    data: acc,
  }));

  const entityNodes = uniqueEntities.map((ent, idx) => ({
    id: ent.entity_id,
    label: ent.entity_id,
    type: ent.entity_type,
    degree: ent.accounts.size,
    x: 520,
    y: 40 + idx * entityYSpacing + entityYSpacing / 2,
    connectedAccounts: Array.from(ent.accounts),
  }));

  const getEntityColor = (type: string) => {
    switch (type) {
      case 'DEVICE':
        return '#38bdf8'; // Cyan
      case 'IP':
        return '#a855f7'; // Purple
      case 'PAYMENT':
        return '#f59e0b'; // Amber
      case 'ADDRESS':
        return '#f43f5e'; // Rose
      default:
        return '#94a3b8';
    }
  };

  const isEdgeActive = (accId: string, entId: string) => {
    if (selectedAccountId && accId === selectedAccountId) return true;
    if (selectedEntityId && entId === selectedEntityId) return true;
    if (hoveredNode && (accId === hoveredNode || entId === hoveredNode)) return true;
    return false;
  };

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Network size={16} color="var(--accent-cyan)" />
            <h3 className="card-title">Bipartite Cluster Topology Visualizer</h3>
          </div>
          <p className="card-description">
            Interactive graph mapping Account Nodes (left) to shared Infrastructure Entity Nodes (right).
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '10px', color: 'var(--text-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#38bdf8' }} />
            <span>Device</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#a855f7' }} />
            <span>IP</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f59e0b' }} />
            <span>Payment</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#f43f5e' }} />
            <span>Address</span>
          </div>
        </div>
      </div>

      {/* SVG Interactive Canvas */}
      <div
        style={{
          backgroundColor: 'var(--bg-app)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', minHeight: '320px', display: 'block' }}
        >
          {/* Subtle Grid Background */}
          <defs>
            <pattern id="graph-grid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#graph-grid)" />

          {/* Section Column Labels */}
          <text x="100" y="22" fill="var(--text-muted)" fontSize="11" fontWeight="700" textAnchor="middle">
            ACCOUNT NODES ({accounts.length})
          </text>
          <text x="520" y="22" fill="var(--text-muted)" fontSize="11" fontWeight="700" textAnchor="middle">
            SHARED ENTITIES ({uniqueEntities.length})
          </text>

          {/* Bipartite Link Edges */}
          {edges.map((edge, idx) => {
            const acc = accountNodes.find((a) => a.id === edge.account_id);
            const ent = entityNodes.find((e) => e.id === edge.entity_id);
            if (!acc || !ent) return null;

            const active = isEdgeActive(edge.account_id, edge.entity_id);
            const entColor = getEntityColor(edge.entity_type);

            // Smooth cubic bezier curve between bipartite columns
            const dx = (ent.x - acc.x) * 0.5;
            const pathD = `M ${acc.x + 70} ${acc.y} C ${acc.x + 70 + dx} ${acc.y}, ${ent.x - 70 - dx} ${ent.y}, ${ent.x - 70} ${ent.y}`;

            return (
              <path
                key={idx}
                d={pathD}
                fill="none"
                stroke={active ? entColor : 'rgba(148, 163, 184, 0.2)'}
                strokeWidth={active ? 2.5 : 1.2}
                strokeDasharray={active ? 'none' : '2,2'}
                style={{ transition: 'all 200ms ease' }}
              />
            );
          })}

          {/* Account Nodes */}
          {accountNodes.map((node) => {
            const isSelected = selectedAccountId === node.id;
            const isHovered = hoveredNode === node.id;
            const isHighRisk = (node.data.suspicious_activity_score ?? 0) >= 0.70;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => onSelectAccount && onSelectAccount(isSelected ? null : node.id)}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Node Pill */}
                <rect
                  x="-70"
                  y="-16"
                  width="140"
                  height="32"
                  rx="6"
                  fill={isSelected ? 'var(--bg-elevated)' : isHovered ? 'var(--bg-card)' : 'var(--bg-card)'}
                  stroke={isSelected ? 'var(--accent-cyan)' : isHighRisk ? 'var(--risk-high)' : 'var(--border-subtle)'}
                  strokeWidth={isSelected ? 2 : 1}
                />

                {/* Node Label */}
                <text
                  x="-35"
                  y="4"
                  fill={isSelected ? 'var(--accent-cyan)' : 'var(--text-primary)'}
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="700"
                >
                  {node.label.length > 13 ? `${node.label.slice(0, 11)}..` : node.label}
                </text>

                {/* Account Marker Dot */}
                <circle
                  cx="-52"
                  cy="0"
                  r="4"
                  fill={isHighRisk ? 'var(--risk-high)' : 'var(--risk-low)'}
                />
              </g>
            );
          })}

          {/* Entity Nodes */}
          {entityNodes.map((node) => {
            const isSelected = selectedEntityId === node.id;
            const isHovered = hoveredNode === node.id;
            const isShared = node.degree >= 2;
            const nodeColor = getEntityColor(node.type);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onClick={() => onSelectEntity && onSelectEntity(isSelected ? null : node.id)}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Node Pill */}
                <rect
                  x="-70"
                  y="-16"
                  width="140"
                  height="32"
                  rx="6"
                  fill={isSelected ? 'var(--bg-elevated)' : isHovered ? 'var(--bg-card)' : 'var(--bg-card)'}
                  stroke={isSelected ? nodeColor : isShared ? nodeColor : 'var(--border-subtle)'}
                  strokeWidth={isSelected ? 2 : isShared ? 1.5 : 1}
                />

                {/* Node Label */}
                <text
                  x="-35"
                  y="4"
                  fill={isSelected ? nodeColor : 'var(--text-primary)'}
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="600"
                >
                  {node.label.length > 13 ? `${node.label.slice(0, 11)}..` : node.label}
                </text>

                {/* Type Tag Dot / Degree */}
                <circle
                  cx="-52"
                  cy="0"
                  r="4"
                  fill={nodeColor}
                />

                {/* Shared Degree Pill */}
                {isShared && (
                  <g transform="translate(52, 0)">
                    <rect x="-10" y="-8" width="20" height="16" rx="8" fill="rgba(168, 85, 247, 0.2)" stroke="var(--accent-purple)" strokeWidth="0.8" />
                    <text x="0" y="3.5" fill="var(--accent-purple)" fontSize="9" fontWeight="800" textAnchor="middle">
                      {node.degree}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* Graph Safety / Bystander Disclaimer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          backgroundColor: 'var(--bg-app)',
          borderRadius: 'var(--radius-sm)',
          fontSize: '11px',
          color: 'var(--text-muted)',
        }}
      >
        <Info size={14} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
        <span>
          <strong>Graph Grounding Safety:</strong> Shared infrastructure (IP/Device/Address) indicates topological connectivity, not guilt.
          The downstream ML engine and bystander protection rules isolate malicious cliques from incidental co-located users.
        </span>
      </div>
    </div>
  );
};
