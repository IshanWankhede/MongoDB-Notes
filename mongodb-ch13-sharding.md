# 📖 Chapter 13 — Sharding

> **MongoDB Handbook — Beginner to Advanced**
> Complete revision notes in official-documentation style (PostgreSQL / Prisma / MongoDB docs format).

---

# Introduction

Chapter 12 solved *availability* — surviving a server failure without losing data or going down. This chapter solves a completely different problem: **what happens when your data (or your write traffic) becomes too big for any single server to handle at all**, no matter how powerful that server is, or how many replicas of it you run?

That's **sharding** — splitting one enormous logical collection across many physical servers, each holding only a slice of the data, so the *system as a whole* can keep growing horizontally, essentially without an upper limit. This chapter covers the architecture that makes this possible: shards, config servers, the query router, shard keys, and chunk migration — plus how to actually pick a good shard key, which is the single most consequential decision in a sharded deployment.

---

# Theory

## Horizontal Scaling

**Horizontal scaling** ("scaling out") means handling more data/traffic by **adding more machines**, each handling a portion of the load — as opposed to **vertical scaling** ("scaling up"), which means making one single machine more powerful (more CPU, RAM, disk).

```
 VERTICAL SCALING                    HORIZONTAL SCALING

 ┌──────────────┐                    ┌────┐ ┌────┐ ┌────┐
 │              │                    │ M1 │ │ M2 │ │ M3 │
 │  ONE BIGGER   │        vs.         │    │ │    │ │    │
 │   MACHINE     │                    └────┘ └────┘ └────┘
 │              │                    (each holds a SLICE
 └──────────────┘                     of the total data)
```

> **Analogy:** Vertical scaling is hiring one superhuman employee who can somehow work faster and faster forever. Horizontal scaling is hiring more regular employees and dividing the work among them. At some point, no single human (or single server) can physically work fast enough or hold enough information alone — you *must* bring in more people (more machines) to keep growing. Sharding is MongoDB's system for organizing that team of machines so they function together as one logical database.

Replica sets (Chapter 12) copy the **same** data to multiple servers for availability. **Sharding** splits **different** data across multiple servers for scale — these are complementary, often combined techniques, not alternatives.

---

## Shards

A **shard** is one of the servers (technically, usually one replica set) that holds a **portion** of the collection's total data. Each shard is a fully functional, independent MongoDB deployment (typically its own replica set, for the availability guarantees from Chapter 12) — it just happens to only contain a *slice* of the whole dataset.

```
 Full "orders" collection (10 million documents)

 ┌────────────┐   ┌────────────┐   ┌────────────┐
 │  Shard 1    │   │  Shard 2    │   │  Shard 3    │
 │ ~3.3M docs  │   │ ~3.3M docs  │   │ ~3.3M docs  │
 │ (its own    │   │ (its own    │   │ (its own    │
 │ replica set)│   │ replica set)│   │ replica set)│
 └────────────┘   └────────────┘   └────────────┘
```

> **Analogy:** If a single library building can only physically fit 500,000 books, and your city needs to store 5,000,000 books, you build 10 separate branch libraries (shards), each holding roughly 500,000 books. No single branch has to hold everything — but together, the whole city's collection is fully available if you know which branch to check.

---

## Config Servers

**Config servers** store the sharded cluster's **metadata** — most importantly, the mapping of which **ranges of data** (chunks) live on which shard. Every query router consults the config servers to know where to route each operation.

```
 ┌──────────────────────────────────────────┐
 │            CONFIG SERVERS                  │
 │  "orders with _id A–F  → Shard 1"           │
 │  "orders with _id G–M  → Shard 2"           │
 │  "orders with _id N–Z  → Shard 3"           │
 └──────────────────────────────────────────┘
```

> **Analogy:** Config servers are like a city's central library catalog system that knows exactly which branch holds which books — without consulting this catalog, you'd have no idea which of the 10 branches to even visit to find a specific book.

