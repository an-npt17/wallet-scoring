from pathlib import Path

DATA_PATH = Path("logs.json")
OUTPUT_DIR = Path("eda/output")
OUTPUT_DIR.mkdir(exist_ok=True)

SAMPLE_FRAC = 0.05  # 5% sampling for expensive aggregations
LARGE_SAMPLE_ROWS = 5_000_000
SMALL_SAMPLE_ROWS = 500_000
