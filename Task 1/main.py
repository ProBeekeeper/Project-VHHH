import arcade
import sys
from atc_database import ATCDatabase
from atc_game_manager import ATCGameManager
from atc_radar_ui import ATCRadarEngine

def main():
    print("Loading Map and Data...")
    try:
        db = ATCDatabase()
        db.initialize()
        game_manager = ATCGameManager(db)
        window = ATCRadarEngine(game_manager)
        window.setup()
        print("✅ Loading completed, starting Project VHHH...")
        arcade.run()
    except Exception as e:
        print(f"❌ System startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()