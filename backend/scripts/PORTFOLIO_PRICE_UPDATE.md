# Portfolio KAMIS update

This is a reproducible, one-off update for **2026-09-03 through 2026-10-02**.
The root `.env` supplies DB_URL, DB_USERNAME, DB_PASSWORD, KAMIS_API_KEY and KAMIS_CERT_ID.
Python dependencies: psycopg, requests and python-dotenv (available in this project environment).

Inputs are the local audit snapshot, category responses and candidate scope CSV under `reports/kamis-audit`.
`audit_kamis_coverage.py`, `fetch_kamis_audit_catalog.py` and `estimate_portfolio_mapping.py` generate those inputs.

From the project root:

```text
python backend/scripts/update_portfolio_kamis_prices.py
python backend/scripts/update_portfolio_kamis_prices.py --fetch
python -m unittest discover -s backend/scripts -p test_portfolio_price_rules.py
python backend/scripts/update_portfolio_kamis_prices.py --apply
python backend/scripts/verify_portfolio_kamis_update.py
```

The first command previews. `--fetch` caches API price responses without changing the DB.
`--apply` requires validated cached responses; it backs up all existing series/mappings and the affected-period price rows, then commits one transaction. Existing historical rows outside the selected period and prior mappings are preserved. Repeating the application upserts the same series/date pairs rather than duplicating them.

Every target mapping contains a source code tuple, mapping type, conversion factor and confidence. Review `reports/kamis-update/mapping_preview.csv` and `portfolio_price_rules.py` for the portfolio assumptions. These estimates are not intended to reproduce an invoice or nutritional yield database.

API summary rows and nonpositive prices are ignored. Actual regional observations are selected, preferring the stored market for existing series; the regional mean is used if that market is absent. Unknown source units are never silently treated as kg. The API's final `kindname` unit takes precedence because `p_convert_kg_yn=Y` still returns 100g, count and litre units for some products.

New normalized reference series use `KAMIS_PORTFOLIO` with a gram-normalized price. The updated backend now collects these references with automatic unit conversion. The shared assumptions are in `src/main/resources/portfolio-price-rules.json`. See `PRICE_CONVERSION.md` for ongoing collection. Do not reuse this one-off workflow's date-bound caches for a different month.

Credentials echoed by KAMIS in `condition` are stripped before saving. API errors print exception types rather than authenticated URLs. Database snapshots/backups and response caches are local ignored files.

The running backend caches costs at startup. Restart it after the update if it points to this database. This script does not deploy or restart AWS services.
