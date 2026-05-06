/**
 * Error boundaries and error handling utilities for the student dashboard
 */

import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from '@/shared/ui/Button';

/**
 * Generic error boundary component
 */
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error boundary caught:', error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleRetry);
      }

      return <DefaultErrorFallback error={this.state.error} onRetry={this.handleRetry} />;
    }

    return this.props.children;
  }
}

/**
 * Default error fallback UI
 */
interface DefaultErrorFallbackProps {
  error: Error;
  onRetry: () => void;
}

const DefaultErrorFallback: React.FC<DefaultErrorFallbackProps> = ({
  error,
  onRetry,
}) => (
  <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
    <div className="flex items-start gap-4">
      <div className="mt-1 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-5 w-5 text-red-600" />
      </div>
      <div className="flex-1">
        <h3 className="font-semibold text-red-900">Something went wrong</h3>
        <p className="mt-1 text-sm text-red-700">{error.message}</p>
        <Button
          onClick={onRetry}
          variant="outline"
          className="mt-4 text-red-600"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Try again
        </Button>
      </div>
    </div>
  </div>
);

/**
 * Async component error boundary with React Query integration
 */
interface AsyncErrorBoundaryProps {
  children: ReactNode;
  isError: boolean;
  error: Error | null;
  isLoading?: boolean;
  onRetry?: () => void;
}

export const AsyncErrorBoundary: React.FC<AsyncErrorBoundaryProps> = ({
  children,
  isError,
  error,
  isLoading,
  onRetry,
}) => {
  if (isLoading) {
    return null; // Let the caller handle loading state
  }

  if (isError && error) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-amber-900">Failed to load data</h4>
            <p className="mt-1 text-sm text-amber-800">{error.message}</p>
            {onRetry && (
              <Button
                onClick={onRetry}
                variant="outline"
                size="sm"
                className="mt-3"
              >
                Retry
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

/**
 * Higher-order component to wrap components with error boundary
 */
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: (error: Error, retry: () => void) => ReactNode
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
};

/**
 * Hook for handling API errors gracefully
 */
interface UseApiErrorHandlerOptions {
  onError?: (error: Error) => void;
  showNotification?: boolean;
}

export const useApiErrorHandler = ({
  onError,
  showNotification = false,
}: UseApiErrorHandlerOptions = {}) => {
  const handleError = (error: unknown) => {
    const apiError = new Error(
      error instanceof Error ? error.message : 'An error occurred'
    );

    console.error('API Error:', apiError);

    if (showNotification) {
      // TODO: Integrate with toast notification system
      console.warn('API Error:', apiError.message);
    }

    onError?.(apiError);
  };

  return { handleError };
};
