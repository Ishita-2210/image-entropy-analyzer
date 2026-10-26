import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DifferencePreview } from './DifferencePreview';

describe('Difference preview', () => {
  it('shows a scale and finishes loading only when pixels are available', () => {
    render(<DifferencePreview imageId="difference" maximum={12.5} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    fireEvent.load(screen.getByAltText('Normalized absolute reconstruction difference'));
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByText('12.50 · maximum error')).toBeInTheDocument();
  });
  it('replaces broken images with a retry action and requests a new preview', () => {
    render(<DifferencePreview imageId="difference" maximum={0} />);
    const original = screen.getByAltText('Normalized absolute reconstruction difference');
    const firstUrl = original.getAttribute('src');
    fireEvent.error(original);
    expect(screen.getByRole('alert')).toHaveTextContent('could not load');
    expect(
      screen.queryByAltText('Normalized absolute reconstruction difference'),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry preview' }));
    const retry = screen.getByAltText('Normalized absolute reconstruction difference');
    expect(retry.getAttribute('src')).not.toBe(firstUrl);
    fireEvent.load(retry);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
