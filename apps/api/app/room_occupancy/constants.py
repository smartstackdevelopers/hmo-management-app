"""F6.5 constants — privacy-sensitive occupancy module."""

from __future__ import annotations

GATE_STATUSES = frozenset({"not_started", "in_progress", "completed", "approved", "rejected"})
REQUIRED_GATE_FIELDS = (
    "feasibility_status",
    "dpia_status",
    "signage_status",
    "retention_policy_status",
    "camera_compatibility_status",
)

OCCUPANCY_STATUSES = frozenset(
    {"available", "occupied", "near_capacity", "at_capacity", "offline"}
)

DEVICE_TYPES = frozenset({"edge_people_counter", "onvif_camera", "rtsp_camera", "sensor"})
DEVICE_CONNECTION_STATUSES = frozenset(
    {"pending", "online", "offline", "error", "disabled", "incompatible"}
)

# Cameras must never be assigned to these room types (privacy rule).
FORBIDDEN_ROOM_TYPE_KEYWORDS = frozenset(
    {"bedroom", "bathroom", "changing", "changing_room", "ensuite", "toilet", "shower"}
)

ALERT_CATEGORIES = frozenset(
    {"at_capacity", "near_capacity", "device_offline", "missing_updates", "connection_failure"}
)

APPROVED_ONLY = "approved"
