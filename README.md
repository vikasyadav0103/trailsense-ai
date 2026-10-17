# TrailSense AI 🌿

**An offline-first nature companion powered by open-source AI.**

TrailSense AI is an early-stage Hacktoberfest project designed to help people spend less time on screens and more time outdoors. The first milestone is bird identification from photographs with a locally loaded open-weight model, plus a local observation journal.

> **Status:** Early development. Offline operation, model accuracy, and end-to-end functionality have not yet been verified.

## Planned architecture

```text
Web UI → Spring Boot API → Python inference service → local open-weight model
                                                   → local observation storage
```

## Roadmap

- [ ] Evaluate model candidates, licenses, species coverage, and hardware requirements.
- [ ] Build a reproducible Python inference proof of concept.
- [ ] Add a Spring Boot API and tests.
- [ ] Build a lightweight interface and local observation journal.
- [ ] Test with external network disconnected after setup.
- [ ] Record outdoor tests, predictions, and known limitations.

## Why open innovation?

Local inference can improve privacy and reduce dependence on cloud APIs. Model weights and licenses must be assessed individually, and the complete app must be tested before claiming offline capability.

## Contributing

Contributions are welcome. Please discuss substantial changes in an issue and include reproducible tests where practical. Do not commit model weights or personal photos without discussion.

## License

The source code is intended to use the MIT License. Model weights and datasets may have separate terms.

Challenge: [Hacktoberfest Open-Source AI Challenge — Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05).
