from livekit import api

API_KEY = "APIWf2XzyCZigBp"
API_SECRET = "l0SuBNehSpg6Qnha0n31ktBrMHCgqxdYHesU7401PY5"

token = api.AccessToken(API_KEY, API_SECRET) \
    .with_identity("test-user") \
    .with_name("Test User") \
    .with_grants(api.VideoGrants(
        room_join=True,
        room="my-room",
        room_create=True,
        can_publish=True,
        can_subscribe=True,
    )).to_jwt()

print(token)