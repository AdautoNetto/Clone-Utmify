"""
Os testes rodam contra um Postgres de verdade (o app usa recursos do Postgres).
Use um banco VAZIO e descartável — os testes apagam tudo dele:

    TEST_DATABASE_URL=postgresql://postgres@localhost:5432/logpose_test pytest tests -q
"""
import os
import uuid

import pytest

TEST_DB = os.getenv("TEST_DATABASE_URL")
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ.setdefault("SECRET_KEY", "chave-so-para-teste-" + uuid.uuid4().hex)


def pytest_collection_modifyitems(config, items):
    if TEST_DB:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL não definido")
    for item in items:
        item.add_marker(skip)


def pytest_ignore_collect(collection_path, config):
    # Sem banco de teste nem dá para importar o app (ele conecta ao subir)
    return (not TEST_DB) and collection_path.name.startswith("test_")
