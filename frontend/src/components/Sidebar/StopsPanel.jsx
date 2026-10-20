// StopsPanel - Delivery Stops Management
export default function StopsPanel({ stops, onOpenAddStop, onDeleteStop }) {
  return (
    <section className="card stops-card">
      <div className="card-header flex-between">
        <h3><i className="fa-solid fa-location-dot"></i> Delivery Stops ({stops.length})</h3>
        <button className="btn btn-sm btn-outline" onClick={onOpenAddStop}>
          <i className="fa-solid fa-plus"></i> Add Stop
        </button>
      </div>
      <div className="card-body scrollable-stops">
        <div className="stops-container">
          {stops.map((stop) => (
            <div key={stop.id} className="stop-item">
              <div className="stop-info">
                <span className="stop-name">
                  {stop.is_depot
                    ? <i className="fa-solid fa-warehouse text-primary"></i>
                    : <i className="fa-solid fa-map-pin"></i>
                  }
                  {stop.id}. {stop.name}
                </span>
                <span className="stop-meta">
                  Demand: <strong>{stop.demand}kg</strong> | Window:{' '}
                  <strong>[{stop.time_window[0]}-{stop.time_window[1]}m]</strong>
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className={`stop-badge prio-${stop.priority}`}>{stop.priority}</span>
                {!stop.is_depot && (
                  <button
                    className="btn btn-sm btn-outline text-danger"
                    style={{ padding: '3px 6px' }}
                    onClick={() => onDeleteStop(stop.id)}
                  >
                    <i className="fa-solid fa-trash"></i>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
