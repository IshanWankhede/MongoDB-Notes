# 📖 Chapter 9 — Schema Validation

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Chapter 3 taught you that MongoDB is "schema-flexible" — any document can have any shape. Chapter 8 taught you how to *design* that shape deliberately. This chapter teaches you how to **enforce** it at the database level, so "flexible" doesn't quietly turn into "chaotic."

MongoDB gives you native, database-level schema validation using **JSON Schema** — a way to declare rules like "this field is required," "this field must be a number," or "this field must match one of these values," directly on the collection itself, independent of whatever application code (Mongoose or otherwise) happens to be writing to it.

---

# Theory

## 9.1 Why Validation?

Without validation, MongoDB will happily accept **any** document into a collection — a typo like `"age": "twenty-one"` (string instead of number) or a missing `email` field won't raise any error. In a small hobby project this rarely matters. In a real production system with multiple services, multiple developers, and data that other teams depend on, this flexibility becomes a liability.

> **Analogy:** A flexible schema without validation is like a form-drop-box with no form template — people can hand in anything: a napkin, a full essay, a blank sheet. Validation is like handing everyone a printed form with labeled boxes and a rule "you must fill in your name and email before we accept this" — you keep the *convenience* of paper forms (documents), but you stop garbage from getting filed away and causing problems months later.

Validation exists to catch bad data **at the point of insertion**, at the database level — a safety net that works even if a rogue script, a buggy migration, or a teammate skips your application's normal validation layer (like Mongoose) entirely.

---

## 9.2 JSON Schema

MongoDB uses the **`$jsonSchema`** operator (a subset of the JSON Schema standard) to describe validation rules for a collection.

```js
db.createCollection("students", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "age"],
      properties: {
        name: { bsonType: "string", description: "must be a string and is required" },
        age: { bsonType: "int", minimum: 0, description: "must be a positive integer and is required" }
      }
    }
  }
})
```

