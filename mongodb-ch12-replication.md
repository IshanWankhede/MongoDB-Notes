# 📖 Chapter 12 — Replication

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Every chapter so far assumed a single, ever-reliable MongoDB server. Real production servers crash, lose power, need maintenance restarts, or sit in a data center that briefly loses network connectivity — and none of that should mean your application goes down or loses data. This chapter covers **replication**: how MongoDB keeps multiple synchronized copies of your data across several servers, automatically survives a server failure, and gives you fine-grained control over exactly how strict your reads and writes should be about consistency versus speed.

This is also where **Read Preference** and **Write Concern** come in — two settings that let you deliberately tune the tradeoff between performance and safety, on a per-operation basis, rather than accepting a single one-size-fits-all default.

---

# Theory

## Replica Sets

A **replica set** is a group of MongoDB servers ("nodes" or "members") that all maintain **copies of the same data**. One node is the **primary** (handles all writes), and the rest are **secondaries** (continuously replicate the primary's changes).

```
        ┌───────────┐
        │  PRIMARY   │  ← all writes go here
        └─────┬─────┘
    replicates│data (via the oplog)
     ┌────────┼────────┐
     ▼                 ▼
┌──────────┐     ┌──────────┐
│ SECONDARY │     │ SECONDARY │
└──────────┘     └──────────┘
```

> **Analogy:** A replica set is like a company keeping identical backup copies of an important physical ledger book in three separate locked safes, in three different buildings. Only one designated safe (the primary) is where new entries are actually written — but every time a new entry is added, couriers immediately carry copies of that entry to the other two safes (secondaries). If the building housing the primary safe burns down, the company can instantly designate one of the other safes as the new "official" one — the business doesn't grind to a halt, because complete, near-up-to-date copies already existed elsewhere.

### Primary
The **one** node in a replica set that accepts all **write** operations. There is always exactly one primary at any given time (when the replica set is healthy).

```js
// This ALWAYS goes to the primary — MongoDB routes it automatically
db.students.insertOne({ name: "Rohan" })
```

### Secondary
Nodes that continuously **replicate** the primary's data changes by tailing its **oplog** (operation log — a special capped collection recording every write). Secondaries can optionally serve **read** operations (see Read Preference), and stand ready to be automatically promoted to primary if the current primary fails.

### Failover
The automatic process of **electing a new primary** when the current primary becomes unavailable (crash, network partition, planned maintenance) — happening without any manual intervention.

```
        ┌───────────┐
        │  PRIMARY   │  ✗ CRASHES
        └───────────┘
              
     ┌────────┼────────┐
     ▼                 ▼
┌──────────┐     ┌──────────┐
│ SECONDARY │     │ SECONDARY │
└─────┬────┘     └──────────┘
      │
      ▼  election happens automatically among remaining nodes
┌──────────┐
│ NEW PRIMARY │  ← one secondary is promoted
└──────────┘
```

> **Analogy:** Failover is like a sports team's designated captain suddenly getting injured mid-match — the team doesn't just stop playing. By pre-agreed rule, the vice-captain immediately steps into the captain role, and play continues with minimal disruption. The team (application) barely skips a beat.

An election typically completes within a few seconds, during which the replica set has **no primary** and cannot accept writes — a brief window worth knowing about, since your application needs to handle this gracefully (usually via automatic driver-level retries).

### High Availability
The overall property that a system continues operating correctly even when individual components fail — replication is MongoDB's core mechanism for achieving this. As long as a **majority** of the replica set's nodes remain reachable, the replica set can elect a primary and keep serving both reads and writes.

```
 3-node replica set: can survive 1 node failing (2 remain = still a majority)
 5-node replica set: can survive 2 nodes failing (3 remain = still a majority)
```

---

## Read Preference

**Read Preference** determines **which node(s)** in a replica set a read operation is allowed to be routed to — giving you a deliberate tradeoff between **absolute freshness** (always read from primary) and **read scalability/availability** (spread reads across secondaries, tolerating slightly stale data).

| Mode | Behavior |
|---|---|
| `primary` (default) | All reads go to the primary — always fully up-to-date |
| `primaryPreferred` | Prefer primary, but fall back to a secondary if primary is unavailable |
| `secondary` | All reads go to secondaries only — never the primary |
| `secondaryPreferred` | Prefer secondaries, but fall back to primary if none are available |
| `nearest` | Read from whichever node has the lowest network latency, regardless of role |

```js
db.students.find().readPref("secondaryPreferred")
```

> **Analogy:** Imagine three identical library branches (primary + 2 secondaries) — the main branch always has the very latest book returns logged instantly, while the other two branches get updated a few moments later via courier. `read: "primary"` means "always go to the main branch, even if it's the busiest." `read: "secondary"` means "go to the quieter branches, and accept that a book returned 2 seconds ago might not show as available quite yet." `nearest` means "just go to whichever branch is physically closest to you right now."

⚠️ **Reading from secondaries introduces "replication lag"** — secondaries are always at least momentarily behind the primary. For data where absolute freshness matters (e.g., checking your own bank balance right after a deposit), `primary` is usually the right choice. For read-heavy, latency-tolerant workloads (e.g., a public analytics dashboard, a product catalog), `secondaryPreferred` or `nearest` can meaningfully improve scalability and reduce load on the primary.

---

## Write Concern

**Write Concern** determines **how many nodes must confirm a write** before MongoDB reports it as successful back to your application — giving you a deliberate tradeoff between **write speed** and **durability guarantees**.

| Write Concern | Meaning |
|---|---|
| `w: 0` | Fire-and-forget — don't even wait for acknowledgment from the primary |
| `w: 1` (default) | Wait for acknowledgment from the primary only |
| `w: "majority"` | Wait until a majority of replica set nodes have acknowledged the write |
| `w: <number>` | Wait for acknowledgment from a specific number of nodes |
| `j: true` | Additionally require the write to be committed to the on-disk journal (survives an immediate crash) |

```js
db.orders.insertOne(
  { customerName: "Rohan", amount: 499 },
  { writeConcern: { w: "majority", j: true } }
)
```

> **Analogy:** Write Concern is like deciding how many people need to confirm they received an important message before you consider it "sent." `w: 0` is shouting into a room without waiting to see if anyone heard you at all. `w: 1` is getting a nod from just the person standing closest to you. `w: "majority"` is waiting until more than half the room has confirmed they heard and understood — much safer, since even if that one closest person later forgets what you said, the majority still remembers.

⚠️ **The tradeoff is real and important:** `w: "majority"` is significantly **safer** (the write is guaranteed to survive even a primary failure immediately afterward, since a majority of nodes already have it) but **slower** (must wait for network round trips to multiple nodes) than `w: 1`. Use `w: "majority"` for critical writes (financial transactions, order confirmations); `w: 1` may be acceptable for high-volume, less-critical writes (e.g., analytics event logging) where losing a rare, recent write is an acceptable risk in exchange for speed.

---

# Why This Exists

A single, unreplicated MongoDB server is a **single point of failure** — if that one machine crashes, loses its disk, or simply needs a routine OS security patch requiring a restart, your entire application goes down and, in the worst case, could lose data that was never safely persisted anywhere else. Replica sets exist to eliminate this single point of failure by keeping multiple synchronized copies of the data across independent servers (ideally in different physical locations/availability zones), so that the failure of any *one* node doesn't take down the whole system.

**Read Preference and Write Concern exist because "safe" and "fast" are fundamentally in tension**, and different parts of a real application legitimately need different points on that spectrum. A public product catalog page can tolerate reading data that's a few hundred milliseconds stale in exchange for spreading load across more servers. A payment confirmation absolutely cannot tolerate silently losing data if the primary crashes a second after acknowledging the write. Rather than forcing one global tradeoff on every operation, MongoDB exposes these as configurable, per-operation settings — letting developers make that call deliberately, operation by operation, exactly where it matters most.

---

# Internal Working

## How replication actually happens — the Oplog

```
 PRIMARY receives a write
        │
        ▼
 Write is applied to the primary's data files
        │
        ▼
 An entry describing this exact change is appended
 to the OPLOG (a special capped collection: local.oplog.rs)
        │
        ▼
 Each SECONDARY continuously "tails" (reads new entries
 from) the primary's oplog, and re-applies each operation
 to its own copy of the data, in the same order
        │
        ▼
 Secondaries are now caught up (with some small delay = "replication lag")
```

The oplog is what makes replication possible at all — it's essentially a running, ordered transcript of "everything that changed and in what order," which any secondary (or a secondary that's fallen behind and reconnects) can replay to catch itself up to the primary's current state.

