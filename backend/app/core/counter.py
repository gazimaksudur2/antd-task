"""Virtual line crossing counter that prevents double-counting.

Algorithm
---------
A horizontal counting line is placed at ``line_y_ratio * frame_height`` (default
50%). For every track we maintain a small state machine:

* ``side`` — the most recent side of the line where the centroid was observed
  (``-1`` above, ``+1`` below).
* ``crossed`` — boolean latch flipped on the first transition between sides.

A vehicle is counted **once** the first time its centroid changes ``side``. The
latch ensures repeat oscillations near the line do not increment the counter,
and the ByteTrack ``track_buffer`` keeps the same ``track_id`` across short
occlusions so re-emerging vehicles re-use the existing latched state.

This handles all the assessment edge cases:

* Stop-and-go traffic: ``side`` stays the same → no extra increments.
* Brief occlusion (lamppost, bridge): track id is preserved → ``crossed``
  remains ``True`` → no double count when the vehicle reappears.
* Long-term loss (track expires): a brand-new id is issued, which is the only
  case where double counting could occur — capped by configuring a long enough
  ``track_buffer``.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class _TrackState:
    side: int = 0  # -1 above, +1 below, 0 unknown
    crossed: bool = False
    first_seen: int = 0
    last_seen: int = 0
    class_name: str = "vehicle"


@dataclass
class CountEvent:
    """Emitted the moment a track first crosses the counting line."""

    track_id: int
    class_name: str
    frame_idx: int
    timestamp: float


@dataclass
class VehicleCounter:
    """Stateful per-job counter."""

    line_y: float
    states: dict[int, _TrackState] = field(default_factory=dict)
    counts: Counter[str] = field(default_factory=Counter)
    crossings: list[CountEvent] = field(default_factory=list)
    unique_track_ids: set[int] = field(default_factory=set)
    track_classes: dict[int, str] = field(default_factory=dict)

    @classmethod
    def from_frame_size(cls, frame_height: int, line_y_ratio: float = 0.5) -> "VehicleCounter":
        return cls(line_y=float(frame_height) * line_y_ratio)

    def update(
        self,
        tracks: list,  # list[Track], avoid circular import
        frame_idx: int,
        timestamp: float,
    ) -> list[CountEvent]:
        """Feed the latest tracked detections; return any newly-counted events."""
        new_events: list[CountEvent] = []
        for t in tracks:
            self.unique_track_ids.add(t.track_id)
            self.track_classes[t.track_id] = t.class_name

            cy = t.centroid[1]
            current_side = -1 if cy < self.line_y else 1
            state = self.states.get(t.track_id)
            if state is None:
                state = _TrackState(
                    side=current_side,
                    first_seen=frame_idx,
                    last_seen=frame_idx,
                    class_name=t.class_name,
                )
                self.states[t.track_id] = state
                continue

            state.last_seen = frame_idx
            state.class_name = t.class_name

            if not state.crossed and state.side != 0 and current_side != state.side:
                state.crossed = True
                self.counts[t.class_name] += 1
                event = CountEvent(
                    track_id=t.track_id,
                    class_name=t.class_name,
                    frame_idx=frame_idx,
                    timestamp=timestamp,
                )
                self.crossings.append(event)
                new_events.append(event)
            state.side = current_side
        return new_events

    @property
    def total(self) -> int:
        return int(sum(self.counts.values()))

    def by_type(self) -> dict[str, int]:
        # Always expose the standard four classes, even if zero, for stable UI.
        out: dict[str, int] = defaultdict(int)
        for cls in ("car", "truck", "bus", "motorcycle"):
            out[cls] = int(self.counts.get(cls, 0))
        for cls, n in self.counts.items():
            out[cls] = int(n)
        return dict(out)
