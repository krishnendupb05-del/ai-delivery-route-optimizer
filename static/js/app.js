// OptiRoute AI - Frontend Application Logic

let map;
let markers = [];
let routePolyline = null;
let closedEdgePolylines = [];
let convergenceChart = null;
let compareChart = null;

let allStops = [];
let activeClosures = [];

const PRIORITY_COLORS = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  NORMAL: '#38bdf8',
  LOW: '#64748b',
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  initConvergenceChart();
  initEventListeners();
  loadStops();
  loadClosures();
});

// Initialize Leaflet Map
function initMap() {
  // Centered on Chengannur / Central Kerala
  map = L.map('map').setView([9.3175, 76.6174], 11);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    subdomains: 'abcd',
    maxZoom: 19,
  }).addTo(map);
}

// Event Listeners
function initEventListeners() {
  document.getElementById('btnOptimize').addEventListener('click', runOptimization);
  document.getElementById('btnResetScenario').addEventListener('click', resetScenario);
  document.getElementById('btnToggleClosure').addEventListener('click', handleAddClosure);
  
  // Modals
  document.getElementById('btnOpenAddStop').addEventListener('click', () => {
    document.getElementById('addStopModal').classList.remove('hidden');
  });
  document.getElementById('btnCloseModal').addEventListener('click', () => {
    document.getElementById('addStopModal').classList.add('hidden');
  });
  document.getElementById('btnCancelModal').addEventListener('click', () => {
    document.getElementById('addStopModal').classList.add('hidden');
  });

  document.getElementById('addStopForm').addEventListener('submit', handleAddStop);

  // Compare Modal
  document.getElementById('btnCompareModal').addEventListener('click', openCompareModal);
  document.getElementById('btnCloseCompareModal').addEventListener('click', () => {
    document.getElementById('compareModal').classList.add('hidden');
  });
  document.getElementById('btnRunComparisonBench').addEventListener('click', runComparisonBenchmark);
}

// Fetch and render stops
async function loadStops() {
  try {
    const res = await fetch('/api/stops');
    allStops = await res.json();
    renderStopsList();
    renderMarkers();
    populateClosureDropdowns();
  } catch (err) {
    console.error('Failed to load stops:', err);
  }
}

// Render stops in sidebar
function renderStopsList() {
  const container = document.getElementById('stopsList');
  const countSpan = document.getElementById('stopCount');
  container.innerHTML = '';
  countSpan.textContent = allStops.length;

  allStops.forEach((stop) => {
    const div = document.createElement('div');
    div.className = 'stop-item';
    div.innerHTML = `
      <div class="stop-info">
        <span class="stop-name">
          ${stop.is_depot ? '<i class="fa-solid fa-warehouse text-primary"></i>' : '<i class="fa-solid fa-map-pin"></i>'}
          ${stop.id}. ${stop.name}
        </span>
        <span class="stop-meta">
          Demand: <strong>${stop.demand}kg</strong> | Window: <strong>[${stop.time_window[0]}-${stop.time_window[1]}m]</strong>
        </span>
      </div>
      <div>
        <span class="stop-badge prio-${stop.priority}">${stop.priority}</span>
        ${!stop.is_depot ? `<button class="btn btn-sm btn-outline text-danger" style="margin-left:6px; padding:3px 6px;" onclick="deleteStop(${stop.id})"><i class="fa-solid fa-trash"></i></button>` : ''}
      </div>
    `;
    container.appendChild(div);
  });
}

// Render map markers
function renderMarkers() {
  markers.forEach((m) => map.removeLayer(m));
  markers = [];

  allStops.forEach((stop) => {
    const isDepot = stop.is_depot;
    const color = isDepot ? '#3b82f6' : PRIORITY_COLORS[stop.priority] || '#38bdf8';

    const circle = L.circleMarker([stop.lat, stop.lng], {
      radius: isDepot ? 11 : 8,
      fillColor: color,
      color: '#ffffff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9,
    }).addTo(map);

    circle.bindPopup(`
      <div style="font-family: sans-serif; font-size: 13px;">
        <strong>Stop #${stop.id}: ${stop.name}</strong><br>
        ${isDepot ? '<span style="color:#3b82f6; font-weight:bold;">Central Depot Hub</span>' : `
          Priority: <b>${stop.priority}</b><br>
          Load Demand: <b>${stop.demand} kg</b><br>
          Time Window: <b>${stop.time_window[0]} - ${stop.time_window[1]} mins</b><br>
          Service Time: <b>${stop.service_time} mins</b>
        `}
      </div>
    `);

    markers.push(circle);
  });
}

