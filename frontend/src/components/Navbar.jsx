// Navbar component
export default function Navbar({ onReset, onCompare, onOptimize, isOptimizing, routeAlgorithmTag }) {
  return (
    <header className="navbar">
      <div className="nav-brand">
        <div className="brand-logo">
          <i className="fa-solid fa-route"></i>
        </div>
        <div>
          <h1 className="brand-title">OptiRoute AI</h1>
          <p className="brand-subtitle">Multi-Constraint Disruption-Resilient Logistics Engine</p>
        </div>
      </div>
      <div className="nav-actions">
        <span className="badge badge-accent">CSD.415 Project Phase 1</span>
        <button className="btn btn-secondary" onClick={onReset}>
          <i className="fa-solid fa-rotate-left"></i> Reset Demo Data
        </button>
        <button className="btn btn-outline" onClick={onCompare}>
          <i className="fa-solid fa-code-compare"></i> Compare ACO vs GA
        </button>
        <button className="btn btn-primary" onClick={onOptimize} disabled={isOptimizing}>
          {isOptimizing
            ? <><i className="fa-solid fa-spinner fa-spin"></i> Optimizing...</>
            : <><i className="fa-solid fa-bolt"></i> Run Optimization</>
          }
        </button>
      </div>
    </header>
  );
}
