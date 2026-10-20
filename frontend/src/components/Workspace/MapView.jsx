import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const PRIORITY_COLORS = {
  CRITICAL: '#ef4444',
  HIGH: '#f97316',
  NORMAL: '#38bdf8',
  LOW: '#64748b',
};

export default function MapView({ stops, closures, routeData, algorithmTag }) {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const routePolylineRef = useRef(null);
  const closurePolylinesRef = useRef([]);

  // Initialize map once — cleanup handles React 18 StrictMode double-mount
  useEffect(() => {
    if (mapInstanceRef.current) return;
    const map = L.map(mapRef.current).setView([9.3175, 76.6174], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markersRef.current = [];
      closurePolylinesRef.current = [];
      routePolylineRef.current = null;
    };
  }, []);

  // Render markers when stops change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !stops.length) return;

    markersRef.current.forEach((m) => map.removeLayer(m));
    markersRef.current = [];

    stops.forEach((stop) => {
      const isDepot = stop.is_depot;
      const color = isDepot ? '#3b82f6' : (PRIORITY_COLORS[stop.priority] || '#38bdf8');
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
          ${isDepot
            ? '<span style="color:#3b82f6; font-weight:bold;">Central Depot Hub</span>'
            : `Priority: <b>${stop.priority}</b><br>
               Load Demand: <b>${stop.demand} kg</b><br>
               Time Window: <b>${stop.time_window[0]} - ${stop.time_window[1]} mins</b><br>
               Service Time: <b>${stop.service_time} mins</b>`
          }
        </div>
      `);
      markersRef.current.push(circle);
    });
  }, [stops]);

  // Render closure polylines when closures change
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    closurePolylinesRef.current.forEach((p) => map.removeLayer(p));
    closurePolylinesRef.current = [];

    closures.forEach((c) => {
      const s1 = stops.find((s) => s.id === c.from_id);
      const s2 = stops.find((s) => s.id === c.to_id);
      if (s1 && s2) {
        const line = L.polyline([[s1.lat, s1.lng], [s2.lat, s2.lng]], {
          color: '#ef4444',
          dashArray: '6, 8',
          weight: 4,
          opacity: 0.9,
        }).addTo(map);
        line.bindPopup(`<b>CLOSED ROAD</b><br>Segment between Stop #${s1.id} and #${s2.id}`);
        closurePolylinesRef.current.push(line);
      }
    });
  }, [closures, stops]);

  // Render optimized route when routeData changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || !routeData) return;

    if (routePolylineRef.current) map.removeLayer(routePolylineRef.current);

    const latlngs = routeData.ordered_stops.map((s) => [s.lat, s.lng]);
    routePolylineRef.current = L.polyline(latlngs, {
      color: '#38bdf8',
      weight: 4,
      opacity: 0.85,
      smoothFactor: 1,
    }).addTo(map);

    map.fitBounds(routePolylineRef.current.getBounds(), { padding: [40, 40] });
  }, [routeData]);

  return (
    <div className="map-wrapper card">
      <div className="card-header map-header">
        <div className="map-title-group">
          <h3><i className="fa-solid fa-map-location-dot"></i> Live Route Map</h3>
          <span className="badge badge-accent">{algorithmTag || 'ACO Ready'}</span>
        </div>
        <div className="map-legend">
          <span className="legend-item"><span className="dot dot-depot"></span> Depot</span>
          <span className="legend-item"><span className="dot dot-critical"></span> Critical</span>
          <span className="legend-item"><span className="dot dot-high"></span> High</span>
          <span className="legend-item"><span className="dot dot-normal"></span> Normal</span>
          <span className="legend-item"><span className="dot dot-low"></span> Low</span>
        </div>
      </div>
      <div ref={mapRef} className="map-container"></div>
    </div>
  );
}
