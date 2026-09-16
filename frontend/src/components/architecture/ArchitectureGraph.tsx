import React, { useState, useMemo, useCallback } from 'react'
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
  BackgroundVariant,
  type Node,
  type Edge,
  type NodeProps,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import {
  Layout,
  Globe,
  Cpu,
  Database,
  Wrench,
  Settings,
  CheckSquare,
  FileCode,
  AlertTriangle,
  Search,
  Layers,
  FolderTree,
  Filter,
  RefreshCw,
  Info,
  X,
  ArrowRight,
  ExternalLink,
  GitFork,
  Maximize2,
} from 'lucide-react'
import type {
  ArchitectureNode,
  ArchitectureEdge,
  ArchitectureCycle,
  ArchitectureLayer,
  ArchitectureGraphData,
} from '../../types/architecture'

// ---------------------------------------------------------------------------
// Layer Color Schemes & Icons
// ---------------------------------------------------------------------------
export const LAYER_CONFIG: Record<
  string,
  {
    label: string
    color: string
    bgBadge: string
    borderBadge: string
    textBadge: string
    nodeBg: string
    nodeBorder: string
    icon: React.ComponentType<{ className?: string }>
  }
> = {
  Presentation: {
    label: 'Presentation',
    color: '#818cf8', // Indigo
    bgBadge: 'bg-indigo-500/10',
    borderBadge: 'border-indigo-500/30',
    textBadge: 'text-indigo-400',
    nodeBg: 'bg-indigo-950/20',
    nodeBorder: 'border-indigo-500/40',
    icon: Layout,
  },
  API: {
    label: 'API & Routing',
    color: '#38bdf8', // Sky
    bgBadge: 'bg-sky-500/10',
    borderBadge: 'border-sky-500/30',
    textBadge: 'text-sky-400',
    nodeBg: 'bg-sky-950/20',
    nodeBorder: 'border-sky-500/40',
    icon: Globe,
  },
  Service: {
    label: 'Service & Logic',
    color: '#34d399', // Emerald
    bgBadge: 'bg-emerald-500/10',
    borderBadge: 'border-emerald-500/30',
    textBadge: 'text-emerald-400',
    nodeBg: 'bg-emerald-950/20',
    nodeBorder: 'border-emerald-500/40',
    icon: Cpu,
  },
  Data: {
    label: 'Data & Models',
    color: '#fbbf24', // Amber
    bgBadge: 'bg-amber-500/10',
    borderBadge: 'border-amber-500/30',
    textBadge: 'text-amber-400',
    nodeBg: 'bg-amber-950/20',
    nodeBorder: 'border-amber-500/40',
    icon: Database,
  },
  Utility: {
    label: 'Utility & Helpers',
    color: '#94a3b8', // Slate
    bgBadge: 'bg-slate-500/10',
    borderBadge: 'border-slate-500/30',
    textBadge: 'text-slate-400',
    nodeBg: 'bg-slate-950/20',
    nodeBorder: 'border-slate-500/40',
    icon: Wrench,
  },
  Configuration: {
    label: 'Configuration',
    color: '#f472b6', // Pink
    bgBadge: 'bg-pink-500/10',
    borderBadge: 'border-pink-500/30',
    textBadge: 'text-pink-400',
    nodeBg: 'bg-pink-950/20',
    nodeBorder: 'border-pink-500/40',
    icon: Settings,
  },
  Test: {
    label: 'Test Suite',
    color: '#a3e635', // Lime
    bgBadge: 'bg-lime-500/10',
    borderBadge: 'border-lime-500/30',
    textBadge: 'text-lime-400',
    nodeBg: 'bg-lime-950/20',
    nodeBorder: 'border-lime-500/40',
    icon: CheckSquare,
  },
  Unknown: {
    label: 'General Code',
    color: '#64748b', // Gray
    bgBadge: 'bg-slate-800/40',
    borderBadge: 'border-slate-700',
    textBadge: 'text-slate-400',
    nodeBg: 'bg-slate-900/30',
    nodeBorder: 'border-slate-700',
    icon: FileCode,
  },
}