// Populate Road Closure Select Options
function populateClosureDropdowns() {
  const fromSel = document.getElementById('closureFrom');
  const toSel = document.getElementById('closureTo');
  fromSel.innerHTML = '';
  toSel.innerHTML = '';

  allStops.forEach((s) => {
    const opt1 = document.createElement('option');
    opt1.value = s.id;
    opt1.textContent = `#${s.id} ${s.name.substring(0, 16)}...`;
    const opt2 = opt1.cloneNode(true);

    fromSel.appendChild(opt1);
    toSel.appendChild(opt2);
  });

  if (allStops.length > 1) {
    toSel.selectedIndex = 1;
  }
}

// Fetch and render road closures
async function loadClosures() {
  try {
    const res = await fetch('/api/closures');
    activeClosures = await res.json();
    renderClosuresList();
    renderClosurePolylines();
  } catch (err) {
    console.error('Failed to load closures:', err);
  }
}

function renderClosuresList() {
  const container = document.getElementById('activeClosuresList');
  const countBadge = document.getElementById('closureCountBadge');
  container.innerHTML = '';
  countBadge.textContent = `${activeClosures.length} Blocked`;

  if (activeClosures.length === 0) {
    container.innerHTML = '<span class="text-muted" style="font-size:0.75rem;">No active road closures.</span>';
    return;
  }

  activeClosures.forEach((c) => {
    const s1 = allStops.find((s) => s.id === c.from_id);
    const s2 = allStops.find((s) => s.id === c.to_id);
    const tag = document.createElement('span');
    tag.className = 'closure-tag';
    tag.innerHTML = `
      <span>Road #${c.from_id} &harr; #${c.to_id}</span>
      <span class="remove-btn" onclick="removeClosure(${c.from_id}, ${c.to_id})">&times;</span>
    `;
    container.appendChild(tag);
  });
}

function renderClosurePolylines() {
  closedEdgePolylines.forEach((p) => map.removeLayer(p));
  closedEdgePolylines = [];

  activeClosures.forEach((c) => {
    const s1 = allStops.find((s) => s.id === c.from_id);
    const s2 = allStops.find((s) => s.id === c.to_id);
    if (s1 && s2) {
      const redDashed = L.polyline(
        [[s1.lat, s1.lng], [s2.lat, s2.lng]],
        {
          color: '#ef4444',
          dashArray: '6, 8',
          weight: 4,
          opacity: 0.9,
        }
      ).addTo(map);
      redDashed.bindPopup(`<b>CLOSED ROAD</b><br>Segment between Stop #${s1.id} and #${s2.id}`);
      closedEdgePolylines.push(redDashed);
    }
  });
}

// Add Stop
async function handleAddStop(e) {
  e.preventDefault();
  const payload = {
    name: document.getElementById('newStopName').value,
    lat: parseFloat(document.getElementById('newStopLat').value),
    lng: parseFloat(document.getElementById('newStopLng').value),
    demand: parseFloat(document.getElementById('newStopDemand').value),
    priority: document.getElementById('newStopPriority').value,
    tw_start: parseFloat(document.getElementById('newStopTwStart').value),
    tw_end: parseFloat(document.getElementById('newStopTwEnd').value),
  };

  try {
    const res = await fetch('/api/stops', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      document.getElementById('addStopModal').classList.add('hidden');
      document.getElementById('addStopForm').reset();
      await loadStops();
    }
  } catch (err) {
    alert('Error saving stop: ' + err);
  }
}

// Delete Stop
async function deleteStop(stopId) {
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
}

