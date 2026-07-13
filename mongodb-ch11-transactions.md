# 📖 Chapter 11 — Transactions

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Every operation you've learned so far — `insertOne`, `updateOne`, even a single `$group` aggregation — is guaranteed to be atomic **on a single document**. But real business logic often spans **multiple documents, sometimes multiple collections**: transferring money between two accounts, placing an order that must both create an order record *and* decrement stock. What happens if the first write succeeds and the second one fails halfway through?

This chapter covers MongoDB's answer: **multi-document transactions** — a way to group several operations together so they either **all** succeed or **all** fail, exactly like SQL's `BEGIN`/`COMMIT`/`ROLLBACK`, adapted to MongoDB's document model via **sessions**.

---

# Theory

## 11.1 Why Transactions Exist

A single `updateOne()` or `insertOne()` in MongoDB is always atomic — it either fully succeeds or fully fails, never leaving one document half-written. But the moment your business logic needs to change **two or more documents together** (as one indivisible unit), single-document atomicity isn't enough.

> **Analogy:** Imagine handing someone ₹5,000 in cash. The moment it leaves your hand, it must simultaneously be gone from you AND present in their hand — there's no safe "in-between" state where the money has vanished from your pocket but hasn't yet appeared in theirs. A transaction is the database's way of guaranteeing that same all-or-nothing handoff, even when the two "hands" are two completely separate documents (or even separate collections).

Without transactions, a bug, a network failure, or a crash occurring *between* two related writes could leave your database in a genuinely broken, inconsistent state — money debited from one account but never credited to another, an order created but stock never decremented (or vice versa).

---

## 11.2 ACID Properties

Transactions guarantee four properties, together known as **ACID**:

| Letter | Property | Meaning |
|---|---|---|
| **A** | Atomicity | All operations in the transaction succeed together, or none of them are applied at all |
| **C** | Consistency | The database moves from one valid state to another — no constraint or rule is ever left violated |
| **I** | Isolation | Concurrent transactions don't see each other's incomplete, in-progress changes |
| **D** | Durability | Once a transaction is committed, its changes survive even a server crash immediately afterward |

> **Analogy:** Think of ACID like the rules of a fair card game. **Atomicity** — a hand is either fully dealt or not dealt at all, never half-dealt. **Consistency** — the deck always has exactly 52 cards before and after any shuffle; a "valid state" is never broken. **Isolation** — one player can't peek at another player's cards mid-deal before the deal is finished. **Durability** — once a hand is dealt and the game proceeds, that dealt hand doesn't mysteriously change if the lights flicker.

MongoDB has always guaranteed full ACID properties at the **single-document** level. Multi-document transactions (introduced in MongoDB 4.0 for replica sets, and 4.2+ for sharded clusters) extend these same guarantees **across multiple documents and collections**.

---

## 11.3 Sessions

A **session** is the MongoDB concept that groups a series of related operations together, providing the context in which a transaction runs. You can't start a transaction without first starting a session — the session is the "container" the transaction lives inside.

```js
const session = client.startSession();

session.startTransaction();
try {
  // operations go here, all tied to this session
  await collection.updateOne({...}, {...}, { session });
  await collection.insertOne({...}, { session });

  await session.commitTransaction();
} catch (error) {
  await session.abortTransaction();
} finally {
  session.endSession();
}
```

> **Analogy:** A session is like a single, dedicated checkout basket at a store. You can put multiple items into that one basket (operations), and only when you reach the register do you decide: **checkout** (commit — all items are actually purchased together) or **abandon the basket** (abort — nothing in it is purchased at all). Without picking up a basket first (starting a session), you can't group items together this way at all — you'd just be buying each item separately, one at a time.

⚠️ **Every operation inside a transaction must explicitly pass the `{ session }` option** — an operation that forgets to include it runs *outside* the transaction entirely, defeating the whole point.

---

## 11.4 Multi Document Transactions

A **multi-document transaction** wraps several read/write operations — potentially across multiple collections — into a single atomic unit using a session.

