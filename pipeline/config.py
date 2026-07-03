from pathlib import Path

DATA_PATH = Path("logs.json")

PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

POSITIONS_PATH = PROCESSED_DIR / "positions.parquet"
FEATURES_PATH = PROCESSED_DIR / "wallet_features.parquet"
LABELS_PATH = PROCESSED_DIR / "labels.parquet"
BASELINES_PATH = PROCESSED_DIR / "baselines.parquet"

MIN_TRADES_FILTER = 5
