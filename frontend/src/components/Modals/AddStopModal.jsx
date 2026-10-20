// AddStopModal - Modal for adding a new delivery stop
export default function AddStopModal({ isOpen, onClose, onSubmit }) {
  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.newStopName.value,
      lat: parseFloat(form.newStopLat.value),
      lng: parseFloat(form.newStopLng.value),
      demand: parseFloat(form.newStopDemand.value),
      priority: form.newStopPriority.value,
      tw_start: parseFloat(form.newStopTwStart.value),
      tw_end: parseFloat(form.newStopTwEnd.value),
    };
    onSubmit(payload, form);
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card">
        <div className="modal-header">
          <h3><i className="fa-solid fa-plus-circle"></i> Add Delivery Stop</h3>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <div className="form-group">
              <label>Stop Name / Customer</label>
              <input type="text" name="newStopName" className="input-control"
                placeholder="e.g. Chengannur Medical Center" required />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Latitude</label>
                <input type="number" step="0.0001" name="newStopLat"
                  className="input-control" defaultValue="9.3200" required />
              </div>
              <div className="form-group">
                <label>Longitude</label>
                <input type="number" step="0.0001" name="newStopLng"
                  className="input-control" defaultValue="76.6200" required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Demand Weight (kg)</label>
                <input type="number" name="newStopDemand" className="input-control"
                  defaultValue="25" min="1" required />
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select name="newStopPriority" className="input-control">
                  <option value="CRITICAL">Critical (Life-saving/Urgent)</option>
                  <option value="HIGH">High (Perishables)</option>
                  <option value="NORMAL" defaultValue>Normal</option>
                  <option value="LOW">Low</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Window Start (min)</label>
                <input type="number" name="newStopTwStart" className="input-control"
                  defaultValue="30" min="0" required />
              </div>
              <div className="form-group">
                <label>Window End (min)</label>
                <input type="number" name="newStopTwEnd" className="input-control"
                  defaultValue="180" min="1" required />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Save Stop</button>
          </div>
        </form>
      </div>
    </div>
  );
}