```js
const session = client.startSession();

try {
  session.startTransaction();

  await accounts.updateOne(
    { _id: "acc1" },
    { $inc: { balance: -5000 } },
    { session }
  );

  await accounts.updateOne(
    { _id: "acc2" },
    { $inc: { balance: 5000 } },
    { session }
  );

  await session.commitTransaction();
  console.log("Transfer successful");
} catch (error) {
  await session.abortTransaction();
  console.log("Transfer failed, rolled back:", error);
} finally {
  session.endSession();
}
```

### The transaction lifecycle

```
 startSession()
       │
       ▼
 startTransaction()
       │
       ▼
 [operation 1, operation 2, operation 3 ... all tagged with { session }]
       │
   ┌───┴───┐
  ALL OK   ANY FAILS
   │           │
   ▼           ▼
commitTransaction()   abortTransaction()
   │                       │
   └──────────┬────────────┘
              ▼
        endSession()
```

If **anything** goes wrong before `commitTransaction()` is called — a validation error, a network blip, a thrown exception — calling `abortTransaction()` undoes **every** operation performed inside that transaction so far, as if none of them ever happened.

---

## 11.5 Banking Example

The classic transaction example: transferring money between two bank accounts must be atomic — the debit and the credit must both happen, or neither should.

```js
async function transferMoney(client, fromAccountId, toAccountId, amount) {
  const session = client.startSession();
  const accounts = client.db("bank").collection("accounts");

  try {
    session.startTransaction();

    const sender = await accounts.findOne({ _id: fromAccountId }, { session });
    if (!sender || sender.balance < amount) {
      throw new Error("Insufficient funds");
    }

    await accounts.updateOne(
      { _id: fromAccountId },
      { $inc: { balance: -amount } },
      { session }
    );

    await accounts.updateOne(
      { _id: toAccountId },
      { $inc: { balance: amount } },
      { session }
    );

    await session.commitTransaction();
    return { success: true };
  } catch (error) {
    await session.abortTransaction();
    return { success: false, error: error.message };
  } finally {
    session.endSession();
  }
}
```

**Why this matters:** if the debit succeeds but a crash/network error happens *before* the credit runs, without a transaction, ₹5,000 would simply **vanish** from the system — debited from account 1, never credited to account 2. The transaction guarantees this can never happen: either both updates land, or neither does.

---

## 11.6 E-commerce Example

Placing an order must **simultaneously** create the order record AND decrement product stock — if only one of these happens, you either oversell inventory or charge a customer for an order that was never actually recorded.

```js
async function placeOrder(client, productId, quantity, customerName) {
  const session = client.startSession();
  const products = client.db("shop").collection("products");
  const orders = client.db("shop").collection("orders");

  try {
    session.startTransaction();

    const product = await products.findOne({ _id: productId }, { session });
    if (!product || product.stock < quantity) {
      throw new Error("Not enough stock");
    }

    await products.updateOne(
      { _id: productId },
      { $inc: { stock: -quantity } },
      { session }
    );

    const orderResult = await orders.insertOne(
      {
        productId,
        quantity,
        customerName,
        orderDate: new Date(),
        status: "confirmed"
      },
      { session }
    );

    await session.commitTransaction();
    return { success: true, orderId: orderResult.insertedId };
  } catch (error) {
    await session.abortTransaction();
    return { success: false, error: error.message };
  } finally {
    session.endSession();
  }
}
```

**Why this matters:** without a transaction, a crash between the stock decrement and the order insert could leave stock reduced with **no order to show for it** (inventory silently vanishes) — or, if ordered the other way, an order created for a product that's actually already out of stock (overselling).

---

## 11.7 Node.js Transaction Example

A complete, reusable transaction wrapper — the pattern you'll actually use in a real backend, since manually repeating try/catch/finally for every transaction gets tedious and error-prone.

```js
const { MongoClient } = require("mongodb");

async function runTransaction(client, operations) {
  const session = client.startSession();
  try {
    let result;
    await session.withTransaction(async () => {
      result = await operations(session);
    });
    return result;
  } finally {
    session.endSession();
  }
}
```

