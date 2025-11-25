import React, { useEffect, useState, useRef } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    MarkerType,
    Position,
    Handle
} from 'reactflow';
import 'reactflow/dist/style.css';

// Custom node with multiple handles for better edge separation
const CustomNode = ({ data }) => {
    return (
        <div style={data.style}>
            <Handle type="target" position={Position.Top} id="top" style={{ opacity: 0 }} />
            <Handle type="target" position={Position.Left} id="left" style={{ opacity: 0 }} />
            <Handle type="target" position={Position.Right} id="right" style={{ opacity: 0 }} />
            {data.label}
            <Handle type="source" position={Position.Bottom} id="bottom" style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Left} id="left-source" style={{ opacity: 0 }} />
            <Handle type="source" position={Position.Right} id="right-source" style={{ opacity: 0 }} />
            <Handle type="target" position={Position.Bottom} id="bottom-target" style={{ opacity: 0 }} />
        </div>
    );
};

const nodeTypes = {
    custom: CustomNode
};

const GraphVisualization = ({ activeAgent }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [previousAgent, setPreviousAgent] = useState(null);
    const currentAgentRef = useRef(activeAgent);

    useEffect(() => {
        if (currentAgentRef.current !== activeAgent) {
            console.log(`Transition: ${currentAgentRef.current} -> ${activeAgent}`);
            setPreviousAgent(currentAgentRef.current);
            currentAgentRef.current = activeAgent;
        }
    }, [activeAgent]);

    useEffect(() => {
        const fetchGraph = async () => {
            try {
                const response = await fetch('/graph');
                const data = await response.json();

                const positions = {
                    'Triage': { x: 350, y: 50 },
                    'Clinical': { x: 100, y: 300 },
                    'Appointment': { x: 600, y: 300 },
                    'Billing': { x: 350, y: 550 }
                };

                const icons = {
                    'Triage': '🏥',
                    'Clinical': '⚕️',
                    'Appointment': '📅',
                    'Billing': '💰'
                };

                const graphNodes = data.nodes.map((node) => ({
                    id: node.id,
                    type: 'custom',
                    data: {
                        label: (
                            <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                                <div style={{ fontSize: '36px', lineHeight: '1', marginBottom: '4px' }}>{icons[node.id]}</div>
                                <div style={{ fontWeight: '700', fontSize: '16px', letterSpacing: '0.3px' }}>{node.label}</div>
                                <div style={{ fontSize: '11px', opacity: 0.9, fontWeight: '500' }}>{node.role}</div>
                            </div>
                        ),
                        style: {
                            background: `linear-gradient(135deg, ${node.color}dd 0%, ${node.color} 50%, ${adjustColor(node.color, -20)} 100%)`,
                            color: 'white',
                            border: '3px solid rgba(255,255,255,0.6)',
                            borderRadius: '20px',
                            padding: '24px',
                            width: 220,
                            boxShadow: '0 20px 40px rgba(0,0,0,0.15), 0 10px 20px rgba(0,0,0,0.1), inset 0 -2px 10px rgba(0,0,0,0.1), inset 0 2px 10px rgba(255,255,255,0.2)',
                            backdropFilter: 'blur(10px)'
                        }
                    },
                    position: positions[node.id]
                }));

                // Use specific handles for ZERO overlapping - edges go around each other
                const graphEdges = [
                    // Triage connections (Top down)
                    { source: 'Triage', target: 'Clinical', label: 'Symptoms', sourceHandle: 'left-source', targetHandle: 'top' },
                    { source: 'Triage', target: 'Appointment', label: 'Booking', sourceHandle: 'right-source', targetHandle: 'top' },
                    { source: 'Triage', target: 'Billing', label: 'Billing', sourceHandle: 'bottom', targetHandle: 'top' },

                    // Clinical <-> Appointment (Horizontal across)
                    { source: 'Clinical', target: 'Appointment', label: 'Book', sourceHandle: 'right-source', targetHandle: 'left' },
                    { source: 'Appointment', target: 'Clinical', label: 'Health', sourceHandle: 'left-source', targetHandle: 'right' },

                    // Clinical <-> Billing (Left side)
                    { source: 'Clinical', target: 'Billing', label: 'Bill', sourceHandle: 'right-source', targetHandle: 'top' },
                    { source: 'Billing', target: 'Clinical', label: 'Check', sourceHandle: 'left-source', targetHandle: 'bottom-target' },

                    // Appointment <-> Billing (Right side)
                    { source: 'Appointment', target: 'Billing', label: 'Pay', sourceHandle: 'left-source', targetHandle: 'top' },
                    { source: 'Billing', target: 'Appointment', label: 'Schedule', sourceHandle: 'right-source', targetHandle: 'bottom-target' },

                    // Billing -> Triage (Return path - Outer curve)
                    { source: 'Billing', target: 'Triage', label: 'Other', sourceHandle: 'right-source', targetHandle: 'right' }
                ].map((edge, index) => ({
                    id: `e${index}`,
                    source: edge.source,
                    target: edge.target,
                    sourceHandle: edge.sourceHandle,
                    targetHandle: edge.targetHandle,
                    label: edge.label,
                    type: 'smoothstep',
                    animated: false,
                    markerEnd: {
                        type: MarkerType.ArrowClosed,
                        width: 20,
                        height: 20,
                        color: '#94a3b8'
                    },
                    style: {
                        stroke: '#cbd5e1',
                        strokeWidth: 3,
                        opacity: 0.6
                    },
                    labelStyle: {
                        fontSize: '11px',
                        fontWeight: '600',
                        fill: '#475569'
                    },
                    labelBgPadding: [8, 4],
                    labelBgBorderRadius: 6,
                    labelBgStyle: {
                        fill: 'white',
                        stroke: '#e2e8f0',
                        strokeWidth: 1.5
                    }
                }));

                setNodes(graphNodes);
                setEdges(graphEdges);
                // setActiveAgent(data.default_agent); // Controlled by parent now
            } catch (error) {
                console.error('Error fetching graph:', error);
            }
        };

        fetchGraph();
    }, []);

    // Update nodes and edges when activeAgent changes
    useEffect(() => {
        // Highlight active node
        setNodes((nds) =>
            nds.map((node) => {
                const isActive = node.id === activeAgent;
                return {
                    ...node,
                    data: {
                        ...node.data,
                        style: {
                            ...node.data.style,
                            border: isActive ? '3px solid #7C3AED' : '3px solid rgba(255,255,255,0.6)',
                            boxShadow: isActive ? '0 0 20px rgba(124, 58, 237, 0.5)' : '0 20px 40px rgba(0,0,0,0.15), 0 10px 20px rgba(0,0,0,0.1), inset 0 -2px 10px rgba(0,0,0,0.1), inset 0 2px 10px rgba(255,255,255,0.2)',
                            transform: isActive ? 'scale(1.05)' : 'scale(1)',
                            transition: 'all 0.3s ease',
                            zIndex: isActive ? 10 : 1
                        }
                    }
                };
            })
        );

        // Highlight ONLY the LATEST TRANSITION edge
        setEdges((eds) =>
            eds.map((edge) => {
                const isLatestTransition = previousAgent && activeAgent &&
                    edge.source === previousAgent &&
                    edge.target === activeAgent;

                return {
                    ...edge,
                    animated: isLatestTransition,
                    style: {
                        ...edge.style,
                        stroke: isLatestTransition ? '#7C3AED' : '#cbd5e1',
                        strokeWidth: isLatestTransition ? 4 : 1.5,
                        opacity: isLatestTransition ? 1 : 0.3,
                        strokeDasharray: isLatestTransition ? 'none' : '5 5',
                        zIndex: isLatestTransition ? 20 : 0,
                        filter: isLatestTransition ? 'drop-shadow(0 0 8px #7C3AED)' : 'none'
                    },
                    markerEnd: {
                        ...edge.markerEnd,
                        color: isLatestTransition ? '#7C3AED' : '#94a3b8'
                    },
                    labelStyle: {
                        ...edge.labelStyle,
                        fill: isLatestTransition ? '#7C3AED' : '#475569',
                        fontWeight: isLatestTransition ? '700' : '600',
                        fontSize: isLatestTransition ? '14px' : '11px'
                    }
                };
            })
        );
    }, [activeAgent, previousAgent, setNodes, setEdges]);
    return (
        <div style={{
            width: '100%',
            height: '100%',
            background: 'radial-gradient(circle at 20% 20%, rgba(59, 130, 246, 0.08) 0%, transparent 50%), radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.08) 0%, transparent 50%), linear-gradient(to bottom right, #f8fafc, #f1f5f9)',
            borderRadius: '20px',
            overflow: 'hidden',
            border: '1px solid rgba(226, 232, 240, 0.8)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)'
        }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.12 }}
                minZoom={0.5}
                maxZoom={1.8}
            >
                <Background color="#cbd5e1" gap={28} size={2} variant="dots" style={{ opacity: 0.25 }} />
                <Controls style={{ borderRadius: '12px', boxShadow: '0 8px 20px rgba(0,0,0,0.12)', border: '1px solid #e2e8f0' }} />
                <MiniMap
                    nodeColor={(node) => ({ 'Triage': '#3B82F6', 'Clinical': '#10B981', 'Appointment': '#8B5CF6', 'Billing': '#F59E0B' }[node.id] || '#64748b')}
                    style={{ background: 'white', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 8px 20px rgba(0,0,0,0.12)' }}
                    masColor="rgba(248, 250, 252, 0.85)"
                />
            </ReactFlow>
            <style>{`
                .react-flow__node { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
                .react-flow__edge-text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
                .react-flow__edge.animated .react-flow__edge-path {
                    stroke-dasharray: 5;
                    animation: dashdraw 0.5s linear infinite;
                }
                @keyframes dashdraw {
                    from { stroke-dashoffset: 10; }
                    to { stroke-dashoffset: 0; }
                }
            `}</style>
        </div >
    );
};

function adjustColor(color, amount) {
    return '#' + color.replace(/^#/, '').replace(/../g, color =>
        ('0' + Math.min(255, Math.max(0, parseInt(color, 16) + amount)).toString(16)).substr(-2)
    );
}

export default GraphVisualization;
