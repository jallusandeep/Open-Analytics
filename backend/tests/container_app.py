"""Real API with background schedulers disabled to avoid external broker calls."""
import app.main as main

main.start_connection_scheduler = lambda: None
main.stop_connection_scheduler = lambda: None
main.start_data_collection_scheduler = lambda: None
main.stop_data_collection_scheduler = lambda: None
app = main.app