`session.withTransaction()` is a **convenience wrapper** provided by the MongoDB driver that automatically handles `startTransaction()`, `commitTransaction()`, `abortTransaction()` on error, and even **automatic retries** for certain transient transaction errors (like brief network hiccups) — it's the officially recommended way to run transactions rather than manually managing the lifecycle yourself.

```js
// Usage
const client = new MongoClient("mongodb://localhost:27017");
await client.connect();

const result = await runTransaction(client, async (session) => {
  const accounts = client.db("bank").collection("accounts");

  await accounts.updateOne({ _id: "acc1" }, { $inc: { balance: -5000 } }, { session });
  await accounts.updateOne({ _id: "acc2" }, { $inc: { balance: 5000 } }, { session });

  return { transferred: 5000 };
});

console.log(result);
```

---

# Why This Exists

MongoDB's document model already solves *most* atomicity needs by letting you embed related data into a single document (Chapter 8) — a single-document write is always atomic, so a huge portion of "I need this to happen all-or-nothing" needs are already covered without transactions at all. But some operations are **fundamentally cross-document or cross-collection by nature** — a bank transfer inherently touches two separate account documents; an order inherently touches both a `products` document (stock) and a new `orders` document. No amount of clever embedding can turn these into a single-document write, because the two pieces of data have entirely separate identities and lifecycles.

Multi-document transactions exist to close this gap — extending the same all-or-nothing guarantee that MongoDB has always had at the single-document level, out to arbitrary groups of operations across documents and collections, matching the guarantee developers have relied on in SQL databases for decades (`BEGIN`/`COMMIT`/`ROLLBACK`).

---

# Internal Working

## What happens during a transaction, under the hood

```
 client.startSession()
        │
        ▼
 session.startTransaction()
        │             MongoDB begins tracking a "snapshot" of the data
        │             as it existed at transaction start (for isolation)
        ▼
 [operations execute against the session]
        │             Changes are held in a PENDING state — NOT yet
        │             visible to other clients/sessions
        ▼
 session.commitTransaction()
        │             All pending changes are atomically applied
        │             and become visible to everyone at once
        ▼
    Durable on disk (via the replica set's write-concern-guaranteed
    replication, exactly like any other MongoDB write)
```

