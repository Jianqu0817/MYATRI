"""Verify the new race regression rejects the interrupted implementation.

Only mutates the imported method in this probe process, never source files.
"""
import inspect
import textwrap

import pytest

import myatri.memory.index as module


source = inspect.getsource(module.MemoryIndex._prepare_rebuild)
source = source.replace("        installed = self.capture_state()\n", "", 1)
source = source.replace(
    '        cache = dict(installed["embedding_cache"])',
    '        installed = self.capture_state()\n        cache = dict(installed["embedding_cache"])',
    1,
)
namespace = {}
exec(textwrap.dedent(source), module.__dict__, namespace)
module.MemoryIndex._prepare_rebuild = namespace["_prepare_rebuild"]
result = pytest.main([
    "tests/test_memory_consistency.py::test_delayed_snapshot_cannot_copy_future_theme_summary_into_saved_generation",
    "-q", "--tb=short", "--basetemp=reports/fix_memory_mutation_tmp",
])
if result != pytest.ExitCode.TESTS_FAILED:
    raise SystemExit(f"Expected the old ordering to fail the regression, got {result}")
print("EXPECTED MUTATION FAILURE OBSERVED; production source was not changed.")