> **Analogy:** `$jsonSchema` is like a blueprint attached to a filing cabinet drawer itself — no matter who tries to file a document into it (your app, a teammate's script, an admin tool), the cabinet checks the blueprint before accepting the file.

### Adding validation to an *existing* collection
```js
db.runCommand({
  collMod: "students",
  validator: {
    $jsonSchema: { /* rules */ }
  }
})
```

---

## 9.3 Required Fields

The `required` array lists field names that **must** be present in every document.

```js
$jsonSchema: {
  required: ["name", "email", "age"]
}
```

If an insert/update is missing any of these fields, MongoDB rejects it (subject to the validation action — see 9.6).

```js
// ❌ REJECTED — missing "email"
db.students.insertOne({ name: "Rohan", age: 21 })

// ✅ ACCEPTED
db.students.insertOne({ name: "Rohan", age: 21, email: "rohan@mail.com" })
```

⚠️ `required` only checks that the **key exists** — it doesn't check that the value is non-empty. `{ email: "" }` still satisfies `required: ["email"]`. Combine with type/pattern rules (below) if you need stricter guarantees.

---

## 9.4 Data Types

Every field's rules can specify a `bsonType` (or `type`, for standard JSON Schema types) — constraining what kind of value is acceptable, plus additional constraints per type.

```js
properties: {
  name: { bsonType: "string" },
  age: { bsonType: "int", minimum: 0, maximum: 120 },
  price: { bsonType: "decimal" },
  isActive: { bsonType: "bool" },
  joinedOn: { bsonType: "date" },
  courses: { bsonType: "array", items: { bsonType: "string" } },
  address: { bsonType: "object" },
  email: { bsonType: "string", pattern: "^.+@.+\\..+$" },     // regex pattern validation
  role: { enum: ["student", "admin", "instructor"] }          // must be one of these exact values
}
```

| Constraint | Purpose |
|---|---|
| `bsonType` | Restrict to a specific BSON type (`"string"`, `"int"`, `"double"`, `"bool"`, `"date"`, `"array"`, `"object"`, `"objectId"`, etc.) |
| `minimum` / `maximum` | Numeric range constraints |
| `minLength` / `maxLength` | String length constraints |
| `pattern` | Regex the string value must match |
| `enum` | Value must be one of a fixed list |
| `items` | Rules applied to each element of an array |

---

## 9.5 Validation Levels

The `validationLevel` setting controls **which writes** get checked against the schema.

| Level | Behavior |
|---|---|
| `"strict"` (default) | ALL inserts and updates are validated — including updates to documents that were already invalid before validation was added |
| `"moderate"` | Only validates inserts and updates to documents that **already satisfy** the schema — pre-existing invalid documents can still be updated (partially) without being forced to fully comply immediately |

```js
db.createCollection("students", {
  validator: { $jsonSchema: { /* ... */ } },
  validationLevel: "moderate"
})
```

> **Analogy:** `"strict"` is like a strict new office policy that applies to absolutely everyone, immediately — including people who joined before the policy existed and don't yet have all the right paperwork. `"moderate"` is a gentler rollout: people who are already "compliant" must stay compliant, but people who were already "grandfathered in" with old, incomplete paperwork are allowed to keep operating (and even make small updates) without being forced to suddenly fix everything at once.

`"moderate"` is especially useful when you're **adding validation to a collection that already has messy legacy data** — it prevents new bad data without breaking every existing update to old, imperfect documents.

---

## 9.6 Validation Actions

The `validationAction` setting controls **what happens** when a write fails validation.

| Action | Behavior |
|---|---|
| `"error"` (default) | The write is **rejected** outright — the client gets an error, nothing is saved |
| `"warn"` | The write is **allowed anyway**, but MongoDB logs a warning in the server log |

```js
db.createCollection("students", {
  validator: { $jsonSchema: { /* ... */ } },
  validationAction: "warn"
})
```

> **Analogy:** `"error"` is a security guard who physically refuses to let an incorrectly filled-out form through the door. `"warn"` is a security guard who lets the form through anyway, but writes a note in the logbook — useful when you're *testing* new validation rules on a live collection and want to see how much data would be rejected, without actually breaking anything yet.

**Common real-world workflow:** roll out new validation rules with `validationAction: "warn"` first, monitor the server logs to see how many existing writes *would* have failed, fix the offending data/application code, then switch to `validationAction: "error"` once you're confident.

---

## 9.7 Real Examples

### User Validation

```js
db.createCollection("users", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["username", "email", "password"],
      properties: {
        username: { bsonType: "string", minLength: 3, maxLength: 30 },
        email: { bsonType: "string", pattern: "^.+@.+\\..+$" },
        password: { bsonType: "string", minLength: 8 },
        role: { enum: ["user", "admin"], description: "must be 'user' or 'admin' if provided" },
        createdAt: { bsonType: "date" }
      }
    }
  },
  validationAction: "error"
})
```

### Product Validation

```js
db.createCollection("products", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "price", "category"],
      properties: {
        name: { bsonType: "string", minLength: 1 },
        price: { bsonType: ["int", "double", "decimal"], minimum: 0 },
        stock: { bsonType: "int", minimum: 0 },
        category: { enum: ["Electronics", "Accessories", "Stationery", "Fitness", "Home & Kitchen"] },
        isAvailable: { bsonType: "bool" }
      }
    }
  },
  validationLevel: "strict",
  validationAction: "error"
})
```

### Student Validation

```js
db.createCollection("students", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "age", "email"],
      properties: {
        name: { bsonType: "string", minLength: 2 },
        age: { bsonType: "int", minimum: 15, maximum: 100 },
        email: { bsonType: "string", pattern: "^.+@.+\\..+$" },
        courses: { bsonType: "array", items: { bsonType: "string" } },
        gpa: { bsonType: "decimal", minimum: 0, maximum: 10 }
      }
    }
  },
  validationLevel: "moderate",   // useful while migrating existing messy student data
  validationAction: "warn"        // start soft, tighten to "error" once confident
})
```

---

# Why This Exists

MongoDB's flexible schema is a genuine strength — but "flexible" and "unvalidated" are not the same thing, and conflating them is one of the most common real-world MongoDB mistakes. Application-level validation (like Mongoose schemas, covered throughout this handbook) is valuable, but it only protects data written **through that specific application code path**. A direct script, a data migration, an admin tool, or a different microservice writing to the same collection can all bypass it entirely.

`$jsonSchema` validation exists to provide a **database-level safety net** that applies no matter *what* is writing to the collection — the same guarantee SQL's `NOT NULL`, `CHECK`, and column type constraints have always provided, but expressed in MongoDB's native document-shaped language, and with the same flexibility to evolve incrementally (`required`, types, ranges, patterns, enums) rather than being locked into a single rigid table definition from day one.

**Validation levels and actions exist specifically to make adopting this safety net practical on a live, already-imperfect production database** — without them, you'd have to either accept zero validation forever, or do a risky "big bang" migration that instantly enforces strict rules on data that was never designed to satisfy them.

---

# Internal Working

## When validation is actually checked

```
 Client sends insertOne() / updateOne() / etc.
        │
        ▼
 MongoDB checks validationLevel:
   "strict"    → always validate
   "moderate"  → validate only if document ALREADY satisfied the schema
        │
        ▼
 Document is checked against $jsonSchema rules
        │
   ┌────┴────┐
  PASS       FAIL
   │           │
   ▼           ▼
 Write      Check validationAction:
 proceeds     "error" → write REJECTED, client gets an error
              "warn"  → write PROCEEDS anyway, server LOGS a warning
```

## Performance note
Schema validation adds a small amount of CPU overhead per write (checking each field against its rule), but this cost is generally **negligible** compared to the disk I/O of the write itself — it's rarely a meaningful bottleneck, and the data-integrity benefit is almost always worth it for production collections.

## Validation vs. Indexes — an important distinction
`$jsonSchema` validation does **not** create an index and does **not** speed up queries — it purely governs what shape of document is *allowed to be written*. Don't confuse it with `unique` indexes (which enforce uniqueness) or with query performance tools from earlier chapters — validation is entirely about **write-time correctness**, not read-time performance.

---

# Syntax

```js
// New collection with validation
db.createCollection("collectionName", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["field1", "field2"],
      properties: {
        field1: { bsonType: "string" },
        field2: { bsonType: "int", minimum: 0 }
      }
    }
  },
  validationLevel: "strict" | "moderate" | "off",
  validationAction: "error" | "warn"
})

// Add/modify validation on an EXISTING collection
db.runCommand({
  collMod: "collectionName",
  validator: { $jsonSchema: { /* ... */ } },
  validationLevel: "moderate",
  validationAction: "warn"
})

// View a collection's current validation rules
db.getCollectionInfos({ name: "collectionName" })
```

---

# Examples

## Testing validation in the shell

```js
use college

db.createCollection("students", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "age"],
      properties: {
        name: { bsonType: "string" },
        age: { bsonType: "int", minimum: 0 }
      }
    }
  }
})

// ❌ Fails — "age" is a string, not an int
db.students.insertOne({ name: "Rohan", age: "21" })

// ✅ Passes
db.students.insertOne({ name: "Rohan", age: 21 })
```

## Rolling out validation on an existing, messy collection safely

```js
// Step 1 — add validation in "warn" mode to see the blast radius
db.runCommand({
  collMod: "students",
  validator: { $jsonSchema: { required: ["email"], properties: { email: { bsonType: "string" } } } },
  validationAction: "warn"
})

// Step 2 — monitor server logs for warnings, fix offending documents/app code

// Step 3 — tighten to enforce once confident
db.runCommand({
  collMod: "students",
  validationAction: "error"
})
```

---

# Visualization

## Validation decision flow

```
                     Write comes in
                          │
                          ▼
              ┌────────────────────────┐
              │ validationLevel check   │
              │  strict / moderate      │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │  $jsonSchema check      │
              │  (required, types, etc)│
              └───────────┬────────────┘
                     PASS │ FAIL
              ┌───────────┴────────────┐
              ▼                        ▼
           Write saved        validationAction check
                                ┌─────┴─────┐
                                ▼           ▼
                             "error"      "warn"
                            REJECTED     ALLOWED
                                          + logged
```

## strict vs moderate

```
 Collection has some OLD documents that DON'T match new rules.

 STRICT:    even updates to those OLD documents are now validated
            (could suddenly start REJECTING routine updates to legacy data!)

 MODERATE:  OLD non-conforming documents are left alone;
            only NEW inserts + updates to already-conforming
            documents are validated
```

---

# Backend Examples

> All backend examples use **Mongoose**. Note: Mongoose's own schema (`new mongoose.Schema({...})`) already performs **application-level validation** before a write is even attempted — this section shows how the two layers (Mongoose validation + MongoDB's native `$jsonSchema`) complement each other as a defense-in-depth strategy.

