import asyncio
import websockets
import json
import requests
import argparse

COMFY_HOST = "127.0.0.1:8188"
MODUSNAP_WS = "wss://api.modusnap.com/bridge"

async def connect_to_modusnap(api_key):
    print(f"Connecting to Modusnap Core OS with key: {api_key[:8]}...")
    try:
        async with websockets.connect(f"{MODUSNAP_WS}?token={api_key}") as websocket:
            print("Connected! Waiting for execution payloads from Modusnap...")
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "execute":
                    await run_comfyui_graph(data["payload"])
    except Exception as e:
        print(f"Connection lost or failed: {e}")

async def run_comfyui_graph(prompt_json):
    print("Executing graph payload on local ComfyUI interface...")
    try:
        response = requests.post(f"http://{COMFY_HOST}/prompt", json={"prompt": prompt_json})
        if response.status_code == 200:
            print("Graph successfully queued to local GPU.")
            # In production, we listen to the local ComfyUI WebSocket here to pipe image chunks back to Modusnap
        else:
            print(f"ComfyUI failed to queue graph: {response.text}")
    except requests.exceptions.RequestException:
        print(f"Error: Could not reach local ComfyUI. Ensure it is running at http://{COMFY_HOST}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modusnap Local Bridge Execution Client")
    parser.add_argument("--key", required=True, help="Your Modusnap Bridge API Key")
    args = parser.parse_args()
    
    # Run the persistent websocket connection
    asyncio.run(connect_to_modusnap(args.key))