## Isolation in practice
MongoDB transactions use **snapshot isolation**: for the duration of the transaction, reads see a consistent snapshot of the data as it was when the transaction began, and writes made inside the transaction are invisible to any other session until `commitTransaction()` succeeds. If two transactions try to modify the **same document** concurrently, one of them will encounter a write conflict and typically needs to be retried (which is exactly why `withTransaction()`'s built-in retry logic is so valuable).

## Why transactions require a replica set (even for a single server in development)
MongoDB's multi-document transaction implementation is built on top of the same underlying replication/oplog machinery used for replica sets — even a single-node "replica set" (common in local development) is required for transactions to work at all; a plain standalone `mongod` with no replica set configuration cannot run multi-document transactions.

## Performance cost
Transactions are not free — they hold locks/snapshots for their duration, and long-running transactions can increase contention and memory usage (MongoDB has a default transaction time limit, typically 60 seconds, after which it's automatically aborted). This is why transactions should be kept **short and focused** — do the minimum necessary work inside a transaction, and avoid slow operations (like external API calls) between its start and commit.

---

# Syntax

```js
// Native driver — manual lifecycle
const session = client.startSession();
try {
  session.startTransaction();
  // ...operations with { session }
  await session.commitTransaction();
} catch (e) {
  await session.abortTransaction();
} finally {
  session.endSession();
}

// Native driver — recommended convenience wrapper (auto retry + commit/abort)
await session.withTransaction(async () => {
  // ...operations with { session }
});

// Mongoose — session usage
const session = await mongoose.startSession();
session.startTransaction();
try {
  await Model.updateOne({...}, {...}, { session });
  await session.commitTransaction();
} catch (e) {
  await session.abortTransaction();
} finally {
  session.endSession();
}
```

---

# Examples

## A failing transaction that correctly rolls back

```js
const session = client.startSession();
const accounts = client.db("bank").collection("accounts");

try {
  session.startTransaction();

  await accounts.updateOne({ _id: "acc1" }, { $inc: { balance: -100000 } }, { session });
  // Suppose a validator rejects this because balance would go negative — throws an error

  await accounts.updateOne({ _id: "acc2" }, { $inc: { balance: 100000 } }, { session });

  await session.commitTransaction();
} catch (error) {
  await session.abortTransaction();
  // acc1's balance is UNCHANGED — the first update is rolled back too,
  // even though it "succeeded" before the error occurred
  console.log("Transaction rolled back:", error.message);
} finally {
  session.endSession();
}
```

## Read-your-own-writes within a transaction

```js
await session.withTransaction(async () => {
  await orders.insertOne({ _id: "o1", status: "pending" }, { session });

  // This find WILL see the just-inserted document, because it's in the SAME session
  const order = await orders.findOne({ _id: "o1" }, { session });
  console.log(order.status); // "pending" — visible within the same transaction
});
```

---

# Visualization

## All-or-nothing guarantee

```
 WITHOUT a transaction:                 WITH a transaction:

  debit acc1  ──✓ done                   debit acc1   ┐
       │                                 credit acc2  ├─ held as PENDING
  [CRASH HAPPENS HERE]                        │        │  until commit
       │                                  commitTransaction()
  credit acc2  ──✗ NEVER RUNS                  │
                                          ┌─────┴─────┐
  Result: ₹5,000 VANISHED                ALL applied   or   NONE applied
  (inconsistent state!)                  (atomic, no in-between state possible)
```

## Transaction lifecycle, end to end

```
 startSession() → startTransaction() → [op1] → [op2] → [op3]
                                                            │
                                              ┌─────────────┴─────────────┐
                                          all succeed                any fails
                                              │                            │
                                       commitTransaction()        abortTransaction()
                                              │                            │
                                              └────────────┬───────────────┘
                                                       endSession()
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Mongoose models (shared)

```js
const mongoose = require("mongoose");
mongoose.connect("mongodb://localhost:27017/shop");

const accountSchema = new mongoose.Schema({
  owner: String,
  balance: { type: Number, min: 0 }
});

const productSchema = new mongoose.Schema({
  name: String,
  stock: { type: Number, min: 0 },
  price: Number
});

const orderSchema = new mongoose.Schema({
  productId: mongoose.Schema.Types.ObjectId,
  quantity: Number,
  customerName: String,
  status: String,
  orderDate: { type: Date, default: Date.now }
});

const Account = mongoose.model("Account", accountSchema);
const Product = mongoose.model("Product", productSchema);
const Order = mongoose.model("Order", orderSchema);
```

## Banking transfer endpoint (Mongoose + session)

```js
app.post("/transfer", async (req, res) => {
  const { fromAccountId, toAccountId, amount } = req.body;
  const session = await mongoose.startSession();

  try {
    session.startTransaction();

    const sender = await Account.findById(fromAccountId).session(session);
    if (!sender || sender.balance < amount) {
      throw new Error("Insufficient funds");
    }

    await Account.updateOne(
      { _id: fromAccountId },
      { $inc: { balance: -amount } },
      { session }
    );

    await Account.updateOne(
      { _id: toAccountId },
      { $inc: { balance: amount } },
      { session }
    );

    await session.commitTransaction();
    res.json({ success: true });
  } catch (error) {
    await session.abortTransaction();
    res.status(400).json({ success: false, error: error.message });
  } finally {
    session.endSession();
  }
});
```

## E-commerce order placement endpoint (Mongoose + session)

```js
app.post("/orders", async (req, res) => {
  const { productId, quantity, customerName } = req.body;
  const session = await mongoose.startSession();

  try {
    session.startTransaction();

    const product = await Product.findById(productId).session(session);
    if (!product || product.stock < quantity) {
      throw new Error("Not enough stock");
    }

    await Product.updateOne(
      { _id: productId },
      { $inc: { stock: -quantity } },
      { session }
    );

    const [order] = await Order.create(
      [{ productId, quantity, customerName, status: "confirmed" }],
      { session }
    );
    // Note: Model.create() with a session requires passing an ARRAY of docs

    await session.commitTransaction();
    res.status(201).json({ success: true, orderId: order._id });
  } catch (error) {
    await session.abortTransaction();
    res.status(400).json({ success: false, error: error.message });
  } finally {
    session.endSession();
  }
});
```

## Reusable transaction helper using Mongoose (recommended pattern)

```js
async function withTransaction(fn) {
  const session = await mongoose.startSession();
  try {
    let result;
    await session.withTransaction(async () => {
      result = await fn(session);
    });
    return result;
  } finally {
    session.endSession();
  }
}

// Usage — much cleaner in route handlers
app.post("/orders", async (req, res) => {
  try {
    const result = await withTransaction(async (session) => {
      const { productId, quantity, customerName } = req.body;

      const product = await Product.findById(productId).session(session);
      if (!product || product.stock < quantity) throw new Error("Not enough stock");

      await Product.updateOne({ _id: productId }, { $inc: { stock: -quantity } }, { session });
      const [order] = await Order.create([{ productId, quantity, customerName, status: "confirmed" }], { session });

      return order;
    });

    res.status(201).json({ success: true, order: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});
```

---

# Interview Questions

**Q1. Why are multi-document transactions needed if a single document write is already atomic in MongoDB?**
Because many real business operations inherently span multiple, separately-identified documents (or even collections) — like debiting one bank account and crediting another. No amount of embedding can merge two independent accounts into a single document, so single-document atomicity alone can't provide the all-or-nothing guarantee these operations need.

**Q2. Explain each letter of ACID in your own words.**
Atomicity: all-or-nothing — every operation in the transaction happens, or none do. Consistency: the database always moves between valid states, never leaving a broken/partial state visible. Isolation: concurrent transactions don't see each other's uncommitted, in-progress changes. Durability: once committed, changes survive even an immediate crash.

**Q3. What is a session, and why is it required to run a transaction?**
A session is a context that groups a sequence of related operations together — it's the container a transaction runs inside. You can't start a transaction without a session because the session is what MongoDB uses to track which operations belong together as one atomic unit.

**Q4. What happens if you forget to pass `{ session }` to an operation inside a transaction block?**
That operation runs completely **outside** the transaction — it commits immediately and independently, and won't be rolled back if the rest of the transaction later fails, silently breaking the atomicity guarantee you were trying to establish.

**Q5. What does `session.withTransaction()` do that manually calling `startTransaction()`/`commitTransaction()`/`abortTransaction()` doesn't handle automatically?**
It automatically manages the full lifecycle (start, commit on success, abort on error) AND automatically retries the transaction on certain transient errors (like brief network issues or write conflicts) — manual management requires you to write and get all of this retry/cleanup logic correct yourself.

**Q6. In the banking example, what specifically goes wrong if a crash happens between the debit and the credit, without a transaction?**
The debit already committed independently (since it's a separate, un-transacted write), but the credit never runs — money is permanently debited from one account and never appears in the other, effectively vanishing from the system with no way to automatically recover it.

**Q7. Why do MongoDB transactions require a replica set, even in local development?**
Because MongoDB's transaction implementation relies on the same underlying replication/oplog infrastructure used by replica sets to track and coordinate changes — a plain standalone `mongod` instance with no replica set configuration lacks this infrastructure entirely and cannot support multi-document transactions.

**Q8. Why should transactions be kept short, and what happens if one runs too long?**
Long-running transactions hold locks/snapshots and increase the risk of write conflicts with other concurrent operations, and MongoDB enforces a default transaction time limit (commonly 60 seconds) after which an in-progress transaction is automatically aborted — so slow operations (like external API calls) should never be performed inside a transaction's boundaries.

**Q9. What isolation guarantee do MongoDB transactions provide, and what does it mean practically?**
Snapshot isolation — for the duration of the transaction, reads see a consistent snapshot of the data as it was when the transaction began, and other sessions can't see the transaction's writes until it's actually committed. This prevents other parts of the application from seeing a "half-updated" intermediate state.

**Q10. Give a non-financial example (outside banking) where multi-document transactions would be essential.**
Placing an e-commerce order: creating the order record and decrementing the product's stock count are two separate documents that must change together — without a transaction, a crash between the two writes could result in either lost inventory tracking (stock decremented, no order recorded) or overselling (order recorded, stock never actually reduced).

---

# Practice Questions

## 🟢 Easy
1. What does the "A" in ACID stand for, and what does it guarantee?
2. Write the basic skeleton (start, try/catch, commit/abort, end) for a MongoDB transaction using the native driver.
3. Why can't you run a transaction without first starting a session?
4. What method on a session automatically handles commit, abort, and retry for you?

## 🟡 Medium
5. Write a transaction (Mongoose, using `mongoose.startSession()`) that moves a `product` from an `outOfStock` collection to an `inStock` collection atomically.
6. Explain what happens to a transaction's pending writes if `abortTransaction()` is called after two of three planned operations have already run inside it.
7. Write a transaction for a library system: borrowing a book must simultaneously decrement `availableCopies` on the book document AND insert a new `borrowRecord` document.
8. Why must every operation inside a transaction explicitly receive the `{ session }` option — what's the risk of forgetting it on just one operation?

## 🔴 Hard
9. Design a transaction for a ticket-booking system where a `seat` document must be marked `booked` and a `booking` document must be created — but ALSO handle the case where two users try to book the SAME seat at nearly the same time (explain what MongoDB does in that conflict scenario).
10. Explain, step by step, why MongoDB transactions require the underlying deployment to be a replica set (or sharded cluster), even for a single-node local development setup.
11. A developer puts a slow external payment-gateway API call INSIDE a transaction, between debiting the account and creating the order. Explain two specific problems this could cause.
12. Compare single-document atomicity (available without any transaction) against multi-document transactions in terms of: (a) performance cost, (b) what guarantees each one provides, and (c) when a well-modeled schema (Chapter 8) can avoid needing a transaction entirely by embedding related data instead.

---

# Mini Project

## 🏦 Mini Project: "Mini Banking API" (Mongoose + Transactions)

Build a small Express + Mongoose banking API demonstrating real multi-document transactions end to end.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect("mongodb://localhost:27017/bankDB");

const accountSchema = new mongoose.Schema({
  owner: String,
  balance: { type: Number, min: 0, default: 0 }
});

const transactionLogSchema = new mongoose.Schema({
  fromAccountId: mongoose.Schema.Types.ObjectId,
  toAccountId: mongoose.Schema.Types.ObjectId,
  amount: Number,
  status: String,
  createdAt: { type: Date, default: Date.now }
});

const Account = mongoose.model("Account", accountSchema);
const TransactionLog = mongoose.model("TransactionLog", transactionLogSchema);

const app = express();
app.use(express.json());

async function withTransaction(fn) {
  const session = await mongoose.startSession();
  try {
    let result;
    await session.withTransaction(async () => { result = await fn(session); });
    return result;
  } finally {
    session.endSession();
  }
}

// Open a new account
app.post("/accounts", async (req, res) => {
  const account = await Account.create(req.body);
  res.status(201).json(account);
});

// Transfer money — fully transactional, including an audit log entry
app.post("/transfer", async (req, res) => {
  const { fromAccountId, toAccountId, amount } = req.body;

  try {
    const result = await withTransaction(async (session) => {
      const sender = await Account.findById(fromAccountId).session(session);
      if (!sender || sender.balance < amount) throw new Error("Insufficient funds");

      await Account.updateOne({ _id: fromAccountId }, { $inc: { balance: -amount } }, { session });
      await Account.updateOne({ _id: toAccountId }, { $inc: { balance: amount } }, { session });

      const [log] = await TransactionLog.create(
        [{ fromAccountId, toAccountId, amount, status: "completed" }],
        { session }
      );

      return log;
    });

    res.json({ success: true, transaction: result });
  } catch (error) {
    res.status(400).json({ success: false, error: error.message });
  }
});

// Balance check
app.get("/accounts/:id/balance", async (req, res) => {
  const account = await Account.findById(req.params.id);
  res.json({ balance: account.balance });
});

app.listen(3000, () => console.log("Mini Banking API running on port 3000"));
```

### 🎯 Stretch Goals
- Add a Mongoose schema validator (`balance: { min: 0 }`) and confirm that an over-draft attempt correctly triggers an `abortTransaction()` via the thrown validation error.
- Simulate a concurrent double-transfer (two requests hitting `/transfer` for the same account at nearly the same time) and observe MongoDB's write-conflict/retry behavior via `withTransaction()`.
- Extend the e-commerce order example (section 11.6) into a full `/orders` + `/products` API with the same `withTransaction()` helper, and add a `/orders/:id/cancel` endpoint that atomically restores stock and updates order status together.

---

# Common Mistakes

1. **Forgetting to pass `{ session }` to one or more operations inside a transaction** — that operation silently runs outside the transaction and won't be rolled back on failure, breaking atomicity without any obvious error.
2. **Not calling `session.endSession()`** (especially forgetting it in a `finally` block), leaking sessions and eventually exhausting the server's session pool.
3. **Putting slow, non-database work (external API calls, heavy computation) inside a transaction**, increasing the chance of hitting MongoDB's transaction time limit and holding locks longer than necessary.
4. **Reaching for a transaction as a default habit**, even when a well-modeled, embedded document (Chapter 8) could have made the operation naturally atomic without any transaction machinery at all.
5. **Assuming transactions work on a standalone `mongod` with no replica set configured** — a common local-development surprise when transactions fail unexpectedly.
6. **Not handling transient transaction errors with retry logic** when manually managing the transaction lifecycle instead of using `withTransaction()`, which handles this automatically.
7. **Assuming a `catch` block alone is enough** without explicitly calling `abortTransaction()` inside it — an unhandled/uncommitted transaction can be left dangling if you don't explicitly abort it on error.

---

# Best Practices

- ✅ Prefer `session.withTransaction()` over manually managing `startTransaction()`/`commitTransaction()`/`abortTransaction()` — it handles retries and lifecycle correctly by default.
- ✅ Keep transactions **short and focused** — only the essential database operations, no slow external calls or heavy computation inside them.
- ✅ Always pass `{ session }` to *every* operation that should be part of the transaction — double-check this carefully in code review, since it's an easy, silent mistake.
- ✅ Always call `session.endSession()` in a `finally` block to avoid leaking sessions.
- ✅ Reach for embedding (Chapter 8) first, and transactions second — if related data can be naturally embedded into one document, you may not need a transaction at all.
- ✅ Design your application to handle transaction retries/failures gracefully (e.g., returning a clear error to the user) rather than assuming a transaction will always succeed on the first attempt.
- ✅ Test transaction rollback behavior explicitly (deliberately trigger a failure partway through) as part of your test suite — don't just test the happy path.
- ✅ In production, ensure your MongoDB deployment is a replica set or sharded cluster — transactions won't work on an unconfigured standalone instance.

---

# Cheat Sheet

## ACID

```
Atomicity   → all-or-nothing
Consistency → valid state to valid state
Isolation   → concurrent transactions don't see each other's in-progress work
Durability  → committed changes survive a crash
```

## Transaction Lifecycle

```js
const session = await mongoose.startSession();
try {
  await session.withTransaction(async () => {
    await Model.updateOne({...}, {...}, { session });
    await Model.create([{...}], { session });   // note: array form with session
  });
} finally {
  session.endSession();
}
```

## Manual Lifecycle (for reference)

```js
session.startTransaction();
try {
  // ...operations with { session }
  await session.commitTransaction();
} catch (e) {
  await session.abortTransaction();
} finally {
  session.endSession();
}
```

## When You Actually Need a Transaction

```
Does the operation span MULTIPLE documents/collections
that must succeed or fail TOGETHER?
       │
      YES → use a transaction
       │
      NO  → a single-document write is already atomic;
            consider embedding (Chapter 8) instead
```

## Key Requirements

```
✅ Requires a replica set (or sharded cluster) — NOT a standalone mongod
✅ Every operation inside needs { session }
✅ Keep transactions SHORT — default time limit ~60 seconds
✅ Use withTransaction() for automatic retry + lifecycle handling
```
