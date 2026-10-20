import { useEffect, useRef, useState } from 'react';
import { Chart, LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip } from 'chart.js';

Chart.register(LineElement, PointElement, LinearScale, CategoryScale, Legend, Tooltip);

export default function CompareModal({ isOpen, onClose, config }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const runBenchmark = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ capacity: config.capacity, speed: config.speed }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        alert('Benchmark notice: ' + (data.message || data.error || 'Server error'));
        return;
      }
      setStats(data);
      renderChart(data.aco.convergence, data.ga.convergence);
    } catch (err) {
      alert('Benchmark error: ' + err);
    } finally {
      setLoading(false);
    }
  };

  const renderChart = (acoConv, gaConv) => {
    if (chartRef.current) chartRef.current.destroy();
    const acoList = acoConv || [];
    const gaList = gaConv || [];
    const maxLen = Math.max(acoList.length, gaList.length);
    const labels = Array.from({ length: maxLen }, (_, i) => i + 1);
    const acoCosts = acoList.map((c) => (typeof c === 'object' && c !== null ? c.best_cost : c));
    const gaCosts = gaList.map((c) => (typeof c === 'object' && c !== null ? c.best_cost : c));

    chartRef.current = new Chart(canvasRef.current.getContext('2d'), {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Ant Colony Optimization (ACO)', borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', data: acoCosts, tension: 0.3 },
          { label: 'Genetic Algorithm (GA)', borderColor: '#a855f7', backgroundColor: 'rgba(168,85,247,0.1)', data: gaCosts, tension: 0.3 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: 'Iteration / Generation', color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { title: { display: true, text: 'Cost (Lower is Better)', color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
        },
        plugins: { legend: { labels: { color: '#f1f5f9' } } },
      },
    });
  };

  useEffect(() => {
    if (isOpen) runBenchmark();
    return () => chartRef.current?.destroy();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-card modal-lg">
        <div className="modal-header">
          <h3><i className="fa-solid fa-code-compare"></i> Comparative Benchmarking: ACO vs Genetic Algorithm</h3>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <div className="compare-stats-grid">
            <div className="stat-box aco-box">
              <h4>Ant Colony Optimization</h4>
              <div className="stat-row"><span>Best Distance:</span> <strong>{stats?.aco?.evaluation?.distance_km ?? '--'} km</strong></div>
              <div className="stat-row"><span>Total Time:</span> <strong>{stats?.aco?.evaluation?.total_time_min ?? '--'} mins</strong></div>
              <div className="stat-row"><span>Execution Time:</span> <strong>{stats?.aco?.execution_time_ms ?? '--'} ms</strong></div>
              <div className="stat-row"><span>Violations:</span> <strong>{stats?.aco?.evaluation?.violations?.length ?? 0}</strong></div>
            </div>
            <div className="stat-box ga-box">
              <h4>Genetic Algorithm</h4>
              <div className="stat-row"><span>Best Distance:</span> <strong>{stats?.ga?.evaluation?.distance_km ?? '--'} km</strong></div>
              <div className="stat-row"><span>Total Time:</span> <strong>{stats?.ga?.evaluation?.total_time_min ?? '--'} mins</strong></div>
              <div className="stat-row"><span>Execution Time:</span> <strong>{stats?.ga?.execution_time_ms ?? '--'} ms</strong></div>
              <div className="stat-row"><span>Violations:</span> <strong>{stats?.ga?.evaluation?.violations?.length ?? 0}</strong></div>
            </div>
          </div>
          <div className="compare-chart-wrapper">
            <canvas ref={canvasRef}></canvas>
          </div>
        </div>
        <div className="modal-footer">
          <button className="btn btn-primary" onClick={runBenchmark} disabled={loading}>
            {loading
              ? <><i className="fa-solid fa-spinner fa-spin"></i> Running Both Solvers...</>
              : <><i className="fa-solid fa-play"></i> Re-Run Benchmark</>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
