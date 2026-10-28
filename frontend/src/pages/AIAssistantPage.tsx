import React, { useState } from 'react';
import {
  Sparkles,
  Send,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  Bot,
  User as UserIcon,
  BookOpen,
} from 'lucide-react';
import { api } from '../services/api';
import type { AIAssistantMessage } from '../types';

export const AIAssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<AIAssistantMessage[]>([
    {
      id: 'msg-initial',
      sender: 'assistant',
      content:
        'Welcome to the PlantProof Regulatory Intelligence & Research Bench. I can cite governing sections of the Factories Act 1948, Water & Air Acts, Indian Boilers Act 1923, and Hazardous Waste Rules 2016 for your Pune facility.',
      timestamp: new Date().toISOString(),
      citations: [
        {
          act: 'The Factories Act, 1948',
          section: 'Section 41G & Chapter IV (Safety)',
          source_url: 'https://dish.maharashtra.gov.in',
        },
      ],
    },
  ]);
  const [input, setInput] = useState<string>('');
  const [querying, setQuerying] = useState<boolean>(false);

  const handleSend = async (queryText?: string) => {
    const text = queryText || input;
    if (!text.trim() || querying) return;

    const userMsg: AIAssistantMessage = {
      id: `msg-${Date.now()}`,
      sender: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setQuerying(true);

    try {
      const response = await api.queryAIAssistant(text.trim(), 'plant-pune-01');
      setMessages((prev) => [...prev, response]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `msg-${Date.now()}`,
          sender: 'assistant',
          content: 'Unable to reach the regulatory inference service. Please check your network connection.',
          timestamp: new Date().toISOString(),
          uncertainty_flag: true,
        },
      ]);
    } finally {
      setQuerying(false);
    }
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: '1200px', margin: '0 auto', height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: '#ecfdf5',
              color: '#059669',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={18} />
          </div>
          <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#0f172a', margin: 0 }}>
            Regulatory Intelligence Assistant
          </h1>
        </div>
        <p style={{ color: '#64748b', fontSize: '13px', margin: 0 }}>
          Direct grounded Q&A with Indian manufacturing statutory codes. Cites official gazette references and flags legal uncertainties.
        </p>
      </div>

      {/* Tenet Alert */}
      <div
        style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #cbd5e1',
          borderLeft: '4px solid #059669',
          borderRadius: '8px',
          padding: '10px 16px',
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '12px',
          color: '#334155',
        }}
      >
        <ShieldCheck size={18} color="#059669" style={{ flexShrink: 0 }} />
        <div>
          <strong>The Cardinal Rule: </strong>
          "AI Proposes, Humans Dispose." Responses provide regulatory pointers with verifiable citations. They do not constitute formal legal guarantees or certifications.
        </div>
      </div>

      {/* Main Chat Container */}
      <div
        style={{
          flex: 1,
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Messages list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {messages.map((msg) => {
            const isUser = msg.sender === 'user';
            return (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                  justifyContent: isUser ? 'flex-end' : 'flex-start',
                }}
              >
                {!isUser && (
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      backgroundColor: '#ecfdf5',
                      color: '#059669',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Bot size={18} />
                  </div>
                )}

                <div style={{ maxWidth: '80%' }}>
                  <div
                    style={{
                      padding: '14px 18px',
                      borderRadius: '12px',
                      fontSize: '13.5px',
                      lineHeight: 1.6,
                      backgroundColor: isUser ? '#059669' : '#f8fafc',
                      color: isUser ? '#ffffff' : '#1e293b',
                      border: isUser ? 'none' : '1px solid #e2e8f0',
                      borderBottomRightRadius: isUser ? '2px' : '12px',
                      borderBottomLeftRadius: isUser ? '12px' : '2px',
                    }}
                  >
                    {msg.content}

                    {/* Uncertainty Banner */}
                    {msg.uncertainty_flag && (
                      <div
                        style={{
                          marginTop: '10px',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#fef2f2',
                          border: '1px solid #fecaca',
                          color: '#991b1b',
                          fontSize: '12px',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '6px',
                        }}
                      >
                        <AlertTriangle size={15} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span>{msg.uncertainty_note || 'Statutory domain out of verified scope or requires legal opinion.'}</span>
                      </div>
                    )}
                  </div>

                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {msg.citations.map((cite, i) => (
                        <a
                          key={i}
                          href={cite.source_url || '#'}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            backgroundColor: '#f1f5f9',
                            border: '1px solid #cbd5e1',
                            fontSize: '11.5px',
                            color: '#059669',
                            textDecoration: 'none',
                            fontWeight: 600,
                          }}
                        >
                          <BookOpen size={12} />
                          <span>{cite.act} • {cite.section}</span>
                          <ExternalLink size={11} />
                        </a>
                      ))}
                    </div>
                  )}

                  <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px', textAlign: isUser ? 'right' : 'left' }}>
                    {new Date(msg.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                {isUser && (
                  <div
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '8px',
                      backgroundColor: '#0f172a',
                      color: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <UserIcon size={16} />
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Suggested Queries */}
        <div style={{ padding: '10px 20px', backgroundColor: '#fafbfc', borderTop: '1px solid #f1f5f9', display: 'flex', gap: '8px', overflowX: 'auto' }}>
          {[
            'Boiler hydraulic testing requirements',
            'MPCB Consent to Operate renewal rules',
            'Hazardous Waste Form 4 deadlines',
            'Is our facility 100% compliant?',
          ].map((prompt, i) => (
            <button
              key={i}
              type="button"
              onClick={() => handleSend(prompt)}
              style={{
                whiteSpace: 'nowrap',
                padding: '5px 12px',
                borderRadius: '9999px',
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                fontSize: '12px',
                color: '#475569',
                cursor: 'pointer',
              }}
              className="table-row-hover"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div style={{ padding: '16px 20px', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            placeholder="Ask questions about state & central manufacturing regulations..."
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '13.5px',
            }}
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || querying}
            className="btn btn-primary"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#059669',
              borderColor: '#059669',
            }}
          >
            <Send size={15} />
            <span>Ask</span>
          </button>
        </div>
      </div>
    </div>
  );
};
