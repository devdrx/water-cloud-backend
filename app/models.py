"""SQLAlchemy 2.0 Declarative ORM models.

These models mirror the TimescaleDB schema in ``schema.sql`` (v3) and are
used by the async API.  The schema is the **superset** of both research
papers:

* Cloud 1 sensors: pH, DO, BOD, COD, EC, Turbidity, Temperature, Flow Rate
* Cloud 2 sensors: pH, DO, EC, Turbidity, Temperature, Ammonia, River Depth

Fields that a given edge node does not report arrive as NULL.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all models."""


class Station(Base):
    __tablename__ = "stations"

    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    status = Column(String(20), server_default="active")
    created_at = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")

    readings = relationship("SensorReading", back_populates="station", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Station {self.id}>"


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        CheckConstraint("ph >= 0 AND ph <= 14", name="ck_ph_range"),
        CheckConstraint("\"do\" >= 0 AND \"do\" <= 20", name="ck_do_range"),
        CheckConstraint("turbidity >= 0", name="ck_turbidity_pos"),
        CheckConstraint("ec >= 0", name="ck_ec_pos"),
        CheckConstraint("bod >= 0", name="ck_bod_pos"),
        CheckConstraint("cod >= 0", name="ck_cod_pos"),
        CheckConstraint("flow_rate >= 0", name="ck_flow_rate_pos"),
        CheckConstraint("ammonia >= 0", name="ck_ammonia_pos"),
        CheckConstraint("river_depth >= 0", name="ck_river_depth_pos"),
        CheckConstraint("wqi >= 0 AND wqi <= 100", name="ck_wqi_range"),
        CheckConstraint(
            "water_class IN ('A','B','C','D','E')", name="ck_water_class"
        ),
        CheckConstraint("edge_latency_ms >= 0", name="ck_latency_pos"),
    )

    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    station_id = Column(
        String(50), ForeignKey("stations.id"), primary_key=True
    )

    # ── Core parameters (both papers) ────────────────────────────────
    ph = Column(Numeric(4, 2))
    do = Column("do", Numeric(5, 2))
    turbidity = Column(Numeric(8, 2))
    ec = Column(Numeric(8, 2))
    temperature = Column(Numeric(5, 2))

    # ── Cloud 1 additional sensors ───────────────────────────────────
    bod = Column(Numeric(6, 2))
    cod = Column(Numeric(6, 2))
    flow_rate = Column(Numeric(6, 2))

    # ── Cloud 2 additional sensors ───────────────────────────────────
    ammonia = Column(Numeric(6, 3))          # NH3 mg/L
    river_depth = Column(Numeric(6, 2))      # YOLOv8 estimate (m)

    # ── Derived / ML outputs ─────────────────────────────────────────
    wqi = Column(Numeric(6, 2))
    water_class = Column(String(1))

    # ── Edge metadata ────────────────────────────────────────────────
    edge_latency_ms = Column(Integer)
    battery_voltage = Column(Numeric(4, 2))  # Cloud 2 energy awareness
    duty_cycle_s = Column(Integer)           # sensing interval (seconds)
    missing_flags = Column(JSONB, server_default="{}")
    shap_values = Column(JSONB, server_default="{}")

    station = relationship("Station", back_populates="readings")

    def __repr__(self) -> str:
        return f"<SensorReading {self.station_id}@{self.time}>"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    time = Column(DateTime(timezone=True), server_default="CURRENT_TIMESTAMP")
    station_id = Column(String(50), ForeignKey("stations.id"))
    water_class = Column(String(1))
    alert_type = Column(String(20))
    recipient = Column(String(100))
    message = Column(Text)
    resolved = Column(Boolean, server_default="false")

    def __repr__(self) -> str:
        return f"<Alert {self.id} station={self.station_id}>"
