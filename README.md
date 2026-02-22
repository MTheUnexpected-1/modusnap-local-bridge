<div align="center">

# Modusnap Local Bridge

Public reference repository for the Modusnap Local Bridge.

[![Status](https://img.shields.io/badge/status-reference_repo-0b1220?style=for-the-badge)](#)
[![Language](https://img.shields.io/badge/language-python-0b1220?style=for-the-badge)](#)

</div>

## Overview

This bridge connects a local ComfyUI runtime to Modusnap over WebSocket.
It now includes **hardware capability detection** and a transparent capability handshake so backend routing can choose compatible execution paths.

## Run

```bash
python3 main.py --key <API_KEY>
```

Optional:

```bash
python3 main.py --key <API_KEY> --print-capabilities
```

## What hardware data is sent

On connect, the bridge sends a `bridge.hello` payload containing:

- OS and architecture
- Python version
- Logical CPU count
- CPU brand string
- Total memory (GB)
- NVIDIA/ROCm presence
- Apple Silicon detection
- Selected backend profile (`nvidia_cuda`, `amd_rocm`, `apple_mps`, or `cpu`)

The same profile is attached to ComfyUI prompt submissions in `extra_data.modusnap_bridge` for compatibility tracing.

## Why this exists

- Prevents scheduling incompatible backend paths.
- Makes runtime selection deterministic and auditable.
- Gives users clear visibility into what the bridge is reporting.

## Message types implemented

- `bridge.hello` (sent at connect)
- `execute` (received from backend)
- `bridge.execution_ack` (sent after local queue attempt)
- `bridge.request_capabilities` (responds with current capabilities)
- `ping` / `pong`

## Public Scope

Included:
- capability handshake behavior
- reference execution flow
- transparent metadata contract

Excluded:
- production auth internals
- private deployment and operations
