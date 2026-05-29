---
sidebar_position: 9
title: lilith-bridge
---

# lilith-bridge

Bridge between synchronous and asynchronous components. Facilitates integration between layers.

## Purpose

Some components are async (LLM providers, network backends), others are sync (SQLite, file I/O). The bridge handles the conversion transparently.

## Usage

```python
from lilith_bridge.app import Bridge

bridge = Bridge(config)
result = bridge.call_sync(async_function, *args)
```
