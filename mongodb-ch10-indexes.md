# 📖 Chapter 10 — Indexes ⭐⭐⭐⭐⭐

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

You can have a perfectly modeled schema (Chapter 8), airtight validation (Chapter 9), and elegant queries (Chapters 5–7) — and your application can *still* grind to a halt at scale if you never learned this chapter. Indexes are the single biggest lever for query performance in MongoDB, which is why this chapter carries the same 5-star weight as Aggregation and Data Modeling.

This chapter explains what an index actually is, why a database needs one at all, how to create every major index type, and — critically — how to read `.explain()` output to *prove* your queries are actually using the indexes you think they are.

---

# Theory

## 10.1 Why Indexes?

Without an index, MongoDB has no way to know where a matching document "lives" other than checking every single document in the collection, one by one. An index is a separate, small, sorted data structure that lets MongoDB **jump directly** to matching documents instead.

> **Analogy:** Imagine a 1,000-page textbook with no index at the back. If someone asks "which pages mention photosynthesis?", you'd have to read every single page from cover to cover. Now imagine that same book *with* an index — you flip to "photosynthesis" in the back, see "pages 45, 112, 300," and go straight there. The index doesn't change what's *in* the book — it just gives you a fast way to find it.

Indexes trade a small amount of **extra storage space** and **slightly slower writes** (the index must also be updated on every insert/update/delete) for a **massive speedup on reads** — usually the right trade, since most applications read far more than they write.

---

## 10.2 Sequential Scan

A **sequential scan** (also called a "collection scan," shown as `COLLSCAN` in `.explain()` output) is what MongoDB falls back to when no useful index exists: it checks **every single document** in the collection against the query filter, one at a time.

```
 Collection scan on 1,000,000 documents, looking for { age: 25 }

 doc1 → check age → no match
 doc2 → check age → no match
 doc3 → check age → MATCH! ✓
 doc4 → check age → no match
 ...
 (continues through ALL 1,000,000 documents, even after finding matches)
```

> **Analogy:** A sequential scan is reading that 1,000-page textbook cover to cover because it has no index — technically it works, but it's painfully slow for a big book, and gets linearly worse the bigger the book gets.

Sequential scans aren't *always* bad — for a tiny collection (say, under a few hundred documents), or when a query genuinely needs to touch most of the collection anyway, a scan can actually be perfectly fine or even preferred (index maintenance has its own overhead). The problem is sequential scans on **large** collections for **selective** queries (ones that only match a small fraction of documents) — that's where indexes pay off enormously.

---

## 10.3 How Index Works

MongoDB indexes are implemented as **B-Trees** (balanced tree structures) — the same fundamental structure used by most relational databases, including PostgreSQL.

```
                    [50]
                 /        \
            [25]            [75]
           /    \           /    \
        [10]   [35]      [60]   [90]
```

