<p align="center">
  <h1 align="center">💧 Water Quality Cloud Backend</h1>
  <p align="center">
    <strong>Cloud Integration Layer (Zone 3)</strong> for the Explainable Hybrid ML Ensemble<br>
    Edge-to-Cloud IoT Water Quality Monitoring System
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.10-3776AB?logo=python&logoColor=white" alt="Python 3.10">
    <img src="https://img.shields.io/badge/FastAPI-0.104-009688?logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/TimescaleDB-PG14-FDB515?logo=timescale&logoColor=white" alt="TimescaleDB">
    <img src="https://img.shields.io/badge/MQTT-Mosquitto-3C5280?logo=eclipsemosquitto&logoColor=white" alt="Mosquitto">
    <img src="https://img.shields.io/badge/Grafana-Latest-F46800?logo=grafana&logoColor=white" alt="Grafana">
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker">
  </p>
</p>

---

## 📖 Overview

This repository contains the **Cloud Integration Layer** of a three‑zone edge‑to‑cloud IoT architecture for real‑time river water quality monitoring across **97 stations** in Uttar Pradesh, India.

The system is the backend for two companion research papers:

| Paper | Focus | ML Model | Sensors |
|-------|-------|----------|---------|
| **Cloud 1** — *Explainable Hybrid ML Ensembles on Edge IoT for Scalable Water Quality Monitoring* | Hybrid ensemble classification + SHAP explainability | RF + XGBoost + MLP (95.1% accuracy) | pH, DO, BOD, COD, EC, Turbidity, Temp, Flow Rate |
| **Cloud 2** — *Energy-Efficient IoT and ML Framework for Real-Time Water Contamination Monitoring* | Energy-aware edge sensing + YOLOv8 depth estimation | Random Forest (92.3% accuracy) | pH, DO, EC, Turbidity, Temp, Ammonia (NH3) |

### How It Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ZONE 1 — Sensing Layer                       │
│   Arduino Uno  ←  pH, DO, EC, Turbidity, Temp, NH3, Flow sensors    │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ UART / I2C
┌───────────────────────────▼─────────────────────────────────────────┐
│                     ZONE 2 — Edge Processing                        │
│   Raspberry Pi 4B                                                   │
│   • Data validation & hybrid imputation                             │
│   • Fuzzy C-Means clustering                                        │
│   • Hybrid ensemble classification (A–E)                            │
│   • TreeSHAP feature attribution                                    │
│   • YOLOv8 river depth estimation (Cloud 2)                         │
│   • 35 ms inference latency, < 2.5 W power                          │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ MQTT (4G/LTE/Wi-Fi)
┌───────────────────────────▼─────────────────────────────────────────┐
│               ZONE 3 — Cloud Integration (this repo)                │
│                                                                     │
│   ┌──────────┐   ┌───────────────┐   ┌──────────────┐               │
│   │Mosquitto │──▶│MQTT Subscriber│──▶│ TimescaleDB │               │
│   │(Auth)    │   │(Retry+Alerts) │   │ (Hypertable) │               │
│   └──────────┘   └───────────────┘   └──────┬───────┘               │
│                                             │                       │
│                        ┌────────────────────┼────────────┐          │
│                        │                    │            │          │
│                   ┌────▼────┐         ┌─────▼─────┐  ┌──▼───┐       │
│                   │ FastAPI │         │  Grafana  │  │Alerts│       │
│                   │ (Async) │         │ Dashboard │  │(SMTP)│       │
│                   └─────────┘         └───────────┘  └──────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

The cloud layer consists of **5 Docker containers** orchestrated via Docker Compose:

