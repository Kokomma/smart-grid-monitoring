-- ============================================================
-- Smart Grid Monitoring — Readings Table
-- Auto-runs when PostgreSQL container starts via Docker
-- ============================================================

CREATE TABLE IF NOT EXISTS grid_readings (
    id              BIGSERIAL PRIMARY KEY,
    reading_id      VARCHAR(60),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feeder_id       VARCHAR(20),
    disco           VARCHAR(60),
    lga             VARCHAR(60),
    voltage_pu      NUMERIC(6,4),
    voltage_phase_a NUMERIC(8,2),
    voltage_phase_b NUMERIC(8,2),
    voltage_phase_c NUMERIC(8,2),
    current_a       NUMERIC(10,2),
    load_kva        NUMERIC(10,2),
    load_pct        NUMERIC(6,2),
    power_factor    NUMERIC(5,3),
    frequency_hz    NUMERIC(5,2),
    temperature_c   NUMERIC(5,1),
    oil_level_pct   NUMERIC(5,1),
    is_energised    BOOLEAN,
    status          VARCHAR(20),
    alert_code      VARCHAR(20),
    alert_message   TEXT
);

CREATE TABLE IF NOT EXISTS grid_events (
    id                   BIGSERIAL PRIMARY KEY,
    event_id             VARCHAR(40),
    timestamp            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feeder_id            VARCHAR(20),
    disco                VARCHAR(60),
    lga                  VARCHAR(60),
    event_type           VARCHAR(30),
    fault_type           VARCHAR(60),
    estimated_customers  INT,
    estimated_mwh_lost   NUMERIC(10,2),
    cause                TEXT,
    severity             VARCHAR(20)
);

CREATE INDEX IF NOT EXISTS idx_readings_timestamp  ON grid_readings(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_readings_feeder     ON grid_readings(feeder_id);
CREATE INDEX IF NOT EXISTS idx_readings_status     ON grid_readings(status);
CREATE INDEX IF NOT EXISTS idx_events_timestamp    ON grid_events(timestamp DESC);

-- Seed feeder reference data
CREATE TABLE IF NOT EXISTS dim_feeders (
    feeder_id       VARCHAR(20) PRIMARY KEY,
    disco           VARCHAR(60),
    lga             VARCHAR(60),
    capacity_kva    INT,
    load_class      VARCHAR(20),
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6)
);

INSERT INTO dim_feeders VALUES
('ABJ-F01','Abuja DisCo',         'Municipal',       500,  'mixed',       9.0574,  7.4898),
('ABJ-F02','Abuja DisCo',         'Gwagwalada',      300,  'residential', 8.9408,  7.0801),
('IKJ-F01','Ikeja DisCo',         'Ikeja',           1000, 'commercial',  6.6018,  3.3515),
('IKJ-F02','Ikeja DisCo',         'Agege',           750,  'industrial',  6.6214,  3.3228),
('EKO-F01','Eko DisCo',           'Victoria Island', 2000, 'commercial',  6.4281,  3.4219),
('EKO-F02','Eko DisCo',           'Surulere',        800,  'residential', 6.5059,  3.3550),
('KAN-F01','Kano DisCo',          'Fagge',           600,  'mixed',       12.0022, 8.5920),
('PHC-F01','Port Harcourt DisCo', 'GRA',             1500, 'industrial',  4.8242,  7.0336),
('IBD-F01','Ibadan DisCo',        'Ibadan North',    400,  'residential', 7.3775,  3.9470),
('YOL-F01','Yola DisCo',          'Yola North',      200,  'residential', 9.2035,  12.4954)
ON CONFLICT DO NOTHING;
