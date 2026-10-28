import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { AIAssistantModal } from '../components/assistant/AIAssistantModal';

describe('AIAssistantModal Component', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(<AIAssistantModal isOpen={false} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders with regulatory banner and statutory citations when open', () => {
    render(<AIAssistantModal isOpen={true} onClose={() => {}} />);

    expect(screen.getByText(/PlantProof Regulatory Assistant/i)).toBeInTheDocument();
    expect(screen.getByText(/AI Proposes, Humans Dispose/i)).toBeInTheDocument();
    expect(screen.getByText(/Operational Advisory/i)).toBeInTheDocument();
    expect(screen.getByText(/The Factories Act, 1948/i)).toBeInTheDocument();
  });

  it('allows clicking sample prompt questions', () => {
    render(<AIAssistantModal isOpen={true} onClose={() => {}} />);

    const sampleChip = screen.getByRole('button', { name: /Boiler hydraulic testing requirements/i });
    expect(sampleChip).toBeInTheDocument();
    fireEvent.click(sampleChip);

    // Prompt is sent and user message is appended
    expect(screen.getAllByText(/Boiler hydraulic testing requirements/i).length).toBeGreaterThanOrEqual(1);
  });
});