## Mongoose schema validation (application layer)

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/college");

const studentSchema = new mongoose.Schema({
  name: { type: String, required: true, minlength: 2 },
  age: { type: Number, required: true, min: 15, max: 100 },
  email: {
    type: String,
    required: true,
    match: /^.+@.+\..+$/
  },
  courses: [String],
  gpa: { type: Number, min: 0, max: 10 }
});

const Student = mongoose.model("Student", studentSchema);
```

## Handling Mongoose validation errors gracefully in Express

```js
app.post("/students", async (req, res) => {
  try {
    const student = await Student.create(req.body);
    res.status(201).json(student);
  } catch (err) {
    if (err.name === "ValidationError") {
      const messages = Object.values(err.errors).map(e => e.message);
      return res.status(400).json({ error: "Validation failed", details: messages });
    }
    res.status(500).json({ error: "Server error" });
  }
});
```

## Applying native MongoDB `$jsonSchema` validation alongside Mongoose (defense-in-depth)

Mongoose validation only protects writes made **through your Node.js app**. Adding native `$jsonSchema` validation on the underlying collection protects against any *other* path writing to it too (a script, a migration, a different service).

```js
// Run once, e.g. in a setup/migration script — NOT typical day-to-day app code
async function applyNativeValidation() {
  await mongoose.connection.db.command({
    collMod: "students",
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["name", "age", "email"],
        properties: {
          name: { bsonType: "string", minLength: 2 },
          age: { bsonType: "int", minimum: 15, maximum: 100 },
          email: { bsonType: "string", pattern: "^.+@.+\\..+$" }
        }
      }
    },
    validationLevel: "moderate",
    validationAction: "warn"   // start soft, tighten later
  });
}
```

## Product validation example (Mongoose + `enum`)

```js
const productSchema = new mongoose.Schema({
  name: { type: String, required: true },
  price: { type: Number, required: true, min: 0 },
  category: {
    type: String,
    required: true,
    enum: ["Electronics", "Accessories", "Stationery", "Fitness", "Home & Kitchen"]
  },
  stock: { type: Number, min: 0, default: 0 }
});

