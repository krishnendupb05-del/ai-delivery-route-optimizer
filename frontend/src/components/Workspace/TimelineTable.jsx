// TimelineTable - Stop Sequence & Timeline
export default function TimelineTable({ timeline, stops }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="card table-card">
        <div className="card-header">
          <h3><i className="fa-solid fa-list-ol"></i> Sequence Timeline</h3>
        </div>
        <div className="card-body table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Trip</th><th>Seq</th><th>Stop Name</th>
                <th>Priority</th><th>Arrival</th><th>Window</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr><td colSpan="7" className="text-center text-muted">Run optimization to view stop timeline</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  const stopsMap = {};
  stops.forEach((s) => (stopsMap[s.id] = s));

  let currentTrip = 1;
  const rows = timeline.map((leg, index) => {
    if (index > 0 && timeline[index - 1].to_id === 0 && leg.to_id !== 0) {
      currentTrip++;
    }
    const tripNum = currentTrip;
    const isDepot = leg.to_id === 0;
    const isLastLeg = index === timeline.length - 1;
    const stop = stopsMap[leg.to_id] || (isDepot
      ? { name: 'Central Depot Hub', priority: 'DEPOT', time_window: [0, 480] }
      : { name: 'Unknown', priority: 'NORMAL', time_window: [0, 0] });

    const isLate = leg.lateness > 0;
    const statusBadge = isDepot
      ? <span className="badge badge-accent">{isLastLeg ? 'Final Return' : '🔄 Reload'}</span>
      : (isLate
        ? <span className="badge badge-danger">Late +{leg.lateness}m</span>
        : <span className="badge badge-accent">On Time</span>
      );

    const stopDisplay = isDepot
      ? (isLastLeg
        ? <><i className="fa-solid fa-flag-checkered text-primary"></i> Central Depot (Route End)</>
        : <><i className="fa-solid fa-rotate text-warning"></i> Central Depot (Reload)</>
      )
      : `${stop.name} (Stop #${leg.to_id})`;

    const priorityBadge = isDepot
      ? <span className="badge" style={{ border: '1px solid #3b82f6', color: '#38bdf8' }}>Depot</span>
      : <span className={`stop-badge prio-${stop.priority}`}>{stop.priority}</span>;

    const windowDisplay = isDepot ? 'Shift Hours' : `[${stop.time_window[0]} - ${stop.time_window[1]}]`;

    return (
      <tr key={index}>
        <td><span className="badge badge-accent">Trip #{tripNum}</span></td>
        <td><strong>#{index + 1}</strong></td>
        <td>{stopDisplay}</td>
        <td>{priorityBadge}</td>
        <td><strong>{leg.arrival_time} min</strong></td>
        <td>{windowDisplay}</td>
        <td>{statusBadge}</td>
      </tr>
    );
  });

  return (
    <div className="card table-card">
      <div className="card-header">
        <h3><i className="fa-solid fa-list-ol"></i> Sequence Timeline</h3>
      </div>
      <div className="card-body table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Trip</th><th>Seq</th><th>Stop Name</th>
              <th>Priority</th><th>Arrival</th><th>Window</th><th>Status</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
  );
}
