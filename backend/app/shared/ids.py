"""app/shared/ids.py — UUIDv7 (RFC 9562) primary keys for every table.

Time-ordered: new rows land at the end of the B-tree index (fast inserts, ids sortable by creation time),
yet still unguessable in URLs. Monotonic within the process: a 12-bit counter (randomly seeded each
millisecond) orders ids created in the same millisecond. Replace with `uuid.uuid7()` once on Python 3.14.
"""

import os
import threading
import time
import uuid

_lock = threading.Lock()
_last_ms = -1
_counter = 0
_COUNTER_MAX = 0xFFF


def uuid7() -> uuid.UUID:
    global _last_ms, _counter
    with _lock:
        ms = time.time_ns() // 1_000_000
        if ms > _last_ms:
            _last_ms = ms
            _counter = int.from_bytes(os.urandom(2)) & 0x3FF  # seed leaves headroom for the counter
        else:  # same millisecond or the clock went backwards: keep ordering by counting on the last ms
            _counter += 1
            if _counter > _COUNTER_MAX:
                _last_ms += 1
                _counter = 0
        ms, counter = _last_ms, _counter
    rand_b = int.from_bytes(os.urandom(8)) & ((1 << 62) - 1)
    value = (ms & ((1 << 48) - 1)) << 80 | 0x7 << 76 | counter << 64 | 0b10 << 62 | rand_b
    return uuid.UUID(int=value)
