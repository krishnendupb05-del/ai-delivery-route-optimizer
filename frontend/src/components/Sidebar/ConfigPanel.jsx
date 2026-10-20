// ConfigPanel - Vehicle & Algorithm Parameters
export default function ConfigPanel({ config, onChange }) {
  return (
    <section className="card config-card">
      <div className="card-header">
        <h3><i className="fa-solid fa-sliders"></i> Vehicle &amp; Algorithm Parameters</h3>
      </div>
      <div className="card-body">
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="algorithmSelect">Algorithm</label>
            <select
              id="algorithmSelect"
              className="input-control"
              value={config.algorithm}
              onChange={(e) => onChange('algorithm', e.target.value)}
            >
              <option value="aco">Ant Colony Optimization (ACO)</option>
              <option value="ga">Genetic Algorithm (GA)</option>
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="vehicleCapacity">Vehicle Capacity (40 - 100 kg)</label>
            <input
              type="number"
              id="vehicleCapacity"
              className="input-control"
              value={config.capacity}
              min="40"
              max="100"
              onChange={(e) => onChange('capacity', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="vehicleSpeed">Average Speed (km/h)</label>
            <input
              type="number"
              id="vehicleSpeed"
              className="input-control"
              value={config.speed}
              min="10"
              max="90"
              onChange={(e) => onChange('speed', e.target.value)}
            />
          </div>
          <div className="form-group">
            <label htmlFor="numIterations">Iterations / Ants</label>
            <input
              type="number"
              id="numIterations"
              className="input-control"
              value={config.iterations}
              min="10"
              max="200"
              onChange={(e) => onChange('iterations', e.target.value)}
            />
          </div>
        </div>
      </div>
    </section>
  );
}
