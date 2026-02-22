# Capabilities Protocol (Public Reference)

## 1. Connection Handshake

When the bridge connects, it sends:

```json
{
  "type": "bridge.hello",
  "payload": {
    "bridge_version": "0.2.0",
    "capabilities": {
      "os": "Darwin",
      "architecture": "arm64",
      "selected_backend_profile": "apple_mps"
    },
    "timestamp": 1739940000
  }
}
```

## 2. Backend Profile Selection

Current selection order:

1. `nvidia_cuda` if `nvidia-smi` is present
2. `amd_rocm` if `rocm-smi` is present
3. `apple_mps` on Apple Silicon
4. `cpu` fallback

## 3. Execution Metadata

For each queued local prompt (`/prompt`), bridge includes:

- `bridge_version`
- `selected_backend_profile`
- `hardware` snapshot
- `timestamp`

inside `extra_data.modusnap_bridge`.

## 4. Explicit Transparency Goal

The public bridge intentionally documents capability reporting behavior so users can review what is being sent and why.
