# 📖 Chapter 5 — Operators

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Chapter 4 taught you the CRUD verbs. This chapter teaches you the **vocabulary** you use inside those verbs' filter objects — the query operators that let you ask precise questions like "students older than 21," "products that are either out of stock OR discontinued," "documents missing a field entirely," or "arrays containing at least 3 specific tags."

Without operators, MongoDB filters could only ever express simple equality (`{ age: 21 }`). Operators are what let your queries express real-world logic — comparisons, boolean combinations, existence checks, array conditions, and regex/expression matching.

---

# Theory

## Comparison Operators

Comparison operators test how a field's value relates to a given value — greater than, less than, in a list, etc.

| Operator | Meaning |
|---|---|
| `$eq` | Equal to |
| `$ne` | Not equal to |
| `$gt` | Greater than |
| `$gte` | Greater than or equal to |
| `$lt` | Less than |
| `$lte` | Less than or equal to |
| `$in` | Value is in a given array |
| `$nin` | Value is NOT in a given array |

> **Analogy:** Comparison operators are like the filters on a shopping website's price slider — "show me items ≥ ₹500 and ≤ ₹2000" is exactly `$gte`/`$lte` in action.

```js
db.students.find({ age: { $eq: 21 } })       // age is exactly 21 (same as { age: 21 })
db.students.find({ age: { $ne: 21 } })       // age is NOT 21
db.students.find({ age: { $gt: 21 } })       // age > 21
db.students.find({ age: { $gte: 21 } })      // age >= 21
db.students.find({ age: { $lt: 21 } })       // age < 21
db.students.find({ age: { $lte: 21 } })      // age <= 21

db.students.find({ course: { $in: ["DBMS", "OS"] } })    // course is DBMS OR OS
db.students.find({ course: { $nin: ["DBMS", "OS"] } })   // course is NEITHER DBMS NOR OS
```

---

## Logical Operators

Logical operators combine multiple conditions.

| Operator | Meaning |
|---|---|
| `$and` | All conditions must be true |
| `$or` | At least one condition must be true |
| `$nor` | NONE of the conditions may be true |
| `$not` | Negates a single condition |

> **Analogy:** `$and` is like a strict bouncer checking every item on a checklist before letting you in. `$or` is a bouncer who lets you in if you satisfy *any one* condition (VIP list, OR ticket, OR guest of someone inside). `$nor` is the opposite of `$or` — none of those things may be true. `$not` just flips a single yes/no answer.

```js
// $and — often implicit! {a: 1, b: 2} already means AND. Explicit $and needed for repeated fields.
db.students.find({ $and: [{ age: { $gte: 20 } }, { age: { $lte: 25 } }] })

// $or
db.students.find({ $or: [{ course: "DBMS" }, { course: "OS" }] })

// $nor — neither condition is true
db.students.find({ $nor: [{ course: "DBMS" }, { age: { $lt: 18 } }] })

// $not — negate a single condition
db.students.find({ age: { $not: { $gt: 21 } } })   // NOT (age > 21), i.e. age <= 21
```

⚠️ **When you actually need explicit `$and`:** if you need the **same field** to satisfy two conditions that can't both live in one object key (since object keys must be unique):
```js
// WRONG — the second "age" key silently overwrites the first in JS objects!
db.students.find({ age: { $gte: 20 }, age: { $lte: 25 } })

// CORRECT — use $and for multiple conditions on the same field
db.students.find({ $and: [{ age: { $gte: 20 } }, { age: { $lte: 25 } }] })
```

---

## Element Operators

Element operators test whether a field exists or what BSON type it is — useful when your schema is flexible and documents may or may not have certain fields.

| Operator | Meaning |
|---|---|
| `$exists` | Field is present (or absent) |
| `$type` | Field is a specific BSON type |

```js
db.students.find({ email: { $exists: true } })    // only documents that HAVE an email field
db.students.find({ email: { $exists: false } })   // only documents MISSING an email field

db.students.find({ age: { $type: "int" } })        // age field is stored as an integer
db.students.find({ age: { $type: "string" } })     // age field is (unexpectedly) a string — great for finding bad data!
```

> **Analogy:** `$exists` is like checking if a form has a "middle name" box filled in at all — regardless of what's written there. `$type` is like checking whether that box was filled in with a number when it should've been text.

