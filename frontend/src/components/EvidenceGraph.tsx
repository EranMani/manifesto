import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
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

const TYPE_ORDER: Record<string, number> = {
  regulation: 0,
  requirement: 1,
  policy: 2,
  evidence: 3,
}

const TYPE_COLORS: Record<string, { bg: string; border: string }> = {
  regulation: { bg: '#dbeafe', border: '#3b82f6' },
  requirement: { bg: '#fef3c7', border: '#f59e0b' },
  policy: { bg: '#d1fae5', border: '#10b981' },
  evidence: { bg: '#ede9fe', border: '#8b5cf6' },
}

const MUTED_STYLE = { opacity: 0.4 }
const HIGHLIGHT_STROKE = '#2563eb'

function typeColumn(type: string): number {
  return TYPE_ORDER[type] ?? Object.keys(TYPE_ORDER).length
}

function layoutNodes(graphNodes: GraphNodeSchema[], highlighted: Set<string>): Node[] {
  const columns = new Map<number, GraphNodeSchema[]>()
  for (const n of graphNodes) {
    const col = typeColumn(n.type)
    if (!columns.has(col)) columns.set(col, [])
    columns.get(col)!.push(n)
  }

  const nodes: Node[] = []
  const xGap = 280
  const yGap = 100

  for (const [col, group] of columns) {
    group.forEach((gn, row) => {
      const isHighlighted = highlighted.has(gn.id)
      const colors = TYPE_COLORS[gn.type] ?? { bg: '#f3f4f6', border: '#9ca3af' }
      nodes.push({
        id: gn.id,
        position: { x: col * xGap, y: row * yGap },
        data: { label: gn.label, nodeType: gn.type },
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
      })
    })
  }

  return nodes
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
      label: e.relationship,
      animated: isHighlighted,
      style: {
        stroke: isHighlighted ? HIGHLIGHT_STROKE : '#d1d5db',
        strokeWidth: isHighlighted ? 2 : 1,
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
    <div className="h-96 w-full rounded-lg border border-gray-200">
      <ReactFlowProvider>
        <InnerGraph graph={graph} />
      </ReactFlowProvider>
    </div>
  )
}
