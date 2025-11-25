import React, { useRef, useState, useEffect } from 'react';
import ChatInterface from './components/ChatInterface';
import GraphVisualization from './components/GraphVisualization';
import { Activity } from 'lucide-react';

function App() {
    const websocketRef = useRef(null);
    const [websocket, setWebsocket] = useState(null);

    // Update websocket state when ref changes
    useEffect(() => {
        const checkWebSocket = setInterval(() => {
            if (websocketRef.current && websocketRef.current !== websocket) {
                setWebsocket(websocketRef.current);
            }
        }, 500);

        return () => clearInterval(checkWebSocket);
    }, [websocket]);

    return (
        <div className="h-screen bg-slate-50 flex flex-col overflow-hidden">
            <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center gap-3 flex-shrink-0 z-10">
                <div className="bg-blue-600 p-2 rounded-lg">
                    <Activity className="w-6 h-6 text-white" />
                </div>
                <div>
                    <h1 className="text-xl font-bold text-slate-900">Healthcare Agent</h1>
                    <p className="text-sm text-slate-500">Intelligent Multi-Agent Support</p>
                </div>
            </header>

            <main className="flex-1 w-full p-4 md:p-6 overflow-hidden">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
                    {/* Left side - Graph */}
                    <div className="flex flex-col h-full overflow-hidden bg-white rounded-2xl shadow-sm border border-slate-200">
                        <div className="p-4 border-b border-slate-100 flex-shrink-0">
                            <h2 className="text-lg font-semibold text-slate-800">Agent Graph</h2>
                        </div>
                        <div className="flex-1 min-h-0 relative">
                            <GraphVisualization websocket={websocket} />
                        </div>
                    </div>

                    {/* Right side - Chat */}
                    <div className="flex flex-col h-full overflow-hidden bg-white rounded-2xl shadow-sm border border-slate-200">
                        <div className="p-4 border-b border-slate-100 flex-shrink-0">
                            <h2 className="text-lg font-semibold text-slate-800">Chat</h2>
                        </div>
                        <div className="flex-1 min-h-0 overflow-y-auto">
                            <ChatInterface websocketRef={websocketRef} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

export default App;
