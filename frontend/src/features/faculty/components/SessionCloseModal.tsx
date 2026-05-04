/**
 * SessionCloseModal
 * ==================
 * Intercepts the "End Session" action and presents the faculty with an
 * interactive React Flow checklist of the curriculum graph nodes.
 *
 * Node visual states (three-tier visual triage):
 *   completed  — Green fill, ✓ badge. Node was already marked done before this session.
 *   selected   — Indigo fill, pulsing ring, ● indicator. Faculty just selected it as covered today.
 *   locked     — Slate/white card, dashed border, 🔒 icon. Not yet taught.
 *
 * On "End Class & Sync":
 *   → POST /api/curriculum/session/close  { session_id, node_ids: [...selectedIds] }
 *   → success → onConfirm()  (caller removes session from active list)
 *   → error   → toast.error, modal stays open for retry
 */

import React, { useCallback, useMemo, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { CheckCircle2, Lock, Circle, Loader2, X, BookOpen, Users } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import { apiClient } from '@/lib/api';
import type { CurriculumGraph, SessionClosePayload, SessionCloseResponse } from '@/types/faculty';

// ---------------------------------------------------------------------------
// Node state types
// ---------------------------------------------------------------------------

type NodeState = 'completed' | 'selected' | 'locked';

interface ChecklistNodeData {
  title: string;
  difficulty?: string;
  nodeState: NodeState;
  onToggle: (id: string, currentState: NodeState) => void;
}

// ---------------------------------------------------------------------------
// Custom checklist node component
// ---------------------------------------------------------------------------

const SessionChecklistNode: React.FC<{ id: string; data: ChecklistNodeData }> = ({
  id,
  data,
}) => {
  const { title, difficulty, nodeState, onToggle } = data;

  const isClickable = nodeState !== 'completed';

  const stateStyles: Record<NodeState, string> = {
    completed:
      'bg-emerald-500 border-emerald-600 text-white shadow-emerald-200 shadow-md cursor-default',
    selected:
      'bg-indigo-600 border-indigo-700 text-white shadow-indigo-200 shadow-lg ring-4 ring-indigo-300 ring-offset-1 cursor-pointer',
    locked:
      'bg-white border-dashed border-slate-300 text-slate-700 shadow-sm hover:border-slate-400 hover:shadow-md cursor-pointer',
  };

  const difficultyPill: Record<string, string> = {
    beginner: 'bg-green-100 text-green-800',
    intermediate: 'bg-yellow-100 text-yellow-800',
    advanced: 'bg-red-100 text-red-800',
  };

  return (
    <div
      className={`px-4 py-3 rounded-xl border-2 transition-all duration-200 select-none ${stateStyles[nodeState]}`}
      style={{ minWidth: '190px' }}
      onClick={() => isClickable && onToggle(id, nodeState)}
      role={isClickable ? 'checkbox' : undefined}
      aria-checked={nodeState === 'selected'}
    >
      {/* Status icon + title row */}
      <div className="flex items-start gap-2">
        <div className="flex-shrink-0 mt-0.5">
          {nodeState === 'completed' && (
            <CheckCircle2 className="h-4 w-4 text-white drop-shadow" />
          )}
          {nodeState === 'selected' && (
            <Circle className="h-4 w-4 text-white fill-white" />
          )}
          {nodeState === 'locked' && (
            <Lock className="h-4 w-4 text-slate-400" />
          )}
        </div>
        <span
          className={`font-semibold text-sm leading-tight ${
            nodeState === 'locked' ? 'text-slate-800' : 'text-white'
          }`}
        >
          {title}
        </span>
      </div>

      {/* Difficulty badge */}
      {difficulty && (
        <div className="mt-2 ml-6">
          <span
            className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
              nodeState !== 'locked'
                ? 'bg-white/20 text-white'
                : (difficultyPill[difficulty] ?? 'bg-slate-100 text-slate-700')
            }`}
          >
            {difficulty}
          </span>
        </div>
      )}

      {/* Selection hint for locked nodes */}
      {nodeState === 'locked' && (
        <p className="mt-2 ml-6 text-xs text-slate-400 italic">Click to mark covered</p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Internal graph component (needs ReactFlowProvider above it)
// ---------------------------------------------------------------------------

interface ChecklistGraphProps {
  graph: CurriculumGraph;
  preCompletedNodeIds: Set<string>;
  onSelectionChange: (selectedIds: Set<string>) => void;
}

const ChecklistGraph: React.FC<ChecklistGraphProps> = ({
  graph,
  preCompletedNodeIds,
  onSelectionChange,
}) => {
  // Track which nodes faculty selected this session
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const handleToggle = useCallback(
    (id: string, currentState: NodeState) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (currentState === 'selected') {
          next.delete(id);
        } else {
          next.add(id);
        }
        onSelectionChange(next);
        return next;
      });
    },
    [onSelectionChange],
  );

  const getNodeState = useCallback(
    (id: string): NodeState => {
      if (preCompletedNodeIds.has(id)) return 'completed';
      if (selectedIds.has(id)) return 'selected';
      return 'locked';
    },
    [preCompletedNodeIds, selectedIds],
  );

  // Build React Flow nodes from the curriculum graph
  const initialNodes: Node<ChecklistNodeData>[] = useMemo(() => {
    const cols = 3;
    const xGap = 260;
    const yGap = 160;
    return graph.nodes.map((node, idx) => ({
      id: node.id,
      type: 'sessionChecklist',
      position: {
        x: (idx % cols) * xGap + 40,
        y: Math.floor(idx / cols) * yGap + 40,
      },
      data: {
        title: node.title,
        difficulty: node.difficulty,
        nodeState: getNodeState(node.id),
        onToggle: handleToggle,
      },
      // Prevent drag — this is a checklist, not a builder
      draggable: false,
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph.nodes]);

  const initialEdges = useMemo(
    () =>
      graph.edges.map((e, idx) => ({
        id: `e-${idx}-${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        animated: false,
        style: { stroke: '#cbd5e1', strokeWidth: 2 },
      })),
    [graph.edges],
  );

  // Rebuild nodes whenever selection changes (to re-render nodeState colour)
  const liveNodes: Node<ChecklistNodeData>[] = useMemo(
    () =>
      initialNodes.map((n) => ({
        ...n,
        data: {
          ...n.data,
          nodeState: getNodeState(n.id),
          onToggle: handleToggle,
        },
      })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [selectedIds, initialNodes, handleToggle],
  );

  const [nodes, , onNodesChange] = useNodesState(liveNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // Sync liveNodes → React Flow state whenever selection changes
  const stableNodes = useMemo(() => {
    return nodes.map((n) => ({
      ...n,
      data: {
        ...n.data,
        nodeState: getNodeState(n.id),
        onToggle: handleToggle,
      },
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedIds, handleToggle]);

  const nodeTypes = useMemo<NodeTypes>(
    () => ({ sessionChecklist: SessionChecklistNode }),
    [],
  );

  return (
    <ReactFlow
      nodes={stableNodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnDrag
      zoomOnScroll
    >
      <Background color="#e2e8f0" gap={20} />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface SessionCloseModalProps {
  sessionId: string;
  /** The full curriculum graph to render as the checklist */
  graph: CurriculumGraph;
  /** Node IDs already marked completed before this session */
  preCompletedNodeIds?: string[];
  isOpen: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

// ---------------------------------------------------------------------------
// Main Modal (public export)
// ---------------------------------------------------------------------------

export const SessionCloseModal: React.FC<SessionCloseModalProps> = ({
  sessionId,
  graph,
  preCompletedNodeIds = [],
  isOpen,
  onCancel,
  onConfirm,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const preCompletedSet = useMemo(
    () => new Set(preCompletedNodeIds),
    [preCompletedNodeIds],
  );

  const mutation = useMutation<SessionCloseResponse, Error, SessionClosePayload>({
    mutationFn: async (payload) => {
      const res = await apiClient.post<SessionCloseResponse>(
        '/curriculum/session/close',
        payload,
      );
      return res.data;
    },
    onSuccess: (data) => {
      toast.success('Session closed & curriculum synced', {
        description: `${data.nodes_completed} node(s) marked complete. ${data.absent_students} absent student(s) queued for risk update.`,
        duration: 6_000,
      });
      onConfirm();
    },
    onError: (err) => {
      toast.error('Failed to sync curriculum', {
        description: err.message ?? 'Please try again.',
        duration: 8_000,
      });
    },
  });

  const handleSync = () => {
    mutation.mutate({
      session_id: sessionId,
      node_ids: Array.from(selectedIds),
      graph_id: graph.id,
    });
  };

  const totalCovered = preCompletedNodeIds.length + selectedIds.size;
  const canSync = selectedIds.size > 0 || preCompletedNodeIds.length > 0;

  if (!isOpen) return null;

  return (
    // Portal-style fullscreen overlay with frosted-glass backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="session-close-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal panel */}
      <div className="relative z-10 w-full max-w-5xl h-[90vh] flex flex-col bg-white rounded-2xl shadow-2xl overflow-hidden">

        {/* ── Header ── */}
        <div className="flex items-center justify-between px-6 py-4 bg-gradient-to-r from-indigo-700 to-indigo-600 text-white flex-shrink-0">
          <div>
            <h2
              id="session-close-title"
              className="text-xl font-bold flex items-center gap-2"
            >
              <BookOpen className="h-5 w-5" />
              End Class & Sync Curriculum
            </h2>
            <p className="text-indigo-200 text-sm mt-0.5">
              Select the topics you covered today. Absent students will be flagged automatically.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="Cancel and keep session active"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Legend ── */}
        <div className="flex items-center gap-6 px-6 py-3 bg-slate-50 border-b border-slate-200 flex-shrink-0 flex-wrap">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
            Legend
          </span>
          <LegendItem color="bg-emerald-500" label="Already Completed" />
          <LegendItem color="bg-indigo-600 ring-2 ring-indigo-300" label="Selected (covered today)" />
          <LegendItem color="bg-white border-dashed border-2 border-slate-300" label="Not Yet Taught" />
          <div className="ml-auto flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1.5 text-slate-600">
              <Circle className="h-4 w-4 text-indigo-500 fill-indigo-500" />
              <span className="font-semibold text-indigo-700">{selectedIds.size}</span> selected
            </span>
            <span className="flex items-center gap-1.5 text-slate-600">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span className="font-semibold text-emerald-700">{preCompletedNodeIds.length}</span> prev. done
            </span>
            <span className="text-slate-400">|</span>
            <span className="text-slate-500">{graph.nodes.length} total nodes</span>
          </div>
        </div>

        {/* ── Graph Canvas ── */}
        <div className="flex-1 min-h-0">
          <ReactFlowProvider>
            <ChecklistGraph
              graph={graph}
              preCompletedNodeIds={preCompletedSet}
              onSelectionChange={setSelectedIds}
            />
          </ReactFlowProvider>
        </div>

        {/* ── Footer / Action Bar ── */}
        <div className="flex items-center justify-between gap-4 px-6 py-4 bg-white border-t border-slate-200 flex-shrink-0">
          {/* Summary */}
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Users className="h-4 w-4 text-slate-400" />
            <span>
              Closing session{' '}
              <span className="font-mono text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-700">
                {sessionId.slice(0, 16)}…
              </span>
            </span>
            {totalCovered > 0 && (
              <span className="text-indigo-600 font-medium">
                {totalCovered} node{totalCovered !== 1 ? 's' : ''} will be marked complete
              </span>
            )}
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={mutation.isPending}
            >
              Keep Session Active
            </Button>

            <Button
              onClick={handleSync}
              disabled={!canSync || mutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 text-white min-w-[180px]"
            >
              {mutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Syncing…
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4 mr-2" />
                  End Class & Sync
                </>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Small legend helper
// ---------------------------------------------------------------------------

const LegendItem: React.FC<{ color: string; label: string }> = ({ color, label }) => (
  <div className="flex items-center gap-2">
    <div className={`h-4 w-4 rounded-sm ${color}`} />
    <span className="text-xs text-slate-600">{label}</span>
  </div>
);
