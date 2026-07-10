# 📖 Chapter 6 — Cursor Methods

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Chapter 5 gave you the vocabulary to *filter* documents precisely. This chapter gives you the tools to control **how many** documents come back, **in what order**, **which page** of results you're looking at, and how to pull **unique values** out of a field — all without writing a single line of application-side JavaScript to do it manually.

These are called "cursor methods" because they're all chained directly onto the cursor object that `find()` returns — and understanding them properly is what separates a query that returns "the whole collection" from a query that returns "page 3, sorted by newest, 20 results at a time" — exactly what every real list/table UI needs.

---

# Theory

## `countDocuments()`

Returns the **number of documents** matching a filter — without actually fetching the documents themselves.

> **Analogy:** `countDocuments()` is like asking the librarian "how many mystery novels do you have?" without asking her to hand you all of them — she just tells you the number.

```js
db.students.countDocuments()                       // total documents in collection
db.students.countDocuments({ course: "DBMS" })      // documents matching a filter
```

⚠️ Older MongoDB versions had a `count()` method that's now deprecated in favor of `countDocuments()` (accurate, filter-aware) and `estimatedDocumentCount()` (very fast, but only for the *whole* collection, using metadata rather than actually scanning — no filter support).

## `sort()`

Orders the results by one or more fields — ascending (`1`) or descending (`-1`).

> **Analogy:** `sort()` is like asking the librarian to hand you books in alphabetical order, or newest-published first.

```js
db.students.find().sort({ age: 1 })                  // ascending by age
db.students.find().sort({ age: -1 })                 // descending by age
db.students.find().sort({ course: 1, age: -1 })       // sort by course A-Z, then age high-to-low within each course
```

## `limit()`

Caps the number of documents returned — essential for pagination and for avoiding accidentally pulling millions of rows into memory.

```js
db.students.find().limit(5)     // only the first 5 matching documents
```

## `skip()`

Skips over a given number of documents before starting to return results — used together with `limit()` for pagination.

```js
db.students.find().skip(10)     // skip the first 10 matching documents
```

> **Analogy:** Imagine a queue of 100 people. `skip(20)` means "ignore the first 20 people in line," and `limit(10)` means "then give me only the next 10." Together, that's exactly how you serve "page 3" of a list, 10 items per page.

## `distinct()`

Returns only the **unique values** for a given field across the collection — MongoDB's equivalent of SQL's `SELECT DISTINCT`.

```js
db.students.distinct("course")
// ["DBMS", "OS", "Networks"]   <- no duplicates, even if 500 students share a course
```

---

## Pagination

Pagination combines `sort()`, `skip()`, and `limit()` to serve data in fixed-size "pages" — exactly what every list UI (product catalogs, search results, admin tables) needs.

```
skip()
limit()
```

### The Formula

```
skip = (pageNumber - 1) * pageSize
limit = pageSize
```

> **Analogy:** Think of a 500-page book split into chapters of 20 pages each. To read "chapter 5," you don't start from page 1 — you skip the first `(5-1) * 20 = 80` pages, then read the next 20. That's exactly `skip()` and `limit()` working together.

```js
// Page 1, 10 per page  → skip 0, limit 10
db.students.find().sort({ _id: 1 }).skip(0).limit(10)

// Page 2, 10 per page  → skip 10, limit 10
db.students.find().sort({ _id: 1 }).skip(10).limit(10)

// Page 3, 10 per page  → skip 20, limit 10
db.students.find().sort({ _id: 1 }).skip(20).limit(10)
```

⚠️ **Always pair `skip()`/`limit()` with a `sort()`** — without an explicit sort order, MongoDB doesn't guarantee documents come back in the same order every time, which would make pagination unreliable (page 2 might repeat or skip documents from page 1).

---

# Why This Exists

No real application ever wants to dump an entire collection to the user at once — imagine an e-commerce site trying to render 2 million products on a single page. `limit()` and `skip()` exist to let applications retrieve data in manageable, predictable chunks — the backbone of every "page 1, 2, 3..." UI you've ever used. `sort()` exists because "manageable chunks" are only useful if they come in a meaningful, *stable* order (newest first, cheapest first, alphabetical). `countDocuments()` exists because UIs also need to show "Showing 1–10 of 245 results" — which requires knowing the total count *without* fetching all 245 documents. `distinct()` exists because a very common need — "what are all the possible categories/tags in this collection?" — would otherwise require fetching every document and de-duplicating manually in application code, which is wasteful and slow at scale.

