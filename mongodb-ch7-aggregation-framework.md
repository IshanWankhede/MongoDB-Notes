# 📖 Chapter 7 — Aggregation Framework ⭐⭐⭐⭐⭐

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Everything up to this chapter — filters, operators, cursor methods — let you **find and shape** documents. The Aggregation Framework lets you **transform, combine, and summarize** them: total revenue per category, average marks per student, top 5 best-selling products, joining data across collections, reshaping nested arrays into flat rows, and running several reports in one single query.

This is the single most powerful (and most heavily interview-tested) feature in MongoDB. If Chapters 4–6 were "SQL's `SELECT`/`WHERE`/`ORDER BY`," this chapter is SQL's `GROUP BY`, `JOIN`, `CASE WHEN`, and window functions — all rolled into one flexible pipeline syntax.

---

# Theory

## 7.1 What is Aggregation?

**Aggregation** is the process of processing multiple documents and returning **computed/summarized results** — totals, averages, counts, groupings, joined data — rather than just the raw documents themselves.

> **Analogy:** A single document is like one receipt from a single purchase. Aggregation is like an accountant taking a whole shoebox of receipts and producing a monthly summary report: total spent, average purchase, spending by category. You're not looking at receipts anymore — you're looking at *insights derived from* them.

```js
// A plain query gives you raw documents
db.orders.find({ category: "Electronics" })

// Aggregation gives you a COMPUTED SUMMARY
db.orders.aggregate([
  { $match: { category: "Electronics" } },
  { $group: { _id: null, totalRevenue: { $sum: "$amount" } } }
])
// [ { _id: null, totalRevenue: 45230 } ]
```

## 7.2 Aggregation Pipeline

An aggregation is built as a **pipeline** — a sequence of "stages," where each stage takes the **output of the previous stage** as its input, transforms it, and passes the result to the next stage.

```
Stage1 → Stage2 → Stage3
```

> **Analogy:** Think of a factory assembly line. Raw material (documents) enters at Stage 1 (say, a filtering station that discards defective parts), moves to Stage 2 (an assembly station that groups parts together), then Stage 3 (a packaging station that arranges the final product for shipping). Each station only cares about what it receives from the station before it — it doesn't know or care about the raw material that started the whole line.

```js
db.orders.aggregate([
  { $match: { status: "delivered" } },        // Stage 1: filter
  { $group: { _id: "$category", total: { $sum: "$amount" } } },  // Stage 2: group & sum
  { $sort: { total: -1 } }                     // Stage 3: sort the summary
])
```

Each stage's output document shape can be **completely different** from its input — this is the key mental shift from `find()` (which always returns documents shaped like the originals) to `aggregate()` (which can reshape data at every step).

---

## 7.3 Pipeline Stages

### `$match`
Filters documents — exactly like `find()`'s filter object. Almost always the **first** stage, to discard irrelevant documents as early as possible (cheaper for everything downstream).

```js
{ $match: { category: "Electronics", price: { $gt: 500 } } }
```

### `$group`
Groups documents by a specified key (`_id`) and computes aggregate values (sum, average, count, etc.) per group — MongoDB's `GROUP BY`.

```js
{ $group: { _id: "$category", totalRevenue: { $sum: "$amount" }, orderCount: { $sum: 1 } } }
```

> **Analogy:** `$group` is like sorting a pile of receipts into labeled envelopes by store name, then writing the total spent on the outside of each envelope.

