import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Loader2, Paperclip, X, MapPin } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

export default function ChatInterface({ onAgentChange }) {
    const [messages, setMessages] = useState([
        { role: 'agent', content: 'Hello! I am the Triage Agent. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [loadingStatus, setLoadingStatus] = useState('Processing...');
    const [selectedFile, setSelectedFile] = useState(null);
    const [location, setLocation] = useState(null);
    const messagesEndRef = useRef(null);
    const threadIdRef = useRef(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    // Auto-fetch location on mount
    useEffect(() => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    console.log("Auto-fetched location:", latitude, longitude);
                    setLocation({ latitude, longitude });
                },
                (error) => {
                    console.warn("Auto-location fetch failed:", error);
                }
            );
        }
    }, []);

    const handleFileSelect = (e) => {
        const file = e.target.files[0];
        if (file) {
            setSelectedFile(file);
        }
    };

    const clearFile = () => {
        setSelectedFile(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const handleLocationShare = () => {
        if (!navigator.geolocation) {
            alert("Geolocation is not supported by your browser");
            return;
        }

        navigator.geolocation.getCurrentPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                setLocation({ latitude, longitude });
                setMessages(prev => [...prev, { role: 'user', content: `📍 Shared Location` }]);
            },
            (error) => {
                console.error("Error getting location:", error);
                alert("Unable to retrieve your location");
            }
        );
    };

    const sendMessage = async (e) => {
        e.preventDefault();
        if ((!input.trim() && !selectedFile && !location) || isLoading) return;

        let messageContent = input;
        let uploadedFilePath = null;

        // Determine loading status based on input
        const lowerInput = input.toLowerCase();
        if (lowerInput.includes('book') || lowerInput.includes('schedule') || lowerInput.includes('appointment')) {
            setLoadingStatus("Booking appointment...");
        } else if (lowerInput.includes('search') || lowerInput.includes('find') || lowerInput.includes('look') || lowerInput.includes('doctor')) {
            setLoadingStatus("Searching for doctors...");
        } else if (selectedFile) {
            setLoadingStatus("Analyzing document...");
        } else {
            setLoadingStatus("Processing...");
        }

        setIsLoading(true);

        // Optimistic update: Show message immediately
        const displayContent = input.trim() || (selectedFile ? `Sent an image: ${selectedFile.name}` : (location ? `📍 Shared Location` : ''));
        const userMsg = { role: 'user', content: displayContent };
        setMessages(prev => [...prev, userMsg]);

        const originalInput = input; // Keep copy for sending
        setInput('');
        clearFile();

        try {
            // Upload file first if selected
            if (selectedFile) {
                const formData = new FormData();
                formData.append('file', selectedFile);

                const uploadResponse = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (!uploadResponse.ok) {
                    throw new Error('File upload failed');
                }

                const uploadData = await uploadResponse.json();
                uploadedFilePath = uploadData.file_path;
                messageContent += `\n[System: User uploaded file at ${uploadedFilePath}]`;
            }

            if (location) {
                messageContent += `\n\n(Context: My current location is Lat: ${location.latitude}, Lng: ${location.longitude})`;
            }

            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageContent || `(Context: My current location is Lat: ${location?.latitude}, Lng: ${location?.longitude})`,
                    thread_id: threadIdRef.current,
                    latitude: location?.latitude,
                    longitude: location?.longitude
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                buffer += chunk;

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.trim()) continue;

                    try {
                        const data = JSON.parse(line);

                        if (data.type === 'thread_id') {
                            threadIdRef.current = data.thread_id;
                        } else if (data.type === 'agent_event') {
                            if (onAgentChange) onAgentChange(data.agent);
                        } else if (data.type === 'token') {
                            setMessages(prev => {
                                const lastMsg = prev[prev.length - 1];
                                if (lastMsg && lastMsg.role === 'agent') {
                                    return [
                                        ...prev.slice(0, -1),
                                        { ...lastMsg, content: lastMsg.content + data.content }
                                    ];
                                } else {
                                    return [...prev, { role: 'agent', content: data.content }];
                                }
                            });
                        } else if (data.type === 'error') {
                            console.error('Error from server:', data.content);
                            setMessages(prev => [...prev, { role: 'agent', content: `Error: ${data.content}` }]);
                        }
                    } catch (e) {
                        console.error('Error parsing JSON chunk:', e);
                    }
                }
            }
        } catch (error) {
            console.error('Error sending message:', error);
            setMessages(prev => [...prev, { role: 'agent', content: 'Sorry, I encountered an error. Please try again.' }]);
        } finally {
            setIsLoading(false);
        }
    };



    return (
        <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, idx) => {
                    return (
                        <div
                            key={idx}
                            className={cn(
                                "flex gap-3 max-w-[80%]",
                                msg.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
                            )}
                        >
                            <div className={cn(
                                "p-3 rounded-2xl text-sm leading-relaxed",
                                msg.role === 'user'
                                    ? "bg-blue-600 text-white rounded-tr-none"
                                    : "bg-slate-100 text-slate-800 rounded-tl-none"
                            )}>
                                <div className="prose prose-sm max-w-none break-words">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            p: ({ node, ...props }) => <p className="mb-1 last:mb-0" {...props} />,
                                            ul: ({ node, ...props }) => <ul className="list-disc ml-4 mb-2" {...props} />,
                                            ol: ({ node, ...props }) => <ol className="list-decimal ml-4 mb-2" {...props} />,
                                            li: ({ node, ...props }) => <li className="mb-0.5" {...props} />,
                                            strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                                            a: ({ node, href, children, ...props }) => {
                                                const isTicket = href?.includes('/api/tickets');
                                                const isCalendar = href?.includes('/api/calendar');
                                                const isBooking = href?.includes('/book_appointment');
                                                const isMailto = href?.startsWith('mailto:');

                                                if (isMailto) {
                                                    return <span>{children}</span>;
                                                }

                                                if (isBooking) {
                                                    return (
                                                        <button
                                                            onClick={(e) => {
                                                                e.preventDefault();
                                                                const url = new URL(href, window.location.origin);
                                                                const name = url.searchParams.get('name');
                                                                const id = url.searchParams.get('id');

                                                                // Use ID internally but don't show it to user
                                                                const msg = `I would like to book an appointment with ${name}. Please check their availability.`;
                                                                setInput(msg);

                                                                setTimeout(() => {
                                                                    const form = e.target.closest('form');
                                                                    if (form) {
                                                                        form.requestSubmit();
                                                                    } else {
                                                                        const submitBtn = document.querySelector('button[type="submit"]');
                                                                        if (submitBtn) submitBtn.click();
                                                                    }
                                                                }, 100);
                                                            }}
                                                            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium transition-colors my-1 no-underline"
                                                        >
                                                            Book Appointment
                                                        </button>
                                                    );
                                                }

                                                if (isTicket || isCalendar) {
                                                    return (
                                                        <a
                                                            href={href}
                                                            className={cn(
                                                                "inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors my-2 no-underline",
                                                                isTicket ? "bg-blue-600 hover:bg-blue-700" : "bg-emerald-600 hover:bg-emerald-700"
                                                            )}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            {...props}
                                                        >
                                                            {isTicket ? <Paperclip size={16} /> : <Bot size={16} />}
                                                            {children}
                                                        </a>
                                                    );
                                                }

                                                return (
                                                    <a
                                                        href={href}
                                                        className={cn(
                                                            "hover:underline",
                                                            msg.role === 'user' ? "text-white underline" : "text-blue-600"
                                                        )}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        {...props}
                                                    >
                                                        {children}
                                                    </a>
                                                );
                                            },
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    );
                })}
                {isLoading && (
                    <div className="flex gap-3 mr-auto">
                        <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center shrink-0">
                            <Bot size={16} />
                        </div>
                        <div className="bg-slate-100 p-3 rounded-2xl rounded-tl-none flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin text-slate-500" />
                            <span className="text-slate-500 text-sm italic">{loadingStatus}</span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={sendMessage} className="p-4 border-t border-slate-100 bg-slate-50">
                {selectedFile && (
                    <div className="flex items-center gap-2 mb-2 p-2 bg-slate-100 rounded-lg w-fit">
                        <span className="text-xs text-slate-600 truncate max-w-[200px]">{selectedFile.name}</span>
                        <button type="button" onClick={clearFile} className="text-slate-500 hover:text-red-500">
                            <X size={14} />
                        </button>
                    </div>
                )}
                {location && (
                    <div className="flex items-center gap-2 mb-2 p-2 bg-blue-50 text-blue-700 rounded-lg w-fit border border-blue-100">
                        <MapPin size={14} />
                        <span className="text-xs">Location attached</span>
                        <button type="button" onClick={() => setLocation(null)} className="text-blue-500 hover:text-red-500">
                            <X size={14} />
                        </button>
                    </div>
                )}
                <div className="flex gap-2">
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileSelect}
                        className="hidden"
                        accept="image/*"
                    />
                    <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="p-2 text-slate-500 hover:text-blue-600 hover:bg-slate-100 rounded-xl transition-colors"
                        title="Upload Prescription"
                    >
                        <Paperclip size={20} />
                    </button>
                    <button
                        type="button"
                        onClick={handleLocationShare}
                        className={cn(
                            "p-2 rounded-xl transition-colors",
                            location ? "text-blue-600 bg-blue-50" : "text-slate-500 hover:text-blue-600 hover:bg-slate-100"
                        )}
                        title="Share Location"
                    >
                        <MapPin size={20} />
                    </button>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your message..."
                        className="flex-1 px-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                    />
                    <button
                        type="submit"
                        disabled={isLoading || (!input.trim() && !selectedFile && !location)}
                        className="bg-blue-600 text-white p-2 rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </form>
        </div >
    );
}
