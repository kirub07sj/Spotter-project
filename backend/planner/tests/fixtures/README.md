# Provider fixtures

**Status: mixed recorded and synthetic.**

- `open_meteo/multi_point_winter.json` and `single_point.json` are real responses
  recorded on 2026-11-20. `open_meteo/recording.json` preserves the capture time and
  request parameters. The historical winter filename does not imply a storm was observed.
- `open_meteo/nulls.json` is synthetic to exercise missing data. `unit_conversion.json`
  preserves nonzero synthetic snow, rain and showers for conversion regression tests.
- Mapbox fixtures remain synthetic: no `MAPBOX_TOKEN` is configured. They follow real
  corridors (I-80, I-70, US-40), but their geometry is not road-accurate.

To replace them with real recordings (needs `MAPBOX_TOKEN`; tokens are stripped):

```bash
cd backend && uv run --env-file ../.env python scripts/record_fixtures.py
```

The two synthetic weather stress fixtures remain intentional regression inputs.
