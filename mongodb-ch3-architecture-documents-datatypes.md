# 📖 Chapter 3 — MongoDB Architecture, Documents & Data Types

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Chapter 1 explained *why* MongoDB exists. This chapter goes one level deeper: the actual **building blocks** MongoDB is made of — Server → Database → Collection → Document → Fields — and the raw material those documents are built from: BSON data types like Strings, Dates, ObjectIds, and Decimal128.

By the end of this chapter you'll know exactly what's inside a MongoDB document at the byte level, why `_id` looks the way it does, and how to run the handful of commands you'll type constantly (`show dbs`, `use`, `show collections`, `dropDatabase()`).

---

# Theory

## 3.1 MongoDB Architecture

MongoDB organizes data in a strict **hierarchy** — each level contains the one below it, similar to folders containing files.

```
Server
 ↓
Database
 ↓
Collection
 ↓
Document
 ↓
Fields
```

> **Analogy:** Think of a **server** as an entire office building. A **database** is one floor of that building dedicated to one company (e.g., "Sales"). A **collection** is a filing cabinet on that floor (e.g., "Invoices"). A **document** is one physical file inside that cabinet (e.g., Invoice #2026-105). A **field** is one line written on that file (e.g., "Amount: ₹5000").

```
┌───────────────────────────── SERVER (mongod) ─────────────────────────────┐
│                                                                            │
│   ┌──────────────── DATABASE: "college" ─────────────────┐                │
│   │                                                        │                │
│   │   ┌──── COLLECTION: "students" ────┐                  │                │
│   │   │  ┌───────────────────────────┐  │                  │                │
│   │   │  │ DOCUMENT                   │  │                  │                │
│   │   │  │  { _id: ObjectId("..."),   │  │  <- FIELDS       │                │
│   │   │  │    name: "Rohan",          │  │                  │                │
│   │   │  │    age: 21 }               │  │                  │                │
│   │   │  └───────────────────────────┘  │                  │                │
│   │   └─────────────────────────────────┘                  │                │
│   │                                                        │                │
│   │   ┌──── COLLECTION: "courses" ────┐                    │                │
│   │   └────────────────────────────────┘                    │                │
│   └────────────────────────────────────────────────────────┘                │
│                                                                            │
│   ┌──────────────── DATABASE: "ecommerce" ────────────────┐               │
│   └──────────────────────────────────────────────────────┘               │
└────────────────────────────────────────────────────────────────────────────┘
```

One MongoDB **server** process (`mongod`) can host many **databases**. Each database holds many **collections**. Each collection holds many **documents**. Each document holds many **fields**.

---

## 3.2 Database

A **database** is a container for collections. Each database has its own set of files on disk and is completely isolated from other databases on the same server (e.g., a `college` database and an `ecommerce` database never mix data).

> **Analogy:** A database is like a separate company floor in the office building — the "Sales" floor doesn't accidentally see filing cabinets from the "HR" floor.

```js
use college       // switches to (or creates) the "college" database
db                // shows which database you're currently using
```

**Important quirk:** MongoDB doesn't actually create the database on disk until you insert at least one document into a collection inside it. `use college` just *selects* it — it stays "phantom" until data is written.

---

## 3.3 Collection

A **collection** is a group of documents — MongoDB's equivalent of a SQL table, but without a fixed schema. Documents inside one collection can have completely different fields.

> **Analogy:** A collection is a filing cabinet drawer labeled "Invoices" — every file inside is *related* (they're all invoices), but one invoice might have a "discount" line and another might not. The cabinet doesn't demand every file look identical.

```js
db.createCollection("students")     // explicit creation
db.students.insertOne({ name: "Rohan" })   // implicit creation — MongoDB auto-creates the collection
```

Collections are created **implicitly** the first time you insert a document into them — you rarely need `createCollection()` explicitly unless you need special options (like validation rules or capped size).

---

## 3.4 Document

A **document** is the basic unit of data storage in MongoDB — a single record, represented as a BSON object (which looks just like JSON).

> **Analogy:** A document is one single file in the filing cabinet — one complete, self-contained record.

```js
{
  _id: ObjectId("64f1a2b3c4d5e6f7a8b9c0d1"),
  name: "Rohan Gupta",
  age: 21,
  isActive: true,
  courses: ["DBMS", "OS"],
  address: { city: "Pune", pincode: "411001" }
}
```

Key properties of a document:
- Maximum size: **16 MB** (large enough for almost anything except embedded binary files)
- Field order is preserved (though rarely relied upon)
- Can nest objects and arrays to any reasonable depth
- Every document **must** have a unique `_id` field (MongoDB auto-generates one if you don't provide it)

---

## 3.5 Fields

A **field** is a key-value pair inside a document — the MongoDB equivalent of a column in a SQL row, except each document can have its own set of fields.

> **Analogy:** A field is one line of text on the file — "Name: Rohan", "Age: 21". Different files (documents) in the same cabinet can have different lines written on them.

```js
{
  name: "Rohan",     // field: name  → value: "Rohan"
  age: 21,           // field: age   → value: 21
  isActive: true      // field: isActive → value: true
}
```
Field names are case-sensitive strings and generally cannot start with `$` or contain a `.` (both are reserved for MongoDB's query/update operators).

---

## 3.6 BSON

**BSON (Binary JSON)** is the binary-encoded format MongoDB actually uses internally to store and transmit documents. JSON is what *you* type and read; BSON is what MongoDB stores on disk and sends over the wire.

```
   You type (JSON-like):              MongoDB stores (BSON, binary):
   { name: "Rohan", age: 21 }    →    \x16\x00\x00\x00\x02name\x00...  (binary bytes)
```

Why binary instead of plain text JSON?
- **Faster to parse** — no need to tokenize text character by character
- **More compact** — binary encoding is denser than text
- **Richer types** — supports `Date`, `ObjectId`, `Binary`, `Decimal128`, `Int32`/`Int64` distinctly, which plain JSON has no native concept of (JSON only has one generic "number" type)
- **Traversable without full parsing** — BSON encodes the byte-length of each field upfront, so MongoDB can skip over fields it doesn't need without decoding the entire document

---

## 3.7 JSON vs BSON

| Feature | JSON | BSON |
|---|---|---|
| Format | Human-readable text | Binary |
| Parsing speed | Slower (text parsing) | Faster (binary parsing) |
| Size | Larger (text) | More compact |
| Data types | String, Number, Boolean, Array, Object, Null | All of JSON's types **plus** Date, ObjectId, Binary, Decimal128, Int32, Int64, Timestamp, Regex |
| Where used | APIs, config files, what you type in the shell | MongoDB's actual storage & wire format |
| Field order | Not guaranteed to matter | Preserved |

> **Analogy:** JSON is like a handwritten letter — easy for a human to read directly. BSON is like that same letter converted to a barcode — a machine reads it far faster, and the barcode can encode more precise information (like an exact date format) than plain handwriting can unambiguously express.

You almost never see raw BSON directly — the Mongo Shell and drivers automatically convert BSON ↔ JSON-like objects for you.

---

## 3.8 ObjectId

`ObjectId` is the default type MongoDB uses for the `_id` field — a special 12-byte identifier that's virtually guaranteed to be unique, even across different servers, without needing to coordinate with anyone.

```js
ObjectId("64f1a2b3c4d5e6f7a8b9c0d1")
```

### Structure of an ObjectId (12 bytes total)

```
┌──────────────┬──────────────┬───────────────┐
│ 4 bytes       │ 5 bytes       │ 3 bytes        │
│ Timestamp     │ Random value  │ Incrementing   │
│ (seconds since│ (unique per   │ counter        │
│  epoch)       │  process)     │ (starts random)│
└──────────────┴──────────────┴───────────────┘
```

- **First 4 bytes** — a Unix timestamp (seconds), meaning you can actually extract *when* a document was created directly from its `_id`!
- **Next 5 bytes** — a random value generated once per process, making collisions across different servers astronomically unlikely
- **Last 3 bytes** — an incrementing counter, ensuring uniqueness even for multiple inserts within the same second on the same process

```js
// Extract creation time straight from the _id — no separate "createdAt" field needed!
ObjectId("64f1a2b3c4d5e6f7a8b9c0d1").getTimestamp()
```

> **Analogy:** An ObjectId is like a passport number that encodes the issuing date, the issuing office, and a serial number all in one string — you can tell a lot just by looking at the number itself, and two different offices will never accidentally issue the same one.

---

## 3.9 Data Types

MongoDB (via BSON) supports a rich set of data types beyond plain JSON's basic four.

| Type | Description | Example |
|---|---|---|
| **String** | UTF-8 text | `"Rohan"` |
| **Number** | Split into `Int32`, `Int64`, `Double` internally | `21`, `499.99` |
| **Boolean** | true/false | `true` |
| **Date** | Milliseconds since Unix epoch (UTC) | `ISODate("2026-07-09T00:00:00Z")` |
| **Array** | Ordered list of values (mixed types allowed) | `["DBMS", "OS", 3]` |
| **Object** | Nested/embedded document | `{ city: "Pune" }` |
| **ObjectId** | 12-byte unique identifier | `ObjectId("64f1a2b3...")` |
| **Null** | Explicit "no value" | `null` |
| **Decimal128** | High-precision decimal (128-bit), for exact math | `NumberDecimal("19.99")` |

### Examples of each in one document

```js
{
  name: "Rohan Gupta",            // String
  age: 21,                        // Number (Int32)
  gpa: NumberDecimal("8.75"),     // Decimal128 — exact precision for financial/grade math
  isActive: true,                 // Boolean
  joinedOn: ISODate("2024-06-01"),// Date
  courses: ["DBMS", "OS"],        // Array
  address: { city: "Pune" },      // Object (embedded document)
  _id: ObjectId("64f1a2b3c4d5e6f7a8b9c0d1"), // ObjectId
  middleName: null                // Null
}
```

### Why Decimal128 matters
Regular JavaScript numbers (`Double`) use floating-point math, which can introduce tiny rounding errors — dangerous for money.

```js
0.1 + 0.2  // 0.30000000000000004  in floating point!
```
`Decimal128` stores numbers in an exact decimal format (like SQL's `NUMERIC`), avoiding these rounding errors — critical for prices, salaries, and financial totals.

---

## 3.10 Database Commands

These are the everyday "navigation" commands you'll type constantly in the Mongo Shell (`mongosh`).

```js
show dbs              // list all databases on this server
use college            // switch to (or create) the "college" database
show collections       // list all collections in the current database
db.dropDatabase()      // permanently delete the CURRENT database
```

### Full navigation walkthrough

```js
show dbs
// admin   40.00 KiB
// config  60.00 KiB
// local   72.00 KiB

use college
// switched to db college

db.students.insertOne({ name: "Rohan" })  // college now actually appears in `show dbs`

show collections
// students

db.dropDatabase()
// { ok: 1, dropped: 'college' }
```

⚠️ `db.dropDatabase()` is **irreversible** and deletes the entire database you're currently in — always double-check `db` (current database name) before running it.

---

# Why This Exists

The Server → Database → Collection → Document → Fields hierarchy exists for the same reason a filing system exists in any large organization: **without structure, retrieval becomes impossible at scale**. Even though MongoDB is "schema-flexible" at the document level, it still needs *some* organizational boundaries — otherwise a single server hosting thousands of unrelated apps would have no way to isolate one app's data from another's, back them up separately, or apply different access permissions.

BSON, ObjectId, and the rich type system exist because plain JSON is a *transport* format, not built for efficient storage or precise computation. MongoDB needed a format that's fast to parse, compact on disk, and capable of representing types (like exact dates and exact decimals) that real applications genuinely need — which plain JSON's single "number" and lack of a date type simply can't provide.

---

# Internal Working

## How a document travels from your code to disk

```
 Your JS Object                BSON (binary)              WiredTiger Storage Engine
 { name: "Rohan" }   ──encode──>  \x16\x00...   ──write──>  compressed on-disk pages
        ▲                                                          │
        │                                                          │
        └──────────────────decode (on read)───────────────────────┘
```

1. You call `db.students.insertOne({ name: "Rohan" })` in the shell or driver.
2. The driver **serializes** your JS object into BSON.
3. The `mongod` server receives the BSON, and the **WiredTiger storage engine** writes it to disk (with compression, by default — MongoDB compresses data on disk to save space).
4. An index (a B-Tree, on `_id` by default, plus any others you create) is updated so this document can be found quickly later.
5. On a `find()`, the reverse happens: WiredTiger reads the BSON bytes, the driver deserializes them back into a JS object for you.

## Why the hierarchy matters internally
Each **database** maps to its own set of files on disk (in the WiredTiger engine, each collection and index typically gets its own file). This is what makes `dropDatabase()` fast and clean — MongoDB can just delete a set of files rather than surgically removing scattered rows.

---

# Syntax

```js
// Architecture navigation
show dbs
use <databaseName>
show collections
db.dropDatabase()

// Collection creation
db.createCollection("collectionName")

// Document insertion (creates collection implicitly if needed)
db.collectionName.insertOne({ field1: value1, field2: value2 })
db.collectionName.insertMany([{ ... }, { ... }])

// Reading documents
db.collectionName.find()
db.collectionName.findOne({ field: value })

// Extracting timestamp from an ObjectId
ObjectId("...").getTimestamp()

// Decimal128 for exact numbers
NumberDecimal("19.99")

// Date
ISODate("2026-07-09")
new Date()
```

---

# Examples

## Example 1 — Full hierarchy in one shell session

```js
use ecommerce
db.createCollection("products")

db.products.insertOne({
  name: "Wireless Mouse",
  price: NumberDecimal("699.99"),
  inStock: true,
  tags: ["electronics", "accessories"],
  dimensions: { widthCm: 6, heightCm: 3 },
  addedOn: new Date(),
  discount: null
})

db.products.findOne()
```

## Example 2 — Inspecting an ObjectId's hidden timestamp

```js
const doc = db.products.findOne();
doc._id.getTimestamp();
// ISODate("2026-07-09T10:42:31.000Z")  <- exact moment this document was created!
```

## Example 3 — Same real entity, different shapes (legal in one collection)

```js
db.products.insertMany([
  { name: "T-Shirt", size: "L", price: NumberDecimal("499.00") },
  { name: "Laptop", specs: { ram: "16GB" }, price: NumberDecimal("55000.00"), warrantyYears: 1 }
]);
```

---

# Visualization

## The full hierarchy, annotated

```
 SERVER  (mongod process, e.g. localhost:27017)
   │
   ├── DATABASE: "college"
   │      │
   │      ├── COLLECTION: "students"
   │      │      ├── DOCUMENT { _id, name: "Rohan", age: 21 }
   │      │      └── DOCUMENT { _id, name: "Simran", city: "Mumbai" }
   │      │
   │      └── COLLECTION: "courses"
   │             └── DOCUMENT { _id, title: "DBMS" }
   │
   └── DATABASE: "ecommerce"
          └── COLLECTION: "products"
                 └── DOCUMENT { _id, name: "Mouse", price: NumberDecimal("699.99") }
```

## ObjectId byte breakdown

```
64f1a2b3   c4d5e6f7a8   b9c0d1
────────   ──────────   ──────
4 bytes     5 bytes      3 bytes
timestamp   random       counter
(when)      (which       (which insert,
             process)     in order)
```

---

# Backend Examples

## Node.js + native driver — exploring the hierarchy programmatically

```js
const { MongoClient } = require("mongodb");
const client = new MongoClient("mongodb://localhost:27017");

async function explore() {
  await client.connect();

  // List all databases on the server
  const admin = client.db().admin();
  const { databases } = await admin.listDatabases();
  console.log(databases.map(d => d.name));

  const db = client.db("college");

  // List all collections in this database
  const collections = await db.listCollections().toArray();
  console.log(collections.map(c => c.name));

  // Insert and inspect the auto-generated ObjectId
  const result = await db.collection("students").insertOne({ name: "Rohan", age: 21 });
  console.log(result.insertedId);                     // ObjectId
  console.log(result.insertedId.getTimestamp());       // creation time, extracted!

  await client.close();
}

explore();
```

## Express route using ObjectId to fetch a single document

```js
const { ObjectId } = require("mongodb");

app.get("/students/:id", async (req, res) => {
  try {
    const student = await db.collection("students")
      .findOne({ _id: new ObjectId(req.params.id) });

    if (!student) return res.status(404).json({ error: "Not found" });
    res.json(student);
  } catch (err) {
    res.status(400).json({ error: "Invalid ID format" });  // e.g. malformed ObjectId string
  }
});
```

## Mongoose — declaring types explicitly (mirrors BSON types)

```js
const mongoose = require("mongoose");

const productSchema = new mongoose.Schema({
  name: String,
  price: mongoose.Schema.Types.Decimal128,   // maps to BSON Decimal128
  inStock: Boolean,
  tags: [String],                            // Array of Strings
  dimensions: {                              // nested Object
    widthCm: Number,
    heightCm: Number
  },
  addedOn: { type: Date, default: Date.now },
  discount: { type: Number, default: null }
});

const Product = mongoose.model("Product", productSchema);
```

---

# Interview Questions

**Q1. What is the hierarchy of data organization in MongoDB?**
Server → Database → Collection → Document → Fields. A server hosts multiple databases; each database holds collections; each collection holds documents; each document holds fields (key-value pairs).

**Q2. What is the difference between a MongoDB collection and a SQL table?**
Both group related records, but a SQL table enforces a fixed schema (every row must have the same columns), while a MongoDB collection allows documents with different fields and structures.

**Q3. What is BSON, and how is it different from JSON?**
BSON (Binary JSON) is MongoDB's binary-encoded storage/wire format. Unlike text-based JSON, BSON is faster to parse, more compact, and supports additional types (Date, ObjectId, Decimal128, Binary) that plain JSON lacks.

**Q4. What is an ObjectId made of?**
A 12-byte value: 4 bytes for a Unix timestamp, 5 bytes of process-unique random value, and 3 bytes of an incrementing counter — together making it globally unique without coordination between servers.

**Q5. Can you get the creation time of a document without a separate `createdAt` field?**
Yes — call `.getTimestamp()` on its `_id` (assuming it's a default-generated ObjectId), since the first 4 bytes encode the creation time.

**Q6. Why does MongoDB provide a `Decimal128` type instead of relying on regular numbers for money?**
Regular floating-point numbers (`Double`) can introduce small rounding errors (e.g. `0.1 + 0.2 !== 0.3` exactly) due to how floating-point math works in binary. `Decimal128` stores decimal numbers exactly, avoiding these errors — critical for financial calculations.

**Q7. When is a MongoDB database or collection actually created on disk?**
A database is only physically created once at least one document is inserted into a collection within it. Simply running `use dbName` just selects/prepares it — it doesn't persist until data is written.

**Q8. What data types does BSON support that plain JSON does not?**
Date, ObjectId, Binary data, Decimal128, distinct Int32/Int64 types, Timestamp, and Regex — plain JSON only has String, Number, Boolean, Array, Object, and Null.

**Q9. What happens when you run `db.dropDatabase()`?**
It permanently and irreversibly deletes the *currently selected* database (`db`) and all its collections/documents/indexes. There's no built-in undo — you must restore from a backup if run by mistake.

**Q10. Can two different fields in the same document have different, unrelated data types across different documents in the same collection?**
Yes — e.g., one document could have `age: 21` (Number) while another has `age: "twenty-one"` (String). MongoDB allows this by default; enforcing consistency requires application-level validation (e.g., Mongoose) or MongoDB's schema validation rules.

---

# Practice Questions

## 🟢 Easy
1. Write out MongoDB's five-level data hierarchy from top to bottom.
2. What command lists all databases on the current server?
3. What command lists all collections in the currently selected database?
4. Name three BSON data types that don't exist in plain JSON.

## 🟡 Medium
5. Explain, step by step, what the 12 bytes of an ObjectId represent.
6. Write a Mongo Shell command sequence that: switches to a database called `library`, creates a `books` collection, inserts one book document, and lists all collections to confirm it worked.
7. Why might using a regular `Number` type for a `price` field cause subtle bugs in a billing system? What type should be used instead?
8. Explain the difference between `db.createCollection("x")` and just running `db.x.insertOne({...})` — do both create a collection?

## 🔴 Hard
9. A junior developer runs `db.dropDatabase()` while connected to the production database by mistake. Explain what would need to happen to recover, and propose two safeguards that could have prevented this.
10. Design a single MongoDB document (with realistic field names/values) for a "blog post" that demonstrates at least 6 different BSON data types (String, Number, Boolean, Date, Array, Object, ObjectId, Null, Decimal128) being used meaningfully — not just for the sake of using them.
11. Explain why BSON encodes the byte-length of fields upfront, and how that enables MongoDB to skip over unneeded fields without fully parsing a document.
12. Compare how "isolation between unrelated data" is achieved in MongoDB (via databases) versus in a traditional SQL server (via schemas/databases) — are the concepts equivalent?

---

# Mini Project

## 🏫 Mini Project: "College Explorer" — Navigate the Full Hierarchy

Build a tiny Node.js script that exercises every concept in this chapter — from server-level listing down to individual field types.

```js
const { MongoClient, ObjectId } = require("mongodb");

async function main() {
  const client = new MongoClient("mongodb://localhost:27017");
  await client.connect();

  // 1. List all databases (SERVER level)
  const { databases } = await client.db().admin().listDatabases();
  console.log("Databases on server:", databases.map(d => d.name));

  // 2. Select / create a DATABASE
  const db = client.db("college");

  // 3. Create a COLLECTION and insert DOCUMENTS with varied FIELDS and types
  await db.collection("students").insertMany([
    {
      name: "Rohan Gupta",              // String
      age: 21,                          // Number
      gpa: require("mongodb").Decimal128.fromString("8.75"), // Decimal128
      isActive: true,                   // Boolean
      enrolledOn: new Date(),           // Date
      courses: ["DBMS", "OS"],          // Array
      address: { city: "Pune" },        // Object
      middleName: null                  // Null
    },
    {
      name: "Simran Mehta",
      age: 22,
      courses: []
    }
  ]);

  // 4. List COLLECTIONS to confirm creation
  console.log("Collections:", (await db.listCollections().toArray()).map(c => c.name));

  // 5. Fetch a document and inspect its ObjectId's hidden timestamp
  const student = await db.collection("students").findOne({ name: "Rohan Gupta" });
  console.log("Created at:", student._id.getTimestamp());

  await client.close();
}

main();
```

### 🎯 Stretch Goals
- Add a route in Express: `GET /students/:id/created-at` that returns just the extracted `getTimestamp()` from the ObjectId — no separate `createdAt` field allowed.
- Add a `db.dropDatabase()` "reset" script — but require typing the database name as a confirmation argument before it runs, as a safeguard exercise.
- Build a small CLI tool that takes a database name and prints its full hierarchy (collections → document count → sample field types) — a mini "College Explorer."

---

# Common Mistakes

1. **Assuming `use dbName` creates the database immediately.** It doesn't — the database only becomes real once you insert a document. Running `show dbs` right after `use newDB` won't show it yet.
2. **Treating `_id` as just a random string.** Ignoring that a default `ObjectId` already encodes a creation timestamp, and adding a redundant `createdAt` field when it's often unnecessary (though many teams still add one explicitly for clarity/indexing convenience — that's a legitimate choice, not always a mistake).
3. **Using `Number`/`Double` for money fields.** Leads to floating-point rounding errors; use `Decimal128` for exact financial math.
4. **Running `db.dropDatabase()` without checking which database is currently selected.** This is one of the most common "oops, I deleted production" stories in MongoDB — always run `db` first to confirm.
5. **Assuming every document in a collection has the same fields**, then writing code that crashes when a field is unexpectedly missing (e.g. `doc.address.city` when `address` doesn't exist on some documents).
6. **Confusing JSON and BSON as if they're the same thing.** JSON is what you *type*; BSON is what's actually *stored*. This matters when explaining why MongoDB supports types (like `Date`) that plain JSON.parse()/stringify() in JavaScript doesn't natively preserve.
7. **Manually constructing `ObjectId` strings instead of letting MongoDB generate them**, risking collisions or malformed IDs.

---

# Best Practices

- ✅ Always confirm the current database (`db`) before running destructive commands like `dropDatabase()`.
- ✅ Use `Decimal128` for any field involving money, precise measurements, or exact decimal math.
- ✅ Let MongoDB auto-generate `_id` as an `ObjectId` unless you have a specific, well-understood reason to use a custom `_id`.
- ✅ Use `.getTimestamp()` on `_id` when you just need creation time and don't want a redundant field — but add an explicit `createdAt` field if you need it indexed independently or if `_id` might ever be custom-set.
- ✅ Keep documents reasonably sized — approaching the 16MB limit is usually a sign you should be referencing data in a separate collection instead of embedding everything.
- ✅ Use consistent field types across documents in the same collection in practice, even though MongoDB doesn't force it — enforce this via Mongoose schemas or `$jsonSchema` validation.
- ✅ Name databases and collections descriptively and consistently (lowercase, no spaces) — e.g. `college`, `students`, not `College_DB `.

---

# Cheat Sheet

## Hierarchy

```
Server → Database → Collection → Document → Fields
```

## Navigation Commands

```js
show dbs                  // list databases
use <dbName>               // switch/create database
show collections           // list collections in current db
db.dropDatabase()          // delete current database (irreversible!)
db.createCollection("x")   // explicitly create a collection
```

## BSON Data Types Quick Reference

| Type | Example |
|---|---|
| String | `"Rohan"` |
| Number | `21`, `499.99` |
| Boolean | `true` / `false` |
| Date | `new Date()`, `ISODate("2026-07-09")` |
| Array | `["DBMS", "OS"]` |
| Object | `{ city: "Pune" }` |
| ObjectId | `ObjectId("64f1a2b3...")` |
| Null | `null` |
| Decimal128 | `NumberDecimal("19.99")` |

## ObjectId Structure

```
4 bytes timestamp | 5 bytes random | 3 bytes counter
```

## JSON vs BSON, One Line Each

```
JSON = text format you type/read
BSON = binary format MongoDB actually stores/transmits
```
