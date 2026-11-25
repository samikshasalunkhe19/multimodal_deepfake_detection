# Multimodal Deepfake Detection Platform (Image + Video)

Upload an **image** or a **video** (or both). Each is analysed by its own module; a **fusion engine** combines the results
into one **risk score (0-100)** with an explanation, the evidence, the limitations, and a downloadable **PDF report**.

> **Results are risk estimates, not proof.** Detectors fail on content unlike their training data. Without a trained model
> the platform returns an "inconclusive" result instead of a confident guess.

## Architecture

```
Streamlit UI (frontend/: app, theme, reasons)  --HTTP-->  FastAPI (backend/)
                                        |  validation + temp storage (utils/)   uploads are deleted after analysis
                                        v
              image_detection                     video_detection
   classifier + Grad-CAM + ELA + metadata    face frames + temporal scoring
                         \                     /
                          fusion engine (modules/fusion) -> risk score, level, explanation
                                        |
                          SQLite/PostgreSQL (database/) -> history, PDF report
```

| Module | Signals | Without a trained model |
|---|---|---|
| Image | Hugging Face classifier (face crop if a face is found), Grad-CAM heat-map, Error Level Analysis, metadata | Medium band only, `usable = false` |
| Video | ~1 frame/s, face crops scored by the same classifier, top-k + temporal-consistency aggregation, suspicious segments with timestamps | `usable = false` |
| Fusion | Weighted log-odds blend of mean and strongest module, corroboration bonus, conflict detection | Skips unusable modules and says why |

## API (docs at `/docs`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze/image`, `/api/analyze/video` | multipart upload, field `file` |
| POST | `/api/analyze/multimodal` | `image` and/or `video` files, fused into one result |
| GET | `/api/history`, `/api/history/{id}` | saved results (`file_type`, `limit`, `offset`) |
| GET | `/api/history/{id}/report.pdf` | PDF report |
| DELETE | `/api/history/{id}` | delete a saved result |
| GET | `/api/health` | status, face detection, limits |

Validation errors return HTTP 400 `{"detail": "..."}` with a user-safe message.

## Quick start

See [docs/install_guide.md](docs/install_guide.md).

```
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
uvicorn backend.main:app --port 8000
streamlit run frontend/app.py
```

## Layout

```
backend/   FastAPI app, config, routes, services (analysis + PDF report)
frontend/  Streamlit UI + API client
modules/   image_detection, video_detection, fusion
database/  SQLAlchemy models, CRUD, sessions
utils/     upload validation, temp files, logging, face/image helpers
training/  evaluate.py (measure accuracy on your labelled data)
tests/     103 tests, no model download needed
```

## Security and privacy

* Uploads are validated by extension, size and real file content (magic bytes) and image dimensions. They are saved under
  random names and always deleted after analysis. Only the result is stored.
* The API has **no authentication or rate limiting**. Do not expose it to the internet as is.

## Honest status

* Accuracy has **not** been measured. Use `python -m training.evaluate --modality image --data dataset/image`
  (folders `real/` and `fake/`) on data from a different source than any model's training data before quoting numbers.
* Fusion weights are documented priors, not fitted.
* Not built: authentication, job queue for long videos, Alembic migrations, Docker, lip-sync checks.