const Product = mongoose.model("Product", productSchema);
```

## User validation example (Mongoose + custom validator)

```js
const userSchema = new mongoose.Schema({
  username: { type: String, required: true, minlength: 3, maxlength: 30 },
  email: { type: String, required: true, unique: true, match: /^.+@.+\..+$/ },
  password: { type: String, required: true, minlength: 8 },
  role: { type: String, enum: ["user", "admin"], default: "user" }
});

const User = mongoose.model("User", userSchema);
```

---

# Interview Questions

**Q1. Why does MongoDB need schema validation if it's already a "flexible schema" database?**
Flexibility at the storage level doesn't mean data quality doesn't matter — real applications still need guarantees like "every user has an email" or "price is never negative." Validation lets you keep the flexibility to evolve your schema over time while still enforcing baseline correctness rules, and crucially, it protects against writes from *any* source, not just your main application code.

**Q2. What is `$jsonSchema`, and where is it used?**
It's the operator MongoDB uses to define validation rules for a collection, based on (a subset of) the JSON Schema standard — specified in the `validator` option when creating or modifying a collection.

**Q3. What's the difference between `required` and specifying a `bsonType` for a field?**
`required` only checks that the **field key exists** in the document — it says nothing about the value's type or content. `bsonType` (and other constraints like `minimum`, `pattern`) validate the **value itself**, once present. You typically use both together.

**Q4. Explain the difference between `validationLevel: "strict"` and `"moderate"`.**
`"strict"` validates every insert and update, including updates to documents that were already non-conforming before the rule was added. `"moderate"` only validates new inserts and updates to documents that already satisfy the schema, leaving pre-existing non-conforming documents free to be updated without being forced into full compliance immediately.

**Q5. Explain the difference between `validationAction: "error"` and `"warn"`.**
`"error"` rejects any write that fails validation outright. `"warn"` allows the write to proceed anyway, but logs a warning on the server — useful for safely testing new validation rules against real traffic before enforcing them.

**Q6. Why would a team choose to roll out validation with `"warn"` before switching to `"error"`?**
To measure the real-world impact of new rules on live data/traffic without risking breaking legitimate application writes — they can review the logged warnings, fix any offending data or application bugs, and only switch to strict enforcement once confident nothing important will be rejected.

**Q7. Does `$jsonSchema` validation improve query performance or create an index?**
No — it only governs what data is allowed to be written. It has no effect on read/query performance and does not create any index; that's a completely separate concern (see Chapter on Indexes).

**Q8. How does Mongoose's schema validation relate to MongoDB's native `$jsonSchema` validation?**
Mongoose validation happens in your Node.js application, before a write is even sent to MongoDB — fast feedback, but only applies to writes made through that specific application code. `$jsonSchema` validation happens at the database level and applies to *any* write to that collection, regardless of source — the two are complementary, not redundant; using both is a defense-in-depth strategy.

**Q9. What happens if a document already violates a NEW `$jsonSchema` rule at the moment the rule is added, under `"strict"` validation?**
The existing invalid document remains in the collection as-is (validation doesn't retroactively delete or fix existing data), but under `"strict"`, any *future* attempt to update that specific document will now also be checked against the new rule — potentially rejecting routine updates to that legacy document until it's brought into compliance.

**Q10. Give an example of a validation rule that `required` alone cannot express, but `bsonType`/`pattern`/`enum` can.**
`required` can't ensure `role` is one of a fixed set of values (`enum: ["user", "admin"]`), nor that `email` looks like a valid email address (`pattern`), nor that `age` is actually numeric rather than a string (`bsonType`) — these all need the additional type/constraint keywords beyond simple presence checking.

---

# Practice Questions

## 🟢 Easy
1. Write a `$jsonSchema` validator requiring a `products` collection to have `name` (string) and `price` (number, minimum 0).
2. What validation action should you use if you want invalid writes to be silently logged but still allowed through?
3. What's the difference between `validationLevel` and `validationAction`?
4. Write a `required` array for a `users` collection requiring `username`, `email`, and `password`.

## 🟡 Medium
5. Write a `$jsonSchema` validator for an `orders` collection requiring `status` to be one of `"pending"`, `"shipped"`, `"delivered"`, or `"cancelled"`, using `enum`.
6. Explain, with an example, why `required: ["email"]` alone is not sufficient to guarantee a document has a *valid* email address.
7. Write a Mongoose schema for a `Book` model with `title` (required string), `isbn` (required, unique), and `price` (number, minimum 0).
8. A collection has existing documents where `age` is sometimes stored as a string. Which `validationLevel` would you choose while migrating this data, and why?

## 🔴 Hard
9. Design a full `$jsonSchema` validator for a `payments` collection: `amount` (positive decimal, required), `method` (enum of `"UPI"`, `"Card"`, `"NetBanking"`, required), `studentId` (objectId, required), `paidOn` (date, required). Include the `collMod` command to apply it to an existing collection.
10. Explain step-by-step what happens when a write fails validation under `validationLevel: "strict"` and `validationAction: "error"` — what does the client receive, and does anything get partially saved?
11. A team has a `users` collection with 2 million existing documents, some missing the newly-required `email` field. Design a safe, staged rollout plan (using validation levels and actions) to eventually enforce `email` as required without breaking production.
12. Compare and contrast `$jsonSchema` validation with Mongoose's built-in schema validation in terms of: (a) where the check happens, (b) what writes it protects against, (c) performance characteristics, and (d) how they should be used together in a real production system.

---

# Mini Project

## 🛡️ Mini Project: "Validated Registration API" (Mongoose + Native Validation)

Build a small registration system demonstrating both layers of validation working together.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/appDB");

// LAYER 1 — Mongoose (application-level) validation
const userSchema = new mongoose.Schema({
  username: { type: String, required: true, minlength: 3, maxlength: 30 },
  email: { type: String, required: true, unique: true, match: /^.+@.+\..+$/ },
  password: { type: String, required: true, minlength: 8 },
  role: { type: String, enum: ["user", "admin"], default: "user" }
});

const User = mongoose.model("User", userSchema);

const app = express();
app.use(express.json());

// LAYER 2 — Native MongoDB $jsonSchema validation, applied once at startup
async function setupValidation() {
  const collections = await mongoose.connection.db.listCollections({ name: "users" }).toArray();

  const validatorConfig = {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["username", "email", "password"],
        properties: {
          username: { bsonType: "string", minLength: 3, maxLength: 30 },
          email: { bsonType: "string", pattern: "^.+@.+\\..+$" },
          password: { bsonType: "string", minLength: 8 },
          role: { enum: ["user", "admin"] }
        }
      }
    },
    validationLevel: "moderate",
    validationAction: "warn"   // start soft — flip to "error" once confident
  };

  if (collections.length > 0) {
    await mongoose.connection.db.command({ collMod: "users", ...validatorConfig });
  } else {
    await mongoose.connection.db.createCollection("users", validatorConfig);
  }
}

mongoose.connection.once("open", setupValidation);

// Registration endpoint — protected by BOTH layers
app.post("/register", async (req, res) => {
  try {
    const user = await User.create(req.body);
    res.status(201).json({ id: user._id, username: user.username, email: user.email });
  } catch (err) {
    if (err.name === "ValidationError") {
      return res.status(400).json({ error: "Validation failed", details: err.message });
    }
    if (err.code === 11000) {
      return res.status(409).json({ error: "Email already registered" });
    }
    res.status(500).json({ error: "Server error" });
  }
});

app.listen(3000, () => console.log("Validated Registration API running on port 3000"));
```