Config servers are themselves deployed as a replica set (for the same availability reasons as any other critical data) — losing the cluster's metadata would make the whole sharded cluster unusable, even if every shard's actual data were perfectly intact.

---

## Query Router (`mongos`)

The **query router** (the `mongos` process) is what your application actually connects to in a sharded cluster — it's a lightweight, stateless routing layer that consults the config servers to figure out **which shard(s)** a given query needs to be sent to, forwards the query there, and merges the results before returning them to your application.

```
        ┌──────────────┐
        │  Your App     │
        └──────┬───────┘
               │  (app just talks to mongos, doesn't know about shards)
        ┌──────▼───────┐
        │   mongos      │  ← consults config servers, routes query
        │ (query router)│
        └──────┬───────┘
    ┌──────────┼──────────┐
    ▼          ▼          ▼
 Shard 1    Shard 2    Shard 3
```

> **Analogy:** The query router is like a city-wide library information desk. You walk up and ask for a specific book — you don't need to know or care which of the 10 branches actually has it. The desk clerk (mongos) checks the catalog (config servers), tells you (or fetches for you) exactly where to go, and if your request spans multiple branches (e.g., "all books published in 2020"), the clerk visits all relevant branches and hands you back one combined, complete answer.

Your application (and Mongoose) connects to `mongos` **exactly the same way** it would connect to a single `mongod` — sharding is largely transparent to application code, which is a deliberate design goal.

---

## Shard Keys

The **shard key** is the field (or combination of fields) MongoDB uses to decide **which shard** each document belongs on. This is, without exaggeration, **the single most important decision** in a sharded deployment — it cannot be easily changed after the fact on a large, already-running collection.

```js
sh.shardCollection("shopDB.orders", { customerId: 1 })
```

Once set, MongoDB uses the shard key's value to partition the collection into contiguous **chunks** (ranges of shard key values), and distributes those chunks across the available shards.

```
 shardKey: customerId

 Shard 1: customerId "A0000" – "H9999"
 Shard 2: customerId "I0000" – "P9999"
 Shard 3: customerId "Q0000" – "Z9999"
```

> **Analogy:** Choosing a shard key is like deciding how to organize a massive city-wide filing system into branch libraries in the first place — by last name (A–H, I–P, Q–Z)? By zip code? By date filed? Choose based on last name, and a search for "all files for Mr. Gupta" goes straight to one branch. Choose poorly (say, by "file color," when 90% of files happen to be blue), and you end up with one overloaded branch holding almost everything, while the others sit nearly empty — the exact opposite of what sharding was supposed to achieve.

### What makes a good shard key
- **High cardinality** — many distinct possible values (a boolean `isActive` field is a terrible shard key; only 2 possible "buckets" exist)
- **Even distribution** — writes/reads spread roughly evenly across the key's range, avoiding "hot" shards
- **Matches common query patterns** — queries that include the shard key can be routed directly to the relevant shard(s); queries that don't must be broadcast to **every** shard (a "scatter-gather" query — much slower)

```
 GOOD shard key example:  customerId (millions of distinct values, evenly spread)
 BAD shard key example:   isActive (only 2 values → massive, unbalanced chunks)
 BAD shard key example:   createdAt alone (all NEW writes go to the SAME "latest" chunk
                          → creates a hot shard that absorbs 100% of insert traffic)
```

---

## Chunk Migration

A **chunk** is a contiguous range of shard key values (and the documents that fall within it) — the actual unit of data MongoDB moves around when balancing a sharded cluster. As data grows or shrinks unevenly, MongoDB's built-in **balancer** process automatically migrates chunks between shards to keep the data (and load) roughly evenly distributed.

```
 BEFORE balancing:                    AFTER chunk migration:

 Shard 1: [chunk][chunk][chunk][chunk]   Shard 1: [chunk][chunk]
 Shard 2: [chunk]                        Shard 2: [chunk][chunk]
 Shard 3: [chunk]                        Shard 3: [chunk][chunk]
   (Shard 1 overloaded)                    (evenly balanced)
```

