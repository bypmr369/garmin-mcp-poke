"""
Configuration for Garmin MCP Server (Poke-compatible)
"""
import os

# Garmin authentication
GARMINTOKENS_BASE64 = os.getenv("GARMINTOKENS_BASE64")
GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")

# Server settings
PORT = int(os.getenv("PORT", 8000))
HOST = os.getenv("HOST", "0.0.0.0")

# Secret path: the server refuses to start without it
MCP_SECRET = os.getenv("MCP_SECRET")
if not MCP_SECRET or len(MCP_SECRET) < 24:
    raise SystemExit("ERROR: set MCP_SECRET (at least 24 characters). Refusing to start without it.")
MCP_PATH = f"/mcp/{MCP_SECRET}"
