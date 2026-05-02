-- ==========================================================================
-- Water Quality Monitoring — TimescaleDB Schema  (v3 – merged Cloud1 + Cloud2)
-- ==========================================================================
-- This file is mounted at /docker-entrypoint-initdb.d/schema.sql and runs
-- automatically on first container startup.  It is IDEMPOTENT (safe to
-- re-run on an empty database).
--
-- Cloud 1 sensors : pH, DO, BOD, COD, EC, Turbidity, Temperature, Flow Rate
-- Cloud 2 sensors : pH, DO, EC, Turbidity, Temperature, Ammonia (NH3)
--                   + YOLOv8 river depth estimation
-- Schema is the SUPERSET — missing sensors for a given node arrive as NULL.
-- ==========================================================================

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ── Stations ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stations (
    id          VARCHAR(50) PRIMARY KEY,
    name        VARCHAR(100),
    latitude    DECIMAL(10, 8),
    longitude   DECIMAL(11, 8),
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ── Sensor Readings (hypertable) ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sensor_readings (
    time            TIMESTAMP WITH TIME ZONE NOT NULL,
    station_id      VARCHAR(50) REFERENCES stations(id),

    -- ── Core water-quality parameters (both papers) ──────────────────────
    ph              DECIMAL(4, 2)   CHECK (ph >= 0 AND ph <= 14),
    "do"            DECIMAL(5, 2)   CHECK ("do" >= 0 AND "do" <= 20),
    turbidity       DECIMAL(8, 2)   CHECK (turbidity >= 0),
    ec              DECIMAL(8, 2)   CHECK (ec >= 0),
    temperature     DECIMAL(5, 2),

    -- ── Cloud 1 additional sensors ──────────────────────────────────────
    bod             DECIMAL(6, 2)   CHECK (bod >= 0),
    cod             DECIMAL(6, 2)   CHECK (cod >= 0),
    flow_rate       DECIMAL(6, 2)   CHECK (flow_rate >= 0),

    -- ── Cloud 2 additional sensors ──────────────────────────────────────
    ammonia         DECIMAL(6, 3)   CHECK (ammonia >= 0),        -- NH3 mg/L
    river_depth     DECIMAL(6, 2)   CHECK (river_depth >= 0),    -- YOLOv8 estimate (m)

    -- ── Derived / ML outputs ────────────────────────────────────────────
    wqi             DECIMAL(6, 2)   CHECK (wqi >= 0 AND wqi <= 100),
    water_class     VARCHAR(1)      CHECK (water_class IN ('A','B','C','D','E')),

    -- ── Edge metadata ───────────────────────────────────────────────────
    edge_latency_ms INTEGER         CHECK (edge_latency_ms >= 0),
    battery_voltage DECIMAL(4, 2),                               -- Cloud 2 energy awareness
    duty_cycle_s    INTEGER,                                     -- sensing interval in seconds
    missing_flags   JSONB DEFAULT '{}',
    shap_values     JSONB DEFAULT '{}'
);

SELECT create_hypertable('sensor_readings', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS ix_sensor_readings_station_time
    ON sensor_readings (station_id, time DESC);
CREATE INDEX IF NOT EXISTS ix_sensor_readings_class
    ON sensor_readings (water_class);
CREATE INDEX IF NOT EXISTS ix_sensor_readings_ammonia
    ON sensor_readings (ammonia)
    WHERE ammonia IS NOT NULL;

-- ── Alerts ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    id           SERIAL PRIMARY KEY,
    time         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    station_id   VARCHAR(50) REFERENCES stations(id),
    water_class  VARCHAR(1) CHECK (water_class IN ('A','B','C','D','E')),
    alert_type   VARCHAR(20),
    recipient    VARCHAR(100),
    message      TEXT,
    resolved     BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_alerts_station_time
    ON alerts (station_id, time DESC);