## How a primary election actually works
When the current primary becomes unreachable, the remaining nodes detect this (via periodic heartbeat pings between all members) and initiate an **election**. Nodes vote based on factors including which node has the most up-to-date oplog data, and (if configured) relative "priority" settings that can bias the election toward preferred nodes (e.g., a more powerful server in the primary data center). The node receiving votes from a **majority** of the replica set becomes the new primary — this majority requirement is exactly why replica sets are typically configured with an **odd** number of nodes (3, 5, 7) — to always have a clear majority possible even if some nodes are unreachable.

## Why `w: "majority"` is durable even across a primary failure
If a write has been acknowledged by a **majority** of nodes, that majority necessarily overlaps with whichever nodes participate in any future election (since elections also require a majority to succeed) — guaranteeing that any newly-elected primary will already have that write in its data. This is the core mathematical guarantee that makes `w: "majority"` genuinely durable, not just "probably fine."

## Read Preference and consistency
When reading from a secondary, you're reading data that reflects the primary's state as of the last oplog entry that secondary has applied — which could be milliseconds (typically) to, in rare degraded scenarios, much longer behind. This is called **eventual consistency** for secondary reads, as opposed to the **strong consistency** guarantee you get from always reading the primary.

---

# Syntax

```js
// Read Preference — Mongo Shell / driver
db.collection.find().readPref("primary" | "primaryPreferred" | "secondary" | "secondaryPreferred" | "nearest")

// Write Concern — per operation
db.collection.insertOne(doc, { writeConcern: { w: "majority", j: true } })
db.collection.updateOne(filter, update, { writeConcern: { w: 1 } })

// Replica set administration (Mongo Shell)
rs.status()             // current state of all members
rs.isMaster()           // (or rs.hello()) — who is currently primary
rs.conf()               // replica set configuration
```

