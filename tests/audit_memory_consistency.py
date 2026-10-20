"""Compatibility entry point; regressions now run in the default test suite."""
from test_memory_consistency import (  # noqa: F401
    OBSERVATIONS,
    test_historical_snapshot_must_not_use_future_semantic_edges,
    test_slow_older_rebuild_must_not_regress_current_watermark,
)