### 🎯 Stretch Goals
- Add a `/admin/validation-report` endpoint that queries the MongoDB logs (or simulates it) to summarize how many documents would fail under `"error"` mode before actually switching.
- Try bypassing Mongoose entirely (e.g., using `mongoose.connection.db.collection("users").insertOne(...)` directly) with invalid data, and confirm the native `$jsonSchema` validator still catches it — proving the defense-in-depth benefit.
- Extend the schema with `pattern`-based password strength rules (e.g., requiring at least one number) at both the Mongoose and native validation layers.

---

# Common Mistakes

1. **Relying only on Mongoose validation and assuming the database itself is protected.** Any write that bypasses Mongoose (scripts, migrations, other services, direct shell access) skips it entirely — only native `$jsonSchema` validation protects at the database level.
2. **Adding strict validation directly to a collection with lots of existing non-conforming data**, immediately breaking routine updates to legacy documents. Use `"moderate"` and/or `"warn"` first.
3. **Assuming `required` guarantees a meaningful, non-empty value.** It only checks the key exists — `""`, `null`, or a wrong type can still pass `required` alone without additional type/pattern constraints.
4. **Forgetting that validation doesn't retroactively fix or reject existing bad data** — it only governs future writes going forward, from the moment the rule is applied.
5. **Confusing validation with indexing** — assuming adding a `$jsonSchema` rule will also make queries on that field faster. It won't; indexing is a completely separate, unrelated feature.
6. **Jumping straight to `validationAction: "error"` on a live production collection** without first testing with `"warn"` to gauge the real-world impact.
8. **Writing overly rigid validation rules too early**, before understanding real access patterns — making legitimate, evolving data shapes (a genuine MongoDB strength) painful to work with.

