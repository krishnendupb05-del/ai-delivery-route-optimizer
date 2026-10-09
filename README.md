# AI-Based Multi-Constraint Delivery Route Optimizer

> **Priority-Aware, Disruption-Resilient Logistics Routing using Ant Colony Optimization & Genetic Algorithms**  
> *CSD.415 Project Phase 1 — College of Engineering Chengannur*

---

## 📌 Project Overview
Planning an efficient delivery route across multiple stops is computationally NP-hard. Real-world logistics requires handling complex constraints simultaneously:
1. **Capacitated Vehicle Routing (CVRP)**: Vehicle carrying capacity limits.
2. **Time Windows (VRPTW)**: Customer delivery deadlines and earliest arrival times.
3. **Delivery Priority Tiers**: Critical (medical/emergency), High (perishables), Normal, and Low priorities.
4. **Dynamic Disruptions**: Live road closures (accidents, construction, floods) requiring immediate re-routing without cold restarting.
5. **Comparative Study**: Benchmarking from-scratch **Ant Colony Optimization (ACO)** against an independent **Genetic Algorithm (GA)**.

---

## 👥 Team Roles & Responsibilities (3-Member Division)

| Member | Role / Area | Modules Owned | Primary Directory |
| :--- | :--- | :--- | :--- |
| **Member 1** | **Core AI & Optimization Lead** | Module 2 (ACO Engine), Module 3 (GA Comparison) | `algorithms/` |
| **Member 2** | **Backend, API & Disruption Lead** | Module 1 (Stop API), Module 4 (Dynamic Closures), Module 7 (Database) | `backend/` |
| **Member 3** | **Frontend, Map & Visualizations Lead** | Module 6 (Leaflet Map), Module 5 (Chart.js Analytics), Stop Entry UI | `static/`, `templates/` |

---

## 🚀 How to Run the Application

### 1. Clone & Setup Virtual Environment
```powershell
# Clone the repository (if on a new machine)
git clone https://github.com/krishnendupb05-del/ai-delivery-route-optimizer.git
cd ai-delivery-route-optimizer

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Application Server
```powershell
python backend/app.py
```

Open your browser and navigate to: **`http://127.0.0.1:5000`**

### 3. Run Automated Tests & Benchmarks
```powershell
python tests/test_optimization.py
```

---

## 📐 System Architecture & Modules

```
                    ┌────────────────────────────┐
                    │      Presentation Layer    │
                    │  Leaflet.js Map + Chart.js │
                    └─────────────┬──────────────┘
                                  │ HTTP / JSON
                    ┌─────────────▼──────────────┐
                    │       Flask REST API       │
                    │   backend/app.py & DB      │
                    └─────────────┬──────────────┘
                                  │ optimize()
                    ┌─────────────▼──────────────┐
                    │     Optimization Engine    │
                    │   algorithms/aco.py & ga   │
                    └─────────────┬──────────────┘
                                  │ read / write
                    ┌─────────────▼──────────────┐
                    │         SQLite DB          │
                    │   Stops, Routes, Closures  │
                    └────────────────────────────┘
```

---

## 🛠️ REST API Endpoints

- `GET /api/stops`: Retrieve all registered delivery stops & depot.
- `POST /api/stops`: Add a new stop with lat/lng, demand, priority, and time windows.
- `DELETE /api/stops/<id>`: Delete an existing delivery stop.
- `POST /api/optimize`: Run optimization (ACO or GA) respecting capacity, time windows, and priority.
- `POST /api/closures/toggle`: Block/unblock a road segment and trigger instant re-optimization.
- `POST /api/compare`: Run side-by-side comparative benchmarking between ACO and GA.
- `GET /api/analytics`: Retrieve historical performance summary.