---

## Array Operators

Array operators query fields that hold arrays — very common in MongoDB since arrays are a first-class field type.

| Operator | Meaning |
|---|---|
| `$size` | Array has exactly N elements |
| `$all` | Array contains ALL of the given values |
| `$elemMatch` | At least one array element matches ALL given conditions together |

```js
// Students with EXACTLY 3 courses
db.students.find({ courses: { $size: 3 } })

// Students who have BOTH "DBMS" and "OS" in their courses (order doesn't matter, can have more)
db.students.find({ courses: { $all: ["DBMS", "OS"] } })

// $elemMatch — for arrays of OBJECTS, matching multiple conditions on the SAME element
db.students.find({
  scores: { $elemMatch: { subject: "Math", marks: { $gte: 90 } } }
})
```

> **Analogy — why `$elemMatch` matters:** Imagine `scores: [{subject: "Math", marks: 60}, {subject: "Science", marks: 95}]`. If you write `{ "scores.subject": "Math", "scores.marks": { $gte: 90 } }` **without** `$elemMatch`, MongoDB checks each condition independently across the *whole array* — so it would incorrectly match this document (Math exists somewhere, and marks ≥ 90 exists somewhere, just not on the *same* element!). `$elemMatch` forces both conditions to be true on the **same single array element**.

```
 scores: [ {subject:"Math", marks:60}, {subject:"Science", marks:95} ]

 WITHOUT $elemMatch:  "subject":"Math" AND "marks":{$gte:90}
   → matches (wrongly!) because SOME element has subject Math,
     and SOME (different) element has marks >= 90

 WITH $elemMatch: { subject: "Math", marks: { $gte: 90 } }
   → correctly does NOT match — no single element satisfies BOTH
```

---

## Evaluation Operators

| Operator | Meaning |
|---|---|
| `$regex` | Field matches a regular expression pattern |
| `$expr` | Allows using aggregation expressions inside a query — lets you compare two FIELDS of the same document to each other |

### `$regex`

```js
db.students.find({ name: { $regex: "^Ro" } })              // name starts with "Ro"
db.students.find({ name: { $regex: "gupta", $options: "i" } })  // case-insensitive match
db.students.find({ email: /@gmail\.com$/ })                 // JS regex literal shorthand
```

> **Analogy:** `$regex` is MongoDB's version of SQL's `LIKE`/`ILIKE` — but far more powerful, since it's a full regular expression engine, not just `%`/`_` wildcards.

### `$expr`

Normal query filters compare a field to a **fixed value**. `$expr` lets you compare **one field to another field** in the same document — something a plain filter can't do.

```js
// Find products where price is greater than their own discountThreshold field
db.products.find({
  $expr: { $gt: ["$price", "$discountThreshold"] }
})

// Find students who scored higher in Science than in Math (comparing two fields)
db.students.find({
  $expr: { $gt: ["$scienceMarks", "$mathMarks"] }
})
```

> **Analogy:** A normal filter is like asking "is your height above 170cm?" — comparing a field to a constant. `$expr` is like asking "are you taller than your sibling?" — comparing two *variables* that live in the same record, something a simple filter has no syntax for.

---

# Why This Exists

A database that could only match exact field-to-constant equality would be nearly useless for real applications — you'd never be able to ask for "products under ₹1000," "users who are either admins or moderators," "orders missing a shipping address," or "students who improved between two exams." Operators exist to give MongoDB's query language the same expressive power SQL gets from `WHERE`, `AND`/`OR`, `LIKE`, `BETWEEN`, and subqueries — but expressed as a JSON-like filter object instead of a text-based clause language, matching MongoDB's document-native philosophy.

