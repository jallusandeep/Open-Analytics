import os

# Base Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
DATA_DIR = os.path.join(BASE_DIR, "data", "News")

# Databases
# Scoring DB (Source)
SCORING_DB_PATH = os.path.join(DATA_DIR, "Scoring", "news_scoring.duckdb")
SCORING_TABLE = "news_scoring"

# AI DB (Target)
AI_DB_PATH = os.path.join(DATA_DIR, "Final", "news_ai.duckdb")
AI_TABLE = "news_ai"

# Final DB (User Request)
FINAL_DB_PATH = os.path.join(DATA_DIR, "Final", "final_news.duckdb")
FINAL_TABLE = "final_news"

# Batch Size
BATCH_SIZE = 1