---

# Internal Working

## How `skip()` + `limit()` actually execute

```
 Collection (100 matching documents, sorted)
 [doc1, doc2, doc3, ... doc10, doc11, ... doc20, ... doc100]

 skip(10).limit(10)
        │
        ▼
 MongoDB still has to WALK PAST the first 10 documents
 (even though they're never returned!) before it can
 start collecting the next 10 to send back.

  [doc1..doc10]  ← walked past, discarded (wasted work)
  [doc11..doc20] ← returned
```

**This is the critical performance gotcha with `skip()`:** it doesn't magically "jump" to the right position — MongoDB (even with an index) still has to traverse and discard every skipped document. On page 1, this is free (`skip(0)`). On page 5,000 of a huge collection (`skip(100000)`), MongoDB has to walk past 100,000 documents *every single time* that page is requested — this gets slower and slower the deeper you paginate. This is why very large-scale systems often switch to **cursor-based ("keyset") pagination** instead (see Best Practices below).

## How `sort()` interacts with indexes

If a **sorted field has an index**, MongoDB can read documents directly in index order (fast, no separate sort step needed). If there's **no index** on the sort field, MongoDB must load all matching documents into memory and sort them there — which can hit memory limits and get slow on large result sets (MongoDB will throw an error if an in-memory sort exceeds its default 100MB limit, unless `allowDiskUse` is used in the aggregation framework).

## How `distinct()` executes
`distinct()` typically scans an index on the target field if one exists (fast — it can walk the index and just collect unique keys), or performs a collection scan and de-duplicates in memory if no index exists.

## How `countDocuments()` differs internally from the old `count()`
`countDocuments()` is implemented as an aggregation pipeline internally (`$match` + `$group`/`$count`), meaning it actually accounts for the filter accurately, including within multi-document transactions. The old `count()` (deprecated) used collection metadata that could occasionally be inaccurate in certain sharded/replicated scenarios.

---

# Syntax

```js
// Count
db.collection.countDocuments(filter)
db.collection.estimatedDocumentCount()   // fast, whole-collection only, no filter

// Sort
db.collection.find(filter).sort({ field: 1 | -1 })

// Limit / Skip
db.collection.find(filter).limit(n)
db.collection.find(filter).skip(n)

// Distinct
db.collection.distinct("fieldName", filter)

// Pagination (combined)
db.collection.find(filter)
  .sort({ field: 1 })
  .skip((page - 1) * pageSize)
  .limit(pageSize)
```

---

# Examples

## Basic cursor method usage

```js
use college

db.students.countDocuments({ course: "DBMS" })
// 42

db.students.find().sort({ age: -1 }).limit(3)
// the 3 oldest students

db.students.distinct("course")
// ["DBMS", "OS", "Networks", "Maths"]
```

## Full pagination example

```js
// Page 2, 5 students per page, newest-registered first
db.students.find()
  .sort({ _id: -1 })
  .skip((2 - 1) * 5)   // skip 5
  .limit(5)
```

## Combining with filters and projections (everything so far, together)

```js
db.students.find(
  { course: "DBMS" },              // filter (Chapter 5)
  { name: 1, age: 1, _id: 0 }      // projection (Chapter 4)
)
.sort({ age: 1 })                   // sort
.skip(0)                            // pagination
.limit(10)
```

---

# Visualization

## Pagination math, visualized

```
 pageSize = 10

 Page 1: skip = (1-1)*10 = 0    →  documents  1-10
 Page 2: skip = (2-1)*10 = 10   →  documents 11-20
 Page 3: skip = (3-1)*10 = 20   →  documents 21-30

 ┌────────────────────────────────────────────────┐
 │ doc1 doc2 ... doc10 | doc11...doc20 | doc21...doc30 │
 │      PAGE 1          |     PAGE 2     |     PAGE 3    │
 └────────────────────────────────────────────────┘
```