`$elemMatch` specifically exists because arrays of embedded objects are extremely common in MongoDB (a document's own strength — no join needed), and without it there would be no way to say "these conditions must all be true on the *same* array element" rather than "true somewhere across the whole array."

`$expr` exists because normal filters are fundamentally "field vs. constant" comparisons — but real business logic frequently needs "field vs. field" comparisons within the same document, which requires pulling in the aggregation framework's expression language into the query layer.

---

# Internal Working

## How MongoDB evaluates a compound filter

```
 Filter: { age: { $gte: 20 }, course: "DBMS" }

 1. MongoDB checks if a useful INDEX exists on "age" or "course".
        │
        ▼
 2. If an index exists, it narrows candidates via the index
    (fast — doesn't scan every document).
    If NOT, it performs a COLLECTION SCAN (checks every document).
        │
        ▼
 3. For each candidate document, EVERY condition in the filter
    object is evaluated (implicit AND between top-level keys).
        │
        ▼
 4. Only documents satisfying ALL conditions are returned.
```

`$or` conditions are handled differently — MongoDB may run **separate index scans for each branch** of the `$or` and then merge/de-duplicate the results, rather than a single combined index lookup. This is why deeply nested `$or`/`$and` combinations can sometimes be slower than a well-designed compound index covering the same logic — worth checking with `.explain()`.

## `$regex` performance note
A `$regex` with a **leading wildcard/unanchored pattern** (e.g. `{ $regex: "gupta" }` without `^`) cannot use a standard index efficiently — similar to SQL's `LIKE '%text%'` limitation — because the index is sorted by prefix, and MongoDB can't know where in the string the match starts. A regex anchored at the start (`^Ro`) *can* use an index, since it can jump straight to entries starting with "Ro".

## `$expr` performance note
Because `$expr` evaluates an aggregation-style expression **per document at query time** rather than doing a direct index lookup, it generally **cannot use indexes as efficiently** as a plain field-to-constant filter. Use it when you genuinely need field-to-field comparison, but don't reach for it as a default replacement for normal filters.

---

# Syntax

```js
// Comparison
{ field: { $eq: value } }
{ field: { $ne: value } }
{ field: { $gt: value } }
{ field: { $gte: value } }
{ field: { $lt: value } }
{ field: { $lte: value } }
{ field: { $in: [v1, v2] } }
{ field: { $nin: [v1, v2] } }

// Logical
{ $and: [ {cond1}, {cond2} ] }
{ $or: [ {cond1}, {cond2} ] }
{ $nor: [ {cond1}, {cond2} ] }
{ field: { $not: { $gt: value } } }

// Element
{ field: { $exists: true|false } }
{ field: { $type: "typeName" } }

// Array
{ arrayField: { $size: N } }
{ arrayField: { $all: [v1, v2] } }
{ arrayField: { $elemMatch: { cond1, cond2 } } }

// Evaluation
{ field: { $regex: "pattern", $options: "i" } }
{ $expr: { $gt: ["$field1", "$field2"] } }
```

---

# Examples

## Combining several operator families in one query

```js
db.students.find({
  $and: [
    { age: { $gte: 20, $lte: 25 } },              // comparison
    { $or: [{ course: "DBMS" }, { course: "OS" }] }, // logical
    { email: { $exists: true } },                    // element
    { courses: { $all: ["DBMS"] } },                 // array
    { name: { $regex: "^R", $options: "i" } }        // evaluation
  ]
})
```

## `$elemMatch` with real data

```js
db.students.insertOne({
  name: "Rohan",
  scores: [
    { subject: "Math", marks: 60 },
    { subject: "Science", marks: 95 }
  ]
})

// Correctly finds nobody (no single subject has marks >= 90 AND is "Math")
db.students.find({ scores: { $elemMatch: { subject: "Math", marks: { $gte: 90 } } } })

// Correctly finds Rohan (Science element satisfies both conditions together)
db.students.find({ scores: { $elemMatch: { subject: "Science", marks: { $gte: 90 } } } })
```

## `$expr` comparing two fields

```js
db.products.insertOne({ name: "Yoga Mat", price: 499, cost: 300 })

// Find products being sold at a loss (price < cost) — impossible with a normal filter!
db.products.find({ $expr: { $lt: ["$price", "$cost"] } })
```

---

# Visualization

## Operator families at a glance

```
 COMPARISON      LOGICAL         ELEMENT        ARRAY            EVALUATION
 ──────────      ────────        ────────       ─────────        ────────────
 $eq  $ne         $and             $exists        $size            $regex
 $gt  $gte         $or             $type          $all             $expr
 $lt  $lte         $nor                            $elemMatch
 $in  $nin         $not
```

## `$or` vs `$and` truth visualization

```
  condition A: age >= 20        condition B: course == "DBMS"

  $and: [A, B]   →  both must be TRUE            ✅ only if A AND B
  $or:  [A, B]   →  either can be TRUE            ✅ if A OR B (or both)
  $nor: [A, B]   →  neither may be TRUE           ✅ only if NOT A AND NOT B
```

---

# Backend Examples

> Backend examples in this chapter (and going forward) use **Mongoose** exclusively.

## Mongoose model (shared across examples)

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/college");

const studentSchema = new mongoose.Schema({
  name: String,
  age: Number,
  email: String,
  course: String,
  courses: [String],
  scores: [{ subject: String, marks: Number }]
});

const Student = mongoose.model("Student", studentSchema);
```

## Comparison operators in an Express filter endpoint

```js
app.get("/students", async (req, res) => {
  const { minAge, maxAge } = req.query;

  const students = await Student.find({
    age: { $gte: Number(minAge) || 0, $lte: Number(maxAge) || 100 }
  });

  res.json(students);
});
```

## Logical operators — flexible search endpoint

```js
app.get("/students/search", async (req, res) => {
  const { course, keyword } = req.query;

  const students = await Student.find({
    $and: [
      course ? { course } : {},
      keyword ? { $or: [
        { name: { $regex: keyword, $options: "i" } },
        { email: { $regex: keyword, $options: "i" } }
      ] } : {}
    ]
  });

  res.json(students);
});
```

## Element operators — find incomplete profiles

```js
app.get("/students/incomplete-profiles", async (req, res) => {
  const students = await Student.find({ email: { $exists: false } });
  res.json(students);
});
```

## Array operators — students with all required courses

```js
app.get("/students/qualified", async (req, res) => {
  // Must have taken BOTH "DBMS" and "OS"
  const students = await Student.find({ courses: { $all: ["DBMS", "OS"] } });
  res.json(students);
});

app.get("/students/toppers", async (req, res) => {
  // At least one score entry where marks >= 90 in the SAME subject entry
  const students = await Student.find({
    scores: { $elemMatch: { marks: { $gte: 90 } } }
  });
  res.json(students);
});
```

## `$expr` — comparing two fields via Mongoose

```js
const productSchema = new mongoose.Schema({
  name: String,
  price: Number,
  cost: Number
});
const Product = mongoose.model("Product", productSchema);

app.get("/products/loss-making", async (req, res) => {
  const products = await Product.find({
    $expr: { $lt: ["$price", "$cost"] }
  });
  res.json(products);
});
```

---

# Interview Questions

**Q1. What's the difference between `$eq` and just writing `{ field: value }`?**
They're functionally identical — `{ age: 21 }` is shorthand for `{ age: { $eq: 21 } }`. You'd use the explicit `$eq` form mainly when combining it with other operators on the same field, or for programmatic query building.

**Q2. Why can't you write `{ age: { $gte: 20 }, age: { $lte: 25 } }` to get an age range?**
Because JavaScript/JSON objects can't have two keys with the same name — the second `age` key overwrites the first. To apply multiple conditions to the same field, you'd combine them in one object (`{ age: { $gte: 20, $lte: 25 } }`) or use explicit `$and` if the conditions are more complex.

**Q3. What's the difference between `$or` and `$nor`?**
`$or` matches documents where **at least one** condition is true. `$nor` matches documents where **none** of the conditions are true (the logical opposite of `$or`).

**Q4. Why would you use `$exists` in a flexible-schema database like MongoDB?**
Because documents in the same collection can have different fields — `$exists` lets you specifically query for documents that do (or don't) have a given field at all, which is a very common need given MongoDB's optional/flexible schema.

**Q5. What problem does `$elemMatch` solve that a plain dot-notation query doesn't?**
Without `$elemMatch`, multiple conditions on fields inside an array of objects are checked independently across the *entire array*, potentially matching when different conditions are satisfied by *different* array elements. `$elemMatch` requires all specified conditions to be true on the **same** array element.

**Q6. What does `$expr` allow that a normal query filter cannot?**
`$expr` allows comparing two fields **within the same document** to each other (e.g., "is `price` less than `cost`?"), using aggregation expression syntax. Normal filters can only compare a field against a fixed constant value.

**Q7. Why is an unanchored `$regex` (e.g., `{ $regex: "abc" }`) potentially slow on large collections?**
Because it can't use a standard index efficiently — the index is sorted by prefix, and matching text anywhere in the string requires checking every value. A regex anchored to the start (`^abc`) *can* leverage an index, similar to how SQL's `LIKE 'abc%'` can use an index but `LIKE '%abc%'` generally can't.

**Q8. What's the difference between `$in` and multiple `$or` conditions on the same field?**
They're functionally equivalent for a single field: `{ course: { $in: ["DBMS", "OS"] } }` is simpler and typically more efficient than `{ $or: [{ course: "DBMS" }, { course: "OS" }] }`, since `$in` is specifically optimized for this exact "value is one of these" case.

**Q9. Give a real-world example where `$type` would be useful.**
Debugging data quality issues in a flexible-schema collection — e.g., finding documents where `age` was accidentally inserted as a string (`"21"`) instead of a number (`21`), using `{ age: { $type: "string" } }`, so you can find and fix inconsistent data.

**Q10. Is `$and` ever implicit, and when do you actually need it explicitly?**
Yes — multiple top-level keys in a filter object are implicitly ANDed together (`{ age: 21, course: "DBMS" }` means age=21 AND course=DBMS). You need explicit `$and` when you need multiple conditions on the **same field** that can't coexist as one key, or when combining complex nested `$or`/`$nor` clauses that need explicit grouping.

---

# Practice Questions

## 🟢 Easy
1. Write a query to find all products with `price` greater than `1000`.
2. Write a query to find all students whose `course` is either `"DBMS"` or `"Networks"`, using `$in`.
3. Write a query to find all documents where the `phone` field does NOT exist.
4. Write a query using `$ne` to find all students who are NOT named `"Rohan"`.

## 🟡 Medium
5. Write a query to find products priced between ₹500 and ₹2000 (inclusive) using `$gte`/`$lte`.
6. Write a query using `$nor` to find students who are neither in `"DBMS"` nor older than `30`.
7. Write a query to find all documents where `tags` is an array with exactly `4` elements.
8. Write a query using `$regex` (case-insensitive) to find all products whose name contains `"mouse"`.

## 🔴 Hard
9. Given `scores: [{subject: "Math", marks: 40}, {subject: "Science", marks: 95}]`, write a query using `$elemMatch` to find students who failed (marks < 50) in Math specifically — and explain why removing `$elemMatch` would give an incorrect result for a student who passed Math but failed Science.
10. Write a query using `$expr` to find all orders where `quantity * pricePerUnit` (two fields on the same document) exceeds a THIRD field, `budgetLimit`, also on the same document.
11. Explain why a query like `{ name: { $regex: "gupta" } }` (no `^` anchor) might perform a full collection scan even if an index exists on `name`, and rewrite it in a way that could use the index.
12. Design a single compound filter (using `$and`, `$or`, `$exists`, and `$in` together) to find: students aged 20–25, enrolled in either `"DBMS"` or `"OS"`, who have an `email` field, and are NOT in the `$nin` list `["banned1", "banned2"]` by name.

---

# Mini Project

## 🔍 Mini Project: "Advanced Student Search API" (Mongoose)

Build an Express + Mongoose API that exposes a single, powerful search endpoint exercising every operator family from this chapter.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/college");

const studentSchema = new mongoose.Schema({
  name: String,
  age: Number,
  email: String,
  courses: [String],
  scores: [{ subject: String, marks: Number }]
});

const Student = mongoose.model("Student", studentSchema);

const app = express();
app.use(express.json());

app.get("/students/advanced-search", async (req, res) => {
  const { minAge, maxAge, courses, hasEmail, minScoreSubject, minScoreValue, nameLike } = req.query;

  const filter = { $and: [] };

  // Comparison
  if (minAge || maxAge) {
    filter.$and.push({
      age: {
        ...(minAge && { $gte: Number(minAge) }),
        ...(maxAge && { $lte: Number(maxAge) })
      }
    });
  }

  // Array — must have ALL listed courses
  if (courses) {
    filter.$and.push({ courses: { $all: courses.split(",") } });
  }

  // Element
  if (hasEmail !== undefined) {
    filter.$and.push({ email: { $exists: hasEmail === "true" } });
  }

  // Array of objects — $elemMatch
  if (minScoreSubject && minScoreValue) {
    filter.$and.push({
      scores: { $elemMatch: { subject: minScoreSubject, marks: { $gte: Number(minScoreValue) } } }
    });
  }

  // Evaluation — regex search
  if (nameLike) {
    filter.$and.push({ name: { $regex: nameLike, $options: "i" } });
  }

  if (filter.$and.length === 0) delete filter.$and;

  const students = await Student.find(filter);
  res.json(students);
});

app.listen(3000, () => console.log("Advanced Search API running on port 3000"));
```

### 🎯 Stretch Goals
- Add a `topperOnly=true` query param that uses `$expr` to compare each student's `scores` average against a fixed passing threshold field stored on the document.
- Add pagination (`$skip`/`$limit` via Mongoose's `.skip()`/`.limit()`) to the search results.
- Add a `debug=true` param that runs `.explain()` on the query and returns whether an index was used — great for learning to spot slow, unindexed `$regex` queries.

---

# Common Mistakes

1. **Writing duplicate keys for the same field**, like `{ age: { $gte: 20 }, age: { $lte: 25 } }` — the second overwrites the first silently. Combine into one object or use `$and`.
2. **Forgetting `$elemMatch` when querying arrays of objects with multiple conditions** — leads to false-positive matches where conditions are satisfied by *different* array elements.
3. **Using unanchored `$regex` on large collections** without realizing it can't use an index — causing slow full collection scans that get worse as data grows.
4. **Reaching for `$expr` as a default** instead of a plain filter, when a normal field-to-constant comparison would work and perform far better.
5. **Confusing `$nin`/`$nor` with simple negation** — `$nin` negates membership in a list for one field; `$nor` negates an entire set of separate conditions. They're not interchangeable.
6. **Assuming `$exists: false` also excludes documents where the field is explicitly `null`** — it doesn't; `$exists` only checks presence/absence of the key, not whether its value is `null`. Use `{ field: null }` or `{ $or: [{field: null}, {field: {$exists: false}}] }` if you need to catch both.
7. **Not adding `$options: "i"` when case-insensitive search is intended**, causing `$regex` searches to miss results due to case mismatches.

---

# Best Practices

- ✅ Prefer `$in` over multiple `$or` clauses on the *same* field — cleaner and typically better optimized.
- ✅ Always use `$elemMatch` when applying multiple conditions to an array of embedded objects.
- ✅ Anchor `$regex` patterns (`^prefix`) whenever possible to allow index usage; consider MongoDB's text search or `Atlas Search` for genuinely unstructured full-text search needs at scale.
- ✅ Use `.explain("executionStats")` to verify whether your compound `$and`/`$or` queries are actually using indexes as expected.
- ✅ Reach for `$expr` only when you truly need field-to-field comparison — don't use it as a catch-all replacement for standard filters.
- ✅ Build dynamic filter objects carefully in application code (as in the mini project) — always guard against empty `$and`/`$or` arrays, which MongoDB may reject or behave unexpectedly on.
- ✅ Combine `$exists` with type checks (`$type`) when auditing data quality in a flexible-schema collection.

---

# Cheat Sheet

## Comparison

```js
$eq  $ne  $gt  $gte  $lt  $lte  $in  $nin
```

## Logical

```js
$and   // all true
$or    // at least one true
$nor   // none true
$not   // negate one condition
```

## Element

```js
$exists   // field present/absent
$type     // field is a specific BSON type
```

## Array

```js
$size       // array has exactly N elements
$all        // array contains all listed values
$elemMatch  // one element satisfies ALL listed conditions together
```

## Evaluation

```js
$regex   // pattern match (like SQL LIKE, but full regex)
$expr    // compare FIELD to FIELD (not just field to constant)
```

## Quick Decision Guide

```
Need a range?                  → $gte / $lte
Need "one of these values"?    → $in
Need "none of these values"?   → $nin
Need "field missing"?          → $exists: false
Need multi-condition match
  on ONE array element?         → $elemMatch
Need to compare two FIELDS?    → $expr
Need text pattern match?       → $regex (anchor with ^ when possible)
```