// ---------------------------------------------------------------------------
// Custom Flow Node
// ---------------------------------------------------------------------------
export interface ArchitectureNodeData extends Record<string, unknown> {
  rawNode: ArchitectureNode
  isHighlighted?: boolean
  isDimmed?: boolean
  isInSelectedCycle?: boolean
}

export type ArchitectureFlowNode = Node<ArchitectureNodeData, 'archNode'>

const CustomArchitectureNodeComponent = ({ data, selected }: NodeProps<ArchitectureFlowNode>) => {
  const { rawNode, isHighlighted, isDimmed, isInSelectedCycle } = data
  const layerConf = LAYER_CONFIG[rawNode.layer] || LAYER_CONFIG.Unknown
  const Icon = layerConf.icon

  const isInCycle = rawNode.metrics.is_in_cycle

  return (
    <div
      className={`relative px-3.5 py-2.5 rounded-xl border transition-all duration-200 cursor-pointer min-w-[210px] max-w-[260px] shadow-lg backdrop-blur-md ${
        layerConf.nodeBg
      } ${
        isInSelectedCycle
          ? 'border-red-500 ring-2 ring-red-500 shadow-red-500/30'
          : selected || isHighlighted
          ? 'border-primary ring-2 ring-primary/40 shadow-primary/20 scale-105'
          : isInCycle
          ? 'border-red-500/80 shadow-red-500/20 ring-1 ring-red-500/40'
          : layerConf.nodeBorder
      } ${isDimmed ? 'opacity-25 grayscale' : 'opacity-100'}`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-slate-900 transition-colors hover:!bg-primary"
      />

      {/* Header: Icon + File Name */}
      <div className="flex items-start gap-2">
        <div
          className={`p-1.5 rounded-lg shrink-0 ${layerConf.bgBadge} ${layerConf.textBadge} border ${layerConf.borderBadge}`}
        >
          <Icon className="w-3.5 h-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span
              className="text-xs font-semibold text-slate-100 truncate block tracking-tight"
              title={rawNode.file_path}
            >
              {rawNode.name}
            </span>
            {isInCycle && (
              <span
                className="shrink-0 text-[10px] px-1 py-0.2 rounded bg-red-500/20 border border-red-500/40 text-red-300 font-mono font-medium flex items-center gap-0.5"
                title="Part of a circular dependency loop"
              >
                <AlertTriangle className="w-2.5 h-2.5" />
                Cycle
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400 truncate mt-0.5" title={rawNode.file_path}>
            {rawNode.file_path}
          </p>
        </div>
      </div>

      {/* Footer: Layer Badge + Degree Metrics */}
      <div className="mt-2.5 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
        <span
          className={`px-1.5 py-0.5 rounded-md font-medium border ${layerConf.bgBadge} ${layerConf.borderBadge} ${layerConf.textBadge}`}
        >
          {rawNode.layer}
        </span>
        <div className="flex items-center gap-2 text-slate-400 font-mono font-medium">
          <span title="In-degree: files importing this">In: {rawNode.metrics.in_degree ?? 0}</span>
          <span className="text-slate-600">|</span>
          <span title="Out-degree: files this imports">Out: {rawNode.metrics.out_degree ?? 0}</span>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-slate-900 transition-colors hover:!bg-primary"
      />
    </div>
  )
}

const nodeTypes = {
  archNode: CustomArchitectureNodeComponent,
}

// ---------------------------------------------------------------------------
// Main Architecture Graph Component
// ---------------------------------------------------------------------------
interface ArchitectureGraphProps {
  graphData: ArchitectureGraphData
  onNodeSelect?: (node: ArchitectureNode | null) => void
}

export const ArchitectureGraph: React.FC<ArchitectureGraphProps> = ({ graphData, onNodeSelect }) => {
  const { nodes: rawNodes, edges: rawEdges, cycles, analysis } = graphData

  // State
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLayer, setSelectedLayer] = useState<string>('ALL')
  const [layoutMode, setLayoutMode] = useState<'layer' | 'directory' | 'grid'>('layer')
  const [highlightCyclesOnly, setHighlightCyclesOnly] = useState(false)
  const [selectedCycleIndex, setSelectedCycleIndex] = useState<number | null>(null)
  const [selectedNode, setSelectedNode] = useState<ArchitectureNode | null>(null)
  const [showCyclesDrawer, setShowCyclesDrawer] = useState(false)

  // Map of node ids to node object for quick lookups
  const nodeMap = useMemo(() => {
    const map = new Map<string, ArchitectureNode>()
    rawNodes.forEach((n) => map.set(n.id, n))
    return map
  }, [rawNodes])

  // Map of file paths to node id
  const pathMap = useMemo(() => {
    const map = new Map<string, string>()
    rawNodes.forEach((n) => map.set(n.file_path, n.id))
    return map
  }, [rawNodes])

  // Set of node IDs in currently selected cycle
  const activeCycleNodeIds = useMemo(() => {
    if (selectedCycleIndex === null || !cycles[selectedCycleIndex]) return new Set<string>()
    const cyclePaths = cycles[selectedCycleIndex]
    const ids = new Set<string>()
    cyclePaths.forEach((path) => {
      const id = pathMap.get(path)
      if (id) ids.add(id)
    })
    return ids
  }, [selectedCycleIndex, cycles, pathMap])

  // Filtered nodes based on search & layer filter
  const filteredNodes = useMemo(() => {
    return rawNodes.filter((node) => {
      if (selectedLayer !== 'ALL' && node.layer !== selectedLayer) {
        return false
      }
      if (highlightCyclesOnly && !node.metrics.is_in_cycle) {
        return false
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase()
        const matchesName = node.name.toLowerCase().includes(q)
        const matchesPath = node.file_path.toLowerCase().includes(q)
        const matchesLayer = node.layer.toLowerCase().includes(q)
        if (!matchesName && !matchesPath && !matchesLayer) return false
      }
      return true
    })
  }, [rawNodes, selectedLayer, highlightCyclesOnly, searchQuery])

  const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((n) => n.id)), [filteredNodes])

  // Compute Layout Positions
  const layoutedNodes: ArchitectureFlowNode[] = useMemo(() => {
    const LAYER_ORDER: ArchitectureLayer[] = [
      'Presentation',
      'API',
      'Service',
      'Data',
      'Utility',
      'Configuration',
      'Test',
      'Unknown',
    ]

    const result: ArchitectureFlowNode[] = []

    if (layoutMode === 'layer') {
      // Group by Layer
      const layerGroups: Record<string, ArchitectureNode[]> = {}
      LAYER_ORDER.forEach((l) => (layerGroups[l] = []))

      filteredNodes.forEach((n) => {
        const layer = LAYER_ORDER.includes(n.layer as ArchitectureLayer) ? n.layer : 'Unknown'
        layerGroups[layer].push(n)
      })

      let currentY = 50
      LAYER_ORDER.forEach((layer) => {
        const group = layerGroups[layer]
        if (group && group.length > 0) {
          const totalWidth = group.length * 280
          const startX = Math.max(50, 600 - totalWidth / 2)

          group.forEach((node, idx) => {
            result.push({
              id: node.id,
              type: 'archNode',
              position: { x: startX + idx * 280, y: currentY },
              data: {
                rawNode: node,
                isInSelectedCycle: activeCycleNodeIds.has(node.id),
                isHighlighted: selectedNode?.id === node.id,
                isDimmed:
                  (selectedNode !== null && selectedNode.id !== node.id && !activeCycleNodeIds.has(node.id)) ||
                  (activeCycleNodeIds.size > 0 && !activeCycleNodeIds.has(node.id)),
              },
            })
          })
          currentY += 180
        }
      })
    } else if (layoutMode === 'directory') {
      // Group by Directory
      const dirGroups: Record<string, ArchitectureNode[]> = {}
      filteredNodes.forEach((n) => {
        const dir = n.directory || 'root'
        if (!dirGroups[dir]) dirGroups[dir] = []
        dirGroups[dir].push(n)
      })

      let currentY = 50
      Object.entries(dirGroups).forEach(([, group]) => {
        group.forEach((node, idx) => {
          result.push({
            id: node.id,
            type: 'archNode',
            position: { x: 50 + idx * 280, y: currentY },
            data: {
              rawNode: node,
              isInSelectedCycle: activeCycleNodeIds.has(node.id),
              isHighlighted: selectedNode?.id === node.id,
              isDimmed:
                (selectedNode !== null && selectedNode.id !== node.id && !activeCycleNodeIds.has(node.id)) ||
                (activeCycleNodeIds.size > 0 && !activeCycleNodeIds.has(node.id)),
            },
          })
        })
        currentY += 180
      })
    } else {
      // Simple Grid
      const cols = Math.max(3, Math.ceil(Math.sqrt(filteredNodes.length)))
      filteredNodes.forEach((node, idx) => {
        const col = idx % cols
        const row = Math.floor(idx / cols)
        result.push({
          id: node.id,
          type: 'archNode',
          position: { x: 50 + col * 280, y: 50 + row * 180 },
          data: {
            rawNode: node,
            isInSelectedCycle: activeCycleNodeIds.has(node.id),
            isHighlighted: selectedNode?.id === node.id,
            isDimmed:
              (selectedNode !== null && selectedNode.id !== node.id && !activeCycleNodeIds.has(node.id)) ||
              (activeCycleNodeIds.size > 0 && !activeCycleNodeIds.has(node.id)),
          },
        })
      })
    }

    return result
  }, [filteredNodes, layoutMode, activeCycleNodeIds, selectedNode])

  // Build Edges
  const layoutedEdges: Edge[] = useMemo(() => {
    return rawEdges
      .filter((e) => filteredNodeIds.has(e.source_node_id) && filteredNodeIds.has(e.target_node_id))
      .map((edge) => {
        const isCycleEdge = edge.is_circular
        const sourceNode = nodeMap.get(edge.source_node_id)
        const targetNode = nodeMap.get(edge.target_node_id)

        const isInCurrentCycle =
          activeCycleNodeIds.size > 0 &&
          sourceNode &&
          targetNode &&
          activeCycleNodeIds.has(sourceNode.id) &&
          activeCycleNodeIds.has(targetNode.id)

        const isConnectedToSelected =
          selectedNode && (selectedNode.id === edge.source_node_id || selectedNode.id === edge.target_node_id)

        return {
          id: edge.id,
          source: edge.source_node_id,
          target: edge.target_node_id,
          animated: isCycleEdge || Boolean(isInCurrentCycle),
          style: {
            stroke: isInCurrentCycle
              ? '#ef4444' // bright red for active cycle
              : isCycleEdge
              ? '#f87171' // red for circular edge
              : isConnectedToSelected
              ? '#38bdf8' // bright cyan for selected connections
              : '#475569', // slate for normal
            strokeWidth: isInCurrentCycle || isConnectedToSelected ? 2.5 : 1.5,
            strokeDasharray: isCycleEdge ? '5,5' : undefined,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isInCurrentCycle
              ? '#ef4444'
              : isCycleEdge
              ? '#f87171'
              : isConnectedToSelected
              ? '#38bdf8'
              : '#64748b',
            width: 14,
            height: 14,
          },
        }
      })
  }, [rawEdges, filteredNodeIds, activeCycleNodeIds, selectedNode, nodeMap])

  const [nodes, setNodes, onNodesChange] = useNodesState<ArchitectureFlowNode>(layoutedNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges)

  // Sync state when layouted changes
  React.useEffect(() => {
    setNodes(layoutedNodes)
    setEdges(layoutedEdges)
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges])

  // Handle Node Click
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const archNode = (node as ArchitectureFlowNode).data.rawNode
      setSelectedNode(archNode)
      if (onNodeSelect) onNodeSelect(archNode)
    },
    [onNodeSelect]
  )

  // Handle Pane Click
  const handlePaneClick = useCallback(() => {
    setSelectedNode(null)
    if (onNodeSelect) onNodeSelect(null)
  }, [onNodeSelect])

  // Get Inspector Details for selected node
  const selectedNodeDetails = useMemo(() => {
    if (!selectedNode) return null

    const incomingEdges = rawEdges.filter((e) => e.target_node_id === selectedNode.id)
    const outgoingEdges = rawEdges.filter((e) => e.source_node_id === selectedNode.id)

    const importedBy = incomingEdges
      .map((e) => nodeMap.get(e.source_node_id))
      .filter((n): n is ArchitectureNode => Boolean(n))

    const imports = outgoingEdges
      .map((e) => nodeMap.get(e.target_node_id))
      .filter((n): n is ArchitectureNode => Boolean(n))

    return {
      incomingEdges,
      outgoingEdges,
      importedBy,
      imports,
    }
  }, [selectedNode, rawEdges, nodeMap])

  return (
    <div className="relative w-full h-[750px] bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden flex flex-col shadow-2xl">
      {/* Top Toolbar */}
      <div className="p-3.5 bg-slate-900/90 border-b border-slate-800 backdrop-blur-md flex flex-wrap items-center justify-between gap-3 z-10">
        {/* Left: Search & Layer Filter */}
        <div className="flex items-center gap-2.5 flex-1 min-w-[320px]">
          <div className="relative flex-1 max-w-xs">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search file, path, or layer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-800/80 border border-slate-700/80 rounded-lg text-slate-100 placeholder-slate-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedLayer}
              onChange={(e) => setSelectedLayer(e.target.value)}
              className="text-xs bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-primary"
            >
              <option value="ALL">All Layers ({rawNodes.length})</option>
              {Object.keys(LAYER_CONFIG).map((layer) => {
                const count = rawNodes.filter((n) => n.layer === layer).length
                if (count === 0) return null
                return (
                  <option key={layer} value={layer}>
                    {LAYER_CONFIG[layer].label} ({count})
                  </option>
                )
              })}
            </select>
          </div>

          <div className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700/60 text-xs">
            <button
              onClick={() => setLayoutMode('layer')}
              className={`px-2 py-1 rounded font-medium transition-colors flex items-center gap-1 ${
                layoutMode === 'layer' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Organize by Architectural Layers"
            >
              <Layers className="w-3 h-3" />
              Layers
            </button>
            <button
              onClick={() => setLayoutMode('directory')}
              className={`px-2 py-1 rounded font-medium transition-colors flex items-center gap-1 ${
                layoutMode === 'directory' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Organize by Directory Structure"
            >
              <FolderTree className="w-3 h-3" />
              Folders
            </button>
            <button
              onClick={() => setLayoutMode('grid')}
              className={`px-2 py-1 rounded font-medium transition-colors flex items-center gap-1 ${
                layoutMode === 'grid' ? 'bg-primary text-primary-foreground shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Simple Grid Layout"
            >
              <Maximize2 className="w-3 h-3" />
              Grid
            </button>
          </div>
        </div>

        {/* Right: Cycles & Summary Badges */}
        <div className="flex items-center gap-2">
          {cycles.length > 0 && (
            <button
              onClick={() => setShowCyclesDrawer(!showCyclesDrawer)}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-colors ${
                cycles.length > 0
                  ? 'bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>{cycles.length} Circular Chains</span>
            </button>
          )}

          <button
            onClick={() => setHighlightCyclesOnly(!highlightCyclesOnly)}
            className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
              highlightCyclesOnly
                ? 'bg-red-600 text-white border-red-500'
                : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {highlightCyclesOnly ? 'Show All Nodes' : 'Only Cycles'}
          </button>

          <div className="hidden lg:flex items-center gap-2 pl-2 border-l border-slate-800 text-xs text-slate-400">
            <span>
              <strong className="text-slate-200">{filteredNodes.length}</strong> nodes
            </span>
            <span>·</span>
            <span>
              <strong className="text-slate-200">{layoutedEdges.length}</strong> imports
            </span>
          </div>
        </div>
      </div>

      {/* Main Flow Canvas */}
      <div className="relative flex-1 w-full h-full">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2.0}
          defaultEdgeOptions={{
            type: 'smoothstep',
          }}
        >
          <Background color="#334155" gap={24} size={1.2} variant={BackgroundVariant.Dots} />
          <Controls className="!bg-slate-900 !border-slate-800 !shadow-xl" />
          <MiniMap
            nodeColor={(n) => {
              const raw = (n as ArchitectureFlowNode).data?.rawNode
              if (raw && LAYER_CONFIG[raw.layer]) {
                return LAYER_CONFIG[raw.layer].color
              }
              return '#475569'
            }}
            className="!bg-slate-950/90 !border-slate-800 !rounded-xl !overflow-hidden"
            maskColor="rgba(15, 23, 42, 0.7)"
          />

          {/* Canvas Bottom Legend */}
          <Panel position="bottom-left" className="!m-4">
            <div className="bg-slate-900/95 border border-slate-800/80 backdrop-blur-md rounded-xl p-2.5 shadow-xl flex flex-wrap items-center gap-3 text-[11px]">
              <span className="font-semibold text-slate-300 flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-primary" /> Layers:
              </span>
              {Object.entries(LAYER_CONFIG).map(([layerKey, conf]) => {
                const count = rawNodes.filter((n) => n.layer === layerKey).length
                if (count === 0 && layerKey !== 'Presentation' && layerKey !== 'API' && layerKey !== 'Service') return null
                return (
                  <div key={layerKey} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: conf.color }} />
                    <span className="text-slate-400">{conf.label}</span>
                  </div>
                )
              })}
              <div className="flex items-center gap-1.5 pl-2 border-l border-slate-800">
                <span className="w-3.5 h-0.5 border-t-2 border-dashed border-red-400 inline-block" />
                <span className="text-red-400 font-medium">Circular Edge</span>
              </div>
            </div>
          </Panel>
        </ReactFlow>

        {/* Circular Dependencies Drawer / Floating Panel */}
        {showCyclesDrawer && cycles.length > 0 && (
          <div className="absolute top-4 left-4 w-96 max-h-[calc(100%-32px)] bg-slate-900/95 border border-red-500/30 backdrop-blur-xl rounded-2xl shadow-2xl p-4 z-20 flex flex-col overflow-hidden animate-in fade-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-red-400 font-semibold text-sm">
                <AlertTriangle className="w-4 h-4" />
                <span>Circular Dependency Loops ({cycles.length})</span>
              </div>
              <button
                onClick={() => setShowCyclesDrawer(false)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400 mt-2 mb-3">
              Click a cycle below to highlight the exact loop and dim unrelated modules:
            </p>

            <div className="space-y-2 overflow-y-auto pr-1 flex-1">
              {cycles.map((cycle, idx) => {
                const isSelected = selectedCycleIndex === idx
                return (
                  <div
                    key={idx}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedCycleIndex(null)
                      } else {
                        setSelectedCycleIndex(idx)
                      }
                    }}
                    className={`p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-red-500/20 border-red-500 text-slate-100 shadow-md ring-1 ring-red-500/50'
                        : 'bg-slate-800/60 border-slate-700/80 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center justify-between font-semibold mb-1.5">
                      <span className="text-red-400">Loop #{idx + 1}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {cycle.length - 1} hops
                      </span>
                    </div>
                    <div className="space-y-1 font-mono text-[11px]">
                      {cycle.map((filePath, stepIdx) => (
                        <div key={stepIdx} className="flex items-center gap-1.5 truncate">
                          {stepIdx > 0 && <ArrowRight className="w-3 h-3 text-red-400 shrink-0" />}
                          <span className="truncate text-slate-200" title={filePath}>
                            {filePath.split('/').pop()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>

            {selectedCycleIndex !== null && (
              <button
                onClick={() => setSelectedCycleIndex(null)}
                className="mt-3 w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-medium border border-slate-700 transition-colors"
              >
                Clear Cycle Selection
              </button>
            )}
          </div>
        )}

        {/* Node Inspector Side-Panel */}
        {selectedNode && selectedNodeDetails && (
          <div className="absolute top-4 right-4 w-96 max-h-[calc(100%-32px)] bg-slate-900/95 border border-slate-800 backdrop-blur-xl rounded-2xl shadow-2xl p-4 z-20 flex flex-col overflow-hidden animate-in fade-in slide-in-from-right duration-200">
            {/* Inspector Header */}
            <div className="flex items-start justify-between pb-3 border-b border-slate-800">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${
                      LAYER_CONFIG[selectedNode.layer]?.bgBadge || 'bg-slate-800'
                    } ${LAYER_CONFIG[selectedNode.layer]?.borderBadge || 'border-slate-700'} ${
                      LAYER_CONFIG[selectedNode.layer]?.textBadge || 'text-slate-300'
                    }`}
                  >
                    {selectedNode.layer}
                  </span>
                  <span className="text-xs font-mono text-slate-400">{selectedNode.language}</span>
                </div>
                <h3 className="text-base font-bold text-slate-100 truncate mt-1" title={selectedNode.name}>
                  {selectedNode.name}
                </h3>
                <p className="text-xs text-slate-400 font-mono truncate mt-0.5" title={selectedNode.file_path}>
                  {selectedNode.file_path}
                </p>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 shrink-0"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Node Metrics Grid */}
            <div className="grid grid-cols-2 gap-2 my-3">
              <div className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-800">
                <div className="text-[10px] text-slate-400 font-medium">In-Degree (Used By)</div>
                <div className="text-lg font-bold text-slate-100 font-mono mt-0.5">
                  {selectedNode.metrics.in_degree ?? 0}
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-800">
                <div className="text-[10px] text-slate-400 font-medium">Out-Degree (Imports)</div>
                <div className="text-lg font-bold text-slate-100 font-mono mt-0.5">
                  {selectedNode.metrics.out_degree ?? 0}
                </div>
              </div>
            </div>

            {selectedNode.metrics.is_in_cycle && (
              <div className="mb-3 p-2.5 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-2 text-xs text-red-300">
                <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                <span>This module participates in a circular dependency cycle.</span>
              </div>
            )}

            {/* Scrollable Relationships List */}
            <div className="space-y-4 overflow-y-auto pr-1 flex-1 text-xs">
              {/* Direct Dependencies (Outgoing) */}
              <div>
                <div className="flex items-center justify-between text-slate-300 font-semibold mb-2">
                  <span className="flex items-center gap-1.5">
                    <ArrowRight className="w-3.5 h-3.5 text-primary" />
                    Direct Imports ({selectedNodeDetails.imports.length})
                  </span>
                </div>
                {selectedNodeDetails.imports.length === 0 ? (
                  <p className="text-slate-500 italic text-[11px]">No local imports detected.</p>
                ) : (
                  <div className="space-y-1.5">
                    {selectedNodeDetails.imports.map((dep) => (
                      <div
                        key={dep.id}
                        onClick={() => setSelectedNode(dep)}
                        className="p-2 rounded-lg bg-slate-800/70 border border-slate-700/60 hover:bg-slate-800 hover:border-primary/50 cursor-pointer transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="text-slate-200 font-semibold truncate text-[11px]">{dep.name}</div>
                          <div className="text-slate-400 truncate text-[10px]">{dep.file_path}</div>
                        </div>
                        <span
                          className={`shrink-0 ml-2 px-1.5 py-0.5 rounded text-[9px] font-medium border ${
                            LAYER_CONFIG[dep.layer]?.bgBadge || 'bg-slate-900'
                          } ${LAYER_CONFIG[dep.layer]?.textBadge || 'text-slate-400'}`}
                        >
                          {dep.layer}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Imported By (Incoming) */}
              <div>
                <div className="flex items-center justify-between text-slate-300 font-semibold mb-2">
                  <span className="flex items-center gap-1.5">
                    <GitFork className="w-3.5 h-3.5 text-emerald-400" />
                    Imported By ({selectedNodeDetails.importedBy.length})
                  </span>
                </div>
                {selectedNodeDetails.importedBy.length === 0 ? (
                  <p className="text-slate-500 italic text-[11px]">No modules import this file directly.</p>
                ) : (
                  <div className="space-y-1.5">
                    {selectedNodeDetails.importedBy.map((importer) => (
                      <div
                        key={importer.id}
                        onClick={() => setSelectedNode(importer)}
                        className="p-2 rounded-lg bg-slate-800/70 border border-slate-700/60 hover:bg-slate-800 hover:border-primary/50 cursor-pointer transition-colors flex items-center justify-between"
                      >
                        <div className="min-w-0 flex-1">
                          <div className="text-slate-200 font-semibold truncate text-[11px]">{importer.name}</div>
                          <div className="text-slate-400 truncate text-[10px]">{importer.file_path}</div>
                        </div>
                        <span
                          className={`shrink-0 ml-2 px-1.5 py-0.5 rounded text-[9px] font-medium border ${
                            LAYER_CONFIG[importer.layer]?.bgBadge || 'bg-slate-900'
                          } ${LAYER_CONFIG[importer.layer]?.textBadge || 'text-slate-400'}`}
                        >
                          {importer.layer}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
