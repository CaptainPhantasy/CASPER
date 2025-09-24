import React from 'react';

type Props = { children: React.ReactNode };
type State = { hasError: boolean; error: any };

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: any) {
    return { hasError: true, error };
  }

  componentDidCatch(error: any, info: any) {
    // eslint-disable-next-line no-console
    console.error('ErrorBoundary caught:', error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    // full reload to reset app state if needed
    location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-900 text-gray-200 flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-gray-800 border border-red-500/30 rounded-lg p-4">
            <div className="text-lg font-semibold text-red-400 mb-2">Something went wrong</div>
            <div className="text-xs text-gray-400 mb-4 whitespace-pre-wrap overflow-auto max-h-48">{String(this.state.error)}</div>
            <div className="flex justify-end">
              <button onClick={this.handleReset} className="px-3 py-2 text-sm bg-red-600 rounded text-white">Reload</button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children as any;
  }
}

export default ErrorBoundary;

