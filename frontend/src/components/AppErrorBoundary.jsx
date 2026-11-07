import React from 'react';
import { AlertTriangle, Home, RotateCcw } from 'lucide-react';

export class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('PULSE interface error:', error, info?.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleHome = () => {
    window.location.hash = '#/ward/roster';
    this.setState({ error: null });
  };

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <div className="error-boundary-card hospital-card" role="alert">
        <div className="error-boundary-icon">
          <AlertTriangle size={26} />
        </div>
        <div className="error-boundary-body">
          <h2>This view could not be rendered</h2>
          <p>
            The clinical workspace hit an unexpected interface error. Patient data was not modified.
            Reload the view or return to the roster to continue.
          </p>
          <pre className="error-boundary-detail">{String(this.state.error?.message || this.state.error)}</pre>
          <div className="error-boundary-actions">
            <button type="button" className="btn btn-primary" onClick={this.handleReload}>
              <RotateCcw size={15} /> Reload workspace
            </button>
            <button type="button" className="btn btn-outline" onClick={this.handleHome}>
              <Home size={15} /> Return to roster
            </button>
          </div>
        </div>
      </div>
    );
  }
}

export default AppErrorBoundary;
