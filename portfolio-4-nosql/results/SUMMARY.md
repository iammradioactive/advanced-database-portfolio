# Portfolio 4: executed checks

Execution context: **GitHub Actions**

Run: https://github.com/iammradioactive/advanced-database-portfolio/actions/runs/45057575305

Result: **PASS - 15/15 checks**

## N01 Persist 600 JSON product documents in an independent key-value engine

```json
{
  "backend": "Berkeley DB",
  "interface": "dbm.ndbm",
  "loaded": 600
}
```

## N02 Cross-model consistency

```json
{
  "matching_products": 600
}
```

## N03 Primary-key lookup

```json
{
  "key": "product:LM-01-0001",
  "value": {
    "active": true,
    "attributes": {
      "allergen_note": "see packaging",
      "brand": "Lagoon Select",
      "pack_units": 1,
      "storage": "cool dry place",
      "unit_size": "5 kg"
    },
    "category": "Groceries",
    "category_id": 1,
    "name": "Lagoon Select Parboiled rice (5 kg; 1 unit pack)",
    "price_kobo": 1140000,
    "product_id": 1,
    "schema_version": 1,
    "sku": "LM-01-0001"
  }
}
```

## N04 Category index plus price filter

```json
{
  "category_id": 1,
  "max_price_kobo": 600000,
  "result_count": 60,
  "sql_result_equal": true
}
```

## N05 Nested flexible-attribute query

```json
{
  "result_count": 55,
  "warranty_min_months": 12,
  "max_price_kobo": 1000000
}
```

## N06 Update a document without relational DDL

```json
{
  "added_attributes": [
    "origin_region",
    "recyclable_packaging"
  ]
}
```

## N07 Delete and restore with maintained category index

```json
{
  "count_after_delete": 99,
  "count_after_restore": 100
}
```

## N08 Category change updates secondary keys

```json
{
  "during_move_counts": {
    "category_1": 99,
    "category_2": 101
  },
  "restored_indexes_valid": true
}
```

## N09 Generic key-value insertion/read/deletion

```json
{
  "draft_published": false
}
```

## N10 Embedded bounded delivery history

```json
{
  "documents": 20,
  "example_order_id": 119997
}
```

## N11 Application-managed TTL

```json
{
  "ttl_seconds": 1,
  "elapsed_seconds": 1.050718369000002,
  "expired_cart_deleted": true,
  "native_engine_ttl": false
}
```

## N12 Persistence across independent processes

```json
{
  "read_back_sku": "LM-01-0001"
}
```

## N13 Application document validation

```json
{
  "rejected": "price_kobo must be a positive integer"
}
```

## N14 Repair application-maintained index after injected deletion

```json
{
  "damage_detected": true,
  "indexes_valid_after_rebuild": true
}
```

## N15 Portable JSON export/import

```json
{
  "documents": 600,
  "sha256": "1c19a6c3cbdabd8ecdf5fd5352b890054cc31394409524545efc8ff7876979d3"
}
```

