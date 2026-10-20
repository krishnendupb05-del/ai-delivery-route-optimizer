// ClosuresPanel - Road Closure Simulation
export default function ClosuresPanel({ stops, closures, onAddClosure, onRemoveClosure, isBlocking }) {
  return (
    <section className="card closures-card">
      <div className="card-header">
        <h3><i className="fa-solid fa-road-barrier text-danger"></i> Road Closure Simulation</h3>
        <span className="badge badge-danger">{closures.length} Blocked</span>
      </div>
      <div className="card-body">
        <p className="section-desc">Simulate construction or accidents to trigger live dynamic re-routing:</p>
        <div className="closure-inputs">
          <select id="closureFrom" className="input-control">
            {stops.map((s) => (
              <option key={s.id} value={s.id}>#{s.id} {s.name.substring(0, 16)}...</option>
            ))}
          </select>
          <span>↔</span>
          <select id="closureTo" className="input-control" defaultValue={stops[1]?.id}>
            {stops.map((s) => (
              <option key={s.id} value={s.id}>#{s.id} {s.name.substring(0, 16)}...</option>
            ))}
          </select>
          <button
            className="btn btn-danger btn-sm"
            onClick={onAddClosure}
            disabled={isBlocking}
          >
            {isBlocking
              ? <><i className="fa-solid fa-spinner fa-spin"></i> Blocking...</>
              : <><i className="fa-solid fa-ban"></i> Block Road</>
            }
          </button>
        </div>
        <div className="tag-list">
          {closures.length === 0 ? (
            <span className="text-muted" style={{ fontSize: '0.75rem' }}>No active road closures.</span>
          ) : (
            closures.map((c) => (
              <span key={`${c.from_id}-${c.to_id}`} className="closure-tag">
                <span>Road #{c.from_id} ↔ #{c.to_id}</span>
                <span className="remove-btn" onClick={() => onRemoveClosure(c.from_id, c.to_id)}>×</span>
              </span>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
