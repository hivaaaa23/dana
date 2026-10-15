import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND / "scripts"))


GOOD = {"APP_ENV": "production", "SECRET_KEY": "x" * 48, "CORS_ORIGINS": "https://dana.example.com",
        "APP_ENCRYPTION_KEY": "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=", "LOG_CHAT_CONTENT": "0",
        "LOG_RETENTION_DAYS": "0", "DATABASE_URL": "sqlite://"}


def run_config(code="import app.config", **env):
    """config را در پروسه‌ی جدا import می‌کند (reload داخل پروسه‌ی تست، شیء settings را عوض می‌کرد)."""
    import os
    e = {k: v for k, v in os.environ.items() if k not in GOOD}
    e.update({**GOOD, **env})
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=e, capture_output=True, text=True)


def test_production_ok():
    r = run_config()
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("env", [
    {"SECRET_KEY": "short"},
    {"SECRET_KEY": "change-this-to-a-long-random-secret-aaaaaaaaaaaa"},
    {"CORS_ORIGINS": "*"},
    {"APP_ENCRYPTION_KEY": "replace-with-a-fernet-key"},
    {"LOG_CHAT_CONTENT": "1", "LOG_RETENTION_DAYS": "0"},
])
def test_production_rejects_unsafe_config(env):
    r = run_config(**env)
    assert r.returncode != 0 and "RuntimeError" in r.stderr


def test_production_accepts_content_logging_with_retention():
    assert run_config(LOG_CHAT_CONTENT="1", LOG_RETENTION_DAYS="30").returncode == 0


def test_widget_origins_required_defaults():
    code = "from app.config import widget_origins_required as w; print(w())"
    assert run_config(code).stdout.strip() == "True"
    assert run_config(code, APP_ENV="development").stdout.strip() == "False"
    assert run_config(code, WIDGET_REQUIRE_ALLOWED_ORIGINS="false").stdout.strip() == "False"


# ---- gen_env ----
def args(*a):
    import gen_env
    return gen_env.parse_args(list(a))


def test_gen_env_production_output():
    import gen_env
    tpl = (BACKEND / ".env.example").read_text(encoding="utf-8")
    out = gen_env.build_env(tpl, args("--production", "--cors", "https://dana.example.com/", "--redis", "redis://r:6379/0", "--proxies", "1"))
    lines = dict(l.split("=", 1) for l in out.splitlines() if "=" in l and not l.startswith("#"))
    assert lines["APP_ENV"] == "production"
    assert lines["CORS_ORIGINS"] == "https://dana.example.com"
    assert lines["REDIS_URL"] == "redis://r:6379/0" and lines["TRUSTED_PROXY_COUNT"] == "1"
    assert len(lines["SECRET_KEY"]) >= 48 and lines["SECRET_KEY"] != "change-this-to-a-long-random-secret"
    from cryptography.fernet import Fernet
    Fernet(lines["APP_ENCRYPTION_KEY"].encode())


@pytest.mark.parametrize("cors", [None, "*", "http://dana.example.com", "https://dana.example.com/app"])
def test_gen_env_production_rejects_bad_cors(cors):
    import gen_env
    a = ["--production"] + (["--cors", cors] if cors else [])
    with pytest.raises(SystemExit):
        gen_env.build_env("CORS_ORIGINS=*\n", args(*a))


def test_gen_env_keeps_existing_keys_with_force():
    import gen_env
    tpl = "SECRET_KEY=a\nAPP_ENCRYPTION_KEY=b\nAPP_ENV=development\nCORS_ORIGINS=*\n"
    out = gen_env.build_env(tpl, args("--production", "--cors", "https://x.example.com"),
                            existing={"SECRET_KEY": "KEEP", "APP_ENCRYPTION_KEY": "KEEP2"})
    assert "SECRET_KEY=KEEP\n" in out and "APP_ENCRYPTION_KEY=KEEP2\n" in out and "APP_ENV=production" in out
