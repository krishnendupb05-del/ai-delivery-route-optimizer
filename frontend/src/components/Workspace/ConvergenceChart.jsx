import { useEffect, useRef } from 'react';
import Chart from 'chart.js/auto';


export default function ConvergenceChart({ history, algoName }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  // Create chart once on mount, destroy on unmount
  useEffect(() => {
    if (!canvasRef.current) return;

    // Destroy any existing chart on this canvas before creating a new one
    if (chartRef.current) {
      chartRef.current.destroy();
      chartRef.current = null;
    }

    const ctx = canvasRef.current.getContext('2d');
    chartRef.current = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Best Composite Cost',
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            data: [],
            tension: 0.3,
            fill: true,
          },
          {
            label: 'Best Route Distance (km)',
            borderColor: '#10b981',
            data: [],
            tension: 0.3,
            borderDash: [5, 5],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: { display: true, text: 'Iteration', color: '#94a3b8' },
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8' },
          },
          y: {
            title: { display: true, text: 'Objective Cost / km', color: '#94a3b8' },
            grid: { color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#94a3b8' },
          },
        },
        plugins: {
          legend: { labels: { color: '#f1f5f9' } },
        },
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, []); // Only run once on mount

  // Update chart data when history changes
  useEffect(() => {
    if (!chartRef.current || !history?.length) return;

    const labels = history.map((h, i) =>
      typeof h === 'object' && h !== null ? h.iteration : i + 1
    );
    const costs = history.map((h) =>
      typeof h === 'object' && h !== null ? h.best_cost : h
    );
    const distances = history.map((h) =>
      typeof h === 'object' && h !== null ? h.best_distance || h.best_cost : h
    );

    chartRef.current.data.labels = labels;
    chartRef.current.data.datasets[0].label = `${algoName} Best Cost`;
    chartRef.current.data.datasets[0].data = costs;
    chartRef.current.data.datasets[1].data = distances;
    chartRef.current.update();
  }, [history, algoName]);

  return (
    <div className="card chart-card">
      <div className="card-header">
        <h3>
          <i className="fa-solid fa-chart-line"></i> Optimization Convergence Curve
        </h3>
      </div>
      <div className="card-body">
        <canvas ref={canvasRef}></canvas>
      </div>
    </div>
  );
}
