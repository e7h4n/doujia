import os
import re
from collections import Counter
from pathlib import Path
from pprint import pformat
from typing import Any

import pytest
from fava.core import FavaLedger
from fava.core.charts import dumps
from fava.util.date import local_today

from .typing import SnapshotFunc


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Path to the test data files."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="module")
def module_path(request: pytest.FixtureRequest) -> Path:
    """Path to the tested module."""
    fspath = getattr(request, "fspath")
    return Path(getattr(request, "path", fspath))


@pytest.fixture(scope="module")
def snap_count() -> Counter[str]:
    """Counter for the number of snapshots per function in a module."""
    return Counter()


@pytest.fixture(scope="module")
def snap_dir(module_path: Path) -> Path:
    """Path to snapshot directory."""
    snap_dir = module_path.parent / "__snapshots__"
    if not snap_dir.exists():
        snap_dir.mkdir()
    return snap_dir


@pytest.fixture()
def snapshot(
    request: pytest.FixtureRequest,
    test_data_dir: Path,
    module_path: Path,
    snap_dir: Path,
    snap_count: Counter[str],
) -> SnapshotFunc:
    """Create a snaphot for some given data."""
    fn_name = request.function.__name__
    module_name = module_path.stem

    def snapshot_data(
        data: Any,
        name: str | None = None,
        *,
        json: bool = False,
    ) -> None:
        if os.environ.get("SNAPSHOT_IGNORE"):
            # For the tests runs with old dependencies, we avoid comparing
            # the snapshots, as they might change in subtle ways between
            # dependency versions.
            return

        snap_count[fn_name] += 1
        filename = f"{module_name}-{fn_name}"
        if name:
            filename = f"{filename}-{name}"
        elif snap_count[fn_name] > 1:
            filename = f"{filename}-{snap_count[fn_name]}"

        if json:
            if not isinstance(data, str):
                data = dumps(data)
            filename += ".json"

        snap_file = snap_dir / filename

        # print strings directly, otherwise try pretty-printing
        out = data if isinstance(data, str) else pformat(data)
        # replace today
        today = local_today()
        out = out.replace(str(today), "TODAY")
        # replace entry hashes
        out = re.sub(r'"[0-9a-f]{32}', '"ENTRY_HASH', out)
        out = re.sub(r"context-[0-9a-f]{32}", "context-ENTRY_HASH", out)
        # replace mtimes
        out = re.sub(r"mtime=\d+", "mtime=MTIME", out)
        out = re.sub(r'id="ledger-mtime">\d+', 'id="ledger-mtime">MTIME', out)
        # replace env-dependant info
        out = out.replace('have_excel": false', 'have_excel": true')

        for dir_path, replacement in [
            (str(test_data_dir), "TEST_DATA_DIR"),
        ]:
            if os.name == "nt":
                search = dir_path.replace("\\", "\\\\") + "\\\\"
                out = out.replace(search, replacement + "/")
            else:
                out = out.replace(dir_path, replacement)

        if os.environ.get("SNAPSHOT_UPDATE"):
            snap_file.write_text(out, "utf-8")
        else:
            contents = snap_file.read_text("utf-8") if snap_file.exists() else ""
            assert out == contents, "Snaphot test failed. Snapshots can be updated with `SNAPSHOT_UPDATE=1 pytest`"

    return snapshot_data


@pytest.fixture()
def doc_ledger(doc_fs_ledger_filename: str) -> FavaLedger:
    assert doc_fs_ledger_filename
    return FavaLedger(path=doc_fs_ledger_filename)