---

# Examples

## Checking replica set status

```js
rs.status()
// shows each member's state: PRIMARY, SECONDARY, health, uptime, etc.
```

## Reading from secondaries for a latency-tolerant report

```js
db.orders.find({ status: "delivered" }).readPref("secondaryPreferred")
// spreads this heavy reporting query's load away from the primary
```

## Requiring strong durability for a critical financial write

```js
db.payments.insertOne(
  { studentId: "s1", amount: 10000, method: "UPI" },
  { writeConcern: { w: "majority", j: true } }
)
// waits until a MAJORITY of nodes have durably persisted this write to disk
```

## Fast, low-durability write for high-volume analytics logging

```js
db.pageViews.insertOne(
  { page: "/home", userId: "u123", timestamp: new Date() },
  { writeConcern: { w: 1 } }
)
// acceptable to lose an occasional page-view event in a rare crash, in exchange for speed
```

---

# Visualization

## Replica set topology

```
                     ┌────────────┐
                     │  PRIMARY    │  ← all writes
                     └─────┬──────┘
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     ┌─────────┐      ┌─────────┐      ┌─────────┐
     │SECONDARY │      │SECONDARY │      │SECONDARY │  ← replicate + optional reads
     └─────────┘      └─────────┘      └─────────┘
```

## Failover sequence

```
 1. PRIMARY crashes
 2. Remaining nodes detect missing heartbeats
 3. An ELECTION begins among healthy SECONDARIES
 4. Node with most up-to-date oplog + majority vote wins
 5. That node becomes the NEW PRIMARY
 6. Application driver automatically detects the new primary and resumes writes
    (brief window of no-writes during the election itself)
```

## Write Concern spectrum

```
 w: 0            w: 1              w: "majority" (+ j: true)
 ─────           ─────              ─────────────────────────
 fastest         balanced           safest
 no ack          primary ack only   majority + disk-durable ack
 riskiest        default            recommended for critical writes
```

## Read Preference spectrum

```
 primary              secondaryPreferred         nearest
 ───────              ───────────────────         ───────
 always fresh         scales reads, some lag      lowest latency
 more load on primary  less load on primary        role doesn't matter
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Mongoose connection with replica set awareness

```js
const mongoose = require("mongoose");