## Why deep `skip()` gets slower

```
 skip(0)        →  walk 0 documents      (instant)
 skip(1,000)    →  walk 1,000 documents  (fast)
 skip(1,000,000)→  walk 1,000,000 docs   (SLOW — even with an index!)
```

## Cursor method chaining order (recommended)

```
 find(filter) → sort() → skip() → limit()
     │             │        │         │
   WHAT          ORDER    OFFSET     PAGE
   to get                              SIZE
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Mongoose model

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/college");

const studentSchema = new mongoose.Schema({
  name: String,
  age: Number,
  course: String
}, { timestamps: true });

const Student = mongoose.model("Student", studentSchema);
```

## `countDocuments()` — total count endpoint

```js
app.get("/students/count", async (req, res) => {
  const { course } = req.query;
  const count = await Student.countDocuments(course ? { course } : {});
  res.json({ count });
});
```

## `sort()` — sortable list endpoint

```js
app.get("/students", async (req, res) => {
  const { sortBy = "name", order = "asc" } = req.query;

  const students = await Student.find().sort({ [sortBy]: order === "asc" ? 1 : -1 });
  res.json(students);
});
```

## `distinct()` — list all course names for a filter dropdown

```js
app.get("/courses", async (req, res) => {
  const courses = await Student.distinct("course");
  res.json(courses);
});
```

## Full pagination endpoint (`skip()` + `limit()` + `sort()` + `countDocuments()`)

```js
app.get("/students/paginated", async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const pageSize = parseInt(req.query.pageSize) || 10;

  const filter = req.query.course ? { course: req.query.course } : {};

  const [students, totalCount] = await Promise.all([
    Student.find(filter)
      .sort({ _id: -1 })
      .skip((page - 1) * pageSize)
      .limit(pageSize),
    Student.countDocuments(filter)
  ]);

  res.json({
    data: students,
    page,
    pageSize,
    totalCount,
    totalPages: Math.ceil(totalCount / pageSize)
  });
});
```

Example response shape your frontend would receive:
```json
{
  "data": [ { "name": "Rohan", "age": 21, "course": "DBMS" }, "..." ],
  "page": 2,
  "pageSize": 10,
  "totalCount": 245,
  "totalPages": 25
}
```

---

# Interview Questions

**Q1. What's the difference between `countDocuments()` and `estimatedDocumentCount()`?**
`countDocuments()` accepts a filter and returns an accurate count by actually evaluating it (implemented as an aggregation internally). `estimatedDocumentCount()` is faster because it uses collection-level metadata instead of scanning, but it only counts the *entire* collection — it can't apply a filter.

**Q2. Why must `sort()` be used together with `skip()`/`limit()` for reliable pagination?**
Without an explicit sort order, MongoDB doesn't guarantee a consistent document order across repeated queries — meaning page 2 could accidentally repeat or skip documents that appeared on page 1. A deterministic sort (ideally on a unique field, or a combination that is unique) guarantees stable page boundaries.

**Q3. Why does `skip()` get slower as the skip value increases, even with an index?**
Because MongoDB still has to traverse and discard every skipped document one by one to reach the desired offset — it can't "jump" directly to position 100,000 the way an array index lookup would. The cost of `skip()` grows linearly with its value.

**Q4. What is `distinct()`, and what's its SQL equivalent?**
`distinct()` returns only the unique values present for a given field across a collection — equivalent to SQL's `SELECT DISTINCT field FROM table`.

**Q5. What's a better alternative to deep `skip()`-based pagination for very large datasets?**
Cursor-based (a.k.a. "keyset") pagination — instead of `skip(N)`, you remember the last document's sort key (e.g. its `_id` or `createdAt`) from the previous page, and query `{ _id: { $gt: lastSeenId } }` with a `limit()`. This avoids walking past discarded documents entirely, since it uses an index range condition instead of an offset.

**Q6. What order do cursor methods typically get chained in, and does the order in code matter?**
Conventionally: `find() → sort() → skip() → limit()`. In the Mongo Shell/driver, the order you *write* `.sort()`/`.skip()`/`.limit()` in code doesn't change the actual execution order — MongoDB always applies sort, then skip, then limit logically, regardless of the order you chained them in your code.

