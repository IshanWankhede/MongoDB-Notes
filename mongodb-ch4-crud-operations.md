# 📖 Chapter 4 — CRUD Operations

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

CRUD — **Create, Read, Update, Delete** — is the beating heart of every database interaction your application will ever make. Chapter 3 taught you what a document *is*; this chapter teaches you how to actually **manipulate** documents: insert them, find them, change them, and remove them.

By the end of this chapter you'll be fluent in every core CRUD method (`insertOne`, `find`, `updateOne`, `deleteMany`, etc.), the most-used update operators (`$set`, `$inc`, `$push`...), projections, and the very important — and very commonly misunderstood — concept of **upsert**.

---

# Theory

## CREATE — Adding New Documents

### `insertOne()`
Inserts a **single** document into a collection.

> **Analogy:** `insertOne()` is like filing one new form into a filing cabinet drawer — one document goes in, one document comes back confirmed.

```js
db.students.insertOne({ name: "Rohan", age: 21, course: "DBMS" })
```

Returns an object confirming success and the auto-generated `_id`:
```js
{ acknowledged: true, insertedId: ObjectId("64f1a2b3c4d5e6f7a8b9c0d1") }
```

### `insertMany()`
Inserts **multiple** documents in a single call — much more efficient than calling `insertOne()` in a loop, since it's a single round-trip to the server.

```js
db.students.insertMany([
  { name: "Simran", age: 22, course: "OS" },
  { name: "Rohan", age: 21, course: "DBMS" },
  { name: "Akarsh", age: 23, course: "Networks" }
])
```

By default, if one document in the batch fails (e.g., duplicate `_id`), MongoDB stops and doesn't insert the remaining ones (**ordered** inserts). You can override this:

```js
db.students.insertMany([...], { ordered: false })
// continues inserting the rest even if one document fails
```

---

## READ — Retrieving Documents

### `find()`
Returns **all** documents matching a filter — technically returns a *cursor* (a pointer to the result set) that you iterate over or convert to an array.

> **Analogy:** `find()` is like asking the librarian "show me every book by this author" — you get a whole stack, not just one.

```js
db.students.find()                          // all documents
db.students.find({ course: "DBMS" })        // filtered
db.students.find({ age: { $gt: 21 } })      // age greater than 21
```

### `findOne()`
Returns only the **first matching document** (or `null` if none match) — not a cursor, just one plain object.

> **Analogy:** `findOne()` is like asking "give me just one example of a mystery novel" — the librarian hands you a single book, not the whole shelf.

```js
db.students.findOne({ name: "Rohan" })
```

