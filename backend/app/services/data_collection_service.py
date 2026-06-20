# backend\app\services\data_collection_service.py
# Compatibility wrapper.
#
# Existing imports such as:
#   from app.services.data_collection_service import sync_upstox_ohlcv_daily_service
# continue to work after moving the implementation into:
#   backend\app\services\data_collection\

from app.services.data_collection import *  # noqa: F401,F403
