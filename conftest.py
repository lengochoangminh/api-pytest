import pytest, re, json, os, base64, shutil
from pathlib import Path
from dotenv import load_dotenv
from config import load_env

# === Constants ===
STORAGE_STATE = Path.cwd() / ".secret/storage_state.json"


# === Functions ===
def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="beta_use1",
        help="Environment to run tests against",
    )
    parser.addoption(
        "--trace-mode",
        action="store",
        default="off",
        help="Enable tracing: 'on' or 'off'",
    )
    parser.addoption(
        "--send-email",
        action="store_true",
        default=False,
        help="Send test report email after test execution",
    )
    parser.addoption(
        "--email-to",
        action="store",
        default="minh.le@tp-link.com",
        help="Comma-separated list of email recipients for the test report",
    )


# === Fixtures ===
@pytest.fixture(scope="session", autouse=True)
def load_environment(request):
    env = request.config.getoption("--env")
    load_env(env)

# === Hooks ===
def pytest_sessionstart(session):    
    file_path = Path(__file__).parent.parent /".secret/storage_state.json"
        
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"[pytest] Deleted file at session start: {file_path}")
    else:
        print(f"[pytest] File not found at session start: {file_path}")

    
