"""OBD2 service for RigSherpa.

Manages Bluetooth/serial OBD2 adapter connections, DTC reading, live
sensor data, and freeze-frame capture.  Uses the python-OBD library.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DTCInfo:
    code: str
    description: str
    status: str = "active"


@dataclass
class SensorSnapshot:
    timestamp: datetime
    rpm: Optional[int] = None
    speed_mph: Optional[float] = None
    coolant_temp_f: Optional[float] = None
    intake_temp_f: Optional[float] = None
    throttle_pct: Optional[float] = None
    engine_load_pct: Optional[float] = None
    fuel_pressure_psi: Optional[float] = None
    voltage: Optional[float] = None
    raw: dict = field(default_factory=dict)


class OBD2Service:
    """Manages OBD2 adapter interaction."""

    def __init__(
        self,
        port: str | None = None,
        baudrate: int | None = None,
        protocol: str | None = None,
    ) -> None:
        self.port = port or settings.obd2_port
        self.baudrate = baudrate or settings.obd2_baudrate
        self.protocol = protocol or settings.obd2_protocol
        self._connection = None

    # -- connection -------------------------------------------------------

    def connect(self) -> bool:
        """Open OBD2 connection.  Returns True on success."""
        try:
            import obd

            if self.port:
                self._connection = obd.OBD(
                    self.port,
                    baudrate=self.baudrate,
                    protocol=self.protocol,
                    fast=False,
                )
            else:
                # Auto-detect port
                self._connection = obd.OBD(fast=False)

            if self._connection.is_connected():
                logger.info("OBD2 connected: %s", self._connection.port_name())
                return True

            logger.warning("OBD2 adapter found but not connected to ECU")
            return False
        except Exception as exc:
            logger.error("OBD2 connection failed: %s", exc)
            return False

    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("OBD2 disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.is_connected()

    # -- DTCs -------------------------------------------------------------

    def read_dtcs(self) -> list[DTCInfo]:
        """Read current Diagnostic Trouble Codes."""
        if not self.is_connected:
            return []
        try:
            import obd

            response = self._connection.query(obd.commands.GET_DTC)
            if response.is_null():
                return []
            dtcs = []
            for code, desc in response.value:
                dtcs.append(DTCInfo(code=code, description=desc or "Unknown"))
            return dtcs
        except Exception as exc:
            logger.error("Failed to read DTCs: %s", exc)
            return []

    def clear_dtcs(self) -> bool:
        """Clear DTCs (use with caution)."""
        if not self.is_connected:
            return False
        try:
            import obd

            self._connection.query(obd.commands.CLEAR_DTC)
            logger.info("DTCs cleared")
            return True
        except Exception as exc:
            logger.error("Failed to clear DTCs: %s", exc)
            return False

    # -- live data --------------------------------------------------------

    def read_sensors(self) -> SensorSnapshot:
        """Take a snapshot of current sensor values."""
        snap = SensorSnapshot(timestamp=datetime.utcnow())
        if not self.is_connected:
            return snap

        try:
            import obd

            def _query(cmd):
                r = self._connection.query(cmd)
                return r.value if not r.is_null() else None

            rpm = _query(obd.commands.RPM)
            if rpm is not None:
                snap.rpm = int(rpm.magnitude)

            speed = _query(obd.commands.SPEED)
            if speed is not None:
                snap.speed_mph = round(speed.to("mph").magnitude, 1)

            coolant = _query(obd.commands.COOLANT_TEMP)
            if coolant is not None:
                snap.coolant_temp_f = round(coolant.to("degF").magnitude, 1)

            intake = _query(obd.commands.INTAKE_TEMP)
            if intake is not None:
                snap.intake_temp_f = round(intake.to("degF").magnitude, 1)

            throttle = _query(obd.commands.THROTTLE_POS)
            if throttle is not None:
                snap.throttle_pct = round(throttle.magnitude, 1)

            load = _query(obd.commands.ENGINE_LOAD)
            if load is not None:
                snap.engine_load_pct = round(load.magnitude, 1)

        except Exception as exc:
            logger.error("Sensor read error: %s", exc)

        return snap

    # -- status -----------------------------------------------------------

    def status(self) -> dict:
        """Return adapter / ECU status summary."""
        if not self.is_connected:
            return {"connected": False, "port": self.port}
        return {
            "connected": True,
            "port": self._connection.port_name(),
            "protocol": str(self._connection.protocol_name()),
            "ecu_available": self._connection.is_connected(),
        }
