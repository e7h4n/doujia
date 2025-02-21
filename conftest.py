"""pytest 参数定义"""

from os import path
from textwrap import dedent

import certifi
import logzero
import pytest
from beancount.core.data import Directive
from beancount.loader import load_file
from fava.core import FavaLedger
from flask import Flask
from logzero import DEBUG, INFO
from pyfakefs.fake_filesystem import FakeFilesystem

from doujia.server import create_app


def pytest_configure(config):
    """根据 -v 参数设置日志级别"""
    if config.getoption("verbose") > 0:
        logzero.loglevel(DEBUG)
    else:
        logzero.loglevel(INFO)


def pytest_addoption(parser):
    """pytest 参数定义"""

    parser.addoption("--username", action="store", help="Username")
    parser.addoption("--password", action="store", help="Password")


@pytest.fixture()
def doc_fs_ledger_filename(request: pytest.FixtureRequest, fs: FakeFilesystem) -> str:
    """Load the docstring as a Beancount file."""
    doc_contents = dedent(request.function.__doc__).splitlines()

    current_file: str | None = None
    contents: list[str] = []
    first_ledger_file: str | None = None
    for line in doc_contents:
        if current_file is None:
            if line.startswith("@@@"):
                current_file = line[3:]
                if current_file.endswith(".bean") and first_ledger_file is None:
                    first_ledger_file = current_file
        else:
            if line.startswith("@@@"):
                fs.create_file(current_file, contents="\n".join(contents))
                contents = []
                current_file = line[3:]
                if current_file.endswith(".bean") and first_ledger_file is None:
                    first_ledger_file = current_file
            else:
                contents.append(line)

    if current_file:
        fs.create_file(current_file, contents="\n".join(contents))
        if current_file.endswith(".bean") and first_ledger_file is None:
            first_ledger_file = current_file

    return first_ledger_file


@pytest.fixture()
def entries(doc_fs_ledger_filename: str) -> list[Directive]:  # type: ignore
    assert doc_fs_ledger_filename
    entries, _, _ = load_file(doc_fs_ledger_filename)
    return entries


@pytest.fixture()
def entries_options(doc_fs_ledger_filename: str) -> list[Directive]:  # type: ignore
    assert doc_fs_ledger_filename
    entries, _, options_map = load_file(doc_fs_ledger_filename)
    return (entries, options_map)


@pytest.fixture()
def doc_ledger(request: pytest.FixtureRequest, fs: FakeFilesystem) -> FavaLedger:
    """Load the docstring as a Beancount file."""
    doc_contents = dedent(request.function.__doc__).splitlines()

    current_file: str | None = None
    contents: list[str] = []
    first_ledger_file: str | None = None
    for line in doc_contents:
        if current_file is None:
            if line.startswith("@@@"):
                current_file = line[3:]
                if current_file.endswith(".bean") and first_ledger_file is None:
                    first_ledger_file = current_file
        else:
            if line.startswith("@@@"):
                fs.create_file(current_file, contents="\n".join(contents))
                contents = []
                current_file = line[3:]
                if current_file.endswith(".bean") and first_ledger_file is None:
                    first_ledger_file = current_file
            else:
                contents.append(line)
    if current_file:
        fs.create_file(current_file, contents="\n".join(contents))
        if current_file.endswith(".bean") and first_ledger_file is None:
            first_ledger_file = current_file

    assert first_ledger_file
    return FavaLedger(path=first_ledger_file)


@pytest.fixture
def init_certificates(fs: FakeFilesystem):
    real_cert_path = certifi.where()
    fs.add_real_file(real_cert_path)


@pytest.fixture(name="app")
def _app():
    return create_app(
        {
            "TESTING": True,
            "CORBADO_API_SECRET": "test-secret",
            "LEDGER_ROOT": path.join(path.dirname(__file__), "src/doujia/server/__tests__"),
        }
    )


@pytest.fixture(name="client")
def _client(app: Flask):
    return app.test_client()
