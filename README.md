# Modusnap Local Bridge

The Modusnap Local Bridge is a lightweight execution client that connects Modusnap cloud orchestration to a local ComfyUI runtime.

Repository remote:
- `https://github.com/MTheUnexpected-1/modusnap-local-bridge.git`

## Purpose

- Maintain a persistent authenticated WebSocket connection to Modusnap bridge services.
- Receive remote `execute` payloads.
- Queue prompt graphs directly into local ComfyUI at `http://127.0.0.1:8188/prompt`.

## Runtime Flow

1. Start bridge client with API key.
2. Bridge connects to `wss://api.modusnap.com/bridge?token=<key>`.
3. When an `execute` message arrives, payload is parsed.
4. Payload is posted to local ComfyUI `/prompt` endpoint.
5. Queue success/failure is reported in terminal logs.

## Usage

```bash
python3 main.py --key <MODUSNAP_BRIDGE_API_KEY>
```

## Requirements

- Python 3.10+
- Dependencies used by current implementation:
  - `websockets`
  - `requests`

Install quickly:

```bash
pip install websockets requests
```

## Configuration

Defaults in `main.py`:
- `COMFY_HOST = "127.0.0.1:8188"`
- `MODUSNAP_WS = "wss://api.modusnap.com/bridge"`

These constants can be moved to environment variables for production deployment profiles.

## Operational Notes

- Ensure local ComfyUI is running before starting bridge.
- If queue calls fail, verify local backend health:
  - `http://127.0.0.1:8188/object_info`
- Network disconnects are surfaced via terminal error output and require reconnect/restart logic improvements for fully unattended operation.

## Roadmap (Bridge Side)

- Add auto-reconnect with exponential backoff.
- Add streaming relay from local ComfyUI WebSocket back to bridge.
- Add structured health/status endpoint for external supervisor integration.
- Add env-based configuration and optional secure key loading.