---

# Best Practices

- ✅ Use validation as a **defense-in-depth** layer alongside (not instead of) application-level validation like Mongoose.
- ✅ When adding validation to an existing, imperfect collection, start with `validationLevel: "moderate"` and `validationAction: "warn"`, then tighten gradually once confident.
- ✅ Combine `required`, `bsonType`, and constraints like `pattern`/`enum`/`minimum` together — `required` alone is rarely sufficient.
- ✅ Periodically review server logs for `"warn"`-mode validation failures to catch data quality issues early, even if you never plan to switch to `"error"` for a particular collection.
- ✅ Keep validation rules focused on genuinely important invariants (required fields, correct types, sane ranges) rather than over-constraining every possible field — preserve MongoDB's flexibility where it actually helps you.
- ✅ Document your validation rules alongside your schema design decisions from Chapter 8 — they're two halves of the same "how is this collection structured and guaranteed" story.
- ✅ Re-run/update your `$jsonSchema` validator (via `collMod`) whenever your Mongoose schema changes meaningfully, so the two layers don't drift out of sync.

---

# Cheat Sheet

## Core Syntax

```js
db.createCollection("name", {
  validator: { $jsonSchema: { bsonType: "object", required: [...], properties: {...} } },
  validationLevel: "strict" | "moderate",
  validationAction: "error" | "warn"
})

db.runCommand({ collMod: "name", validator: {...}, validationLevel: "...", validationAction: "..." })
```

## Common `$jsonSchema` Keywords

```js
bsonType     // "string" | "int" | "double" | "decimal" | "bool" | "date" | "array" | "object" | "objectId"
required     // ["field1", "field2"]
minimum / maximum       // numeric range
minLength / maxLength    // string length range
pattern      // regex the string must match
enum         // must be one of these fixed values
items        // rules for each element of an array
```

## Levels & Actions

```
validationLevel:
  strict    → validate ALL writes, including updates to old invalid docs
  moderate  → only validate new inserts + updates to already-valid docs

validationAction:
  error → reject invalid writes
  warn  → allow invalid writes, just log a warning
```

## Rollout Pattern

```
1. Add validator with { validationLevel: "moderate", validationAction: "warn" }
2. Monitor logs / fix bad data & app code
3. Switch to { validationAction: "error" }
4. (Optional, once fully migrated) Switch to { validationLevel: "strict" }
```

## Mongoose vs Native Validation

```
Mongoose validation   → application layer, fast feedback, only protects THIS app's writes
$jsonSchema validation → database layer, protects ALL writes from ANY source
Best practice          → use BOTH together
```
