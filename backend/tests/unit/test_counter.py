"""Unit tests for the virtual-line vehicle counter state machine."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.counter import VehicleCounter


@dataclass
class FakeTrack:
    track_id: int
    class_name: str
    cx: float
    cy: float

    @property
    def centroid(self) -> tuple[float, float]:
        return (self.cx, self.cy)


def make_counter(line_y: float = 100.0) -> VehicleCounter:
    return VehicleCounter(line_y=line_y)


def test_single_crossing_counts_once():
    counter = make_counter()
    # Above the line (y < 100) → no count yet
    counter.update([FakeTrack(1, "car", 50, 80)], frame_idx=0, timestamp=0.0)
    # Cross to below the line (y > 100) → count
    events = counter.update([FakeTrack(1, "car", 50, 120)], frame_idx=1, timestamp=0.04)
    assert len(events) == 1
    assert counter.total == 1
    assert counter.by_type()["car"] == 1


def test_no_double_count_on_repeat_oscillation_after_crossing():
    counter = make_counter()
    counter.update([FakeTrack(1, "car", 50, 80)], 0, 0.0)
    counter.update([FakeTrack(1, "car", 50, 120)], 1, 0.04)  # crosses → counted
    # Vehicle wobbles back and forth across the line; no extra increments.
    counter.update([FakeTrack(1, "car", 50, 80)], 2, 0.08)
    counter.update([FakeTrack(1, "car", 50, 120)], 3, 0.12)
    counter.update([FakeTrack(1, "car", 50, 80)], 4, 0.16)
    assert counter.total == 1


def test_stopped_vehicle_is_not_counted():
    counter = make_counter()
    # Stays above the line for many frames — never crosses.
    for f in range(20):
        counter.update([FakeTrack(1, "car", 50, 60)], f, f * 0.04)
    assert counter.total == 0
    assert counter.by_type()["car"] == 0


def test_multiple_vehicles_counted_independently():
    counter = make_counter()
    counter.update(
        [
            FakeTrack(1, "car", 50, 80),
            FakeTrack(2, "truck", 100, 80),
            FakeTrack(3, "bus", 150, 80),
        ],
        0,
        0.0,
    )
    counter.update(
        [
            FakeTrack(1, "car", 50, 120),
            FakeTrack(2, "truck", 100, 120),
            FakeTrack(3, "bus", 150, 120),
        ],
        1,
        0.04,
    )
    assert counter.total == 3
    by_type = counter.by_type()
    assert by_type["car"] == 1
    assert by_type["truck"] == 1
    assert by_type["bus"] == 1


def test_occlusion_persistence_via_same_id():
    """If ByteTrack keeps the same ID through occlusion, no double count occurs."""
    counter = make_counter()
    counter.update([FakeTrack(1, "car", 50, 80)], 0, 0.0)
    counter.update([FakeTrack(1, "car", 50, 120)], 1, 0.04)  # counted
    # Vehicle disappears for a few frames (no observation) — emulated by
    # passing an empty list. State is preserved; track_buffer in real ByteTrack
    # keeps the ID alive on re-emergence.
    for f in range(2, 8):
        counter.update([], f, f * 0.04)
    # Re-emerges past the line — same ID, latch is set, no second count.
    counter.update([FakeTrack(1, "car", 50, 130)], 8, 0.32)
    assert counter.total == 1


def test_new_id_after_long_loss_double_counts_only_once_per_track():
    """When ByteTrack issues a new ID (long occlusion), counter treats it as new."""
    counter = make_counter()
    # First track crosses.
    counter.update([FakeTrack(1, "car", 50, 80)], 0, 0.0)
    counter.update([FakeTrack(1, "car", 50, 120)], 1, 0.04)
    # Same physical car, but tracker assigned a new id after long loss.
    counter.update([FakeTrack(99, "car", 60, 80)], 50, 2.0)
    counter.update([FakeTrack(99, "car", 60, 120)], 51, 2.04)
    # Two separate tracks → 2 counts. Real-world mitigation lives in ByteTrack
    # configuration (track_buffer); this test documents the contract.
    assert counter.total == 2


def test_crossings_log_records_event_metadata():
    counter = make_counter()
    counter.update([FakeTrack(7, "motorcycle", 30, 50)], 0, 0.0)
    counter.update([FakeTrack(7, "motorcycle", 30, 150)], 5, 0.20)
    assert len(counter.crossings) == 1
    event = counter.crossings[0]
    assert event.track_id == 7
    assert event.class_name == "motorcycle"
    assert event.frame_idx == 5
    assert event.timestamp == 0.20


def test_unique_track_ids_tracked():
    counter = make_counter()
    counter.update([FakeTrack(1, "car", 0, 0), FakeTrack(2, "truck", 0, 0)], 0, 0.0)
    counter.update([FakeTrack(3, "bus", 0, 0)], 1, 0.04)
    assert counter.unique_track_ids == {1, 2, 3}
