import React, { useCallback, useState, useMemo } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow';
import type {
  Node,
  Connection,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Plus, Trash2, Save, X } from 'lucide-react';
import { Button } from '@/shared/ui/Button';
import type { CurriculumNode, CurriculumGraph, CurriculumResource } from '@/types/faculty';

interface CurriculumGraphBuilderProps {
  graph: CurriculumGraph | null;
  onSave: (graph: CurriculumGraph) => void;
}

interface NodeData {
  label: string;
  title: string;
  description?: string;
  resources: CurriculumResource[];
  difficulty?: string;
}

// Custom node component
const CurriculumNodeComponent: React.FC<any> = ({ data, selected }) => {
  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 transition-all ${
        selected
          ? 'border-indigo-500 bg-indigo-50 shadow-lg'
          : 'border-slate-300 bg-white shadow-sm hover:shadow-md'
      }`}
      style={{ minWidth: '180px' }}
    >
      <div className="font-semibold text-slate-900 text-sm">{data.title}</div>
      {data.difficulty && (
        <span className={`inline-block text-xs mt-1 px-2 py-0.5 rounded-full ${
          data.difficulty === 'beginner'
            ? 'bg-green-100 text-green-800'
            : data.difficulty === 'intermediate'
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-red-100 text-red-800'
        }`}>
          {data.difficulty}
        </span>
      )}
      {data.resources.length > 0 && (
        <div className="mt-2 text-xs text-slate-600 flex gap-1">
          📎 {data.resources.length} resource{data.resources.length !== 1 ? 's' : ''}
        </div>
      )}
    </div>
  );
};

const CurriculumGraphBuilderInternal: React.FC<CurriculumGraphBuilderProps> = ({
  graph,
  onSave,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [showResourceModal, setShowResourceModal] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [graphTitle, setGraphTitle] = useState(graph?.title || '');
  
  const [nodeForm, setNodeForm] = useState<CurriculumNode>({
    id: `node-${Date.now()}`, title: '', description: '', resources: [], difficulty: 'beginner', estimatedHours: 1,
  });
  
  const [resourceForm, setResourceForm] = useState<CurriculumResource>({
    id: `resource-${Date.now()}`, title: '', type: 'pdf', uri: '', createdAt: new Date().toISOString(),
  });

  const { getNode } = useReactFlow();

  // FIX: Memoize nodeTypes to prevent the React Flow re-render warning
  const nodeTypes = useMemo<NodeTypes>(() => ({ curriculum: CurriculumNodeComponent }), []);

  const onConnect = useCallback((connection: Connection) => {
    setEdges((eds) => addEdge(connection, eds));
  }, [setEdges]);

  const handleAddNode = () => {
    if (!nodeForm.title.trim()) {
      alert('Please enter a node title');
      return;
    }

    const newNode: Node<NodeData> = {
      id: nodeForm.id,
      data: {
        label: nodeForm.title,
        title: nodeForm.title,
        description: nodeForm.description,
        resources: nodeForm.resources,
        difficulty: nodeForm.difficulty,
      },
      position: { x: Math.random() * 800, y: Math.random() * 600 },
      type: 'curriculum',
    };

    setNodes((nds) => [...nds, newNode]);
    setNodeForm({
      id: `node-${Date.now()}`,
      title: '',
      description: '',
      resources: [],
      difficulty: 'beginner',
      estimatedHours: 1,
    });
    setShowNodeModal(false);
  };

  const handleAddResource = () => {
    if (!resourceForm.title.trim() || !resourceForm.uri.trim()) {
      alert('Please fill in all resource fields');
      return;
    }

    setNodeForm((prev) => ({
      ...prev,
      resources: [...prev.resources, { ...resourceForm, id: `resource-${Date.now()}` }],
    }));

    setResourceForm({
      id: `resource-${Date.now()}`,
      title: '',
      type: 'pdf',
      uri: '',
      createdAt: new Date().toISOString(),
    });
  };

  const handleDeleteNode = (nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) =>
      eds.filter((e) => e.source !== nodeId && e.target !== nodeId)
    );
    setSelectedNode(null);
  };

  const handleSaveGraph = () => {
    if (!graphTitle.trim()) {
      alert('Please enter a curriculum graph title');
      return;
    }

    if (nodes.length === 0) {
      alert('Please add at least one node to the curriculum');
      return;
    }

    const curriculumNodes: CurriculumNode[] = nodes.map((node) => ({
      id: node.id,
      title: (node.data as NodeData).title,
      description: (node.data as NodeData).description,
      resources: (node.data as NodeData).resources,
      difficulty: (node.data as NodeData).difficulty as any,
    }));

    const savedGraph: CurriculumGraph = {
      id: graph?.id || `graph-${Date.now()}`,
      title: graphTitle,
      nodes: curriculumNodes,
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
      })),
      createdAt: graph?.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    onSave(savedGraph);
  };

  return (
    <div className="flex h-screen bg-slate-50">
      {/* React Flow Canvas */}
      <div className="flex-1 flex flex-col">
        <div className="bg-white border-b border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Curriculum Graph Title
              </label>
              <input
                type="text"
                value={graphTitle}
                onChange={(e) => setGraphTitle(e.target.value)}
                placeholder="e.g., Advanced Computer Science Track"
                className="w-full max-w-md px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <Button onClick={handleSaveGraph} size="sm">
              <Save className="w-4 h-4 mr-2" />
              Save Graph
            </Button>
          </div>
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          onNodeClick={(_event, node) => setSelectedNode(node.id)}
          deleteKeyCode={['Backspace']}
          onNodesDelete={(deleted) => {
            deleted.forEach((node) => {
              setEdges((eds) =>
                eds.filter((e) => e.source !== node.id && e.target !== node.id)
              );
            });
          }}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>

      {/* Control Panel */}
      <div className="w-96 bg-white border-l border-slate-200 shadow-lg flex flex-col">
        {/* Add Node Section */}
        <div className="border-b border-slate-200 p-4">
          <h3 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Add Node
          </h3>

          {!showNodeModal ? (
            <Button
              onClick={() => setShowNodeModal(true)}
              className="w-full"
              variant="outline"
            >
              Create New Node
            </Button>
          ) : (
            // FIX: Changed <form> to <div> to prevent implicit submission disconnections
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={nodeForm.title}
                  onChange={(e) => setNodeForm({ ...nodeForm, title: e.target.value })}
                  placeholder="e.g., Data Structures"
                  className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Description
                </label>
                <textarea
                  value={nodeForm.description || ''}
                  onChange={(e) => setNodeForm({ ...nodeForm, description: e.target.value })}
                  placeholder="Node description"
                  rows={2}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Difficulty
                  </label>
                  <select
                    value={nodeForm.difficulty || 'beginner'}
                    onChange={(e) => setNodeForm({ ...nodeForm, difficulty: e.target.value as any })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Hours
                  </label>
                  <input
                    type="number"
                    value={nodeForm.estimatedHours || 1}
                    onChange={(e) => setNodeForm({ ...nodeForm, estimatedHours: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Resources Section */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-semibold text-slate-700">Resources</h4>
                  <button
                    type="button"
                    onClick={() => setShowResourceModal(true)}
                    className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                  >
                    + Add
                  </button>
                </div>

                {showResourceModal && (
                  <div className="bg-slate-50 p-3 rounded-md space-y-2 mb-2">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Resource Title *
                      </label>
                      <input
                        type="text"
                        value={resourceForm.title}
                        onChange={(e) => setResourceForm({ ...resourceForm, title: e.target.value })}
                        placeholder="e.g., Lecture Slides"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Type
                      </label>
                      <select
                        value={resourceForm.type}
                        onChange={(e) => setResourceForm({ ...resourceForm, type: e.target.value as any })}
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="pdf">PDF</option>
                        <option value="video">Video</option>
                        <option value="link">Link</option>
                        <option value="quiz">Quiz</option>
                        <option value="assignment">Assignment</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        URI *
                      </label>
                      <input
                        type="text"
                        value={resourceForm.uri}
                        onChange={(e) => setResourceForm({ ...resourceForm, uri: e.target.value })}
                        placeholder="https://example.com/resource"
                        className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div className="flex gap-2">
                      <Button onClick={handleAddResource} size="sm" className="flex-1">
                        Add
                      </Button>
                      <Button
                        onClick={() => setShowResourceModal(false)}
                        size="sm"
                        variant="outline"
                        className="flex-1"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}

                <div className="space-y-1">
                  {nodeForm.resources.map((resource) => (
                    <div
                      key={resource.id}
                      className="flex items-center justify-between bg-slate-50 p-2 rounded text-xs"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-slate-900 truncate">{resource.title}</p>
                        <p className="text-slate-500">📦 {resource.type}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setNodeForm({
                            ...nodeForm,
                            resources: nodeForm.resources.filter((r) => r.id !== resource.id),
                          });
                        }}
                        className="ml-1 p-1 hover:bg-red-100 rounded"
                      >
                        <X className="w-3 h-3 text-red-600" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button onClick={handleAddNode} className="flex-1" size="sm">
                  Add Node
                </Button>
                <Button
                  onClick={() => setShowNodeModal(false)}
                  variant="outline"
                  size="sm"
                  className="flex-1"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Selected Node Details */}
        {selectedNode && (
          <div className="flex-1 p-4 overflow-y-auto border-b border-slate-200">
            <h4 className="font-semibold text-slate-900 mb-3">Node Details</h4>
            {selectedNode && (
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium text-slate-700 mb-1">Title</p>
                  <p className="text-sm text-slate-900">
                    {getNode(selectedNode)?.data?.title}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-700 mb-1">Difficulty</p>
                  <p className="text-sm text-slate-900">
                    {getNode(selectedNode)?.data?.difficulty}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-slate-700 mb-3">Resources</p>
                  {(getNode(selectedNode)?.data?.resources || []).length > 0 ? (
                    <div className="space-y-2">
                      {(getNode(selectedNode)?.data?.resources || []).map((r: any) => (
                        <div key={r.id} className="bg-slate-50 p-2 rounded text-xs">
                          <p className="font-medium text-slate-900">{r.title}</p>
                          <p className="text-slate-600 truncate">{r.uri}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-500">No resources attached</p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Delete Node Button */}
        {selectedNode && (
          <div className="bg-red-50 border-t border-red-200 p-4">
            <Button
              onClick={() => handleDeleteNode(selectedNode)}
              variant="destructive"
              className="w-full"
              size="sm"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Delete Node
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

// Export a Wrapper component that provides the context
export const CurriculumGraphBuilder: React.FC<CurriculumGraphBuilderProps> = (props) => {
  return (
    <ReactFlowProvider>
      <CurriculumGraphBuilderInternal {...props} />
    </ReactFlowProvider>
  );
};
