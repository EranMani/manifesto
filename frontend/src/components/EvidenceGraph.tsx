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

const COLUMN_ORDER: Record<string, number> = {
  buyer: 0,
  purchase_order: 1,
  vendor: 2,
  shipment: 3,
  product: 4,
  event: 4,
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

function layoutNodes(graphNodes: GraphNodeSchema[], highlighted: Set<string>): Node[] {
  const xGap = 220
  const yGap = 80

  const columns = new Map<number, GraphNodeSchema[]>()
  const productNodes: GraphNodeSchema[] = []
  const eventNodes: GraphNodeSchema[] = []

  for (const n of graphNodes) {
    if (n.type === 'product') {
      productNodes.push(n)
    } else if (n.type === 'event') {
      eventNodes.push(n)
    } else {
      const col = COLUMN_ORDER[n.type] ?? 5
      if (!columns.has(col)) columns.set(col, [])
      columns.get(col)!.push(n)
    }
  }

  const nodes: Node[] = []

  for (const [col, group] of columns) {
    group.forEach((gn, row) => {
      const isHighlighted = highlighted.has(gn.id)
      const colors = getNodeColors(gn)
      nodes.push(buildNode(gn, col * xGap, row * yGap, isHighlighted, colors))
    })
  }

  const col4X = 4 * xGap
  productNodes.forEach((gn, row) => {
    const isHighlighted = highlighted.has(gn.id)
    const colors = getNodeColors(gn)
    nodes.push(buildNode(gn, col4X, row * yGap, isHighlighted, colors))
  })

  const eventStartY = productNodes.length * yGap
  eventNodes.forEach((gn, row) => {
    const isHighlighted = highlighted.has(gn.id)
    const colors = getNodeColors(gn)
    nodes.push(buildNode(gn, col4X, eventStartY + row * yGap, isHighlighted, colors))
  })

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
): Node {
  return {
    id: gn.id,
    position: { x, y },
    data: { label: buildNodeLabel(gn) },
    style: {
      background: colors.bg,
      border: `2px solid ${isHighlighted ? HIGHLIGHT_STROKE : colors.border}`,
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 13,
      fontWeight: isHighlighted ? 600 : 400,
      boxShadow: isHighlighted ? `0 0 0 2px ${HIGHLIGHT_STROKE}40` : 'none',
      ...(isHighlighted ? {} : MUTED_STYLE),
    },
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }
}

function layoutEdges(
  graphEdges: { source: string; target: string; relationship: string }[],
  highlighted: Set<string>,
): Edge[] {
  return graphEdges.map((e, i) => {
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
  const initialNodes = useMemo(() => layoutNodes(graph.nodes, highlighted), [graph.nodes, highlighted])
  const initialEdges = useMemo(() => layoutEdges(graph.edges, highlighted), [graph.edges, highlighted])

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)
  const { fitView } = useReactFlow()
  const [selectedNode, setSelectedNode] = useState<GraphNodeSchema | null>(null)

  useEffect(() => {
    setSelectedNode(null)
    const timer = setTimeout(() => fitView({ padding: 0.2 }), 50)
    return () => clearTimeout(timer)
  }, [graph, fitView])

  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
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
    <div className="h-[500px] w-full rounded-lg border border-gray-200">
      <ReactFlowProvider>
        <InnerGraph graph={graph} />
      </ReactFlowProvider>
    </div>
  )
}