### `$project`
Reshapes each document — include/exclude fields, rename them, or compute new fields from existing ones (like a more powerful version of `find()`'s projection).

```js
{ $project: { name: 1, totalWithTax: { $multiply: ["$price", 1.18] }, _id: 0 } }
```

### `$sort`
Same as the cursor's `.sort()`, but as a pipeline stage — orders documents ascending (`1`) or descending (`-1`).

```js
{ $sort: { totalRevenue: -1 } }
```

### `$limit`
Caps the number of documents passed to the next stage.

```js
{ $limit: 5 }   // top 5, if placed after a $sort
```

### `$skip`
Skips a number of documents — used for pagination within a pipeline.

```js
{ $skip: 10 }
```

### `$count`
Outputs a single document containing the **count** of documents at that point in the pipeline.

```js
{ $count: "totalMatchingOrders" }
// [ { totalMatchingOrders: 245 } ]
```

### `$lookup`
Performs a **left outer join** with another collection — MongoDB's answer to SQL's `JOIN`.

```js
{
  $lookup: {
    from: "products",         // collection to join with
    localField: "productId",  // field on THIS collection (orders)
    foreignField: "_id",      // field on the OTHER collection (products)
    as: "productInfo"         // name of the new array field holding matches
  }
}
```

> **Analogy:** `$lookup` is like stapling a copy of the relevant product catalog page to every order receipt, so you don't have to look it up separately later.

### `$unwind`
"Flattens" an array field — turns **one document with an array of N elements** into **N separate documents**, each with one element from that array.

```js
// Before: { name: "Rohan", courses: ["DBMS", "OS"] }
{ $unwind: "$courses" }
// After:
// { name: "Rohan", courses: "DBMS" }
// { name: "Rohan", courses: "OS" }
```

> **Analogy:** `$unwind` is like taking one shopping receipt listing 3 items and splitting it into 3 separate single-item receipts — same underlying purchase, just represented one-item-per-row instead of one-list-per-receipt. This is often needed right before a `$group` on values that live inside an array.

### `$addFields`
Adds new fields to documents (keeping all existing fields) — unlike `$project`, it doesn't require you to explicitly list every field you want to keep.

```js
{ $addFields: { totalWithTax: { $multiply: ["$price", 1.18] } } }
// original document is UNCHANGED except for the new field being added
```

### `$facet`
Runs **multiple independent sub-pipelines** on the *same* input documents in a single stage, returning all their results together — perfect for a "one query, many reports" dashboard need.

```js
{
  $facet: {
    byCategory: [{ $group: { _id: "$category", total: { $sum: "$amount" } } }],
    topOrders: [{ $sort: { amount: -1 } }, { $limit: 3 }],
    totalCount: [{ $count: "count" }]
  }
}
```

---

## 7.4 Group Operators

These are used **inside** `$group` (or `$project`/`$addFields`) to compute values across documents in a group.

| Operator | Purpose |
|---|---|
| `$sum` | Total of a numeric field (or count, using `$sum: 1`) |
| `$avg` | Average of a numeric field |
| `$min` | Smallest value in the group |
| `$max` | Largest value in the group |
| `$push` | Collect values into an array (duplicates allowed) |
| `$addToSet` | Collect unique values into an array (no duplicates) |
| `$first` | The value from the FIRST document in the group (respects any preceding `$sort`) |
| `$last` | The value from the LAST document in the group |

```js
db.orders.aggregate([
  { $group: {
      _id: "$category",
      totalRevenue: { $sum: "$amount" },
      orderCount: { $sum: 1 },
      avgOrderValue: { $avg: "$amount" },
      cheapestOrder: { $min: "$amount" },
      priciestOrder: { $max: "$amount" },
      allCustomers: { $push: "$customerName" },
      uniqueCustomers: { $addToSet: "$customerName" }
  }}
])
```

⚠️ **`$first`/`$last` depend on document order** — they only give meaningful results if you've already `$sort`-ed the pipeline before the `$group` stage.

```js
db.orders.aggregate([
  { $sort: { orderDate: 1 } },
  { $group: { _id: "$customerName", firstOrderAmount: { $first: "$amount" }, latestOrderAmount: { $last: "$amount" } } }
])
```

---

## 7.5 Conditional Operators

### `$cond`
An if/then/else expression — MongoDB's version of a ternary operator.

```js
{ $project: {
    name: 1,
    stockStatus: {
      $cond: { if: { $gt: ["$stock", 0] }, then: "In Stock", else: "Out of Stock" }
    }
}}
```
Shorthand array form: `{ $cond: [ <if>, <then>, <else> ] }`

### `$switch`
Handles **multiple** conditions — like a `switch`/`case` statement, cleaner than nesting many `$cond`s.

```js
{ $project: {
    name: 1,
    priceTier: {
      $switch: {
        branches: [
          { case: { $lt: ["$price", 500] }, then: "Budget" },
          { case: { $lt: ["$price", 2000] }, then: "Mid-range" },
          { case: { $gte: ["$price", 2000] }, then: "Premium" }
        ],
        default: "Unknown"
      }
    }
}}
```

---

## 7.6 Date Operators

| Operator | Purpose |
|---|---|
| `$dateAdd` | Add a duration to a date |
| `$dateDiff` | Difference between two dates in a given unit |
| `$year` | Extract the year from a date |
| `$month` | Extract the month from a date |
| `$dayOfMonth` | Extract the day of the month |
| `$hour` | Extract the hour |

```js
{ $project: {
    orderDate: 1,
    dueDate: { $dateAdd: { startDate: "$orderDate", unit: "day", amount: 7 } },
    daysSinceOrder: { $dateDiff: { startDate: "$orderDate", endDate: "$$NOW", unit: "day" } },
    orderYear: { $year: "$orderDate" },
    orderMonth: { $month: "$orderDate" },
    orderDay: { $dayOfMonth: "$orderDate" },
    orderHour: { $hour: "$orderDate" }
}}
```

Real use: monthly revenue reports.
```js
db.orders.aggregate([
  { $group: {
      _id: { year: { $year: "$orderDate" }, month: { $month: "$orderDate" } },
      totalRevenue: { $sum: "$amount" }
  }},
  { $sort: { "_id.year": 1, "_id.month": 1 } }
])
```

---

## 7.7 Variables

Aggregation expressions can reference special **system variables** and developer-defined **user variables** — both prefixed with `$$` to distinguish them from normal field references (`$fieldName`).

### System Variables

| Variable | Meaning |
|---|---|
| `$$ROOT` | The complete original document at the start of the pipeline |
| `$$CURRENT` | The current document at the current stage (usually same as the implicit document context) |
| `$$NOW` | The current date/time when the aggregation runs |

```js
{ $group: {
    _id: "$category",
    cheapestFullProduct: { $min: "$$ROOT" }   // keeps the ENTIRE original document, not just one field
}}
```

### User Variables (`$let`)

`$let` defines your **own temporary variables** within an expression — useful to avoid repeating a complex sub-expression multiple times, or to name intermediate values for clarity.

```js
{ $project: {
    name: 1,
    finalPrice: {
      $let: {
        vars: { discountedPrice: { $multiply: ["$price", 0.9] } },
        in: { $round: ["$$discountedPrice", 2] }
      }
    }
}}
```

> **Analogy:** `$let` is like a spreadsheet formula that says "let X = A2*0.9, then show me ROUND(X, 2)" — instead of writing the discount calculation twice if you need to reuse it.

---

# Why This Exists

Real business questions are almost never "give me all the raw rows" — they're "what's our total revenue by category this month," "who are our top 10 customers," "what's the average order value," or "join this order with its product details and flatten the item list." A plain `find()` simply has no vocabulary for grouping, summarizing, joining, or reshaping data — it only filters and returns documents as-is.

The **pipeline design** (Stage1 → Stage2 → Stage3) exists because real reporting logic is naturally a sequence of transformations — filter first, then join, then flatten an array, then group, then sort the summary, then paginate the final report. Modeling this as a chain of small, composable stages (rather than one giant monolithic query) mirrors how you'd actually reason about the problem step by step, and lets MongoDB optimize/reorder certain stages internally for performance.

`$lookup` and `$unwind` specifically exist because MongoDB's document model, while great for embedding, still sometimes needs to combine data that lives in **separate collections** (referencing, not embedding) or needs to treat **array elements as individual rows** for grouping/counting purposes — both are things `find()` alone simply cannot do.

---

# Internal Working

## How a pipeline executes, stage by stage

```
 Input Collection (e.g. 10,000 orders)
        │
        ▼
 ┌─────────────┐   discards documents that don't match
 │  $match      │   (ideally uses an INDEX — cheapest to run first)
 └──────┬──────┘
        │  (e.g. 2,000 remain)
        ▼
 ┌─────────────┐   joins in related documents from another collection
 │  $lookup     │
 └──────┬──────┘
        │
        ▼
 ┌─────────────┐   flattens array fields into individual documents
 │  $unwind     │
 └──────┬──────┘
        │  (e.g. now 5,000 "rows", one per array item)
        ▼
 ┌─────────────┐   groups documents, computes sums/averages/etc
 │  $group      │
 └──────┬──────┘
        │  (e.g. now only 8 category-summary documents)
        ▼
 ┌─────────────┐   orders the SUMMARY documents
 │  $sort       │
 └──────┬──────┘
        ▼
   Final Output
```

**Why `$match` should come first:** MongoDB's aggregation optimizer can push an early `$match` down to use an index and drastically shrink the working set before expensive stages like `$lookup`, `$unwind`, or `$group` ever run — directly analogous to filtering rows before joining in SQL for performance.

## How `$group` works internally
MongoDB effectively builds an in-memory (or, for very large datasets, spill-to-disk with `allowDiskUse: true`) hash table keyed by the `_id` expression you specify, accumulating values (`$sum`, `$push`, etc.) into each bucket as documents stream through. This is conceptually identical to how a SQL engine executes `GROUP BY` with aggregate functions.

## How `$lookup` executes
For each document from the pipeline so far, MongoDB looks up matching documents in the `from` collection where `foreignField` equals the document's `localField` value — conceptually a per-document index lookup (fast if `foreignField` is indexed) rather than a single combined join plan like some SQL engines use, though modern MongoDB versions have optimized this significantly for equality joins.

## Memory limits
Each aggregation stage has a default **100MB** memory limit for stages like `$group` and `$sort`. If exceeded, MongoDB throws an error unless you add `{ allowDiskUse: true }` as an option to `aggregate()`, which lets it write intermediate results to temporary disk files — slower, but able to handle much larger datasets.

```js
db.orders.aggregate([ ... ], { allowDiskUse: true })
```

---

# Syntax

```js
db.collection.aggregate([
  { $match: { ... } },
  { $group: { _id: <expr>, field: { $sum/$avg/$min/$max/$push/$addToSet/$first/$last: <expr> } } },
  { $project: { field1: 1, computed: { <expression> } } },
  { $addFields: { newField: { <expression> } } },
  { $sort: { field: 1 | -1 } },
  { $limit: n },
  { $skip: n },
  { $count: "outputFieldName" },
  { $lookup: { from: "otherCollection", localField: "x", foreignField: "y", as: "joined" } },
  { $unwind: "$arrayField" },
  { $facet: { name1: [ ...subPipeline ], name2: [ ...subPipeline ] } }
], { allowDiskUse: true })
```

---

# Examples

## Revenue report by category

```js
db.orders.aggregate([
  { $match: { status: "delivered" } },
  { $group: { _id: "$category", totalRevenue: { $sum: "$amount" }, orders: { $sum: 1 } } },
  { $sort: { totalRevenue: -1 } }
])
```

## Join + unwind + group (orders → products → category summary)

```js
db.orders.aggregate([
  { $lookup: { from: "products", localField: "productId", foreignField: "_id", as: "product" } },
  { $unwind: "$product" },
  { $group: { _id: "$product.category", totalRevenue: { $sum: "$amount" } } },
  { $sort: { totalRevenue: -1 } }
])
```

## Conditional pricing tiers with `$switch`

```js
db.products.aggregate([
  { $project: {
      name: 1,
      priceTier: {
        $switch: {
          branches: [
            { case: { $lt: ["$price", 500] }, then: "Budget" },
            { case: { $lt: ["$price", 2000] }, then: "Mid-range" }
          ],
          default: "Premium"
        }
      }
  }}
])
```

## Monthly revenue trend using date operators

```js
db.orders.aggregate([
  { $group: {
      _id: { year: { $year: "$orderDate" }, month: { $month: "$orderDate" } },
      revenue: { $sum: "$amount" }
  }},
  { $sort: { "_id.year": 1, "_id.month": 1 } }
])
```

## `$facet` — one query, three reports at once

```js
db.orders.aggregate([
  { $match: { status: "delivered" } },
  { $facet: {
      revenueByCategory: [{ $group: { _id: "$category", total: { $sum: "$amount" } } }],
      top3Orders: [{ $sort: { amount: -1 } }, { $limit: 3 }],
      totalOrders: [{ $count: "count" }]
  }}
])
```

---

# Visualization

## The pipeline as an assembly line

```
 [10,000 raw orders]
        │
   ┌────▼────┐
   │ $match   │ → 2,000 relevant orders
   └────┬────┘
   ┌────▼────┐
   │ $lookup  │ → each order now has its product info attached
   └────┬────┘
   ┌────▼────┐
   │ $group   │ → collapsed into 8 category summaries
   └────┬────┘
   ┌────▼────┐
   │ $sort    │ → summaries ordered highest revenue first
   └────┬────┘
   [Final Report: 8 documents]
```

## `$unwind` visualized

```
 BEFORE (1 document):
 { student: "Rohan", courses: ["DBMS", "OS", "Networks"] }

 AFTER $unwind: "$courses"  (3 documents):
 { student: "Rohan", courses: "DBMS" }
 { student: "Rohan", courses: "OS" }
 { student: "Rohan", courses: "Networks" }
```

## `$facet` — one input, multiple parallel reports

```
                    ┌──> revenueByCategory
 [filtered orders] ─┼──> top3Orders
                    └──> totalOrders
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Mongoose models (shared)

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/shop");

const orderSchema = new mongoose.Schema({
  customerName: String,
  productId: mongoose.Schema.Types.ObjectId,
  category: String,
  amount: Number,
  status: String,
  orderDate: Date
});

const productSchema = new mongoose.Schema({
  name: String,
  category: String,
  price: Number,
  stock: Number
});

const Order = mongoose.model("Order", orderSchema);
const Product = mongoose.model("Product", productSchema);
```

## Revenue-by-category report endpoint

```js
app.get("/reports/revenue-by-category", async (req, res) => {
  const report = await Order.aggregate([
    { $match: { status: "delivered" } },
    { $group: { _id: "$category", totalRevenue: { $sum: "$amount" }, orderCount: { $sum: 1 } } },
    { $sort: { totalRevenue: -1 } }
  ]);
  res.json(report);
});
```

## Join across collections (`$lookup` + `$unwind`) via Mongoose

```js
app.get("/reports/orders-with-product-info", async (req, res) => {
  const orders = await Order.aggregate([
    { $lookup: {
        from: "products",        // MUST be the actual MongoDB collection name
        localField: "productId",
        foreignField: "_id",
        as: "product"
    }},
    { $unwind: "$product" },
    { $project: { customerName: 1, amount: 1, "product.name": 1, "product.category": 1 } }
  ]);
  res.json(orders);
});
```

## Monthly revenue trend endpoint

```js
app.get("/reports/monthly-revenue", async (req, res) => {
  const trend = await Order.aggregate([
    { $group: {
        _id: { year: { $year: "$orderDate" }, month: { $month: "$orderDate" } },
        revenue: { $sum: "$amount" }
    }},
    { $sort: { "_id.year": 1, "_id.month": 1 } }
  ]);
  res.json(trend);
});
```

## Dashboard endpoint using `$facet`

```js
app.get("/reports/dashboard", async (req, res) => {
  const [dashboard] = await Order.aggregate([
    { $match: { status: "delivered" } },
    { $facet: {
        revenueByCategory: [{ $group: { _id: "$category", total: { $sum: "$amount" } } }],
        topOrders: [{ $sort: { amount: -1 } }, { $limit: 5 }],
        totalStats: [{ $group: { _id: null, totalRevenue: { $sum: "$amount" }, totalOrders: { $sum: 1 } } }]
    }}
  ]);
  res.json(dashboard);
});
```

## Conditional stock status using `$cond`

```js
app.get("/products/stock-status", async (req, res) => {
  const products = await Product.aggregate([
    { $project: {
        name: 1,
        stock: 1,
        status: { $cond: { if: { $gt: ["$stock", 0] }, then: "In Stock", else: "Out of Stock" } }
    }}
  ]);
  res.json(products);
});
```

---

# Interview Questions

**Q1. What is the Aggregation Framework, and how is it different from `find()`?**
It's a pipeline-based tool for transforming, summarizing, and combining documents (grouping, joining, computing derived fields) — unlike `find()`, which only filters and returns documents in their original shape. Aggregation can reshape data completely at each stage.

**Q2. Explain the pipeline concept in your own words.**
An aggregation pipeline is a sequence of stages where each stage receives the output of the previous stage as its input and passes its own output to the next — like an assembly line, where each station transforms the product a little more before passing it along.

**Q3. Why should `$match` usually be the first stage in a pipeline?**
Because it lets MongoDB use an index to discard irrelevant documents immediately, shrinking the amount of data that expensive downstream stages (like `$lookup`, `$unwind`, `$group`) have to process — a major performance win, similar to filtering rows before joining in SQL.

**Q4. What's the difference between `$project` and `$addFields`?**
`$project` requires you to explicitly specify every field you want to keep (anything not listed is dropped, unless included with `1`). `$addFields` keeps all existing fields automatically and only adds (or overwrites) the fields you specify — you don't need to re-list the whole document.

**Q5. What does `$unwind` do, and when would you need it before a `$group`?**
`$unwind` deconstructs an array field, turning one document with an N-element array into N separate documents (one per array element). You need it before `$group` whenever you want to aggregate on values that live *inside* an array — `$group` can't reach inside an unflattened array to group by its individual elements.

**Q6. How does `$lookup` work, and what's its SQL equivalent?**
`$lookup` performs a left outer join with another collection, matching a local field against a foreign field and attaching the results as a new array field. It's MongoDB's equivalent of SQL's `LEFT JOIN`.

**Q7. What's the difference between `$first`/`$last` and `$min`/`$max` inside `$group`?**
`$min`/`$max` return the smallest/largest **value** of a field, regardless of document order. `$first`/`$last` return the value from whichever document happens to be first/last **in the current pipeline order** — meaningless unless you've explicitly `$sort`-ed beforehand.

**Q8. What is `$facet` used for, and give a real use case.**
`$facet` runs multiple independent sub-pipelines on the same input set of documents in a single aggregation call, returning all their results together. A common use case: building a dashboard that needs a category breakdown, a top-N list, and a total count — all from the same filtered order set — in a single round trip instead of three separate queries.

**Q9. What is `allowDiskUse`, and when would you need it?**
An option passed to `.aggregate()` that allows stages like `$group` and `$sort` to write intermediate data to temporary disk files if they'd otherwise exceed the default 100MB in-memory limit — needed for aggregations over very large datasets that can't fit comfortably in memory.

**Q10. What's the difference between `$$ROOT` and a normal field reference like `$fieldName`?**
`$fieldName` (single `$`) refers to a specific field's value within the current document. `$$ROOT` (double `$$`, a system variable) refers to the **entire original document** at that point in the pipeline — useful when you want to keep the whole document (e.g., inside `$min`/`$max`/`$push`) rather than just one field's value.

---

# Practice Questions

## 🟢 Easy
1. Write an aggregation to count how many orders exist per `status` value.
2. Write an aggregation using `$match` and `$count` to find how many products have `stock` equal to `0`.
3. Write a `$project` stage that renames `product_name` to `name` and includes `price`.
4. Write a `$sort` + `$limit` pipeline to find the 3 most expensive products.

## 🟡 Medium
5. Write an aggregation to compute the average `price` of products in each `category`, sorted from highest to lowest average.
6. Given `students` with a `scores` array of `{subject, marks}` objects, write a pipeline using `$unwind` and `$group` to find the average `marks` per `subject` across all students.
7. Write a pipeline using `$lookup` to join `orders` with `customers` (on `customerId` / `_id`), then `$unwind` the result, and project just `orderId`, `amount`, and `customerName`.
8. Write a `$project` stage using `$cond` to label products as `"Low Stock"` if `stock < 10`, otherwise `"Sufficient Stock"`.

## 🔴 Hard
9. Write a pipeline that computes total monthly revenue for the last 12 months using `$year`, `$month`, and `$group`, sorted chronologically.
10. Using `$facet`, write a single aggregation that returns: (a) total revenue by category, (b) the top 5 highest-value orders, and (c) the overall total order count — all from one `orders.aggregate()` call.
11. Explain, using the pipeline execution model, why placing `$match` AFTER a `$lookup`/`$unwind` (instead of before) could hurt performance significantly on a large collection — and rewrite an example pipeline to fix the ordering.
12. Design an aggregation using `$group` with `$first`/`$last` (after an appropriate `$sort`) to find, for each customer, their very first order amount and their most recent order amount.

---

# Mini Project

## 📊 Mini Project: "Sales Analytics Dashboard API" (Mongoose)

Build a single Express + Mongoose reporting API exercising nearly every stage and operator from this chapter.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/salesDB");

const orderSchema = new mongoose.Schema({
  customerName: String,
  productId: mongoose.Schema.Types.ObjectId,
  amount: Number,
  status: String,
  orderDate: Date
});

const productSchema = new mongoose.Schema({
  name: String,
  category: String,
  price: Number,
  stock: Number
});

const Order = mongoose.model("Order", orderSchema);
const Product = mongoose.model("Product", productSchema);

const app = express();
app.use(express.json());

// Full dashboard: revenue by category, top orders, monthly trend, stock status — in ONE call
app.get("/dashboard", async (req, res) => {
  const [dashboard] = await Order.aggregate([
    { $match: { status: "delivered" } },
    { $lookup: { from: "products", localField: "productId", foreignField: "_id", as: "product" } },
    { $unwind: "$product" },
    { $facet: {
        revenueByCategory: [
          { $group: { _id: "$product.category", totalRevenue: { $sum: "$amount" } } },
          { $sort: { totalRevenue: -1 } }
        ],
        monthlyTrend: [
          { $group: {
              _id: { year: { $year: "$orderDate" }, month: { $month: "$orderDate" } },
              revenue: { $sum: "$amount" }
          }},
          { $sort: { "_id.year": 1, "_id.month": 1 } }
        ],
        topOrders: [
          { $sort: { amount: -1 } },
          { $limit: 5 },
          { $project: { customerName: 1, amount: 1, "product.name": 1 } }
        ],
        overallStats: [
          { $group: { _id: null, totalRevenue: { $sum: "$amount" }, totalOrders: { $sum: 1 }, avgOrderValue: { $avg: "$amount" } } }
        ]
    }}
  ]);

  res.json(dashboard);
});

// Product price tiers using $switch
app.get("/products/price-tiers", async (req, res) => {
  const products = await Product.aggregate([
    { $project: {
        name: 1,
        priceTier: {
          $switch: {
            branches: [
              { case: { $lt: ["$price", 500] }, then: "Budget" },
              { case: { $lt: ["$price", 2000] }, then: "Mid-range" }
            ],
            default: "Premium"
          }
        }
    }}
  ]);
  res.json(products);
});

app.listen(3000, () => console.log("Sales Analytics API running on port 3000"));
```

### 🎯 Stretch Goals
- Add a `$facet` branch that uses `$addToSet` to list all unique customer names who placed a delivered order.
- Add `$dateDiff` to compute average delivery time if a `deliveredDate` field is added.
- Add `{ allowDiskUse: true }` and test the dashboard against a seeded collection of 500,000+ orders.

---

# Common Mistakes

1. **Putting `$match` too late in the pipeline** (or skipping it entirely), forcing expensive stages like `$lookup`/`$unwind`/`$group` to process far more documents than necessary.
2. **Using `$first`/`$last` without a preceding `$sort`** — the result becomes dependent on arbitrary/unspecified document order and isn't meaningful.
3. **Forgetting `$unwind` before grouping on array contents**, which silently produces wrong or empty group results since `$group` can't reach inside an un-flattened array.
4. **Confusing `$project`'s exclusion behavior** — forgetting that once you use inclusion (`field: 1`), every field not listed is dropped (except `_id`), unlike `$addFields`, which preserves everything by default.
5. **Not indexing the `foreignField` used in `$lookup`**, causing slow joins on large "other" collections.
6. **Hitting the 100MB memory limit** on `$group`/`$sort` for large datasets without adding `{ allowDiskUse: true }`, causing the aggregation to fail outright.
7. **Using the wrong collection name string in `$lookup`'s `from` field** — it must be the actual MongoDB collection name (usually lowercase, pluralized by Mongoose, e.g. `"products"`, not the Mongoose model name `"Product"`).
8. **Overcomplicating a report with nested `$cond`s** instead of a cleaner `$switch` when there are more than 2 conditions.

---

# Best Practices

- ✅ Always place `$match` (and `$sort`+`$limit`, if applicable early) as early as possible in the pipeline to minimize downstream work.
- ✅ Add indexes on fields used in `$match`, `$sort`, and `$lookup`'s `foreignField` — the aggregation optimizer can leverage them just like `find()` does.
- ✅ Use `$addFields` instead of `$project` when you just want to add/compute one new field and keep everything else untouched.
- ✅ Always `$sort` before relying on `$first`/`$last` inside `$group`.
- ✅ Use `$facet` to combine multiple related reports into a single round-trip instead of firing off several separate `aggregate()` calls.
- ✅ Use `{ allowDiskUse: true }` proactively for aggregations over large collections, rather than waiting for a memory-limit error in production.
- ✅ Prefer `$switch` over deeply nested `$cond` expressions once you have more than two branches — it's far more readable.
- ✅ Test complex pipelines stage-by-stage in the Mongo Shell (comment out later stages) to verify each stage's output shape before adding the next.

---

# Cheat Sheet

## Pipeline Stages

```js
$match      // filter documents (like find())
$group      // group + aggregate (like SQL GROUP BY)
$project    // reshape / include-exclude / compute fields
$sort       // order documents
$limit      // cap result count
$skip       // offset (pagination)
$count      // output a single count document
$lookup     // left outer join with another collection
$unwind     // flatten an array into multiple documents
$addFields  // add/compute fields, keep everything else
$facet      // run multiple sub-pipelines in parallel
```

## Group Operators

```js
$sum   $avg   $min   $max   $push   $addToSet   $first   $last
```

## Conditional Operators

```js
$cond    // if / then / else
$switch  // multi-branch case/when
```

## Date Operators

```js
$dateAdd   $dateDiff   $year   $month   $dayOfMonth   $hour
```

## Variables

```js
$$ROOT     // entire original document
$$CURRENT  // current document at this stage
$$NOW      // current date/time
$let       // define your own temporary variables
```

## Standard Pipeline Pattern

```js
db.col.aggregate([
  { $match: {...} },      // filter early
  { $lookup: {...} },     // join if needed
  { $unwind: "$arr" },    // flatten if needed
  { $group: {...} },      // summarize
  { $sort: {...} },       // order the summary
  { $limit: n }           // cap the report size
], { allowDiskUse: true })
```
