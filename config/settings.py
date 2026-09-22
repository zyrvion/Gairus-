import os


class Settings:
    APP_NAME = "Gaïrus"
    MODE = os.getenv("GAIRUS_MODE", "approval")
    DATA_DIR = os.getenv("GAIRUS_DATA_DIR", "data")
