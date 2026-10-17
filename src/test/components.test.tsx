import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { StatusBadge } from '@/components/data-display/status-badge';
import { PriorityBadge } from '@/components/data-display/priority-badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

describe('UI & Data Display Components', () => {
  it('renders StatusBadge with accessible label and text', () => {
    render(<StatusBadge status="in_progress" />);
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Status: In Progress');
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('renders PriorityBadge with text and priority level', () => {
    render(<PriorityBadge priority="urgent" />);
    expect(screen.getByText('Urgent')).toBeInTheDocument();
  });

  it('renders EmptyState with custom title, message and action', () => {
    render(
      <EmptyState
        title="No Reports Found"
        description="Try adjusting your filter parameters."
        actionText="Reset Filters"
        onAction={() => {}}
      />
    );
    expect(screen.getByText('No Reports Found')).toBeInTheDocument();
    expect(screen.getByText('Try adjusting your filter parameters.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reset Filters' })).toBeInTheDocument();
  });

  it('renders Breadcrumbs hierarchy correctly', () => {
    render(
      <BrowserRouter>
        <Breadcrumbs
          items={[
            { label: 'Admin Portal', href: '/admin/dashboard' },
            { label: 'Manage Reports' },
          ]}
        />
      </BrowserRouter>
    );
    expect(screen.getByText('Admin Portal')).toBeInTheDocument();
    expect(screen.getByText('Manage Reports')).toBeInTheDocument();
  });

  it('renders Button in loading state with disabled attribute', () => {
    render(<Button isLoading>Submit Report</Button>);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('renders Input with label and error feedback', () => {
    render(
      <Input
        label="Report Summary"
        error="Title must be at least 5 characters"
        placeholder="Enter summary..."
      />
    );
    expect(screen.getByText('Report Summary')).toBeInTheDocument();
    expect(screen.getByText('Title must be at least 5 characters')).toBeInTheDocument();
  });
});