| Service | Image / Build | Port | Purpose |
|---------|--------------|------|---------|
| **db** | `timescale/timescaledb:latest-pg14` | `5432` | TimescaleDB hypertable for high-frequency sensor readings |
| **mosquitto** | Custom build (`mosquitto/Dockerfile`) | `11883` | MQTT broker with password authentication (remapped from 1883 for Hyper-V compatibility) |
| **mqtt_subscriber** | Custom build (`Dockerfile.subscriber`) | — | Continuous Python service: validates, inserts, alerts |
| **api** | Custom build (`Dockerfile.api`) | `8000` | FastAPI REST API with async DB, API key auth, Pydantic models |
| **grafana** | `grafana/grafana:latest` | `3000` | Auto-provisioned dashboard with 12 panels |

---

## 📁 Project Structure

```
water-cloud-backend/
├── app/                            # FastAPI application package
│   ├── config.py                   # pydantic-settings (env-based config)
│   ├── database.py                 # Async SQLAlchemy engine (asyncpg)
│   ├── models.py                   # ORM models (Station, SensorReading, Alert)
│   ├── dependencies.py             # X-API-Key authentication dependency
│   ├── main.py                     # App factory, lifespan, CORS, routers
│   ├── routers/
│   │   ├── stations.py             # GET /stations, /stations/{id}/latest, /history
│   │   ├── shap.py                 # GET /shap/{station_id}
│   │   └── health.py               # GET /health (no auth — Docker probe)
│   ├── schemas/                    # Pydantic response models
│   │   ├── stations.py             # StationOut, StationListResponse
│   │   ├── readings.py             # SensorReadingOut, HistoryResponse
│   │   └── alerts.py               # AlertOut, AlertListResponse
│   └── services/
│       └── alert_service.py        # Non-blocking SMTP (thread pool)
│
├── subscriber/                     # MQTT subscriber package
│   ├── config.py                   # Subscriber-specific settings (sync DB)
│   ├── handler.py                  # Pydantic validation → tenacity retry → threaded alerts
│   └── main.py                     # Entry point: signal handling, auto-reconnect
│
├── mosquitto/                      # Auth-enabled MQTT broker
│   ├── Dockerfile                  # Custom image with entrypoint
│   ├── entrypoint.sh               # Generates password_file from env at runtime
│   └── mosquitto.conf              # allow_anonymous false
│
├── grafana/provisioning/
│   ├── datasources/datasource.yml  # PostgreSQL datasource (hardcoded credentials)
│   └── dashboards/
│       ├── dashboard.yml           # Dashboard provider config
│       └── water_quality.json      # 12-panel water quality dashboard
│
├── schema.sql                      # TimescaleDB schema (v3 — merged papers)
├── docker-compose.yml              # Production-hardened orchestration
├── Dockerfile.api                  # API image (non-root user)
├── Dockerfile.subscriber           # Subscriber image (non-root user)
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
└── .gitignore
```

---

## 📊 Database Schema

The `sensor_readings` hypertable stores the **superset** of both papers. Fields that a given edge node does not report arrive as `NULL`.

| Column | Type | Source | Description |
|--------|------|--------|-------------|
| `time` | TIMESTAMPTZ | System | Insertion timestamp (hypertable partition key) |
| `station_id` | VARCHAR(50) | Edge | Monitoring station identifier (FK → stations) |
| `ph` | DECIMAL(4,2) | Both | Acidity / alkalinity (0–14) |
| `"do"` | DECIMAL(5,2) | Both | Dissolved oxygen (0–20 mg/L) (Quoted to avoid PostgreSQL reserved keyword) |
| `turbidity` | DECIMAL(8,2) | Both | Suspended solids (NTU) |
| `ec` | DECIMAL(8,2) | Both | Electrical conductivity (µS/cm) |
| `temperature` | DECIMAL(5,2) | Both | Water temperature (°C) |
| `bod` | DECIMAL(6,2) | Cloud 1 | Biochemical oxygen demand (mg/L) |
| `cod` | DECIMAL(6,2) | Cloud 1 | Chemical oxygen demand (mg/L) |
| `flow_rate` | DECIMAL(6,2) | Cloud 1 | Flow rate (L/min) |
| `ammonia` | DECIMAL(6,3) | Cloud 2 | NH₃ concentration (mg/L) |
| `river_depth` | DECIMAL(6,2) | Cloud 2 | YOLOv8 depth estimate (m) |
| `wqi` | DECIMAL(6,2) | Edge ML | Water Quality Index (0–100) |
| `water_class` | VARCHAR(1) | Edge ML | Classification result (A–E) |
| `edge_latency_ms` | INTEGER | Edge | Inference latency (ms) |
| `battery_voltage` | DECIMAL(4,2) | Cloud 2 | Edge node battery level (V) |
| `duty_cycle_s` | INTEGER | Cloud 2 | Sensing interval (seconds) |
| `missing_flags` | JSONB | Edge | Per-feature imputation flags |
| `shap_values` | JSONB | Edge | SHAP feature attributions |

