import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  Position,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { GraphSchema, GraphNodeSchema } from '../api/assistant'

const TYPE_COLORS: Record<string, { bg: string; border: string }> = {
  buyer: { bg: '#dbeafe', border: '#3b82f6' },
  purchase_order: { bg: '#fef3c7', border: '#f59e0b' },
  vendor: { bg: '#ede9fe', border: '#8b5cf6' },
  shipment: { bg: '#f1f5f9', border: '#64748b' },
  product: { bg: '#ccfbf1', border: '#14b8a6' },
  event: { bg: '#f3f4f6', border: '#9ca3af' },
}

const STATUS_CATEGORY_COLORS: Record<string, { bg: string; border: string }> = {
  done: { bg: '#dcfce7', border: '#22c55e' },
  active: { bg: '#fff7ed', border: '#f97316' },
  issue: { bg: '#fee2e2', border: '#ef4444' },
}

const ENTITY_ROW_ORDER: Record<string, number> = {
  buyer: 0,
  purchase_order: 1,
  vendor: 2,
  shipment: 3,
  product: 4,
}

const MUTED_STYLE = { opacity: 0.4 }
const HIGHLIGHT_STROKE = '#2563eb'

function getNodeColors(node: GraphNodeSchema): { bg: string; border: string } {
  if (node.status_category && STATUS_CATEGORY_COLORS[node.status_category]) {
    return STATUS_CATEGORY_COLORS[node.status_category]
  }
  return TYPE_COLORS[node.type] ?? { bg: '#f3f4f6', border: '#9ca3af' }
}

function statusBadgeColor(category: string): string {
  switch (category) {
    case 'done': return '#22c55e'
    case 'active': return '#f97316'
    case 'issue': return '#ef4444'
    default: return '#9ca3af'
  }
}

