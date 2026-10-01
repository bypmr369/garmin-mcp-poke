"""
Garmin MCP Server - Poke Compatible
All 95+ tools from garmin_mcp, served over HTTP for Poke.
"""
import os
import sys

# Add src directory to path for module imports
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

load_dotenv()

from fastmcp import FastMCP
from config import PORT, HOST, MCP_PATH
from garmin_client import init_garmin_client

# Import all tool modules
from modules import (
    activity_management,
    health_wellness,
    training,
    user_profile,
    devices,
    gear_management,
    weight_management,
    challenges,
    workouts,
    workout_templates,
    data_management,
    womens_health,
)

# Initialize Garmin client
garmin_client = init_garmin_client()
if not garmin_client:
    print("Failed to initialize Garmin Connect client. Exiting.", file=sys.stderr)
    sys.exit(1)

print("Garmin Connect client initialized successfully.", file=sys.stderr)

# Configure all modules with the Garmin client
activity_management.configure(garmin_client)
health_wellness.configure(garmin_client)
training.configure(garmin_client)
user_profile.configure(garmin_client)
devices.configure(garmin_client)
gear_management.configure(garmin_client)
weight_management.configure(garmin_client)
challenges.configure(garmin_client)
workouts.configure(garmin_client)
data_management.configure(garmin_client)
womens_health.configure(garmin_client)

# Create FastMCP app (standalone fastmcp package, not mcp.server.fastmcp)
mcp = FastMCP("Garmin MCP Server")

# Register tools from all modules
mcp = activity_management.register_tools(mcp)
mcp = health_wellness.register_tools(mcp)
mcp = training.register_tools(mcp)
mcp = user_profile.register_tools(mcp)
mcp = devices.register_tools(mcp)
mcp = gear_management.register_tools(mcp)
mcp = weight_management.register_tools(mcp)
mcp = challenges.register_tools(mcp)
mcp = workouts.register_tools(mcp)
mcp = data_management.register_tools(mcp)
mcp = womens_health.register_tools(mcp)

# Register resources (workout templates)
mcp = workout_templates.register_resources(mcp)

# Run the server
if __name__ == "__main__":
    print(f"Starting Garmin MCP Server on {HOST}:{PORT}", file=sys.stderr)

    mcp.run(
        transport="http",
      host=HOST,
      path=MCP_PATH,
        port=PORT,
        stateless_http=True,
    )
