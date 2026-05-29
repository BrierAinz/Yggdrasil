---
name: pixai-generation
description: Generate images via PixAI GraphQL API with custom LoRAs
version: 1.0
tags: [pixai, image-generation, lora, sdxl, api]
---

# PixAI API — Image Generation via GraphQL

## Authentication
```
API_TOKEN = "sk-ln7AYoAOtsdnR5I2Ds2YoqEJQc9Wl2adEWsHyHjf0YEqtFLd"
Headers: Authorization: Bearer <TOKEN>, Content-Type: application/json
Endpoint: https://api.pixai.art/graphql
```

## Key IDs (User: brierainz)
- **PhotoPedia XL (SDXL photorealistic)**: `1701440086941361361`
- **Ehyra LoRA**: `2010111271331364248`
- **Trigger word**: `Ehyra` (or `ehyra`)

## Create Generation Task
```python
CREATE_TASK_MUTATION = """
mutation createGenerationTask($parameters: JSONObject!) {
  createGenerationTask(parameters: $parameters) {
    id userId parameters outputs status priority
  }
}
"""

parameters = {
    "prompts": "<prompt text>",
    "extra": {"naturalPrompts": "<same prompt>"},
    "negativePrompts": "<negative prompt>",
    "samplingSteps": 50,
    "samplingMethod": "Euler a",
    "cfgScale": 4,
    "width": 768,
    "height": 1280,
    "clipSkip": 2,
    "seed": "",
    "modelId": "1701440086941361361",
    "lora": {"2010111271331364248": 1},
    "loraParameters": [{
        "weight": 1,
        "versionId": "2010111271331364248",
        "positionInfo": {"endIndex": 0, "startIndex": 0},
        "triggerWords": "Ehyra"
    }],
    "priority": 1000,
    "controlNets": [],
    "isPrivate": False,
    "lightning": False,
    "enablePreview": False,
    "promptHelper": {
        "enable": True,
        "withStage": True,
        "userWantToEnable": True,
        "forcePromptHelperDetectionSide": "server"
    }
}

payload = {
    "operationName": "createGenerationTask",
    "query": CREATE_TASK_MUTATION,
    "variables": {"parameters": parameters}
}
resp = requests.post(API, json=payload, headers=HEADERS)
task_id = resp.json()["data"]["createGenerationTask"]["id"]
```

## Poll Task Status
```python
GET_TASK_QUERY = """
query getTaskById($id: ID!) {
  task(id: $id) {
    id status media { id type width height urls { variant url } imageType fileUrl }
  }
}
"""
```

- Poll every 8s. Status flow: waiting -> running -> completed
- On completed: get `media.urls` where `variant == "PUBLIC"`
- Images are usually webp format on CloudFront CDN

## Download Image
```python
img_resp = requests.get(public_url, timeout=30)
with open(fpath, "wb") as f:
    f.write(img_resp.content)
```

## LoRA Weight
- `loraParameters.weight`: 0.7-0.85 for balance (1.0 = max consistency)
- `lora` dict also needs weight: `{"<lora_version_id>": <weight>}`
- Both must match for consistent results

## Prompt Tips for Ehyra on PhotoPedia XL
- Start with trigger: `ehyra, 1girl, ...`
- Include `photorealistic` in positive prompt
- Add `anime, cartoon, illustration, 3d render` in negative prompt
- CFG 4-7, Euler a sampler, 50 steps
- Dimensions: 768x1280 (portrait) or 1280x768 (landscape)

## Cost
- 768x1280: ~3900 credits/image (priority 1000)

## Pitfalls
- GraphQL introspection DISABLED - use documented queries only
- REST /v1/model returns Forbidden - everything via GraphQL
- `promptHelper` required by PixAI pipeline (auto-enhances prompts)
- `extra.naturalPrompts` should match `prompts`
- `lora` dict and `loraParameters` array must both be present