function formatRelationship(rel: string): string {
  return rel
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

function makeLabelNode(id: string, x: number, y: number, text: string): Node {
  return {
    id,
    position: { x, y },
    data: { label: text },
    selectable: false,
    draggable: false,
    connectable: false,
    style: {
      background: 'transparent',
      border: 'none',
      boxShadow: 'none',
      fontSize: 12,
      fontWeight: 600,
      color: '#6b7280',
      padding: 0,
    },
  }
}

function layoutNodes(graphNodes: GraphNodeSchema[], highlighted: Set<string>): Node[] {
  const yGap = 80
  const eventYGap = 70

  const entityByRow = new Map<number, GraphNodeSchema[]>()
  const eventNodes: GraphNodeSchema[] = []

  for (const n of graphNodes) {
    if (n.type === 'event') {
      eventNodes.push(n)
    } else {
      const row = ENTITY_ROW_ORDER[n.type] ?? 5
      if (!entityByRow.has(row)) entityByRow.set(row, [])
      entityByRow.get(row)!.push(n)
    }
  }

  const nodes: Node[] = []

  if (entityByRow.size > 0) {
    nodes.push(makeLabelNode('__label-entities', 0, -40, 'Shipment Details'))
    for (const [row, group] of entityByRow) {
      group.forEach((gn, col) => {
        const isHighlighted = highlighted.has(gn.id)
        const colors = getNodeColors(gn)
        nodes.push(buildNode(gn, col * 220, row * yGap, isHighlighted, colors, false, false))
      })
    }
  }

  if (eventNodes.length > 0) {
    nodes.push(makeLabelNode('__label-timeline', 500, -40, 'Event Timeline'))
    eventNodes.forEach((gn, i) => {
      const isHighlighted = highlighted.has(gn.id)
      const colors = getNodeColors(gn)
      nodes.push(buildNode(gn, 500, i * eventYGap, isHighlighted, colors, true, i === eventNodes.length - 1))
    })
  }

  if (entityByRow.size > 0 && eventNodes.length > 0) {
    const maxEntityRow = Math.max(...entityByRow.keys())
    const entityHeight = (maxEntityRow + 1) * yGap
    const eventHeight = eventNodes.length * eventYGap
    nodes.push({
      id: '__separator',
      position: { x: 390, y: -30 },
      data: { label: '' },
      selectable: false,
      draggable: false,
      connectable: false,
      style: {
        width: 1,
        height: Math.max(entityHeight, eventHeight),
        background: 'transparent',
        border: 'none',
        borderLeft: '1px dashed #d1d5db',
        boxShadow: 'none',
        padding: 0,
      },
    })
  }

  return nodes
}

function buildNodeLabel(gn: GraphNodeSchema): React.ReactNode {
  if (!gn.status) return gn.label
  const badgeColor = gn.status_category ? statusBadgeColor(gn.status_category) : '#9ca3af'
  return React.createElement('div', { style: { textAlign: 'center' as const } },
    React.createElement('div', null, gn.label),
    React.createElement('span', {
      style: {
        display: 'inline-block',
        marginTop: 4,
        padding: '1px 8px',
        borderRadius: 9999,
        fontSize: 10,
        fontWeight: 600,
        color: '#fff',
        backgroundColor: badgeColor,
      },
    }, gn.status),
  )
}

function buildNode(
  gn: GraphNodeSchema,
  x: number,
  y: number,
  isHighlighted: boolean,
  colors: { bg: string; border: string },
  isEvent: boolean,
  isCurrentEvent: boolean,
): Node {
  return {
    id: gn.id,
    position: { x, y },
    data: { label: buildNodeLabel(gn) },
    style: {
      background: colors.bg,
      border: `2px solid ${isHighlighted ? HIGHLIGHT_STROKE : colors.border}`,
      borderRadius: 8,
      padding: isCurrentEvent ? '10px 14px' : '8px 12px',
      fontSize: 13,
      fontWeight: isCurrentEvent ? 700 : isHighlighted ? 600 : 400,
      boxShadow: isCurrentEvent
        ? `0 0 8px ${colors.border}60`
        : isHighlighted
          ? `0 0 0 2px ${HIGHLIGHT_STROKE}40`
          : 'none',
      ...(isHighlighted ? {} : MUTED_STYLE),
    },
    sourcePosition: isEvent ? Position.Bottom : Position.Right,
    targetPosition: isEvent ? Position.Top : Position.Left,
  }
}

function layoutEdges(
  graphEdges: { source: string; target: string; relationship: string }[],
  highlighted: Set<string>,
  eventNodeIds: string[],
): Edge[] {
  const edges: Edge[] = graphEdges.map((e, i) => {
    const isHighlighted = highlighted.has(e.source) && highlighted.has(e.target)
    return {
      id: `e-${i}`,
      source: e.source,
      target: e.target,
      label: formatRelationship(e.relationship),
      animated: isHighlighted,
      style: {
        stroke: isHighlighted ? HIGHLIGHT_STROKE : '#d1d5db',
        strokeWidth: isHighlighted ? 2 : 1.5,
        ...(isHighlighted ? {} : MUTED_STYLE),
      },
      labelStyle: {
        fontSize: 11,
        fill: isHighlighted ? '#1e40af' : '#9ca3af',
      },
    }
  })

  for (let i = 0; i < eventNodeIds.length - 1; i++) {
    const source = eventNodeIds[i]
    const target = eventNodeIds[i + 1]
    const bothHighlighted = highlighted.has(source) && highlighted.has(target)
    edges.push({
      id: `timeline-${i}`,
      source,
      target,
      label: 'Then',
      animated: bothHighlighted,
      style: {
        stroke: bothHighlighted ? HIGHLIGHT_STROKE : '#9ca3af',
        strokeWidth: 1.5,
        strokeDasharray: '5 3',
        ...(bothHighlighted ? {} : MUTED_STYLE),
      },
      labelStyle: {
        fontSize: 10,
        fill: bothHighlighted ? '#1e40af' : '#9ca3af',
      },
    })
  }

  return edges
}

interface DetailPanelProps {
  node: GraphNodeSchema
  onClose: () => void
}

function DetailPanel({ node, onClose }: DetailPanelProps) {
  return (
    <div className="absolute right-0 top-0 h-full w-64 border-l border-gray-200 bg-white p-4 shadow-lg z-10">
      <button
        onClick={onClose}
        className="absolute right-2 top-2 text-gray-400 hover:text-gray-600"
        aria-label="Close detail panel"
      >
        &times;
      </button>
      <h3 className="mt-2 text-sm font-semibold text-gray-900">{node.label}</h3>
      <dl className="mt-3 space-y-2 text-xs text-gray-600">
        <div>
          <dt className="font-medium text-gray-500">Type</dt>
          <dd className="capitalize">{node.type}</dd>
        </div>
        <div>
          <dt className="font-medium text-gray-500">ID</dt>
          <dd className="font-mono">{node.id}</dd>
        </div>
        {node.status && (
          <div>
            <dt className="font-medium text-gray-500">Status</dt>
            <dd className="capitalize">{node.status}</dd>
          </div>
        )}
      </dl>
    </div>
  )
}

interface InnerGraphProps {
  graph: GraphSchema
}

function InnerGraph({ graph }: InnerGraphProps) {
  const highlighted = useMemo(() => new Set(graph.highlighted_path), [graph.highlighted_path])
  const eventNodeIds = useMemo(
    () => graph.nodes.filter((n) => n.type === 'event').map((n) => n.id),
    [graph.nodes],
  )
  const initialNodes = useMemo(() => layoutNodes(graph.nodes, highlighted), [graph.nodes, highlighted])
  const initialEdges = useMemo(
    () => layoutEdges(graph.edges, highlighted, eventNodeIds),
    [graph.edges, highlighted, eventNodeIds],
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const { fitView } = useReactFlow()
  const [selectedNode, setSelectedNode] = useState<GraphNodeSchema | null>(null)

  useEffect(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
    setSelectedNode(null)
    const timer = setTimeout(() => fitView({ padding: 0.2 }), 50)
    return () => clearTimeout(timer)
  }, [initialNodes, initialEdges, setNodes, setEdges, fitView])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      if (node.id.startsWith('__')) return
      const graphNode = graph.nodes.find((n) => n.id === node.id)
      if (graphNode) setSelectedNode(graphNode)
    },
    [graph.nodes],
  )

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls />
      </ReactFlow>
      {selectedNode && (
        <DetailPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  )
}

interface EvidenceGraphProps {
  graph: GraphSchema | null
}

export default function EvidenceGraph({ graph }: EvidenceGraphProps) {
  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50">
        <p className="text-sm text-gray-500">
          No evidence graph available. Ask a question to generate one.
        </p>
      </div>
    )
  }

  return (
    <div className="h-[400px] w-full rounded-lg border border-gray-200">
      <ReactFlowProvider>
        <InnerGraph graph={graph} />
      </ReactFlowProvider>
    </div>
  )
}
