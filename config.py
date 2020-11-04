import yaml
import os

with open("/etc/apcupsd/config.yaml", "r") as f:
    settings = yaml.safe_load(f)
