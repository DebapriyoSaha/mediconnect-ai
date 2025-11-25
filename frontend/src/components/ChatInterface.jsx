import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export default function ChatInterface({ websocketRef }) {
    const [messages, setMessages] = useState([
        { role: 'agent', content: 'Hello! I am the Triage Agent. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const ws = websocketRef || useRef(null);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Connect to WebSocket
        console.log('Attempting WebSocket connection to wss://healthcare-multi-agent.vercel.app/ws/chat');
        ws.current = new WebSocket('wss://healthcare-multi-agent.vercel.app/ws/chat');

        // console.log('Attempting WebSocket connection to ws://127.0.0.1:8000/ws/chat');
        // ws.current = new WebSocket('ws://127.0.0.1:8000/ws/chat');

        ws.current.onopen = () => {
            console.log('WebSocket connected successfully!');
        };

        ws.current.onmessage = (event) => {
            console.log('Received message:', event.data);
            let message = event.data;

            // Try to parse as JSON in case it's a structured response
            try {
                const parsed = JSON.parse(message);
                console.log('Parsed JSON:', parsed);

                // Skip agent event messages - these are for the graph visualization only
                if (parsed.type === 'agent_event') {
                    console.log('Skipping agent event message');
                    return;
                }

                // If it's an array of content objects, extract the text
                if (Array.isArray(parsed)) {
                    message = parsed.map(item => item.text || '').join('');
                    console.log('Extracted text from array:', message);
                } else if (parsed.text) {
                    message = parsed.text;
                    console.log('Extracted text from object:', message);
                }
            } catch (e) {
                // If not JSON, use the message as-is (it's already a string)
                console.log('Message is plain text, not JSON');
            }

            console.log('Final message to display:', message);
            setMessages(prev => {
                return [...prev, { role: 'agent', content: message }];
            });
            setIsLoading(false);
        };

        ws.current.onerror = (error) => {
            console.error('WebSocket error:', error);
            setIsLoading(false);
        };

        ws.current.onclose = () => {
            console.log('WebSocket disconnected');
        };

        return () => {
            if (ws.current) ws.current.close();
        };
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = (e) => {
        e.preventDefault();
        console.log('Send button clicked, input value:', input);

        if (!input.trim() || isLoading) {
            console.log('Message not sent - input empty or loading:', { input, isLoading });
            return;
        }

        const userMsg = { role: 'user', content: input };
        console.log('Adding user message to UI:', userMsg);
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        console.log('WebSocket readyState:', ws.current?.readyState);
        console.log('WebSocket.OPEN constant:', WebSocket.OPEN);

        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            console.log('Sending message via WebSocket:', userMsg.content);
            ws.current.send(JSON.stringify({ type: 'message', content: userMsg.content }));
        } else {
            console.error('WebSocket not connected, readyState:', ws.current?.readyState);
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={cn(
                            "flex gap-3 max-w-[80%]",
                            msg.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
                        )}
                    >
                        <div className={cn(
                            "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                            msg.role === 'user' ? "bg-blue-600 text-white" : "bg-emerald-600 text-white"
                        )}>
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                        </div>
                        <div className={cn(
                            "p-3 rounded-2xl text-sm leading-relaxed",
                            msg.role === 'user'
                                ? "bg-blue-600 text-white rounded-tr-none"
                                : "bg-slate-100 text-slate-800 rounded-tl-none"
                        )}>
                            {msg.content}
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="flex gap-3 mr-auto">
                        <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0">
                            <Bot size={16} />
                        </div>
                        <div className="bg-slate-100 p-3 rounded-2xl rounded-tl-none flex items-center">
                            <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={sendMessage} className="p-4 border-t border-slate-100 bg-slate-50">
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your message..."
                        className="flex-1 px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </form>
        </div>
    );
}
