import pytest

from database.load_database import _get_database_config


def test_get_database_config_reads_environment(
        monkeypatch
):
    """
    ETL database configuration should be read from the
    Treasury environment variables.
    """

    monkeypatch.setenv(
        "TREASURY_DB_HOST",
        "test-host"
    )

    monkeypatch.setenv(
        "TREASURY_DB_PORT",
        "3307"
    )

    monkeypatch.setenv(
        "TREASURY_DB_NAME",
        "test_database"
    )

    monkeypatch.setenv(
        "TREASURY_ETL_DB_USER",
        "test_etl_user"
    )

    monkeypatch.setenv(
        "TREASURY_ETL_DB_PASSWORD",
        "test_password"
    )

    config = _get_database_config()

    assert config == {
        "host": "test-host",
        "port": 3307,
        "name": "test_database",
        "user": "test_etl_user",
        "password": "test_password"
    }


def test_get_database_config_requires_etl_user(
        monkeypatch
):
    """
    Missing ETL username should fail before any database
    connection is attempted.
    """

    monkeypatch.delenv(
        "TREASURY_ETL_DB_USER",
        raising=False
    )

    monkeypatch.setenv(
        "TREASURY_ETL_DB_PASSWORD",
        "test_password"
    )

    with pytest.raises(
        RuntimeError,
        match="TREASURY_ETL_DB_USER"
    ):
        _get_database_config()


def test_get_database_config_requires_etl_password(
        monkeypatch
):
    """
    Missing ETL password should fail before any database
    connection is attempted.
    """

    monkeypatch.setenv(
        "TREASURY_ETL_DB_USER",
        "test_etl_user"
    )

    monkeypatch.delenv(
        "TREASURY_ETL_DB_PASSWORD",
        raising=False
    )

    with pytest.raises(
        RuntimeError,
        match="TREASURY_ETL_DB_PASSWORD"
    ):
        _get_database_config()


def test_explicit_credentials_override_environment(
        monkeypatch
):
    """
    Explicit credentials should override environment
    credentials for controlled testing or other use.
    """

    monkeypatch.setenv(
        "TREASURY_ETL_DB_USER",
        "environment_user"
    )

    monkeypatch.setenv(
        "TREASURY_ETL_DB_PASSWORD",
        "environment_password"
    )

    config = _get_database_config(
        db_user="override_user",
        db_password="override_password"
    )

    assert config["user"] == "override_user"

    assert (
        config["password"]
        == "override_password"
    )