// Connection string listing all replica set members
mongoose.connect(
  "mongodb://node1.example.com:27017,node2.example.com:27017,node3.example.com:27017/shopDB?replicaSet=rs0",
  {
    readPreference: "primaryPreferred",   // sensible default for most app reads
    w: "majority",                         // sensible default for most app writes
    wtimeoutMS: 5000                       // fail the write if majority ack takes too long
  }
);
```

## Per-query read preference override — heavy reporting query

```js
app.get("/reports/monthly-revenue", async (req, res) => {
  const report = await Order.aggregate([
    { $group: { _id: { $month: "$orderDate" }, revenue: { $sum: "$amount" } } }
  ]).read("secondaryPreferred");   // offload this heavy analytics read from the primary

  res.json(report);
});
```

## Per-write write concern override — critical payment confirmation

```js
app.post("/payments", async (req, res) => {
  try {
    const payment = await Payment.create(
      [req.body],
      { writeConcern: { w: "majority", j: true } }
    );
    res.status(201).json(payment[0]);
  } catch (error) {
    res.status(500).json({ error: "Payment could not be durably confirmed" });
  }
});
```

## Fast-path write concern for high-volume, low-criticality logging

```js
const pageViewSchema = new mongoose.Schema({
  page: String,
  userId: String,
  timestamp: { type: Date, default: Date.now }
});

const PageView = mongoose.model("PageView", pageViewSchema);

app.post("/track", async (req, res) => {
  // fire-and-forget-ish: acceptable to lose a rare event in exchange for speed
  await PageView.create([req.body], { writeConcern: { w: 1 } });
  res.status(202).send();
});
```

## Gracefully handling a brief primary election window

```js
app.post("/orders", async (req, res) => {
  try {
    const order = await Order.create(req.body);
    res.status(201).json(order);
  } catch (error) {
    if (error.name === "MongoNetworkError" || error.message.includes("not master")) {
      // A failover election may be in progress — the driver typically retries
      // automatically, but surface a clear, retryable error to the client if it persists
      return res.status(503).json({ error: "Service temporarily unavailable, please retry" });
    }
    res.status(500).json({ error: "Server error" });
  }
});
```

---

# Interview Questions

**Q1. What is a replica set, and why does MongoDB use one?**
A replica set is a group of MongoDB servers holding synchronized copies of the same data — one primary handling writes, and secondaries replicating those changes. It exists to eliminate a single point of failure and provide high availability: if the primary goes down, a secondary can automatically take over.

**Q2. What's the difference between a primary and a secondary?**
The primary accepts all write operations and is the authoritative source of truth. Secondaries continuously replicate the primary's changes (via the oplog) and can optionally serve read traffic, but cannot accept writes directly, and stand ready to be elected as the new primary if needed.

**Q3. What is failover, and roughly how long does it take?**
Failover is the automatic process of electing a new primary when the current one becomes unavailable. It typically completes within a few seconds, during which the replica set temporarily cannot accept writes.

**Q4. Why do replica sets typically have an odd number of nodes?**
Because primary elections require a **majority** vote to succeed, and an odd number of total nodes guarantees a clear, unambiguous majority is always mathematically possible, even if some nodes are unreachable — avoiding tie-vote scenarios that an even number of nodes could produce.

**Q5. What is the oplog, and what role does it play in replication?**
The oplog is a special capped collection on the primary that records every write operation in order. Secondaries continuously read ("tail") new oplog entries and re-apply them to their own data, which is the actual mechanism that keeps replication in sync.

**Q6. What is Read Preference, and why would you ever read from a secondary instead of the primary?**
Read Preference controls which replica set members a read operation can be routed to. Reading from secondaries can reduce load on the primary and improve read scalability/latency (e.g., `nearest`), at the cost of potentially reading slightly stale ("eventually consistent") data due to replication lag — an acceptable tradeoff for latency-tolerant workloads like reporting or catalogs.

**Q7. What is Write Concern, and what does `w: "majority"` specifically guarantee?**
Write Concern controls how many replica set members must acknowledge a write before MongoDB reports success. `w: "majority"` guarantees the write has been durably recorded on a majority of nodes — meaning it will survive even an immediate primary failure, since any newly-elected primary will necessarily have been part of that same majority.

**Q8. What's the tradeoff between `w: 1` and `w: "majority"`?**
`w: 1` is faster (only waits for the primary's local acknowledgment) but riskier — a write acknowledged this way could theoretically be lost if the primary crashes before replicating it to any secondary. `w: "majority"` is slower (waits for multiple network round trips) but durable — the write is guaranteed to survive a primary failure immediately afterward.

**Q9. What does `j: true` add on top of a write concern setting?**
It additionally requires the write to be committed to the on-disk journal (not just held in memory) before acknowledgment, ensuring the write would survive even an abrupt power loss/crash on the acknowledging node(s), not just a graceful failover.

**Q10. In what scenario would you deliberately choose `w: 1` over `w: "majority"` despite the durability tradeoff?**
For high-volume, lower-criticality writes where speed matters more than guaranteeing zero data loss in a rare failure window — e.g., analytics event logging, page view tracking, or non-critical telemetry — where occasionally losing a very recent write during a rare crash is an acceptable cost for significantly better write throughput.

---

# Practice Questions

## 🟢 Easy
1. What are the two main roles a node can have in a replica set?
2. What happens to a replica set's ability to accept writes during a primary election?
3. Name the default Write Concern value in MongoDB.
4. Name the default Read Preference value in MongoDB.

## 🟡 Medium
5. Explain why a 4-node replica set doesn't provide meaningfully better failure tolerance than a 3-node one, in terms of majority voting.
6. Write a query using `.readPref()` to explicitly route a read to secondaries only (not primary-preferred, just secondary).
7. Write an `insertOne()` call with a write concern that waits for acknowledgment from at least 2 nodes.
8. Explain, in your own words, what "replication lag" means and why it matters for an application reading from secondaries.

## 🔴 Hard
9. A team's checkout/payment endpoint uses `w: 1` for speed. Explain a realistic failure scenario where this setting could cause a customer to be told "payment successful" even though the payment record is later lost — and explain how `w: "majority"` would have prevented it.
10. Explain, step by step, why a write acknowledged with `w: "majority"` is guaranteed to be present on whichever node is elected as the new primary after a failure — connect this to how elections themselves require a majority vote.
11. Design a reasonable Read Preference and Write Concern strategy for a hypothetical e-commerce system with three types of operations: (a) placing an order, (b) viewing a public product catalog page, (c) writing internal analytics/clickstream events. Justify each choice.
12. Explain the difference between "strong consistency" (reading from primary) and "eventual consistency" (reading from secondaries), and describe a real feature in an application where eventual consistency would be a genuinely bad user experience if used by mistake.

---

# Mini Project

## 🛰️ Mini Project: "Resilience-Aware Order API" (Mongoose)

Build an Express + Mongoose API that deliberately applies different Read Preference / Write Concern settings to different endpoints, based on their actual criticality — the core skill this chapter is really teaching.

```js
const mongoose = require("mongoose");
const express = require("express");