// Add Closure
async function handleAddClosure() {
  const fromId = parseInt(document.getElementById('closureFrom').value);
  const toId = parseInt(document.getElementById('closureTo').value);

  if (fromId === toId) {
    alert('Please select two different stops to mark a closed segment.');
    return;
  }

  await fetch('/api/closures/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_id: fromId, to_id: toId, is_closed: true }),
  });

  await loadClosures();
  // Automatically trigger dynamic re-optimization
  runOptimization();
}

// Remove Closure
async function removeClosure(fromId, toId) {
  await fetch('/api/closures/toggle', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ from_id: fromId, to_id: toId, is_closed: false }),
  });
  await loadClosures();
  runOptimization();
}

// Reset Scenario
async function resetScenario() {
  if (!confirm('Reset stops and closures to demo state?')) return;
  await fetch('/api/reset-scenario', { method: 'POST' });
  await loadStops();
  await loadClosures();
  if (routePolyline) map.removeLayer(routePolyline);
}

// Run Optimization
async function runOptimization() {
  const btn = document.getElementById('btnOptimize');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Optimizing...';

  const algo = document.getElementById('algorithmSelect').value;
  const capacity = parseFloat(document.getElementById('vehicleCapacity').value);
  const speed = parseFloat(document.getElementById('vehicleSpeed').value);
  const iterations = parseInt(document.getElementById('numIterations').value);

  const payload = {
    algorithm: algo,
    capacity: capacity,
    speed: speed,
    iterations: iterations,
    num_ants: iterations,
    generations: iterations,
  };

  try {
    const res = await fetch('/api/optimize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    updateKPIs(data);
    drawOptimizedRoute(data);
    updateTimelineTable(data);
    updateConvergenceChart(data.convergence_history, data.algorithm);
  } catch (err) {
    alert('Optimization failed: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-bolt"></i> Run Optimization';
  }
}

// Update KPI Cards
function updateKPIs(data) {
  const evalData = data.evaluation;
  document.getElementById('metricDistance').textContent = `${evalData.distance_km} km`;
  document.getElementById('metricSaved').textContent = `${data.improvements.percentage_saved}% saved vs baseline`;
  document.getElementById('metricTime').textContent = `${evalData.total_time_min} mins`;
  document.getElementById('metricTimelineCount').textContent = `${data.route_ids.length - 1} route legs`;
  document.getElementById('metricCapacity').textContent = `${evalData.capacity_used} / ${evalData.capacity_limit} kg`;
  
  const capStatus = document.getElementById('metricCapacityStatus');
  if (evalData.capacity_used <= evalData.capacity_limit) {
    capStatus.textContent = 'Within capacity';
    capStatus.className = 'kpi-sub text-success';
  } else {
    capStatus.textContent = 'Capacity exceeded!';
    capStatus.className = 'kpi-sub text-danger';
  }

  document.getElementById('metricRuntime').textContent = `${data.execution_time_ms} ms`;
  const valStatus = document.getElementById('metricValidity');
  if (evalData.is_valid) {
    valStatus.textContent = 'Valid (0 Violations)';
    valStatus.className = 'kpi-sub text-success';
  } else {
    valStatus.textContent = `${evalData.violations.length} Violation(s)`;
    valStatus.className = 'kpi-sub text-danger';
  }

  document.getElementById('routeAlgorithmTag').textContent = `${data.algorithm} (${data.execution_time_ms}ms)`;
}

// Draw Route Polyline on Map
function drawOptimizedRoute(data) {
  if (routePolyline) {
    map.removeLayer(routePolyline);
  }

  const latlngs = [];
  data.ordered_stops.forEach((s) => {
    latlngs.push([s.lat, s.lng]);
  });

  routePolyline = L.polyline(latlngs, {
    color: '#38bdf8',
    weight: 4,
    opacity: 0.85,
    smoothFactor: 1,
  }).addTo(map);

  map.fitBounds(routePolyline.getBounds(), { padding: [40, 40] });
}

// Update Timeline Table
function updateTimelineTable(data) {
  const tbody = document.getElementById('timelineBody');
  tbody.innerHTML = '';

  const timeline = data.evaluation.timeline || [];
  const stopsMap = {};
  allStops.forEach((s) => (stopsMap[s.id] = s));

  timeline.forEach((leg, index) => {
    const stop = stopsMap[leg.to_id] || { name: 'Unknown', priority: 'NORMAL', time_window: [0, 0] };
    const tr = document.createElement('tr');

    const isLate = leg.lateness > 0;
    const statusBadge = isLate
      ? `<span class="badge badge-danger">Late +${leg.lateness}m</span>`
      : `<span class="badge badge-accent">On Time</span>`;

    tr.innerHTML = `
      <td><strong>#${index + 1}</strong></td>
      <td>${stop.name} (Stop #${leg.to_id})</td>
      <td><span class="stop-badge prio-${stop.priority}">${stop.priority}</span></td>
      <td><strong>${leg.arrival_time} min</strong></td>
      <td>[${stop.time_window[0]} - ${stop.time_window[1]}]</td>
      <td>${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

// Chart.js Convergence Chart
function initConvergenceChart() {
  const ctx = document.getElementById('convergenceChart').getContext('2d');
  convergenceChart = new Chart(ctx, {
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
}

function updateConvergenceChart(history, algoName) {
  if (!convergenceChart || !history) return;

  const labels = history.map((h) => h.iteration);
  const costs = history.map((h) => h.best_cost);
  const distances = history.map((h) => h.best_distance);

  convergenceChart.data.labels = labels;
  convergenceChart.data.datasets[0].label = `${algoName} Best Cost`;
  convergenceChart.data.datasets[0].data = costs;
  convergenceChart.data.datasets[1].data = distances;
  convergenceChart.update();
}

// Compare Modal Logic
function openCompareModal() {
  document.getElementById('compareModal').classList.remove('hidden');
  runComparisonBenchmark();
}

async function runComparisonBenchmark() {
  const btn = document.getElementById('btnRunComparisonBench');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Both Solvers...';

  const capacity = parseFloat(document.getElementById('vehicleCapacity').value);
  const speed = parseFloat(document.getElementById('vehicleSpeed').value);

  try {
    const res = await fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capacity, speed }),
    });
    const data = await res.json();

    // ACO stats
    document.getElementById('cmpAcoDist').textContent = `${data.aco.evaluation.distance_km} km`;
    document.getElementById('cmpAcoTime').textContent = `${data.aco.evaluation.total_time_min} mins`;
    document.getElementById('cmpAcoExec').textContent = `${data.aco.execution_time_ms} ms`;
    document.getElementById('cmpAcoViolations').textContent = data.aco.evaluation.violations.length;

    // GA stats
    document.getElementById('cmpGaDist').textContent = `${data.ga.evaluation.distance_km} km`;
    document.getElementById('cmpGaTime').textContent = `${data.ga.evaluation.total_time_min} mins`;
    document.getElementById('cmpGaExec').textContent = `${data.ga.execution_time_ms} ms`;
    document.getElementById('cmpGaViolations').textContent = data.ga.evaluation.violations.length;

    renderComparisonChart(data.aco.convergence, data.ga.convergence);
  } catch (err) {
    alert('Benchmark error: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-play"></i> Re-Run Benchmark';
  }
}

function renderComparisonChart(acoConv, gaConv) {
  const ctx = document.getElementById('compareConvergenceChart').getContext('2d');
  if (compareChart) {
    compareChart.destroy();
  }

  const labels = acoConv.map((c) => c.iteration);
  const acoCosts = acoConv.map((c) => c.best_cost);
  const gaCosts = gaConv.map((c) => c.best_cost);

  compareChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Ant Colony Optimization (ACO)',
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          data: acoCosts,
          tension: 0.3,
        },
        {
          label: 'Genetic Algorithm (GA)',
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
          data: gaCosts,
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: { display: true, text: 'Iteration / Generation', color: '#94a3b8' },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' },
        },
        y: {
          title: { display: true, text: 'Cost (Lower is Better)', color: '#94a3b8' },
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#94a3b8' },
        },
      },
      plugins: {
        legend: { labels: { color: '#f1f5f9' } },
      },
    },
  });
}