### Projection
Projection controls **which fields** are returned — critical for performance (don't pull megabytes of unneeded data over the network) and for hiding sensitive fields (like passwords).

```js
// Second argument to find()/findOne() is the projection
db.students.find({}, { name: 1, course: 1 })          // ONLY name, course, and _id (included by default)
db.students.find({}, { name: 1, course: 1, _id: 0 })  // exclude _id explicitly
db.students.find({}, { password: 0 })                  // include everything EXCEPT password
```
⚠️ You cannot mix inclusion (`1`) and exclusion (`0`) in the same projection — except for `_id`, which is the one field allowed to be excluded alongside inclusions.

---

## UPDATE — Modifying Existing Documents

### `updateOne()`
Updates the **first** document that matches a filter.

```js
db.students.updateOne(
  { name: "Rohan" },
  { $set: { age: 22 } }
)
```

### `updateMany()`
Updates **all** documents that match a filter.

```js
db.students.updateMany(
  { course: "DBMS" },
  { $set: { passed: true } }
)
```

### `replaceOne()`
**Replaces the entire document** (except `_id`) with a brand-new one — unlike `updateOne`, it doesn't merge fields, it wipes and rewrites the whole document.

```js
db.students.replaceOne(
  { name: "Rohan" },
  { name: "Rohan Gupta", age: 22, course: "Networks" }
)
// Any fields NOT in the new document (like the old "course: DBMS") are GONE
```

> **Analogy:** `updateOne()` with `$set` is like editing one line on an existing form. `replaceOne()` is like throwing the entire form away and stapling in a brand-new one — anything you didn't rewrite is simply gone.

### Upsert
"Upsert" = **Update** + Ins**ert**. If a matching document exists, it's updated; if **no** document matches, a **new one is created** using the filter + update data combined.

```js
db.students.updateOne(
  { name: "New Student" },
  { $set: { age: 20, course: "DBMS" } },
  { upsert: true }
)
// If "New Student" doesn't exist yet, this CREATES a document:
// { _id: ObjectId(...), name: "New Student", age: 20, course: "DBMS" }
```

> **Analogy:** Upsert is like telling a receptionist "find John's file and update his phone number — but if John doesn't have a file yet, just create one." One instruction handles both cases.

---

## Update Operators

Update operators are special `$`-prefixed keys used inside the update document to describe *how* to change data — without them, MongoDB would only know how to replace the whole document.

| Operator | Purpose |
|---|---|
| `$set` | Set (or add) a field's value |
| `$unset` | Remove a field entirely |
| `$rename` | Rename a field |
| `$inc` | Increment/decrement a numeric field |
| `$push` | Add an item to an array |
| `$pull` | Remove item(s) from an array matching a condition |
| `$addToSet` | Add an item to an array, but only if it's not already present |

### `$set`
```js
db.students.updateOne({ name: "Rohan" }, { $set: { age: 22, city: "Pune" } })
// Updates age, ADDS city if it didn't exist before — other fields untouched
```

### `$unset`
```js
db.students.updateOne({ name: "Rohan" }, { $unset: { city: "" } })
// Removes the "city" field entirely (the value "" is ignored, just a convention)
```

### `$rename`
```js
db.students.updateOne({ name: "Rohan" }, { $rename: { course: "subject" } })
// The field "course" is now called "subject", value unchanged
```

### `$inc`
```js
db.products.updateOne({ name: "Yoga Mat" }, { $inc: { stock: -1 } })
// Decreases stock by 1 (negative values decrement)

db.students.updateOne({ name: "Rohan" }, { $inc: { loginCount: 1 } })
// Increases loginCount by 1 — perfect for counters, atomically!
```

### `$push`
```js
db.students.updateOne({ name: "Rohan" }, { $push: { courses: "Networks" } })
// Appends "Networks" to the courses array (allows duplicates)
```

### `$pull`
```js
db.students.updateOne({ name: "Rohan" }, { $pull: { courses: "OS" } })
// Removes ALL occurrences of "OS" from the courses array
```

### `$addToSet`
```js
db.students.updateOne({ name: "Rohan" }, { $addToSet: { courses: "DBMS" } })
// Adds "DBMS" ONLY if it's not already in the array — prevents duplicates
```

> **Analogy:** `$push` is like tossing another book onto a pile — even if there's already a copy there. `$addToSet` is like a librarian who checks the shelf first and only adds the book if it's not already there.

---

## DELETE — Removing Documents

### `deleteOne()`
Deletes the **first** document matching a filter.

```js
db.students.deleteOne({ name: "Rohan" })
```

### `deleteMany()`
Deletes **all** documents matching a filter.

```js
db.students.deleteMany({ course: "DBMS" })

// ⚠️ Deletes EVERY document in the collection if given an empty filter!
db.students.deleteMany({})
```

> **Analogy:** `deleteOne()` is pulling one specific file out of the cabinet. `deleteMany()` with a broad filter is like emptying an entire drawer — do it carefully.

---

# Why This Exists

Every application, no matter how simple, needs to persist data (Create), retrieve it (Read), keep it current (Update), and eventually remove it (Delete). CRUD isn't a MongoDB-specific idea — it's the universal shape of data interaction across virtually every kind of database and API. MongoDB's specific CRUD methods exist to map this universal need onto its document model: instead of `INSERT INTO ... VALUES` you get `insertOne()`, instead of `UPDATE ... SET` you get `updateOne({ $set: {...} })`.

The **update operators** (`$set`, `$inc`, `$push`, etc.) exist because a document isn't just a flat row — it has nested objects and arrays, and you often want to change *part* of that structure without re-sending or overwriting the whole thing. Without operators, every update would have to be a full `replaceOne()`, forcing you to read the entire document first, modify it in your app, then write the whole thing back — wasteful and prone to race conditions if two updates happen concurrently.

**Upsert** exists to eliminate a very common "check-then-act" bug: without it, you'd need to first `findOne()` to check if a document exists, then decide whether to `insertOne()` or `updateOne()` — two round trips, and a race condition if two requests do this simultaneously. Upsert makes it atomic and a single operation.

---

# Internal Working

## What happens during `updateOne({ $set: { age: 22 } })`

```
1. MongoDB finds the FIRST document matching the filter
   using an index (if one exists) or a collection scan.
        │
        ▼
2. The matched document is located on disk (WiredTiger storage engine).
        │
        ▼
3. Only the SPECIFIED fields ($set: {age: 22}) are modified
   in place — the rest of the document is untouched.
        │
        ▼
4. The modified document is written back to disk.
        │
        ▼
5. Any indexes on the changed field(s) are updated to stay in sync.
```

**Why `$set` is more efficient than `replaceOne()`:** MongoDB only needs to touch the specific bytes/fields being changed (especially efficient with WiredTiger's document-level operations), rather than reconstructing and rewriting the entire document from scratch.

## How `find()` returns a cursor, not an array

`find()` doesn't immediately fetch all matching documents into memory — it returns a **cursor**, which lazily fetches documents from the server in **batches** as you iterate. This matters for large result sets: `find()` on a 10-million-document collection won't try to load all 10 million into memory at once; it streams them.

```js
const cursor = db.students.find({ course: "DBMS" });
while (await cursor.hasNext()) {
  console.log(await cursor.next());   // fetched batch-by-batch under the hood
}

// Or, common shortcut: materialize into a full array (careful with huge result sets!)
const all = await db.students.find({ course: "DBMS" }).toArray();
```

## Upsert internals
When `upsert: true` and no document matches, MongoDB constructs a new document by combining the **filter's equality conditions** with the fields from your update document (`$set`, etc.), then inserts it — atomically, as a single operation, so there's no window where two concurrent requests could both decide "it doesn't exist yet" and create duplicates.

---

# Syntax

```js
// CREATE
db.collection.insertOne({ field: value })
db.collection.insertMany([{ ... }, { ... }], { ordered: true|false })

// READ
db.collection.find(filter, projection)
db.collection.findOne(filter, projection)

// UPDATE
db.collection.updateOne(filter, { $set: {...} }, { upsert: true|false })
db.collection.updateMany(filter, { $set: {...} })
db.collection.replaceOne(filter, newDocument)

// Update operators (used inside the update document)
{ $set: { field: value } }
{ $unset: { field: "" } }
{ $rename: { oldField: "newField" } }
{ $inc: { field: number } }
{ $push: { arrayField: value } }
{ $pull: { arrayField: conditionOrValue } }
{ $addToSet: { arrayField: value } }

// DELETE
db.collection.deleteOne(filter)
db.collection.deleteMany(filter)
```

---

# Examples

## Full CRUD lifecycle in one session

```js
use college

// CREATE
db.students.insertMany([
  { name: "Rohan", age: 21, courses: ["DBMS"], stock: 0 },
  { name: "Simran", age: 22, courses: ["OS", "Networks"] }
])

// READ
db.students.find({ age: { $gte: 21 } })
db.students.findOne({ name: "Rohan" }, { name: 1, courses: 1, _id: 0 })

// UPDATE with operators
db.students.updateOne({ name: "Rohan" }, { $set: { age: 22 } })
db.students.updateOne({ name: "Rohan" }, { $push: { courses: "Networks" } })
db.students.updateOne({ name: "Rohan" }, { $addToSet: { courses: "DBMS" } })  // no duplicate added
db.students.updateOne({ name: "Rohan" }, { $inc: { loginCount: 1 } })
db.students.updateOne({ name: "Rohan" }, { $rename: { courses: "subjects" } })
db.students.updateOne({ name: "Rohan" }, { $unset: { loginCount: "" } })

// UPSERT — creates if not found
db.students.updateOne(
  { name: "Akarsh" },
  { $set: { age: 23, subjects: ["Networks"] } },
  { upsert: true }
)

// DELETE
db.students.deleteOne({ name: "Simran" })
```

## Projection examples

```js
// Only names and ages, hide _id
db.students.find({}, { name: 1, age: 1, _id: 0 })

// Everything except a sensitive field
db.students.find({}, { password: 0 })
```

---

# Visualization

## CRUD → SQL equivalent map

```
 MongoDB                          SQL
 ────────────────────             ─────────────────────
 insertOne() / insertMany()  <-->  INSERT INTO ...
 find() / findOne()          <-->  SELECT ...
 updateOne() / updateMany()  <-->  UPDATE ... SET ...
 replaceOne()                <-->  (no direct equivalent — like DELETE + INSERT)
 deleteOne() / deleteMany()  <-->  DELETE FROM ...
```

## `updateOne` with `$set` vs `replaceOne`

```
 BEFORE:  { _id: 1, name: "Rohan", age: 21, course: "DBMS" }

 updateOne({$set:{age: 22}})        replaceOne({name:"Rohan", age:22})
 ────────────────────────────       ─────────────────────────────────
 { _id: 1, name: "Rohan",           { _id: 1, name: "Rohan", age: 22 }
   age: 22, course: "DBMS" }         <- "course" field is GONE!
   ^ course untouched
```

## Array operators visualized

```
 courses: ["DBMS", "OS"]

 $push: "OS"        →  ["DBMS", "OS", "OS"]     (duplicate allowed)
 $addToSet: "OS"    →  ["DBMS", "OS"]           (no change, already exists)
 $pull: "OS"        →  ["DBMS"]                 (all "OS" removed)
```

---

# Backend Examples

## Node.js + Express — full CRUD API (native driver)

```js
const express = require("express");
const { MongoClient, ObjectId } = require("mongodb");

const app = express();
app.use(express.json());
let db;

MongoClient.connect("mongodb://localhost:27017").then(client => {
  db = client.db("college");
  app.listen(3000, () => console.log("Server running on port 3000"));
});

// CREATE
app.post("/students", async (req, res) => {
  const result = await db.collection("students").insertOne(req.body);
  res.status(201).json(result);
});

// READ (all, with optional projection)
app.get("/students", async (req, res) => {
  const students = await db.collection("students")
    .find({}, { projection: { password: 0 } })
    .toArray();
  res.json(students);
});

// READ (one)
app.get("/students/:id", async (req, res) => {
  const student = await db.collection("students")
    .findOne({ _id: new ObjectId(req.params.id) });
  if (!student) return res.status(404).json({ error: "Not found" });
  res.json(student);
});

// UPDATE
app.patch("/students/:id", async (req, res) => {
  const result = await db.collection("students").updateOne(
    { _id: new ObjectId(req.params.id) },
    { $set: req.body }
  );
  res.json(result);
});

// UPDATE — add a course (array push, no duplicates)
app.post("/students/:id/courses", async (req, res) => {
  const result = await db.collection("students").updateOne(
    { _id: new ObjectId(req.params.id) },
    { $addToSet: { courses: req.body.course } }
  );
  res.json(result);
});

// DELETE
app.delete("/students/:id", async (req, res) => {
  const result = await db.collection("students").deleteOne({ _id: new ObjectId(req.params.id) });
  res.json(result);
});
```

## Mongoose — same API, schema-backed

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/college");

const studentSchema = new mongoose.Schema({
  name: { type: String, required: true },
  age: Number,
  courses: [String],
  loginCount: { type: Number, default: 0 }
});

const Student = mongoose.model("Student", studentSchema);

const app = express();
app.use(express.json());

// CREATE
app.post("/students", async (req, res) => {
  const student = await Student.create(req.body);   // wraps insertOne()
  res.status(201).json(student);
});

// READ with projection (Mongoose calls it "select")
app.get("/students", async (req, res) => {
  const students = await Student.find().select("name age -_id");
  res.json(students);
});

// UPDATE — $set under the hood
app.patch("/students/:id", async (req, res) => {
  const student = await Student.findByIdAndUpdate(
    req.params.id,
    { $set: req.body },
    { new: true }   // return the UPDATED document, not the old one
  );
  res.json(student);
});

// UPDATE — increment login count atomically
app.post("/students/:id/login", async (req, res) => {
  const student = await Student.findByIdAndUpdate(
    req.params.id,
    { $inc: { loginCount: 1 } },
    { new: true }
  );
  res.json(student);
});

// UPSERT example
app.put("/students/by-name/:name", async (req, res) => {
  const student = await Student.findOneAndUpdate(
    { name: req.params.name },
    { $set: req.body },
    { upsert: true, new: true }
  );
  res.json(student);
});

// DELETE
app.delete("/students/:id", async (req, res) => {
  await Student.findByIdAndDelete(req.params.id);
  res.status(204).send();
});

app.listen(3000, () => console.log("Server running on port 3000"));
```

---

# Interview Questions

**Q1. What's the difference between `insertOne()` and `insertMany()`?**
`insertOne()` inserts a single document and returns its `insertedId`. `insertMany()` inserts an array of documents in one round-trip and returns an array of `insertedIds` — much more efficient than looping `insertOne()` calls.

**Q2. What's the difference between `find()` and `findOne()`?**
`find()` returns a cursor over **all** matching documents (lazily fetched in batches). `findOne()` returns just the **first** matching document as a plain object, or `null` if nothing matches.

**Q3. What is a projection, and why use it?**
A projection specifies which fields to include or exclude in query results. It's used to reduce network payload (don't fetch fields you don't need) and to hide sensitive fields (like passwords) from query results.

**Q4. What's the difference between `updateOne()` and `replaceOne()`?**
`updateOne()` (typically with `$set`) modifies only the specified fields, leaving the rest of the document untouched. `replaceOne()` wipes out the entire document (except `_id`) and replaces it with a brand-new one — any fields not included in the replacement are lost.

**Q5. What is "upsert," and what problem does it solve?**
Upsert = update-or-insert. If a matching document exists, it's updated; if not, a new one is created from the filter + update data. It solves the race-condition/two-round-trip problem of manually checking "does this exist?" before deciding whether to insert or update.

**Q6. What's the difference between `$push` and `$addToSet`?**
`$push` appends a value to an array unconditionally, allowing duplicates. `$addToSet` only appends if the value isn't already present in the array, preventing duplicates.

**Q7. What happens if you run `deleteMany({})`?**
It deletes **every document** in the collection (an empty filter matches everything) — the collection itself still exists, just empty. This is a common and dangerous mistake if the empty `{}` is left in by accident.

**Q8. Why is `$inc` considered "atomic," and why does that matter?**
`$inc` increments a value directly on the server in a single atomic operation, so even if many requests increment the same counter simultaneously, none of the increments are lost (unlike reading a value, adding 1 in app code, then writing it back — which can race and lose updates).

**Q9. What does a cursor returned by `find()` actually represent?**
It's a pointer/reference to the result set on the server, not the data itself. Documents are fetched lazily in batches as you iterate, which avoids loading potentially huge result sets entirely into memory at once.

**Q10. Can you mix inclusion and exclusion in a single projection? Give an example of what's allowed.**
No, except for `_id`. You can do `{ name: 1, age: 1, _id: 0 }` (inclusion + excluding `_id`), but you cannot do `{ name: 1, age: 0 }` — mixing a "true" inclusion field with an exclusion of a different field is not allowed.

---

# Practice Questions

## 🟢 Easy
1. Write a query to insert a single product document with `name`, `price`, and `inStock` fields.
2. Write a query to find all students whose `age` is exactly `21`.
3. Write a query to delete one document where `name` is `"Rohan"`.
4. What's the difference between `$set` and `$unset`?

## 🟡 Medium
5. Write a projection query that returns only `name` and `email` fields (and excludes `_id`) for all documents in a `users` collection.
6. Write an `updateMany()` that adds `10` bonus points to every student whose `course` is `"DBMS"`, using `$inc`.
7. Write an upsert query: if a product named `"Yoga Mat"` exists, set its `price` to `599`; if it doesn't exist, create it with `price: 599` and `category: "Fitness"`.
8. Write a query using `$push` to add `"Chess"` to a student's `hobbies` array, and a separate query using `$addToSet` to safely add `"Chess"` again without creating a duplicate.

## 🔴 Hard
9. Explain, using `replaceOne()`, why replacing a document that has an `address` object could silently delete that address if you're not careful — then show the correct way to update just one nested field instead.
10. Write a MongoDB query that removes all occurrences of the value `"Suspended"` from a `statusHistory` array field, across ALL documents in the collection.
11. A junior developer runs `db.orders.deleteMany({ status: "pending" })` intending to delete only pending test orders, but the `status` field was actually blank/undefined on thousands of real orders due to a bug — meaning `deleteMany({ status: "pending" })` matched nothing, but a teammate later ran `deleteMany({})` by mistake on the same collection. Explain the difference in outcome between these two calls, and propose a safeguard your team could add before any `deleteMany()` runs in production.
12. Explain why `$inc` is safer than reading a field's current value in your Node.js app, adding 1, and writing it back with `$set`, under high concurrency (many simultaneous requests).

---

# Mini Project

## 🛒 Mini Project: "Mini Inventory Manager" (Full CRUD + Operators)

Build a small Express + MongoDB API that exercises every CRUD method and operator in this chapter.

```js
const express = require("express");
const { MongoClient, ObjectId } = require("mongodb");

const app = express();
app.use(express.json());
let products;

MongoClient.connect("mongodb://localhost:27017").then(client => {
  products = client.db("inventoryDB").collection("products");
  app.listen(3000, () => console.log("Inventory Manager running on port 3000"));
});

// CREATE — add a product
app.post("/products", async (req, res) => {
  const result = await products.insertOne({ ...req.body, tags: [], stock: req.body.stock || 0 });
  res.status(201).json(result);
});

// READ — list all, with projection (hide internal notes field)
app.get("/products", async (req, res) => {
  const all = await products.find({}, { projection: { internalNotes: 0 } }).toArray();
  res.json(all);
});

// READ — search by category
app.get("/products/category/:cat", async (req, res) => {
  const items = await products.find({ category: req.params.cat }).toArray();
  res.json(items);
});

// UPDATE — restock (increment stock)
app.post("/products/:id/restock", async (req, res) => {
  const result = await products.updateOne(
    { _id: new ObjectId(req.params.id) },
    { $inc: { stock: req.body.quantity } }
  );
  res.json(result);
});

// UPDATE — sell (decrement stock, never below 0 — enforced in app logic)
app.post("/products/:id/sell", async (req, res) => {
  const result = await products.updateOne(
    { _id: new ObjectId(req.params.id), stock: { $gte: req.body.quantity } },
    { $inc: { stock: -req.body.quantity } }
  );
  if (result.matchedCount === 0) return res.status(400).json({ error: "Not enough stock" });
  res.json(result);
});

// UPDATE — add a tag without duplicates
app.post("/products/:id/tags", async (req, res) => {
  const result = await products.updateOne(
    { _id: new ObjectId(req.params.id) },
    { $addToSet: { tags: req.body.tag } }
  );
  res.json(result);
});

// UPDATE — remove a tag
app.delete("/products/:id/tags/:tag", async (req, res) => {
  const result = await products.updateOne(
    { _id: new ObjectId(req.params.id) },
    { $pull: { tags: req.params.tag } }
  );
  res.json(result);
});

// UPSERT — set-or-create a product by name
app.put("/products/by-name/:name", async (req, res) => {
  const result = await products.updateOne(
    { name: req.params.name },
    { $set: req.body },
    { upsert: true }
  );
  res.json(result);
});

// DELETE — remove out-of-stock products
app.delete("/products/out-of-stock", async (req, res) => {
  const result = await products.deleteMany({ stock: 0 });
  res.json(result);
});
```

### 🎯 Stretch Goals
- Add a `$rename` route to rename a field across a product (e.g. `quantity` → `stock`) for legacy data cleanup.
- Add validation with Mongoose so `stock` can never be set to a negative number directly.
- Add an endpoint that uses `replaceOne()` and compare what happens to `tags`/other fields versus using `$set`.

---

# Common Mistakes

1. **Running `deleteMany({})` by accident** — an empty filter matches *every* document, wiping the whole collection. Always double-check the filter object isn't accidentally empty.
2. **Using `replaceOne()` when you meant `updateOne()` with `$set`** — this silently deletes any fields not included in the replacement document.
3. **Forgetting `$set` in an update call**, e.g. `updateOne({name: "Rohan"}, {age: 22})` — this actually tries to **replace** the whole document with `{age: 22}` (since there's no operator), potentially wiping other fields or throwing an error depending on the driver/version.
4. **Using `$push` when you meant `$addToSet`**, resulting in duplicate values silently piling up in an array over time.
5. **Assuming `find()` returns an array directly** — it returns a cursor; forgetting to call `.toArray()` (or iterate it) leads to confusing "why is this not an array" bugs.
6. **Not using projections on large documents**, pulling megabytes of unused data over the network unnecessarily, especially in list/pagination endpoints.
7. **Relying on `upsert: true` without realizing it can create unexpected documents** if the filter is broader/looser than intended (e.g. a typo in a field name creates a duplicate document instead of updating the intended one).
8. **Assuming `updateMany()` and `deleteMany()` are transactional across all matched documents by default** — without an explicit multi-document transaction, other operations could interleave between individual document updates within the batch.

---

# Best Practices

- ✅ Always double, triple-check filters before running `updateMany()` or `deleteMany()` in production — consider running the equivalent `find()`/`countDocuments()` first to preview what would be affected.
- ✅ Prefer `updateOne()` with `$set` over `replaceOne()` unless you genuinely intend to wipe and replace the whole document.
- ✅ Use `$addToSet` instead of `$push` whenever duplicates in an array would be a bug (e.g. tags, unique memberships).
- ✅ Use projections in read endpoints, especially list/pagination endpoints, to keep payloads small and avoid leaking sensitive fields.
- ✅ Use `$inc` for counters instead of read-modify-write in application code — it's atomic and avoids lost updates under concurrency.
- ✅ Use `upsert: true` deliberately and narrowly — make sure your filter is specific enough that it can't accidentally create duplicate/unintended documents.
- ✅ Use `{ new: true }` in Mongoose's `findOneAndUpdate`/`findByIdAndUpdate` when you need the **updated** document back, not the stale pre-update version (the default).
- ✅ For bulk writes with mixed operations, consider `bulkWrite()` for efficiency instead of many separate calls.

---

# Cheat Sheet

## CRUD Methods

```js
// CREATE
db.col.insertOne({...})
db.col.insertMany([{...}, {...}])

// READ
db.col.find(filter, projection)
db.col.findOne(filter, projection)

// UPDATE
db.col.updateOne(filter, { $set: {...} })
db.col.updateMany(filter, { $set: {...} })
db.col.replaceOne(filter, newDoc)
db.col.updateOne(filter, { $set: {...} }, { upsert: true })

// DELETE
db.col.deleteOne(filter)
db.col.deleteMany(filter)
```

## Update Operators Quick Reference

| Operator | Effect |
|---|---|
| `$set` | Set/add a field's value |
| `$unset` | Remove a field |
| `$rename` | Rename a field |
| `$inc` | Increment/decrement a number |
| `$push` | Add to array (duplicates allowed) |
| `$pull` | Remove matching item(s) from array |
| `$addToSet` | Add to array (no duplicates) |

## Projection Rules

```
{ field: 1 }        → include only these fields (+ _id by default)
{ field: 0 }        → exclude only these fields (include everything else)
{ field: 1, _id: 0 } → the ONE allowed mix (including fields, excluding _id)
```

## Danger Zone ⚠️

```js
db.col.deleteMany({})     // deletes EVERYTHING in the collection
db.col.replaceOne(...)    // wipes fields not in the new document
{ upsert: true }          // can silently CREATE a document if filter doesn't match
```
