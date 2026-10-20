import { useState, useCallback, useEffect } from 'react';
import Navbar from './components/Navbar';
import ConfigPanel from './components/Sidebar/ConfigPanel';
import ClosuresPanel from './components/Sidebar/ClosuresPanel';
import StopsPanel from './components/Sidebar/StopsPanel';
import KPIBanner from './components/Workspace/KPIBanner';
import MapView from './components/Workspace/MapView';
import ConvergenceChart from './components/Workspace/ConvergenceChart';
import TimelineTable from './components/Workspace/TimelineTable';
import AddStopModal from './components/Modals/AddStopModal';
import CompareModal from './components/Modals/CompareModal';

const DEFAULT_CONFIG = {
  algorithm: 'aco',
  capacity: 80,
  speed: 35,
  iterations: 60,
};

function buildKPIs(data) {
  if (!data) return {};
  const evalData = data.evaluation || {};
  const numTrips = data.num_trips || evalData.num_trips || 1;
  const depotReturns = data.depot_returns !== undefined ? data.depot_returns : (evalData.depot_returns || 0);
  const capacityOk = evalData.capacity_used <= evalData.capacity_limit || numTrips > 1;

  return {
    trips: `${numTrips} ${numTrips === 1 ? 'Trip' : 'Trips'}`,
    depotReturns: depotReturns > 0
      ? `${depotReturns} Depot ${depotReturns === 1 ? 'Reload' : 'Reloads'}`
      : 'Single Direct Leg',
    distance: `${evalData.distance_km} km`,
    saved: `${data.improvements?.percentage_saved}% saved vs baseline`,
    time: `${evalData.total_time_min} mins`,
    legs: `${(data.route_ids || []).length - 1} route legs`,
    capacity: `${evalData.capacity_used} / ${evalData.capacity_limit} kg`,
    capacityStatus: numTrips > 1
      ? `${numTrips} Trips (Reloaded at Depot)`
      : capacityOk ? 'Within capacity' : 'Capacity exceeded!',
    capacityClass: capacityOk ? 'text-success' : 'text-danger',
    runtime: `${data.execution_time_ms} ms`,
    validity: evalData.is_valid
      ? 'Valid (0 Violations)'
      : `${(evalData.violations || []).length} Violation(s)`,
    validityClass: evalData.is_valid ? 'text-success' : 'text-danger',
  };
}

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [stops, setStops] = useState([]);
  const [closures, setClosures] = useState([]);
  const [routeData, setRouteData] = useState(null);
  const [kpis, setKPIs] = useState({});
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [isBlocking, setIsBlocking] = useState(false);
  const [showAddStop, setShowAddStop] = useState(false);
  const [showCompare, setShowCompare] = useState(false);
  const [algorithmTag, setAlgorithmTag] = useState('ACO Ready');

  const loadStops = useCallback(async () => {
    try {
      let res = await fetch('/api/stops');
      let data = await res.json();
      if (!Array.isArray(data) || data.length === 0) {
        await fetch('/api/reset-scenario', { method: 'POST' });
        res = await fetch('/api/stops');
        data = await res.json();
      }
      setStops(data);
    } catch (err) {
      console.error('Failed to load stops:', err);
    }
  }, []);

  const loadClosures = useCallback(async () => {
    try {
      const res = await fetch('/api/closures');
      const data = await res.json();
      setClosures(data);
    } catch (err) {
      console.error('Failed to load closures:', err);
    }
  }, []);

  // Run once on mount only — no deps to avoid infinite re-fetch loop
  useEffect(() => {
    loadStops();
    loadClosures();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleConfigChange = (key, value) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const handleOptimize = async () => {
    setIsOptimizing(true);
    try {
      const payload = {
        algorithm: config.algorithm,
        capacity: parseFloat(config.capacity),
        speed: parseFloat(config.speed),
        iterations: parseInt(config.iterations),
        num_ants: parseInt(config.iterations),
        generations: parseInt(config.iterations),
      };
      const res = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        alert('Optimization Notice: ' + (data.message || data.error || 'Server error'));
        return;
      }
      setRouteData(data);
      setKPIs(buildKPIs(data));
      setAlgorithmTag(`${data.algorithm} (${data.execution_time_ms}ms)`);
    } catch (err) {
      alert('Optimization failed: ' + err);
    } finally {
      setIsOptimizing(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Reset stops and closures to demo state?')) return;
    await fetch('/api/reset-scenario', { method: 'POST' });
    setRouteData(null);
    setKPIs({});
    setAlgorithmTag('ACO Ready');
    await loadStops();
    await loadClosures();
  };

  const handleAddClosure = async () => {
    const fromSel = document.getElementById('closureFrom');
    const toSel = document.getElementById('closureTo');
    if (!fromSel || !toSel) return;
    const fromId = parseInt(fromSel.value);
    const toId = parseInt(toSel.value);
    if (isNaN(fromId) || isNaN(toId) || fromId === toId) {
      alert('Please select two different stops to mark a closed segment.');
      return;
    }
    setIsBlocking(true);
    try {
      const res = await fetch('/api/closures/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_id: fromId, to_id: toId, is_closed: true }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.message || errData.error || 'Failed to toggle closure');
      }
      await loadClosures();
      await handleOptimize();
    } catch (err) {
      alert('Failed to simulate road closure: ' + err.message);
    } finally {
      setIsBlocking(false);
    }
  };

  const handleRemoveClosure = async (fromId, toId) => {
    try {
      const res = await fetch('/api/closures/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_id: fromId, to_id: toId, is_closed: false }),
      });
      if (!res.ok) throw new Error('Failed to remove closure');
      await loadClosures();
      await handleOptimize();
    } catch (err) {
      alert('Failed to remove closure: ' + err.message);
    }
  };

  const handleAddStop = async (payload, form) => {
    try {
      const res = await fetch('/api/stops', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        setShowAddStop(false);
        form.reset();
        await loadStops();
      }
    } catch (err) {
      alert('Error saving stop: ' + err);
    }
  };

  const handleDeleteStop = async (stopId) => {
    if (!confirm(`Delete delivery stop #${stopId}?`)) return;
    try {
      const res = await fetch(`/api/stops/${stopId}`, { method: 'DELETE' });
      if (res.ok) {
        await loadStops();
        await loadClosures();
      }
    } catch (err) {
      alert('Error deleting stop: ' + err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar
        onReset={handleReset}
        onCompare={() => setShowCompare(true)}
        onOptimize={handleOptimize}
        isOptimizing={isOptimizing}
        routeAlgorithmTag={algorithmTag}
      />

      <main className="dashboard-grid">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <ConfigPanel config={config} onChange={handleConfigChange} />
          <ClosuresPanel
            stops={stops}
            closures={closures}
            onAddClosure={handleAddClosure}
            onRemoveClosure={handleRemoveClosure}
            isBlocking={isBlocking}
          />
          <StopsPanel
            stops={stops}
            onOpenAddStop={() => setShowAddStop(true)}
            onDeleteStop={handleDeleteStop}
          />
        </aside>

        {/* Right Workspace */}
        <section className="workspace">
          <KPIBanner kpis={kpis} />
          <MapView
            stops={stops}
            closures={closures}
            routeData={routeData}
            algorithmTag={algorithmTag}
          />
          <div className="bottom-panels">
            <ConvergenceChart
              history={routeData?.convergence_history}
              algoName={routeData?.algorithm || config.algorithm.toUpperCase()}
            />
            <TimelineTable
              timeline={routeData?.evaluation?.timeline}
              stops={stops}
            />
          </div>
        </section>
      </main>

      {/* Modals */}
      <AddStopModal
        isOpen={showAddStop}
        onClose={() => setShowAddStop(false)}
        onSubmit={handleAddStop}
      />
      <CompareModal
        isOpen={showCompare}
        onClose={() => setShowCompare(false)}
        config={config}
      />
    </div>
  );
}
