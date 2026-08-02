from app.config import load_settings
from app.mojang_api import MojangApiClient
from app.hypixel_api import HypixelApiClient


settings = load_settings()

print("Name:", settings.minecraft_username)
print("Key vorhanden:", settings.has_api_key)


mojang = MojangApiClient()

player = mojang.get_player_by_username(
    settings.minecraft_username
)

print("\nMinecraft gefunden:")
print(player)


hypixel = HypixelApiClient(
    settings.hypixel_api_key
)

profiles = hypixel.get_skyblock_profiles(
    player.compact_uuid
)

print("\nSkyBlock Profile:")
print(len(profiles))

for profile in profiles:
    print(
        profile.get("cute_name"),
        profile.get("game_mode")
    )