**Q7. Why might a `sort()` on an unindexed field be risky on a large collection?**
MongoDB may need to load all matching documents into memory to sort them, which can be slow and is subject to a memory limit (throwing an error) if the result set is large enough without an index to sort by.

**Q8. In a paginated API response, why do you typically return `totalCount` and `totalPages` in addition to the page's data?**
So the frontend can render pagination UI correctly — showing "Page 2 of 25," enabling/disabling next/previous buttons, or jumping directly to a specific page — none of which is possible with just the current page's documents alone.

**Q9. What does `find().distinct()`-style deduplication save you from doing manually?**
Without `distinct()`, you'd have to fetch every document, extract the field's value in application code, and de-duplicate manually (e.g., with a JS `Set`) — wasteful in both network transfer and memory for large collections, versus letting MongoDB do it server-side, often index-assisted.

**Q10. Why is it recommended to run `countDocuments()` and the paginated `find()` in parallel (e.g., `Promise.all`) rather than sequentially?**
Because the two queries are independent of each other — running them sequentially would mean waiting for the count query to finish before even starting the data query, doubling the wait time unnecessarily. Running them concurrently cuts the total response time roughly in half.

---

# Practice Questions

## 🟢 Easy
1. Write a query to count how many students are enrolled in `"OS"`.
2. Write a query to sort all products by `price` from highest to lowest.
3. Write a query to return only the first 5 documents in the `products` collection.
4. Write a query to get all distinct `category` values in the `products` collection.

## 🟡 Medium
5. Write a full pagination query for "page 4" with a page size of `15`, sorted by `createdAt` descending.
6. Explain why `db.students.find().skip(5).limit(5)` might return inconsistent results across two separate calls if no `sort()` is applied — and fix it.
7. Write a query that returns the total count of `"Fitness"` category products, and separately, the first 10 of them sorted by price ascending.
8. Write a `distinct()` query to find all unique `payment_method` values used across all orders.

## 🔴 Hard
9. Explain, step by step, why `skip(500000)` on a 1-million-document collection is significantly slower than `skip(10)`, even though both use the same index for sorting.
10. Design a cursor-based ("keyset") pagination query as an alternative to `skip()`/`limit()` for a `posts` collection sorted by `createdAt` descending, where the client provides the `createdAt` of the last post they saw.
11. A team's paginated endpoint returns `totalCount` using `countDocuments()` on every single page request, and their collection has 50 million documents. Propose a way to reduce the performance cost of repeatedly counting the same large collection (hint: think about caching or `estimatedDocumentCount()`).
12. Write a query combining `sort()`, `skip()`, `limit()`, and a compound filter (using operators from Chapter 5) to return "page 2" of DBMS students aged 20–25, sorted by age ascending, 5 per page.

---

# Mini Project

## 📚 Mini Project: "Paginated Course Catalog API" (Mongoose)

Build a full pagination-ready catalog API using every cursor method from this chapter.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/catalogDB");

const courseSchema = new mongoose.Schema({
  title: String,
  category: String,
  price: Number,
  enrolledCount: Number
}, { timestamps: true });

const Course = mongoose.model("Course", courseSchema);

const app = express();
app.use(express.json());

// GET /courses?page=2&pageSize=10&sortBy=price&order=desc&category=DBMS
app.get("/courses", async (req, res) => {
  const page = parseInt(req.query.page) || 1;
  const pageSize = parseInt(req.query.pageSize) || 10;
  const sortBy = req.query.sortBy || "createdAt";
  const order = req.query.order === "asc" ? 1 : -1;
  const filter = req.query.category ? { category: req.query.category } : {};

  const [courses, totalCount] = await Promise.all([
    Course.find(filter)
      .sort({ [sortBy]: order })
      .skip((page - 1) * pageSize)
      .limit(pageSize),
    Course.countDocuments(filter)
  ]);

  res.json({
    data: courses,
    page,
    pageSize,
    totalCount,
    totalPages: Math.ceil(totalCount / pageSize)
  });
});

