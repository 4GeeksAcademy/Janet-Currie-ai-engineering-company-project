# Tech updates — Caching optimisation

- In-process `TtlCache` (`app/cache.py`): bounded OrderedDict, monotonic clock, `threading.Lock`, deepcopy on get/set, max 512 entries. Not Redis or `functools.lru_cache`.
- Keys: `v1:inventory:products:list`, `v1:inventory:products:id:{id}`, `v1:inventory:orders:list`. TTL 30 s plus write invalidation after successful product/inbound/outbound commits.
- `REQUEST_TIMING` middleware logs method, route template, status, elapsed ms (default on locally; tests set `0`). Never logs bodies, tokens, or emails.
- Volume seed env: `INVENTORY_LOAD_EXTRA`, `SUPPLIER_LOAD_EXTRA`. Canonical six SKUs / 15 suppliers stay the default; pytest still uses temp DBs.
- Staff `/operations` and `/incidents` use `next/dynamic` with accessible `role="status"` loading. `MovementHistory` memoizes `deriveMovementRows`.
- Trail: root [`CACHING_REPORT.md`](../../../CACHING_REPORT.md). Durable notes: [`implementation-memory/caching.md`](../../implementation-memory/caching.md).
