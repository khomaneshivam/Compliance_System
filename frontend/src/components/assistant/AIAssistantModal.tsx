import React, { useState } from 'react';
import {
  Sparkles,
  Send,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  X,
  Bot,
  User as UserIcon,
  BookOpen,
} from 'lucide-react';
import { api } from '../../services/api';
import type { AIAssistantMessage } from '../../types';

interface AIAssistantModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AIAssistantModal: React.FC<AIAssistantModalProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<AIAssistantMessage[]>([
    {
      id: 'msg-initial',
      sender: 'assistant',
      content:
        'Hello! I am the PlantProof Regulatory Intelligence Assistant. You can ask me about Central and Maharashtra statutory requirements (MPCB, DISH, PESO, CPCB), renewal windows, or gazette amendment impacts for Acme Pune Plant.',
      timestamp: new Date().toISOString(),
      citations: [
        {
          act: 'The Factories Act, 1948',
          section: 'Statutory Safety & Licensing Framework',
          source_url: 'https://dish.maharashtra.gov.in',
        },
      ],
    },
  ]);
  const [input, setInput] = useState<string>('');
  const [querying, setQuerying] = useState<boolean>(false);

  if (!isOpen) return null;

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
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.55)',
        backdropFilter: 'blur(3px)',
        zIndex: 1200,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          height: '620px',
          backgroundColor: '#ffffff',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          border: '1px solid #cbd5e1',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: '#06281e',
            color: '#ffffff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid #1e3a30',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(52, 211, 153, 0.2)',
                color: '#34d399',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                PlantProof Regulatory Assistant
              </h2>
              <div style={{ fontSize: '11px', color: '#a7f3d0' }}>
                Grounded in Official Indian Statutory Codes • "AI Proposes, Humans Dispose"
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#ffffff', cursor: 'pointer' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Cardinal Tenet Warning Banner */}
        <div
          style={{
            backgroundColor: '#fffbeb',
            borderBottom: '1px solid #fde68a',
            padding: '8px 16px',
            fontSize: '11.5px',
            color: '#92400e',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <ShieldCheck size={14} color="#d97706" style={{ flexShrink: 0 }} />
          <span>
            <strong>Operational Advisory: </strong>
            Responses provide statutory pointers with citations. They do not constitute formal legal opinions or absolute compliance certifications.
          </span>
        </div>

        {/* Chat Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
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
                      width: '28px',
                      height: '28px',
                      borderRadius: '6px',
                      backgroundColor: '#ecfdf5',
                      color: '#059669',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <Bot size={16} />
                  </div>
                )}

                <div style={{ maxWidth: '82%' }}>
                  <div
                    style={{
                      padding: '12px 16px',
                      borderRadius: '10px',
                      fontSize: '13px',
                      lineHeight: 1.55,
                      backgroundColor: isUser ? '#059669' : '#f8fafc',
                      color: isUser ? '#ffffff' : '#1e293b',
                      border: isUser ? 'none' : '1px solid #e2e8f0',
                      borderBottomRightRadius: isUser ? '2px' : '10px',
                      borderBottomLeftRadius: isUser ? '10px' : '2px',
                    }}
                  >
                    {msg.content}

                    {/* Uncertainty Banner */}
                    {msg.uncertainty_flag && (
                      <div
                        style={{
                          marginTop: '8px',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          backgroundColor: '#fef2f2',
                          border: '1px solid #fecaca',
                          color: '#991b1b',
                          fontSize: '11.5px',
                          display: 'flex',
                          alignItems: 'flex-start',
                          gap: '6px',
                        }}
                      >
                        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                        <span>{msg.uncertainty_note || 'Ambiguous query or out-of-scope regulatory domain.'}</span>
                      </div>
                    )}
                  </div>

                  {/* Grounded Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '6px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
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
                            padding: '3px 8px',
                            borderRadius: '4px',
                            backgroundColor: '#f1f5f9',
                            border: '1px solid #cbd5e1',
                            fontSize: '11px',
                            color: '#059669',
                            textDecoration: 'none',
                            fontWeight: 600,
                          }}
                        >
                          <BookOpen size={11} />
                          <span>{cite.act} • {cite.section}</span>
                          <ExternalLink size={10} />
                        </a>
                      ))}
                    </div>
                  )}

                  <div style={{ fontSize: '10px', color: '#94a3b8', marginTop: '3px', textAlign: isUser ? 'right' : 'left' }}>
                    {new Date(msg.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>

                {isUser && (
                  <div
                    style={{
                      width: '28px',
                      height: '28px',
                      borderRadius: '6px',
                      backgroundColor: '#0f172a',
                      color: '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    <UserIcon size={14} />
                  </div>
                )}
              </div>
            );
          })}
          {querying && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', color: '#059669', fontSize: '12px' }}>
              <Bot size={16} />
              <span>Checking statutory references and Maharashtra gazette registers...</span>
            </div>
          )}
        </div>

        {/* Suggested Queries */}
        <div style={{ padding: '8px 20px', backgroundColor: '#fafbfc', borderTop: '1px solid #f1f5f9', display: 'flex', gap: '8px', overflowX: 'auto' }}>
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
                padding: '4px 10px',
                borderRadius: '9999px',
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e1',
                fontSize: '11.5px',
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
        <div style={{ padding: '14px 20px', borderTop: '1px solid #e2e8f0', display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSend();
            }}
            placeholder="Ask a compliance question with grounded citations..."
            style={{
              flex: 1,
              padding: '9px 14px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              fontSize: '13px',
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
            <Send size={14} />
            <span>Ask</span>
          </button>
        </div>
      </div>
    </div>
  );
};
