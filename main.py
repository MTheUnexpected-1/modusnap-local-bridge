import argparse
import asyncio
import json
import platform
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

DEFAULT_COMFY_HOST = "127.0.0.1:8188"
DEFAULT_MODUSNAP_WS = "wss://api.modusnap.com/bridge"
BRIDGE_VERSION = "0.2.0"


@dataclass
class HardwareCapabilities:
    os: str
    os_version: str
    architecture: str
    python_version: str
    cpu_count_logical: int
    cpu_brand: str
    total_memory_gb: Optional[float]
    has_nvidia: bool
    has_rocm: bool
    is_apple_silicon: bool
    selected_backend_profile: str


def run_command(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        return (completed.stdout or completed.stderr or "").strip()
    except Exception:
        return ""


def detect_total_memory_gb() -> Optional[float]:
    if hasattr(os_module := __import__("os"), "sysconf"):
        try:
            page_size = os_module.sysconf("SC_PAGE_SIZE")
            page_count = os_module.sysconf("SC_PHYS_PAGES")
            if page_size and page_count:
                return round((page_size * page_count) / (1024**3), 2)
        except Exception:
            return None
    return None


def detect_cpu_brand() -> str:
    machine = platform.processor() or platform.machine()
    if machine:
        return machine

    if platform.system() == "Darwin":
        out = run_command(["sysctl", "-n", "machdep.cpu.brand_string"])
        if out:
            return out

    return "unknown"


def detect_hardware_capabilities() -> HardwareCapabilities:
    system = platform.system()
    machine = platform.machine().lower()

    has_nvidia = shutil.which("nvidia-smi") is not None
    has_rocm = shutil.which("rocm-smi") is not None
    is_apple_silicon = system == "Darwin" and machine in {"arm64", "aarch64"}

    if has_nvidia:
        selected_profile = "nvidia_cuda"
    elif has_rocm:
        selected_profile = "amd_rocm"
    elif is_apple_silicon:
        selected_profile = "apple_mps"
    else:
        selected_profile = "cpu"

    return HardwareCapabilities(
        os=system,
        os_version=platform.version(),
        architecture=platform.machine(),
        python_version=platform.python_version(),
        cpu_count_logical=__import__("os").cpu_count() or 1,
        cpu_brand=detect_cpu_brand(),
        total_memory_gb=detect_total_memory_gb(),
        has_nvidia=has_nvidia,
        has_rocm=has_rocm,
        is_apple_silicon=is_apple_silicon,
        selected_backend_profile=selected_profile,
    )


def build_hello_payload(capabilities: HardwareCapabilities) -> Dict[str, Any]:
    return {
        "type": "bridge.hello",
        "payload": {
            "bridge_version": BRIDGE_VERSION,
            "capabilities": asdict(capabilities),
            "timestamp": int(time.time()),
        },
    }


async def post_execution_ack(websocket: Any, prompt_id: str, ok: bool, details: Dict[str, Any]) -> None:
    message = {
        "type": "bridge.execution_ack",
        "payload": {
            "prompt_id": prompt_id,
            "ok": ok,
            "details": details,
            "timestamp": int(time.time()),
        },
    }
    await websocket.send(json.dumps(message))


def run_comfyui_graph(prompt_json: Dict[str, Any], comfy_host: str, capabilities: HardwareCapabilities) -> tuple[bool, Dict[str, Any]]:
    import requests

    print("Executing graph payload on local ComfyUI interface...")
    url = f"http://{comfy_host}/prompt"
    payload = {
        "prompt": prompt_json,
        "extra_data": {
            "modusnap_bridge": {
                "bridge_version": BRIDGE_VERSION,
                "selected_backend_profile": capabilities.selected_backend_profile,
                "hardware": asdict(capabilities),
                "timestamp": int(time.time()),
            }
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}
            print("Graph successfully queued to local backend.")
            return True, {"status": response.status_code, "response": data}

        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}
        print(f"ComfyUI failed to queue graph: {error_data}")
        return False, {"status": response.status_code, "response": error_data}
    except requests.exceptions.RequestException as error:
        message = f"Could not reach local ComfyUI at http://{comfy_host}: {error}"
        print(message)
        return False, {"status": None, "error": message}


async def connect_once(api_key: str, ws_url: str, comfy_host: str, capabilities: HardwareCapabilities) -> None:
    import websockets

    print(f"Connecting to Modusnap Bridge with key prefix: {api_key[:8]}...")
    async with websockets.connect(f"{ws_url}?token={api_key}") as websocket:
        await websocket.send(json.dumps(build_hello_payload(capabilities)))
        print(f"Connected. Sent hardware profile: {capabilities.selected_backend_profile}")
        print("Waiting for bridge commands...")

        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                print(f"Ignoring non-JSON message: {message[:120]}")
                continue

            message_type = data.get("type")
            payload = data.get("payload")

            if message_type == "execute" and isinstance(payload, dict):
                prompt = payload.get("prompt") if isinstance(payload.get("prompt"), dict) else payload
                prompt_id = str(payload.get("prompt_id") or payload.get("id") or "unknown")
                ok, details = run_comfyui_graph(prompt, comfy_host, capabilities)
                await post_execution_ack(websocket, prompt_id=prompt_id, ok=ok, details=details)
                continue

            if message_type == "bridge.request_capabilities":
                await websocket.send(json.dumps(build_hello_payload(capabilities)))
                continue

            if message_type == "ping":
                await websocket.send(json.dumps({"type": "pong", "timestamp": int(time.time())}))
                continue

            print(f"Received unsupported message type: {message_type}")


async def run_bridge(api_key: str, ws_url: str, comfy_host: str) -> None:
    import websockets

    capabilities = detect_hardware_capabilities()
    print("Detected hardware capabilities:")
    print(json.dumps(asdict(capabilities), indent=2))

    retry_seconds = 2
    max_retry_seconds = 30

    while True:
        try:
            await connect_once(api_key=api_key, ws_url=ws_url, comfy_host=comfy_host, capabilities=capabilities)
            retry_seconds = 2
        except KeyboardInterrupt:
            raise
        except Exception as error:
            print(f"Bridge disconnected: {error}")
            print(f"Reconnecting in {retry_seconds}s...")
            await asyncio.sleep(retry_seconds)
            retry_seconds = min(retry_seconds * 2, max_retry_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Modusnap Local Bridge Execution Client")
    parser.add_argument("--key", required=True, help="Your Modusnap Bridge API Key")
    parser.add_argument("--ws-url", default=DEFAULT_MODUSNAP_WS, help=f"Bridge websocket URL (default: {DEFAULT_MODUSNAP_WS})")
    parser.add_argument("--comfy-host", default=DEFAULT_COMFY_HOST, help=f"Local ComfyUI host:port (default: {DEFAULT_COMFY_HOST})")
    parser.add_argument("--print-capabilities", action="store_true", help="Print detected hardware capabilities and exit")
    args = parser.parse_args()

    capabilities = detect_hardware_capabilities()
    if args.print_capabilities:
        print(json.dumps(asdict(capabilities), indent=2))
        return

    asyncio.run(run_bridge(api_key=args.key, ws_url=args.ws_url, comfy_host=args.comfy_host))


if __name__ == "__main__":
    main()