> **Analogy:** Chunk migration is like a city library system noticing that one branch has become massively overcrowded with books (perhaps a popular new author's entire back-catalog got filed there), while other branches are nearly empty — the system automatically arranges for a courier to physically relocate some sections of books from the overloaded branch to the emptier ones, without ever losing track of which book is where, and without making the collection unavailable to readers during the move.

The **balancer** runs automatically and periodically checks for uneven distribution, initiating migrations in the background. Migrations do add temporary load to the cluster, so MongoDB is designed to migrate gradually and avoid disrupting live traffic.

---

## Real World Use Cases

| Use Case | Why Sharding Fits |
|---|---|
| **Massive social media platforms** | Billions of posts/users — no single server (or even a single replica set) could hold or serve this data volume/throughput |
| **IoT sensor data at scale** | Millions of devices sending constant high-frequency telemetry — write throughput alone can exceed what one primary can handle |
| **Global multi-region applications** | Shard by region so European user data lives on shards physically located in Europe, reducing latency and meeting data-residency regulations |
| **Large e-commerce platforms during peak events** | Massive traffic spikes (e.g., a big sale day) need write throughput spread across many shards, not funneled through one primary |
| **Gaming platforms with huge player bases** | Player state, match history, and leaderboards at a scale exceeding single-server capacity |

⚠️ **Important reality check:** sharding adds real operational complexity (more servers to manage, harder queries to reason about, an immutable-in-practice shard key decision). Most applications — even fairly large, successful ones — **never actually need to shard**; a well-indexed replica set can handle a surprising amount of scale. Sharding is a tool for genuine, measured scale problems, not a default architecture to reach for early.

---

# Why This Exists

No matter how powerful a single server (or even a well-replicated set of identical servers, as in Chapter 12) becomes, there is a hard ceiling — a maximum amount of RAM, disk, and CPU any one machine can physically have, and a maximum write throughput a single primary can process, since every write in a replica set still funnels through **one** primary node. Sharding exists to break through that ceiling entirely: instead of one primary handling *all* writes for the *entire* dataset, a sharded cluster spreads both the storage **and** the write throughput across many independent primaries (one per shard), each responsible for only a fraction of the total data.

The specific architecture — config servers holding metadata, `mongos` as a transparent routing layer, shard keys defining how data is partitioned, and automatic chunk migration for rebalancing — exists to make this horizontal split **invisible to application code**. Without this architecture, every application would need to manually track "which server holds which customer's data" and implement its own routing logic — exactly the kind of complex, error-prone, infrastructure-level problem a database is supposed to solve *for* you, not push back onto your application.

---

# Internal Working

## How a query gets routed in a sharded cluster

```
 App sends: db.orders.find({ customerId: "C12345" })
                    │
                    ▼
              mongos (query router)
                    │
     consults CONFIG SERVERS: "which shard holds
     the chunk containing customerId: C12345?"
                    │
                    ▼
        "That's in a chunk currently on Shard 2"
                    │
                    ▼
     mongos forwards the query ONLY to Shard 2
                    │
                    ▼
     Shard 2 executes the query locally, returns results
                    │
                    ▼
     mongos returns the result to the app
     (a SINGLE, targeted query — fast!)
```

## What happens with a query that doesn't include the shard key

```
 App sends: db.orders.find({ status: "pending" })   (shard key is customerId, NOT status)
                    │
                    ▼
              mongos has NO WAY to know which shard(s)
              might contain matching documents
                    │
                    ▼
     mongos broadcasts the query to ALL shards
     ("scatter-gather")
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
     Shard 1     Shard 2     Shard 3
     (each searches its own local data)
        │           │           │
        └───────────┼───────────┘
                    ▼
     mongos MERGES all partial results together
     (slower — every shard had to do work, even
      if most had zero matching documents)
```

**This is exactly why shard key choice matters so much:** queries matching the shard key are fast, single-shard "targeted" operations; queries that don't include it become slow, cluster-wide "scatter-gather" operations.

## How chunk splitting and migration work internally
As a chunk grows past a configured size threshold (data keeps being inserted into that shard key range), MongoDB automatically **splits** it into two smaller chunks. The **balancer** background process then periodically compares the number of chunks across shards, and if the imbalance exceeds a threshold, it migrates chunks from the more-loaded shard to less-loaded ones — updating the config servers' metadata to reflect the chunk's new location once the migration completes, ensuring the query router always has an accurate, current map.

---

# Syntax

```js
// Enable sharding on a database
sh.enableSharding("shopDB")

// Shard a specific collection with a chosen shard key
sh.shardCollection("shopDB.orders", { customerId: 1 })

// Compound shard key
sh.shardCollection("shopDB.orders", { customerId: 1, orderDate: 1 })

// Check sharding status of the cluster
sh.status()

// Check how balanced a sharded collection currently is
db.orders.getShardDistribution()
```

---

# Examples

## Setting up sharding on a collection

```js
// 1. Enable sharding for the database
sh.enableSharding("shopDB")

// 2. Choose and apply a shard key
sh.shardCollection("shopDB.orders", { customerId: 1 })

// 3. Verify
sh.status()
```

## A well-targeted query (uses the shard key)

```js
// Shard key is customerId — this query is routed to exactly ONE shard
db.orders.find({ customerId: "C12345" })
```

## A scatter-gather query (doesn't use the shard key)

```js
// Shard key is customerId — this query has to check EVERY shard
db.orders.find({ status: "pending" })
```

## A compound shard key balancing distribution AND common query patterns

```js
// Spreads writes evenly (customerId has high cardinality)
// AND supports efficient date-range queries WITHIN a customer's own data
sh.shardCollection("shopDB.orders", { customerId: 1, orderDate: 1 })
```

---

# Visualization

## Full sharded cluster architecture

```
                         ┌──────────────┐
                         │  Your App     │
                         │  (Mongoose)   │
                         └──────┬───────┘
                                │
                         ┌──────▼───────┐
                         │   mongos      │  ← query router
                         └──────┬───────┘
                 ┌──────────────┼──────────────┐
                 ▼                              ▼
       ┌──────────────────┐          ┌──────────────────┐
       │  CONFIG SERVERS    │          │      SHARDS        │
       │  (metadata: which   │◄────────│  Shard 1 (replica   │
       │   chunk is where)   │         │   set)              │
       └──────────────────┘          │  Shard 2 (replica   │
                                       │   set)              │
                                       │  Shard 3 (replica   │
                                       │   set)              │
                                       └──────────────────┘
```

## Good vs bad shard key distribution

```
 GOOD shard key (high cardinality, even spread):

 Shard 1: ████████████    Shard 2: ████████████    Shard 3: ████████████
 (roughly equal load across all shards)

 BAD shard key (low cardinality / monotonic, e.g. plain createdAt):

 Shard 1: ██                Shard 2: ██                Shard 3: ████████████████████
 (all NEW writes pile onto ONE "hot" shard — the others sit nearly idle)
```

## Targeted query vs scatter-gather query

```
 TARGETED (includes shard key):        SCATTER-GATHER (excludes shard key):

    mongos                                 mongos
      │                                   /   |   \
      ▼                                  ▼    ▼    ▼
   Shard 2 only                      Shard1 Shard2 Shard3
   (fast, 1 shard touched)           (slow, ALL shards touched)
```

---

# Backend Examples

> All backend examples use **Mongoose**.

## Connecting Mongoose to a sharded cluster (via `mongos`)

```js
const mongoose = require("mongoose");

// Application code connects to mongos EXACTLY like a normal MongoDB server —
// sharding is transparent; nothing about your Mongoose code needs to change.
mongoose.connect("mongodb://mongos-router1:27017,mongos-router2:27017/shopDB");
```

## Designing a schema with the shard key in mind

```js
const orderSchema = new mongoose.Schema({
  customerId: { type: String, required: true, index: true },  // this IS the shard key
  productId: mongoose.Schema.Types.ObjectId,
  amount: Number,
  status: String,
  orderDate: { type: Date, default: Date.now }
});

const Order = mongoose.model("Order", orderSchema);
```

## Writing queries that deliberately include the shard key (targeted, fast)

```js
app.get("/customers/:customerId/orders", async (req, res) => {
  // Includes "customerId" — the shard key — so mongos routes this
  // to exactly the shard(s) holding this customer's data
  const orders = await Order.find({ customerId: req.params.customerId });
  res.json(orders);
});
```

## Recognizing (and being deliberate about) a scatter-gather query

```js
app.get("/orders/pending", async (req, res) => {
  // "status" is NOT the shard key — this query broadcasts to ALL shards.
  // Acceptable for an occasional admin report; would be a red flag
  // if this were a high-frequency, latency-sensitive endpoint.
  const pendingOrders = await Order.find({ status: "pending" });
  res.json(pendingOrders);
});
```

## Checking shard distribution health from application tooling

```js
app.get("/admin/shard-distribution", async (req, res) => {
  const stats = await mongoose.connection.db.command({
    collStats: "orders"
  });
  res.json({
    shardCount: stats.shards ? Object.keys(stats.shards).length : 1,
    totalSizeBytes: stats.size
  });
});
```

---

# Interview Questions

**Q1. What problem does sharding solve that replication (Chapter 12) does not?**
Replication solves availability — keeping multiple identical copies of the *same* data so the system survives a server failure. Sharding solves scale — splitting *different* portions of the data across multiple servers so the total dataset size and write throughput can grow beyond what any single server (or single primary) could handle alone.

**Q2. What are the three main architectural components of a sharded cluster?**
Shards (hold the actual data, in slices), config servers (store metadata about which data lives on which shard), and the query router / `mongos` (routes application queries to the correct shard(s) based on the config servers' metadata).

**Q3. What is a shard key, and why is choosing it so consequential?**
The shard key is the field (or fields) used to determine which shard each document belongs on. It's consequential because it directly determines whether data and write load are evenly distributed across shards, whether common queries can be efficiently routed to a single shard, and because changing a poorly-chosen shard key on an already-large, live collection is operationally very difficult.

**Q4. What makes a shard key "bad," and give a concrete example.**
Low cardinality (few distinct values, causing uneven, lumpy distribution) or monotonically increasing values like a plain timestamp (causing all new writes to pile onto whichever shard currently holds the "latest" range, creating a hot shard) are both bad shard key choices. Example: sharding on a boolean `isActive` field would only ever create two possible buckets, guaranteeing severe imbalance.

**Q5. What is a "scatter-gather" query, and why is it slower than a targeted query?**
It's a query that doesn't include the shard key, forcing `mongos` to broadcast the query to every shard in the cluster (since it has no way to know which shard(s) might hold matching documents) and merge all the partial results together — slower because every shard must do work, even if most end up returning nothing.

**Q6. What is the role of config servers, and why are they typically deployed as a replica set themselves?**
Config servers store the cluster's metadata — specifically, the mapping of chunks (shard key ranges) to shards. They're deployed as a replica set because losing this metadata would make the entire sharded cluster unusable (queries couldn't be routed correctly), even if every individual shard's actual data were perfectly intact — the same availability reasoning from Chapter 12 applies here too.

**Q7. What is chunk migration, and what triggers it?**
Chunk migration is the process of moving a contiguous range of shard-key data (a chunk) from one shard to another, performed automatically by MongoDB's balancer process whenever it detects a meaningful imbalance in chunk distribution across shards (e.g., one shard has grown to hold significantly more chunks than others).

**Q8. Does an application connecting via Mongoose need to know it's talking to a sharded cluster instead of a single server?**
No — the application connects to `mongos` exactly as it would connect to any single MongoDB server, and sharding is designed to be largely transparent at the application/driver level. The application does, however, need to be *designed* with shard key considerations in mind (i.e., including the shard key in common queries) to actually benefit from sharding's performance advantages.

**Q9. Why shouldn't most applications reach for sharding by default?**
Sharding introduces significant operational complexity (more servers, an effectively irreversible shard key decision, scatter-gather query risks) that isn't justified unless an application has a genuine, measured need — a single well-indexed, properly-resourced replica set can handle a very large amount of real-world traffic and data before sharding becomes necessary.

**Q10. Give a real-world scenario where a compound shard key would be preferable to a single-field shard key.**
An e-commerce platform sharding `orders` by `customerId` alone would achieve good write distribution, but a common query like "this customer's orders in the last 30 days" would still need to scan across that customer's entire chunk. A compound shard key like `{ customerId: 1, orderDate: 1 }` maintains good distribution (from the high-cardinality `customerId`) while also allowing efficient range queries on `orderDate` *within* a given customer's already-targeted shard.

---

# Practice Questions

## 🟢 Easy
1. What is the difference between horizontal scaling and vertical scaling?
2. Name the three main components of a sharded MongoDB cluster.
3. What does the query router (`mongos`) actually do?
4. Why is a boolean field generally a poor choice for a shard key?

## 🟡 Medium
5. Explain why a query that includes the shard key is faster than one that doesn't, using the concept of "targeted" vs "scatter-gather" queries.
6. Write the two shell commands needed to enable sharding on a database called `analyticsDB` and shard its `events` collection by a `deviceId` field.
7. Explain why config servers are deployed as a replica set rather than a single server.
8. A team shards a `logs` collection using a plain, ever-increasing `timestamp` field as the shard key. Explain what problem this will cause as new logs are continuously written.

## 🔴 Hard
9. Design a shard key for a global ride-sharing app's `rides` collection, where the most common query is "find all of this specific driver's completed rides." Justify your choice, including cardinality and query-pattern considerations.
10. Explain, step by step, what happens internally when a chunk grows too large — from the initial split, through the balancer detecting imbalance, to the actual migration and config server metadata update.
11. A junior engineer proposes sharding a brand-new application's database from day one, "to be ready for scale." Explain, using this chapter's real-world use cases and tradeoffs, why this is often premature — and what signals would indicate sharding has actually become necessary.
12. Compare and contrast replication and sharding across these dimensions: (a) what specific problem each solves, (b) whether they can be used together, and (c) what happens to a single logical collection's data under each (identical copies vs. distinct partitions).

---

# Mini Project

## 🌐 Mini Project: "Sharding-Aware Order Service Design" (Mongoose)

Since actually running a multi-node sharded cluster requires real infrastructure, this mini project focuses on **designing and documenting** a sharding-ready schema and query strategy — the actual skill that matters most for most engineers, even before ever touching a real `mongos` deployment.

```js
const mongoose = require("mongoose");
const express = require("express");

// Assume this connects to a `mongos` router in a real sharded deployment;
// works identically against a single mongod during local development.
mongoose.connect("mongodb://localhost:27017/shopDB");

// Schema explicitly designed around an intended shard key: customerId
const orderSchema = new mongoose.Schema({
  customerId: { type: String, required: true, index: true },  // intended shard key
  productId: mongoose.Schema.Types.ObjectId,
  amount: Number,
  status: String,
  orderDate: { type: Date, default: Date.now }
});

const Order = mongoose.model("Order", orderSchema);

const app = express();
app.use(express.json());

// ✅ TARGETED query pattern — always include customerId wherever possible
app.get("/customers/:customerId/orders", async (req, res) => {
  const orders = await Order.find({ customerId: req.params.customerId })
    .sort({ orderDate: -1 });
  res.json(orders);
});

// ⚠️ SCATTER-GATHER query pattern — flagged clearly as an admin-only,
// infrequent operation, since it would hit every shard in production
app.get("/admin/orders/pending", async (req, res) => {
  const pending = await Order.find({ status: "pending" });
  res.json({
    warning: "This query does not use the shard key and would scatter-gather in production",
    count: pending.length,
    orders: pending
  });
});

// Simulated "shard distribution health check" endpoint
app.get("/admin/collection-stats", async (req, res) => {
  const stats = await mongoose.connection.db.command({ collStats: "orders" });
  res.json({ count: stats.count, sizeBytes: stats.size, indexSizes: stats.indexSizes });
});

app.listen(3000, () => console.log("Sharding-Aware Order Service running on port 3000"));
```

### 🎯 Stretch Goals
- Document (as comments or a README) which of your app's actual endpoints would be "targeted" vs. "scatter-gather" if this collection were sharded by `customerId` — a genuinely useful exercise before ever sharding for real.
- Research and note what a **hashed shard key** (`sh.shardCollection(ns, { field: "hashed" })`) is, and when it's preferred over a plain range-based shard key (hint: it trades range-query efficiency for near-perfect write distribution).
- If you have access to Docker, look up MongoDB's official guide to spinning up a local multi-shard test cluster, and run `sh.status()` against it for real.

---

# Common Mistakes

1. **Reaching for sharding far too early**, before a genuine, measured scale problem exists — adding significant operational complexity for no real benefit.
2. **Choosing a low-cardinality or monotonically increasing shard key** (like a plain boolean or a plain timestamp), leading to severe, unbalanced "hot shard" problems.
3. **Designing queries that never include the shard key**, unknowingly turning every single request into an expensive scatter-gather operation across the whole cluster.
4. **Assuming the shard key can be easily changed later** — on an already-large, live sharded collection, changing the shard key is a very involved, often near-impractical operation; get it right (or close to right) from the start.
5. **Confusing sharding with replication**, assuming sharding alone provides high availability — a shard with no replica set backing it is still a single point of failure for its slice of the data.
6. **Not designing the application's query patterns around the chosen shard key** — picking a great shard key for distribution but then writing all common queries without it anyway, gaining none of the routing benefits.
7. **Underestimating the operational overhead of a sharded cluster** — more servers to monitor, patch, and manage, and more complex failure scenarios to reason about.

---

# Best Practices

- ✅ Exhaust simpler scaling options first (better indexing, read replicas via Chapter 12, vertical scaling, caching) before reaching for sharding.
- ✅ Choose a shard key with **high cardinality**, **even distribution**, and that **matches your application's most common query patterns**.
- ✅ Design (or at least sketch out) your intended shard key **before** your collection grows large — changing it later is difficult and disruptive.
- ✅ Consider a **hashed shard key** when you need near-perfect write distribution and don't rely heavily on range queries on that field.
- ✅ Actively identify and minimize scatter-gather queries in your application — if a query pattern is both frequent and can't include the shard key, that's a strong signal to reconsider the shard key choice.
- ✅ Combine sharding with replication (each shard as its own replica set) for both scale *and* availability together — they solve different problems and are meant to be layered.
- ✅ Monitor chunk distribution (`db.collection.getShardDistribution()`) in production to catch emerging imbalance early, rather than discovering a hot shard only after it becomes a real incident.

---

# Cheat Sheet

## Sharded Cluster Components

```
Shards          → hold actual data (each usually its own replica set)
Config Servers  → store metadata: which chunk lives on which shard
mongos          → query router the application actually connects to
```

## Shard Key Quality Checklist

```
✅ High cardinality (many distinct values)
✅ Even distribution across the value range
✅ Matches common query filters (avoids scatter-gather)
❌ Avoid: booleans, low-cardinality enums, plain monotonic timestamps
```

## Query Routing

```
Query INCLUDES shard key   → targeted, routed to ONE (or few) shard(s), FAST
Query EXCLUDES shard key   → scatter-gather, broadcast to ALL shards, SLOW
```

## Setup Syntax

```js
sh.enableSharding("dbName")
sh.shardCollection("dbName.collectionName", { shardKeyField: 1 })
sh.status()
db.collection.getShardDistribution()
```

## Sharding vs Replication

```
Replication → SAME data copied to multiple servers → solves AVAILABILITY
Sharding    → DIFFERENT data split across servers    → solves SCALE
Real production systems often use BOTH together.
```