Each node stores sorted key values (the indexed field's values) along with pointers to where the actual documents live on disk. Because the tree is **sorted** and **balanced**, MongoDB can find any value in roughly `O(log n)` steps — for a million documents, that's about 20 comparisons instead of a million.

> **Analogy:** A B-Tree index works like the phone book (remember those?) — names are sorted alphabetically, and finding "Rohan Gupta" doesn't mean starting from "Aaron Aaronson" and reading every entry; you flip roughly to the middle, see you're too far/not far enough, and narrow in — a handful of flips gets you there, not thousands.

### Index anatomy
```
 Index on "age" field:

  age value  →  pointer to document location
  ─────────     ──────────────────────────
    18       →  disk location of doc #4521
    21       →  disk location of doc #102
    21       →  disk location of doc #88
    25       →  disk location of doc #3
    ...         (sorted by age, fast to binary-search)
```

Every collection automatically gets **one index for free**: on `_id` — this is why `findOne({ _id: ... })` is always fast, even without you doing anything.

---

## 10.4 Creating Indexes

```js
db.collection.createIndex({ field: 1 })    // ascending
db.collection.createIndex({ field: -1 })   // descending
```
(For single-field indexes, ascending vs. descending rarely matters for lookup performance — it matters more for sort direction and compound indexes.)

### Types

#### Single Field Index
Indexes one field.
```js
db.students.createIndex({ age: 1 })
```

#### Compound Index
Indexes **multiple fields together**, in a specific order — field order matters enormously.
```js
db.students.createIndex({ course: 1, age: -1 })
```
This index efficiently supports queries filtering on `course` alone, or on `course` AND `age` together — but **not** efficiently on `age` alone (see the "prefix rule" in section 10.6).

#### Unique Index
Enforces that no two documents can share the same value for the indexed field(s) — like a SQL `UNIQUE` constraint.
```js
db.users.createIndex({ email: 1 }, { unique: true })
```

#### Multikey Index
Automatically created when you index a field that holds an **array** — MongoDB indexes each array element individually.
```js
db.students.createIndex({ courses: 1 })
// if courses: ["DBMS", "OS"], BOTH "DBMS" and "OS" get their own index entries
// pointing back to the SAME document
```

#### Text Index
Enables full-text search across string content — tokenizes text, ignores common "stop words," and supports relevance-based search.
```js
db.products.createIndex({ name: "text", description: "text" })
db.products.find({ $text: { $search: "wireless mouse" } })
```

#### TTL Index (Time-To-Live)
Automatically **deletes documents** after a certain amount of time has passed since a date field's value — perfect for session data, temporary tokens, or logs that should expire.
```js
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 3600 })
// documents are auto-deleted ~1 hour after their "createdAt" value
```

#### Geospatial Index
Enables location-based queries — "find all restaurants within 5km of this point."
```js
db.restaurants.createIndex({ location: "2dsphere" })
db.restaurants.find({
  location: { $near: { $geometry: { type: "Point", coordinates: [73.8567, 18.5204] }, $maxDistance: 5000 } }
})
```

---

## 10.5 `explain()`

`.explain()` shows you **how** MongoDB actually plans to execute a query — the single most important debugging tool for index performance, telling you definitively whether an index was used or not.

```js
db.students.find({ age: 25 }).explain("executionStats")
```

Key fields to look for in the output:

| Field | Meaning |
|---|---|
| `stage: "COLLSCAN"` | ⚠️ No index used — full collection scan |
| `stage: "IXSCAN"` | ✅ An index was used |
| `nReturned` | Number of documents actually returned |
| `totalDocsExamined` | Number of documents MongoDB had to look at |
| `totalKeysExamined` | Number of index entries MongoDB had to look at |
| `executionTimeMillis` | How long the query took |

> **The single most important number to compare:** `totalDocsExamined` vs. `nReturned`. If MongoDB examined 1,000,000 documents to return just 5, that's a huge red flag — either there's no index, or the existing index isn't selective/useful for this particular query.

```js
// GOOD: index used, examined ≈ returned
{ stage: "IXSCAN", nReturned: 5, totalKeysExamined: 5, totalDocsExamined: 5 }

// BAD: no index, examined >> returned
{ stage: "COLLSCAN", nReturned: 5, totalDocsExamined: 1000000 }
```

---

## 10.6 Performance Optimization

### The "prefix rule" for compound indexes
A compound index `{ a: 1, b: 1, c: 1 }` can efficiently serve queries filtering on:
- `{ a }`  ✅
- `{ a, b }`  ✅
- `{ a, b, c }`  ✅
- `{ b }` alone  ❌ (skips the prefix — can't use this index efficiently)
- `{ c }` alone  ❌

```
 Index: { category: 1, price: 1 }

 ✅ find({ category: "Electronics" })                    → uses index
 ✅ find({ category: "Electronics", price: { $gt: 500 } }) → uses index fully
 ❌ find({ price: { $gt: 500 } })                          → CANNOT use this index
```

> **Analogy:** A compound index is like a phone book sorted by **last name, then first name**. You can quickly find "Gupta" or "Gupta, Rohan" — but you can't efficiently find "everyone whose first name is Rohan" using that same book, because it's not sorted by first name at all; you'd have to scan the whole thing.

### Covered queries
If a query's filter, sort, AND projection **all** consist entirely of indexed fields, MongoDB can answer the query using **only the index**, without ever touching the actual documents on disk — extremely fast.

```js
db.students.createIndex({ name: 1, age: 1 })

// COVERED query — only touches the index, never the actual documents
db.students.find({ name: "Rohan" }, { name: 1, age: 1, _id: 0 })
```

### Selectivity matters
An index on a field with very few distinct values (like a boolean `isActive`) is far less useful than one on a highly selective field (like `email`) — because even with the index, MongoDB may still need to examine a large fraction of matching documents.

---

## 10.7 Index Tradeoffs

Indexes are not free — every index you add has real costs.

| Benefit | Cost |
|---|---|
| Much faster reads/lookups | Slightly slower writes (every insert/update/delete must also update each relevant index) |
| Faster sorting on indexed fields | Extra disk space used to store the index itself |
| Enables covered queries | More indexes = more maintenance overhead, more RAM used to keep indexes cached |

> **Analogy:** Every index is like adding another table of contents to a book — helpful for readers, but now every time an author edits the book (adds/removes a page), *all* the tables of contents need to be updated too. One or two indexes are clearly worth it. Twenty overlapping ones start to slow down every single edit for marginal reader benefit.

**Rule of thumb:** index fields you frequently `$match`/`find()`/`sort()`/`$lookup` on — don't index every field "just in case."

---

# Why This Exists

Every database — relational or document-based — faces the exact same fundamental problem: as data grows from hundreds to millions of records, checking every single record for every single query becomes catastrophically slow. Indexes exist to trade a bounded, predictable amount of extra storage and write overhead for a **logarithmic** (rather than linear) search cost — the difference between a query taking 20 comparisons instead of 1,000,000 as your collection grows.

The variety of index **types** (compound, multikey, text, TTL, geospatial) exists because "find things fast" means different things depending on the shape of the query: sometimes you need multiple fields together, sometimes you need to search inside arrays, sometimes you need fuzzy text relevance ranking, sometimes you need automatic expiration, and sometimes you need physical distance calculations — a single generic B-Tree can't efficiently serve all of these use cases, so MongoDB provides specialized index structures for each.

`.explain()` exists because **assuming** an index is being used is a common and expensive mistake — without a way to verify the actual execution plan, developers would be flying blind, unable to distinguish a genuinely fast query from one that happens to be fast today only because the collection is still small.

---

# Internal Working

## What happens during an indexed query

```
 Query: db.students.find({ age: 25 })   (with index on "age")

 1. MongoDB consults the query planner, which checks available indexes.
 2. The B-Tree index on "age" is chosen (IXSCAN).
 3. MongoDB performs a binary-search-like traversal of the B-Tree
    to find the starting point for age == 25.
 4. It walks the sorted index entries matching age == 25,
    following each entry's pointer to fetch the ACTUAL document from disk.
 5. Only the matching documents are read from disk — everything else is skipped entirely.
```

## What happens without an index (COLLSCAN)

```
 Query: db.students.find({ age: 25 })   (NO index on "age")

 1. No usable index found — planner falls back to a full collection scan.
 2. MongoDB reads EVERY document from disk, in storage order.
 3. Each document's "age" field is checked against the filter.
 4. Matching documents are collected; non-matching ones are discarded
    AFTER having been fully read from disk — wasted I/O.
```

## How the query planner chooses between multiple candidate indexes
When several indexes could theoretically serve a query, MongoDB's query planner runs a brief **competition**: it tries the top candidate plans in parallel on a small sample, sees which one returns results fastest/most efficiently, and then commits to that plan (caching the choice for similar future queries). You can inspect this competition directly via `.explain("allPlansExecution")`.

## Why writes get slower with more indexes
Every index is a **separate physical B-Tree data structure** that must stay in sync with the collection. On every `insertOne()`, `updateOne()`, or `deleteOne()`, MongoDB must also insert/update/remove the corresponding entries in **every index** that covers a changed field — so five indexes mean up to five extra B-Tree updates per write, not just one.

---

# Syntax

```js
// Create indexes
db.collection.createIndex({ field: 1 })                          // single field, ascending
db.collection.createIndex({ field: -1 })                         // single field, descending
db.collection.createIndex({ field1: 1, field2: -1 })              // compound
db.collection.createIndex({ field: 1 }, { unique: true })         // unique
db.collection.createIndex({ arrayField: 1 })                      // multikey (automatic if array)
db.collection.createIndex({ textField: "text" })                  // text
db.collection.createIndex({ dateField: 1 }, { expireAfterSeconds: 3600 })  // TTL
db.collection.createIndex({ location: "2dsphere" })                // geospatial

// Inspect
db.collection.getIndexes()
db.collection.find(filter).explain("executionStats")

// Remove
db.collection.dropIndex({ field: 1 })
db.collection.dropIndexes()   // removes ALL except the default _id index
```

---

# Examples

## Full example — from scan to indexed to verified

```js
use college
db.students.insertMany([ /* ...100,000 documents... */ ])

// Step 1 — check current (bad) performance
db.students.find({ course: "DBMS" }).explain("executionStats")
// stage: "COLLSCAN", totalDocsExamined: 100000, executionTimeMillis: 340

// Step 2 — create the index
db.students.createIndex({ course: 1 })

// Step 3 — verify the improvement
db.students.find({ course: "DBMS" }).explain("executionStats")
// stage: "IXSCAN", totalDocsExamined: 4200, executionTimeMillis: 6
```

## Compound index respecting the prefix rule

```js
db.orders.createIndex({ customerId: 1, orderDate: -1 })

// ✅ uses the index (matches the prefix: customerId)
db.orders.find({ customerId: ObjectId("...") }).sort({ orderDate: -1 })

// ❌ does NOT use this index efficiently (skips the prefix)
db.orders.find({ orderDate: { $gte: ISODate("2026-01-01") } })
```

## TTL index for expiring sessions

```js
db.sessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 1800 })
db.sessions.insertOne({ userId: "u1", token: "abc123", createdAt: new Date() })
// this document is automatically deleted ~30 minutes later, no cron job needed
```

---

# Visualization

## Sequential Scan vs Indexed Scan

```
 SEQUENTIAL SCAN (no index)          INDEXED SCAN (B-Tree index)
 ─────────────────────────           ────────────────────────────
 doc1 doc2 doc3 ... doc999999         [Balanced B-Tree, sorted]
   │    │    │         │                      │
   ▼    ▼    ▼         ▼               Binary-search-like jump
 check check check ... check                  │
   (EVERY document                    → straight to matches
    gets touched)                       (most documents SKIPPED)
```

## Compound Index Prefix Rule

```
 Index: { a: 1, b: 1, c: 1 }

 Query filters:      Can use this index?
 { a }                     ✅  (prefix)
 { a, b }                  ✅  (prefix)
 { a, b, c }                ✅  (full match)
 { b }                     ❌  (not a prefix)
 { c }                     ❌  (not a prefix)
 { b, c }                   ❌  (not a prefix)
```

## `.explain()` output at a glance

```
 { stage: "IXSCAN",  totalDocsExamined: 5,       nReturned: 5 }   ✅ efficient
 { stage: "COLLSCAN", totalDocsExamined: 1000000, nReturned: 5 }   ⚠️ inefficient
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Defining indexes directly in a Mongoose schema

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/shop");

const userSchema = new mongoose.Schema({
  username: String,
  email: { type: String, unique: true },   // creates a unique index automatically
  role: String
});

const productSchema = new mongoose.Schema({
  name: String,
  category: String,
  price: Number,
  tags: [String]
});

// Compound index — supports category+price queries efficiently
productSchema.index({ category: 1, price: -1 });

// Text index — supports full-text search on name
productSchema.index({ name: "text" });

const User = mongoose.model("User", userSchema);
const Product = mongoose.model("Product", productSchema);
```

## TTL index via Mongoose (auto-expiring sessions)

```js
const sessionSchema = new mongoose.Schema({
  userId: mongoose.Schema.Types.ObjectId,
  token: String,
  createdAt: { type: Date, default: Date.now, expires: 1800 }   // expires in 1800 seconds
});

const Session = mongoose.model("Session", sessionSchema);
```

## Search endpoint using a text index

```js
app.get("/products/search", async (req, res) => {
  const { q } = req.query;
  const results = await Product.find({ $text: { $search: q } });
  res.json(results);
});
```

## Filter endpoint that correctly leverages a compound index

```js
app.get("/products", async (req, res) => {
  const { category, minPrice } = req.query;

  // Matches the { category: 1, price: -1 } compound index's PREFIX
  const products = await Product.find({
    category,
    ...(minPrice && { price: { $gte: Number(minPrice) } })
  }).sort({ price: -1 });

  res.json(products);
});
```

## A route to verify index usage during development

```js
app.get("/debug/explain", async (req, res) => {
  const { category } = req.query;
  const explanation = await Product.find({ category }).explain("executionStats");
  res.json({
    stage: explanation.executionStats.executionStages.stage,
    docsExamined: explanation.executionStats.totalDocsExamined,
    returned: explanation.executionStats.nReturned
  });
});
```

## Geospatial query — nearby stores

```js
const storeSchema = new mongoose.Schema({
  name: String,
  location: { type: { type: String, enum: ["Point"], default: "Point" }, coordinates: [Number] }
});
storeSchema.index({ location: "2dsphere" });

const Store = mongoose.model("Store", storeSchema);

app.get("/stores/nearby", async (req, res) => {
  const { lng, lat, maxDistanceMeters = 5000 } = req.query;

  const stores = await Store.find({
    location: {
      $near: {
        $geometry: { type: "Point", coordinates: [Number(lng), Number(lat)] },
        $maxDistance: Number(maxDistanceMeters)
      }
    }
  });

  res.json(stores);
});
```

---

# Interview Questions

**Q1. What is an index, and why does it speed up queries?**
An index is a separate, sorted B-Tree data structure that maps field values to the physical location of the documents that contain them. It lets MongoDB jump nearly directly to matching documents (roughly `O(log n)`) instead of checking every document in the collection (`O(n)`), the way a book's index lets you find a topic without reading every page.

**Q2. What is a sequential scan (COLLSCAN), and when does it happen?**
A full collection scan where MongoDB checks every single document against the query filter, one by one — it happens when no usable index exists for the query being run.

**Q3. What data structure do MongoDB indexes use internally?**
A B-Tree (balanced tree) — the same fundamental structure used by most relational databases like PostgreSQL for their indexes.

**Q4. What is the "prefix rule" for compound indexes?**
A compound index `{ a: 1, b: 1, c: 1 }` can efficiently serve queries filtering on `a` alone, `a` and `b`, or all three — but not on `b` or `c` alone, since the index is physically sorted starting with `a`, and skipping straight to a middle/later field isn't possible without scanning.

**Q5. What does `.explain("executionStats")` show, and what's the most important comparison to make in its output?**
It shows the actual execution plan MongoDB chose for a query — whether it used an index (`IXSCAN`) or scanned the whole collection (`COLLSCAN`), plus stats like `totalDocsExamined` and `nReturned`. The most important comparison is `totalDocsExamined` vs. `nReturned` — a huge gap between them signals an inefficient query, even if an index is technically being used.

**Q6. What is a multikey index, and when is it automatically created?**
An index on a field whose values are arrays — MongoDB automatically indexes each array element individually, so a document with `tags: ["a", "b"]` gets two index entries, both pointing back to the same document. It's created automatically the moment you index an array field; no special syntax is needed.

**Q7. What is a covered query, and why is it especially fast?**
A query where every field in the filter, sort, and projection is part of a single index — meaning MongoDB can answer the entire query using only the index, without ever reading the actual documents from disk, making it significantly faster than a typical indexed query.

**Q8. What is the main tradeoff of adding more indexes to a collection?**
Faster reads, but slower writes (every insert/update/delete must also update each relevant index) and increased disk/memory usage to store and cache the indexes — so indexes should be added deliberately for genuinely common query patterns, not applied to every field indiscriminately.

**Q9. What's a TTL index, and give a real use case.**
An index that automatically deletes documents a set number of seconds after a date field's value — commonly used for session tokens, password reset codes, or temporary caches that should expire automatically without a separate cleanup job.

**Q10. Why might an index exist on a field, yet a query on that field still shows `COLLSCAN` in `.explain()`?**
Common reasons: the query doesn't actually match the index's prefix in a compound index, the query uses an operator that can't leverage that index efficiently (like an unanchored `$regex`), the field is referenced via `$expr` (which can't always use standard indexes), or MongoDB's query planner determined a collection scan was actually cheaper for this specific query (e.g., the filter matches most of the collection anyway, making the index not selective enough to be worth using).

---

# Practice Questions

## 🟢 Easy
1. Write a command to create a single-field ascending index on `email` in a `users` collection.
2. What does `COLLSCAN` mean in `.explain()` output?
3. Write a command to create a unique index on `sku_code` in a `products` collection.
4. What automatic index does every MongoDB collection have by default?

## 🟡 Medium
5. Create a compound index on `{ category: 1, price: -1 }` and write two example queries: one that WOULD use this index efficiently, and one that would NOT.
6. Run `.explain("executionStats")` (conceptually) on a query and explain what it would mean if `totalDocsExamined` was 500,000 but `nReturned` was only 3.
7. Write a TTL index definition that deletes password-reset-token documents 15 minutes after creation.
8. Explain, with an example, what a multikey index is and why it's created automatically.

## 🔴 Hard
9. A team has a compound index `{ status: 1, createdAt: -1 }` but a very common query filters only on `createdAt` (without `status`). Explain why this query performs poorly, and propose two different solutions.
10. Design a covered query: create an appropriate index and write a `find()` call (with filter + projection) that MongoDB could answer using only the index, without touching the actual documents.
11. Explain why adding 15 indexes to a write-heavy collection (thousands of inserts per second) could hurt overall system performance, even though each individual index speeds up certain reads.
12. A geospatial "find nearby stores" query and a text "search product names" query both need to run efficiently on the same `products` collection. Design the necessary indexes and explain why they're structurally different from a standard B-Tree single-field index.

---

# Mini Project

## ⚡ Mini Project: "Query Performance Lab" (Mongoose)

Build a small Express + Mongoose app that lets you compare indexed vs. unindexed query performance hands-on.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/perfLabDB");

const productSchema = new mongoose.Schema({
  name: String,
  category: String,
  price: Number,
  tags: [String]
});

const Product = mongoose.model("Product", productSchema);

const app = express();
app.use(express.json());

// Seed 100,000 test documents
app.post("/seed", async (req, res) => {
  const categories = ["Electronics", "Fitness", "Stationery", "Accessories"];
  const docs = Array.from({ length: 100000 }, (_, i) => ({
    name: `Product ${i}`,
    category: categories[i % categories.length],
    price: Math.floor(Math.random() * 5000),
    tags: ["tag" + (i % 10), "tag" + (i % 7)]
  }));
  await Product.insertMany(docs);
  res.json({ inserted: docs.length });
});

// Run the SAME query with and without an index, and compare
app.get("/compare", async (req, res) => {
  const { category } = req.query;

  // BEFORE — drop the index if it exists, to simulate no-index performance
  await Product.collection.dropIndexes().catch(() => {});
  const before = await Product.find({ category }).explain("executionStats");

  // Create the index
  await Product.collection.createIndex({ category: 1 });

  // AFTER
  const after = await Product.find({ category }).explain("executionStats");

  res.json({
    withoutIndex: {
      stage: before.executionStats.executionStages.stage,
      docsExamined: before.executionStats.totalDocsExamined,
      timeMs: before.executionStats.executionTimeMillis
    },
    withIndex: {
      stage: after.executionStats.executionStages.stage,
      docsExamined: after.executionStats.totalDocsExamined,
      timeMs: after.executionStats.executionTimeMillis
    }
  });
});

app.listen(3000, () => console.log("Query Performance Lab running on port 3000"));
```

### 🎯 Stretch Goals
- Extend `/compare` to test a compound index `{ category: 1, price: -1 }` against a query that uses both fields vs. one that only uses `price`.
- Add a text index on `name` and build a `/search` endpoint, comparing its `.explain()` output against a `$regex`-based search on the same field.
- Add a TTL-indexed `logs` collection and observe (via a scheduled check) documents actually disappearing after their expiry window.

---

# Common Mistakes

1. **Assuming an index is being used without ever checking `.explain()`** — a query can silently fall back to `COLLSCAN` for reasons that aren't obvious (wrong field order in a compound index, unanchored regex, `$expr`, etc.).
2. **Creating indexes on every field "just in case,"** without considering the real cost to write performance and memory/disk usage.
3. **Ignoring the compound index prefix rule**, expecting `{ a: 1, b: 1 }` to help a query that only filters on `b`.
4. **Forgetting that array fields automatically create multikey indexes**, and being surprised by unexpected index size growth on large arrays.
5. **Using `unique: true` on a field that already has duplicate values**, causing the index creation itself to fail until the duplicates are resolved.
6. **Not indexing fields used in `$sort`**, causing MongoDB to perform expensive in-memory sorts (and potentially hit sort memory limits) on large result sets.
7. **Treating TTL indexes as instantaneous** — MongoDB's TTL background process runs periodically (roughly every 60 seconds), so expired documents aren't deleted the exact instant they expire, just shortly after.
8. **Over-relying on `$regex`-based "search"** instead of a proper text index, missing out on relevance ranking and much better performance for genuine text search use cases.

---

# Best Practices

- ✅ Always verify index usage with `.explain("executionStats")` — don't assume, confirm.
- ✅ Design compound indexes to match your **actual, most common query patterns**, respecting field order (equality fields first, then sort/range fields — a common convention known as the "ESR rule": Equality, Sort, Range).
- ✅ Index fields used in `$match`, `sort()`, and `$lookup`'s `foreignField` for frequently-run queries.
- ✅ Use `unique: true` for fields that must never duplicate (emails, SKU codes, usernames) — it's both a data-integrity guarantee and a performance win.
- ✅ Use TTL indexes for naturally expiring data (sessions, tokens, temporary logs) instead of writing manual cleanup cron jobs.
- ✅ Periodically audit existing indexes (`db.collection.getIndexes()` + usage stats via `$indexStats`) and drop ones that are never actually used — unused indexes are pure overhead.
- ✅ Prefer a proper text index over `$regex` for genuine full-text search needs, especially at scale.
- ✅ Keep indexes in mind from the very start of schema design (Chapter 8) — retrofitting good indexing onto a poorly modeled schema only goes so far.

---

# Cheat Sheet

## Creating Indexes

```js
db.col.createIndex({ field: 1 })                             // single field
db.col.createIndex({ field1: 1, field2: -1 })                  // compound
db.col.createIndex({ field: 1 }, { unique: true })              // unique
db.col.createIndex({ arrayField: 1 })                           // multikey (automatic)
db.col.createIndex({ textField: "text" })                       // text
db.col.createIndex({ dateField: 1 }, { expireAfterSeconds: N })  // TTL
db.col.createIndex({ location: "2dsphere" })                    // geospatial
```

## Inspecting

```js
db.col.getIndexes()
db.col.find(filter).explain("executionStats")
```

## `.explain()` Key Fields

```
stage: "IXSCAN"   → ✅ index used
stage: "COLLSCAN" → ⚠️ full scan, no index used
totalDocsExamined vs nReturned  → BIG gap = inefficient query
```

## Compound Index Prefix Rule

```
Index { a, b, c }  serves:  {a}  {a,b}  {a,b,c}
                   does NOT serve:  {b}  {c}  {b,c}
```

## Tradeoff Summary

```
MORE INDEXES → faster reads, slower writes, more disk/RAM usage
FEWER INDEXES → faster writes, slower reads on unindexed queries
```

## Index Type Cheat Sheet

```
Single Field   → basic lookups on one field
Compound       → multi-field filters/sorts together
Unique         → enforce no-duplicates (emails, SKUs)
Multikey       → automatic, for array fields
Text           → full-text search with relevance ranking
TTL            → auto-expire documents after N seconds
Geospatial     → location-based "near me" queries
```