All sensor columns have `CHECK` constraints enforcing physical ranges.

---

## 🔌 MQTT Payload Format

The Raspberry Pi edge nodes publish JSON to `water_quality/stations/{station_id}`:

```json
{
  "station_id": "ST-01",
  "ph": 7.2,
  "do": 6.5,
  "bod": 2.1,
  "cod": 15.4,
  "ec": 350,
  "turbidity": 12.5,
  "temperature": 24.5,
  "flow_rate": 1.2,
  "ammonia": 0.45,
  "river_depth": 2.8,
  "wqi": 85.0,
  "water_class": "B",
  "edge_latency_ms": 35,
  "battery_voltage": 11.8,
  "duty_cycle_s": 300,
  "missing_flags": {"bod": "median_imputed"},
  "shap_values": {"do": 0.45, "bod": -0.12, "ammonia": 0.08}
}
```

> **Note:** All fields except `station_id` are optional. A Cloud 1 node omits `ammonia` / `river_depth`; a Cloud 2 node omits `bod` / `cod` / `flow_rate`. The subscriber accepts both.

---

## 🚀 Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose v2)
- Git

### 1. Clone & Configure

```bash
git clone https://github.com/your-username/water-cloud-backend.git
cd water-cloud-backend

cp .env.example .env
# Edit .env with your real credentials
```

### 2. Build & Launch

```bash
docker compose up --build -d
```

This starts all 5 services. The DB healthcheck ensures schema.sql runs before dependent services start.

### 3. Verify

```bash
# Health check (no auth required)
curl http://localhost:8000/health
# → {"status": "healthy", "database": "connected"}

# List stations (requires API key)
curl -H "X-API-Key: YOUR_API_KEY" http://localhost:8000/stations

# OpenAPI docs
# Open http://localhost:8000/docs in your browser

# Grafana dashboard
# Open http://localhost:3000 (admin / your GF_SECURITY_ADMIN_PASSWORD)
```

### 4. Simulate an Edge Node

```bash
docker exec water-cloud-backend-mosquitto-1 mosquitto_pub \
  -u wateriot -P changeme_mqtt_password \
  -t "water_quality/stations/ST-01" \
  -m '{"station_id":"ST-01","ph":7.2,"do":6.5,"wqi":85,"water_class":"B","edge_latency_ms":35}'
```

> **Important:** If you are connecting from an external client or script on your host machine, use port **11883** (e.g. `localhost:11883`) instead of the standard `1883` to bypass Windows Hyper-V reserved port exclusions.

---

## 🔒 Security

| Layer | Mechanism |
|-------|-----------|
| **API** | `X-API-Key` header required on all endpoints (except `/health`) |
| **MQTT** | Username/password authentication (`allow_anonymous false`) |
| **Database** | Credentials via `.env` file (not hardcoded) |
| **Docker** | Non-root user in API and subscriber containers |
| **Secrets** | `.env` excluded from Git via `.gitignore` |

---

## 🛡️ Resilience Features