mongoose.connect(
  "mongodb://localhost:27017,localhost:27018,localhost:27019/shopDB?replicaSet=rs0"
);

const orderSchema = new mongoose.Schema({
  customerName: String,
  productId: mongoose.Schema.Types.ObjectId,
  amount: Number,
  status: String,
  orderDate: { type: Date, default: Date.now }
});

const clickEventSchema = new mongoose.Schema({
  page: String,
  userId: String,
  timestamp: { type: Date, default: Date.now }
});

const Order = mongoose.model("Order", orderSchema);
const ClickEvent = mongoose.model("ClickEvent", clickEventSchema);

const app = express();
app.use(express.json());

// CRITICAL write — order placement — strong durability
app.post("/orders", async (req, res) => {
  try {
    const [order] = await Order.create(
      [req.body],
      { writeConcern: { w: "majority", j: true } }
    );
    res.status(201).json(order);
  } catch (error) {
    res.status(500).json({ error: "Could not durably confirm order" });
  }
});

// LOW-CRITICALITY, high-volume write — analytics — optimize for speed
app.post("/track-click", async (req, res) => {
  await ClickEvent.create([req.body], { writeConcern: { w: 1 } });
  res.status(202).send();
});

// FRESHNESS-CRITICAL read — a customer checking their OWN just-placed order
app.get("/orders/:id", async (req, res) => {
  const order = await Order.findById(req.params.id).read("primary");
  res.json(order);
});

