// KPIBanner - 5 Metric Cards
export default function KPIBanner({ kpis }) {
  const {
    trips = '-- Trips',
    depotReturns = '-- Reloads',
    distance = '-- km',
    saved = '--% vs Baseline',
    time = '-- mins',
    legs = '-- legs',
    capacity = '-- / -- kg',
    capacityStatus = 'Within capacity',
    capacityClass = '',
    runtime = '-- ms',
    validity = 'Ready',
    validityClass = '',
  } = kpis || {};

  return (
    <div className="kpi-banner">
      <div className="kpi-card">
        <div className="kpi-icon icon-teal"><i className="fa-solid fa-truck-fast"></i></div>
        <div className="kpi-content">
          <span className="kpi-title">Scheduled Trips</span>
          <span className="kpi-val">{trips}</span>
          <span className="kpi-sub text-accent">{depotReturns}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon icon-blue"><i className="fa-solid fa-route"></i></div>
        <div className="kpi-content">
          <span className="kpi-title">Optimized Distance</span>
          <span className="kpi-val">{distance}</span>
          <span className="kpi-sub text-success">{saved}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon icon-green"><i className="fa-solid fa-clock"></i></div>
        <div className="kpi-content">
          <span className="kpi-title">Total Travel Time</span>
          <span className="kpi-val">{time}</span>
          <span className="kpi-sub">{legs}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon icon-amber"><i className="fa-solid fa-weight-hanging"></i></div>
        <div className="kpi-content">
          <span className="kpi-title">Vehicle Load</span>
          <span className="kpi-val">{capacity}</span>
          <span className={`kpi-sub ${capacityClass}`}>{capacityStatus}</span>
        </div>
      </div>

      <div className="kpi-card">
        <div className="kpi-icon icon-purple"><i className="fa-solid fa-microchip"></i></div>
        <div className="kpi-content">
          <span className="kpi-title">Runtime &amp; Status</span>
          <span className="kpi-val">{runtime}</span>
          <span className={`kpi-sub ${validityClass}`}>{validity}</span>
        </div>
      </div>
    </div>
  );
}