| Feature | Implementation |
|---------|---------------|
| **DB retry** | `tenacity` exponential backoff (5 attempts, 1–30 s) on every INSERT |
| **MQTT reconnect** | Auto-reconnect on disconnect + initial connection retry with backoff |
| **Healthchecks** | `pg_isready` (DB), `mosquitto_pub` (MQTT), HTTP `/health` (API) |
| **Startup ordering** | `depends_on: condition: service_healthy` prevents race conditions |
| **Non-blocking alerts** | SMTP emails run in daemon threads — never block MQTT loop or API |
| **Graceful shutdown** | SIGINT/SIGTERM handlers in subscriber for clean disconnect |
| **Restart policy** | `restart: unless-stopped` on all services |

---

## 📡 API Endpoints

All endpoints (except `/health`) require the `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe — DB connectivity check |
| `GET` | `/stations` | List all registered monitoring stations |
| `GET` | `/stations/{id}/latest` | Most recent sensor reading for a station |
| `GET` | `/stations/{id}/history?limit=100` | Historical readings (max 1000) |
| `GET` | `/shap/{station_id}` | Latest SHAP feature importance values |

Full OpenAPI spec available at `http://localhost:8000/docs`.

---

## 📈 Grafana Dashboard

The auto-provisioned dashboard includes **12 panels**:

| Row | Panels |
|-----|--------|
| **Overview** | Total Stations · Avg WQI (1h) · Polluted Stations (D/E) · Alerts Today |
| **Trends** | WQI Time Series (multi-station) · Water Class Distribution (donut) |
| **Sensors** | pH Over Time · DO/BOD/COD Over Time · Turbidity & EC · Edge Latency Gauge |
| **Details** | Latest Reading Per Station (table) · Recent Alerts (table) |

---

## ⚙️ Configuration Reference

All configuration is via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `wateradmin` | Database username |
| `POSTGRES_PASSWORD` | — | Database password |
| `POSTGRES_DB` | `waterdb` | Database name |
| `API_KEY` | — | Shared API key for FastAPI |
| `MQTT_USER` | `wateriot` | MQTT broker username |
| `MQTT_PASSWORD` | — | MQTT broker password |
| `SMTP_HOST` | `smtp` | SMTP server for email alerts |
| `SMTP_PORT` | `25` | SMTP port |
| `SMTP_USER` | — | Alert sender email |
| `ALERT_EMAIL` | — | Alert recipient email |
| `GF_SECURITY_ADMIN_PASSWORD` | — | Grafana admin password |

---

## 🧰 Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| API Framework | **FastAPI** + Uvicorn | Async, auto OpenAPI docs, Pydantic integration |
| Database | **TimescaleDB** (PostgreSQL 14) | Hypertables optimized for time-series IoT data |
| Async DB Driver | **asyncpg** + SQLAlchemy 2.0 | Non-blocking queries for 97-station concurrency |
| Message Broker | **Eclipse Mosquitto** | Lightweight MQTT broker, native IoT protocol |
| MQTT Client | **paho-mqtt** | Mature Python MQTT library |
| Config | **pydantic-settings** | Typed, validated config with `.env` support |
| Retry | **tenacity** | Declarative retry with exponential backoff |
| Dashboarding | **Grafana** | Rich time-series visualization with alerting |
| Deployment | **Docker Compose** | Reproducible, single-command deployment |

---

## 📚 Related Publications

1. **G. Singh, N. Anand** — *"Explainable Hybrid Machine Learning Ensembles on Edge IoT for Scalable Water Quality Monitoring"* — 97 stations, 340,200 samples, 95.1% accuracy, SHAP explainability.

2. **P. Kushwaha, N. Anand, G. Singh** — *"Energy-Efficient IoT and Machine Learning Framework for Real-Time Water Contamination Monitoring"* — Energy-aware edge sensing, YOLOv8 river depth estimation, 92.3% accuracy.

---

## 🤝 Acknowledgements

This research is financially supported by the **Council of Science and Technology, Uttar Pradesh (CSTUP)** under Project ID **CSTUP/2023/2389**.

---

## 📄 License

This project is part of academic research at **IIIT Lucknow**. Contact the authors for licensing information.
