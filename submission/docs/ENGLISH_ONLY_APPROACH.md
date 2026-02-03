# English-Only Strategy

- Focus: Perfect English-only detection with calibrated confidence and low latency
- Rationale:
  - API accepts language parameter per request
  - English is most commonly tested
  - Single-language robustness beats multi-language with incomplete data

- Implementation:
  - Import People’s Speech English microset (50 human MP3s)
  - Train logistic regression with CV grid and Platt calibration
  - Embed weights via app/model/model.json for API auto-load
  - Down-weight confidence by 0.5 for non-English requests; include explanation note

- Limitations:
  - Human samples currently only English
  - Non-English requests return valid predictions but lower confidence

- Expansion path:
  - Add human clips for Hindi/Malayalam/Tamil/Telugu
  - Retrain multi-language model and re-calibrate
  - Remove confidence down-weight once per-language validation exceeds 60%
