# Architecture (planned)

## Goals

- Encourage short, meaningful outdoor observations.
- Keep AI inference local by default.
- Make model selection replaceable.
- Avoid requiring an account or cloud inference API for the MVP.
- Communicate uncertainty and model limitations clearly.

## Components

### Web UI

A responsive UI will support image selection or capture, ranked predictions, an observation journal, and optional nature missions. Manual image upload should remain available when browser camera access is unavailable.

### Spring Boot API

Proposed endpoints (not implemented yet):

- GET /api/health — health status.
- POST /api/identifications — accept an image and return ranked predictions.
- GET /api/observations — list saved observations.
- POST /api/observations — save an observation.
- DELETE /api/observations/{id} — delete an observation.

### Python inference service

Load the chosen model once at startup, validate image input, preprocess consistently, and return ranked predictions. Include model identity and revision in service metadata.

## Model selection checklist

Record the model repository and immutable revision, weight and code licenses, classes/species supported, preprocessing, hardware requirements, evaluation dataset provenance, results, and known confusion cases. An image classifier may not cover every species. Do not present confidence as calibrated certainty unless calibration has been evaluated.

## Offline acceptance test

After dependencies and model files have been downloaded:

1. Disconnect external network access.
2. Start all required services using local dependencies and weights.
3. Run a known test image through inference.
4. Save and retrieve an observation.
5. Verify these flows do not require outbound network access.
6. Record hardware, OS, model revision, commands, and results.

Setup may require internet access; document this clearly. Do not call the app fully offline until the test passes.

## Privacy

Avoid remote image uploads and analytics by default. Document temporary image handling, enforce request size limits, and never log image bytes or personal notes.