// LATENCY-TOLERANT, heavy read — admin dashboard report
app.get("/reports/orders-summary", async (req, res) => {
  const summary = await Order.aggregate([
    { $group: { _id: "$status", count: { $sum: 1 }, totalAmount: { $sum: "$amount" } } }
  ]).read("secondaryPreferred");
  res.json(summary);
});

app.listen(3000, () => console.log("Resilience-Aware Order API running on port 3000"));
```

### 🎯 Stretch Goals
- Spin up a local 3-node replica set (via `mongod --replSet` on three ports) and actually run `rs.status()` to watch primary/secondary roles live.
- Manually kill the primary process and observe (via the app's logs) how the Node.js driver detects and recovers from the failover window.
- Add a `wtimeoutMS` setting to the critical write path and simulate a slow/unreachable secondary to see the write concern timeout behavior in action.

---

# Common Mistakes

1. **Assuming a single unreplicated MongoDB instance is production-ready.** No replication means no automatic failover and a genuine risk of total data loss on hardware failure — never treat a standalone `mongod` as a production database.
2. **Using `secondary`/`secondaryPreferred` read preference for data that requires absolute freshness** (e.g., checking your own balance right after a deposit), and being confused by "stale" results due to replication lag.
3. **Using `w: 1` (or worse, `w: 0`) for genuinely critical writes** (payments, orders) purely for speed, without understanding the real, if rare, data-loss risk this introduces during a primary failure.
4. **Using `w: "majority"` indiscriminately for every single write**, including high-volume, low-criticality ones (like analytics events), unnecessarily hurting write throughput where it isn't actually needed.
5. **Forgetting that a brief "no primary available" window exists during failover**, and not handling the resulting transient errors gracefully in application code (assuming every write will always succeed instantly).
6. **Not configuring an odd number of replica set members**, risking ambiguous/tied elections.
7. **Confusing replication (multiple copies for availability) with sharding (splitting data across servers for scale)** — they solve different problems and are often used together, not interchangeably.

---

# Best Practices

- ✅ Always run production MongoDB deployments as a replica set (minimum 3 nodes), never a standalone instance.
- ✅ Choose Write Concern deliberately, per operation type: `w: "majority"` (+ `j: true`) for critical, financial, or user-facing confirmations; `w: 1` for high-volume, loss-tolerant logging/analytics.
- ✅ Choose Read Preference deliberately: `primary` for freshness-critical reads (a user's own just-written data); `secondaryPreferred`/`nearest` for latency-tolerant, high-volume reads (reports, catalogs, dashboards).
- ✅ Set a reasonable `wtimeoutMS` alongside `w: "majority"` so a critical write fails fast (with a clear error) rather than hanging indefinitely if enough nodes are unreachable.
- ✅ Design your application to gracefully handle the brief "no primary" window during failover — surface clear, retryable errors rather than crashing or hanging.
- ✅ Monitor replication lag in production (`rs.printSecondaryReplicationInfo()` or equivalent tooling) — growing lag is an early warning sign of an overloaded or struggling secondary.
- ✅ Understand that replication (availability/durability) and sharding (horizontal scale) are complementary, often combined in large production deployments — don't treat them as alternatives to each other.

---

# Cheat Sheet

## Replica Set Roles

```
PRIMARY    → accepts all writes, one at a time
SECONDARY  → replicates primary via oplog, optional reads, can be elected primary
FAILOVER   → automatic re-election of a new primary if current one fails
```

## Read Preference Options

```js
"primary"              // always fresh, most load on primary
"primaryPreferred"      // primary if available, else secondary
"secondary"             // secondaries only
"secondaryPreferred"    // secondaries if available, else primary
"nearest"               // lowest latency node, regardless of role
```

## Write Concern Options

```js
{ w: 0 }                          // fire-and-forget, fastest, riskiest
{ w: 1 }                          // primary ack only (default)
{ w: "majority" }                 // majority ack, durable across failover
{ w: "majority", j: true }        // + on-disk journal commit, safest
```

## Decision Guide

```
Critical write (payment, order)         → w: "majority", j: true
High-volume, low-criticality write      → w: 1
User reading their OWN fresh data       → readPreference: "primary"
Heavy reporting / dashboard read        → readPreference: "secondaryPreferred"
```

## Replica Set Admin Commands

```js
rs.status()   // member states
rs.conf()     // configuration
rs.hello()    // who is currently primary
```
