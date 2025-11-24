from loguru import logger
import os
import yaml

CONFIG_PATH = "config.yaml"

# Basic logger setup
if not os.path.exists("logs"):
    os.makedirs("logs", exist_ok=True)

logger.add("logs/system.log", rotation="10 MB", backtrace=True, diagnose=True)


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)