// GET /courses/categories  — for a filter dropdown in the UI
app.get("/courses/categories", async (req, res) => {
  const categories = await Course.distinct("category");
  res.json(categories);
});

// GET /courses/stats  — quick counts per category
app.get("/courses/stats", async (req, res) => {
  const categories = await Course.distinct("category");
  const stats = await Promise.all(
    categories.map(async (cat) => ({
      category: cat,
      count: await Course.countDocuments({ category: cat })
    }))
  );
  res.json(stats);
});

app.listen(3000, () => console.log("Course Catalog API running on port 3000"));
```

### 🎯 Stretch Goals
- Replace `skip()`/`limit()` with cursor-based pagination using `_id` or `createdAt` as the keyset, and compare performance on a seeded collection of 100,000+ documents.
- Add a `MAX_PAGE_SIZE` guard so clients can't request `pageSize=999999` and accidentally overload the server.
- Cache the `totalCount` result for a few seconds (e.g., in memory or Redis) so it isn't recalculated on every single page request.

---

# Common Mistakes

1. **Using `skip()`/`limit()` without a `sort()`.** Document order isn't guaranteed without an explicit sort, so pages can show duplicate or missing items unpredictably.
2. **Assuming `skip()` is a cheap "jump to position" operation.** It isn't — MongoDB still walks through and discards every skipped document, making deep pagination progressively slower.
3. **Recomputing `countDocuments()` on every page load for huge collections** without considering the performance cost, when an estimated or cached count might be acceptable for the UI's purposes.
4. **Confusing chaining order with execution order.** Writing `.limit(10).skip(5)` instead of `.skip(5).limit(10)` in code doesn't change what MongoDB actually does — sort, then skip, then limit are applied in that logical order regardless of how you chained them.
5. **Forgetting `distinct()` exists**, and instead fetching all documents just to de-duplicate one field's values manually in application code.
6. **Sorting on an unindexed field for large collections**, causing slow in-memory sorts or hitting MongoDB's sort memory limit.
7. **Not guarding `pageSize` from user input**, allowing a malicious or buggy client to request an enormous `limit()` value that could overload the server.

---

# Best Practices

- ✅ Always pair `skip()`/`limit()` with an explicit, ideally unique-field-inclusive `sort()` for stable pagination.
- ✅ For very large collections or "infinite scroll" UIs, prefer **cursor/keyset pagination** (`{ _id: { $gt: lastSeenId } }` + `limit()`) over deep `skip()`, since it avoids the linear slowdown entirely.
- ✅ Index any field you regularly `sort()` or `distinct()` on for large collections.
- ✅ Run `countDocuments()` and the paginated `find()` concurrently (`Promise.all`) rather than sequentially.
- ✅ Cap `pageSize` server-side (e.g., max 100) regardless of what the client requests, to prevent abuse or accidental overload.
- ✅ Use `estimatedDocumentCount()` instead of `countDocuments()` when you only need a rough total-collection size and don't need to apply a filter (e.g., dashboard stats that can tolerate slight staleness).
- ✅ Return pagination metadata (`page`, `pageSize`, `totalCount`, `totalPages`) alongside data in every paginated API response, so frontends can build correct pagination UI.

---

# Cheat Sheet

## Cursor Methods

```js
db.col.countDocuments(filter)     // accurate count matching filter
db.col.estimatedDocumentCount()   // fast, whole-collection estimate, no filter
db.col.find().sort({ field: 1|-1 })
db.col.find().limit(n)
db.col.find().skip(n)
db.col.distinct("field", filter)
```

## Pagination Formula

```
skip  = (page - 1) * pageSize
limit = pageSize
```

## Recommended Chain Order

```js
db.col.find(filter)
  .sort({ field: 1 })
  .skip((page - 1) * pageSize)
  .limit(pageSize)
```

## Mongoose Pagination One-Liner Pattern

```js
const [data, totalCount] = await Promise.all([
  Model.find(filter).sort(sortObj).skip(skip).limit(limit),
  Model.countDocuments(filter)
]);
```

## When Deep Pagination Gets Slow

```
skip(0)        → instant
skip(1,000)    → fast
skip(500,000)  → slow — switch to cursor/keyset pagination instead
```
