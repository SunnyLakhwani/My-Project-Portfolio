// ============================================================
//  Restaurant Management System — CodeAlpha Task 3
//  Single-file version: main.js
//  Stack: Express.js + SQLite (sql.js) — no MySQL needed!
//  Run:   node main.js
//  Seed:  node main.js --seed
// ============================================================

require("dotenv").config();

const express    = require("express");
const cors       = require("cors");
const morgan     = require("morgan");
const bcrypt     = require("bcryptjs");
const jwt        = require("jsonwebtoken");
const { v4: uuidv4 } = require("uuid");
const initSqlJs  = require("sql.js");
const fs         = require("fs");

const app  = express();
app.use(express.json());
const PORT = process.env.PORT || 3000;
const DB_PATH    = process.env.DB_PATH || "./restaurant.db";
const JWT_SECRET = process.env.JWT_SECRET || "change_this_secret";
const JWT_EXPIRES = process.env.JWT_EXPIRES_IN || "24h";

// ─────────────────────────────────────────────────────────────
//  DATABASE SETUP
// ─────────────────────────────────────────────────────────────

let db = null;

function saveToDisk() {
  const data   = db.export();
  const buffer = Buffer.from(data);
  fs.writeFileSync(DB_PATH, buffer);
}

// Auto-save every 30 seconds so we never lose data
setInterval(() => { if (db) saveToDisk(); }, 30000);

async function initDatabase() {
  const SQL = await initSqlJs();

  if (fs.existsSync(DB_PATH)) {
    db = new SQL.Database(fs.readFileSync(DB_PATH));
    console.log("📂 Loaded existing database.");
  } else {
    db = new SQL.Database();
    console.log("🆕 Created fresh database.");
  }

  // ── users ──────────────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,
    role       TEXT NOT NULL DEFAULT 'staff',
    created_at TEXT DEFAULT (datetime('now'))
  )`);

  // ── menu_items ─────────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS menu_items (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT,
    category     TEXT NOT NULL,
    price        REAL NOT NULL,
    is_available INTEGER DEFAULT 1,
    created_at   TEXT DEFAULT (datetime('now'))
  )`);

  // ── restaurant_tables ──────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS restaurant_tables (
    id           TEXT PRIMARY KEY,
    table_number INTEGER UNIQUE NOT NULL,
    capacity     INTEGER NOT NULL,
    status       TEXT DEFAULT 'available',
    location     TEXT DEFAULT 'main hall'
  )`);

  // ── reservations ───────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS reservations (
    id             TEXT PRIMARY KEY,
    table_id       TEXT NOT NULL,
    customer_name  TEXT NOT NULL,
    customer_phone TEXT,
    party_size     INTEGER NOT NULL,
    reserved_date  TEXT NOT NULL,
    reserved_time  TEXT NOT NULL,
    status         TEXT DEFAULT 'confirmed',
    notes          TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (table_id) REFERENCES restaurant_tables(id)
  )`);

  // ── orders ─────────────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS orders (
    id            TEXT PRIMARY KEY,
    table_id      TEXT,
    order_type    TEXT DEFAULT 'dine-in',
    status        TEXT DEFAULT 'pending',
    total_amount  REAL DEFAULT 0,
    customer_name TEXT,
    notes         TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (table_id) REFERENCES restaurant_tables(id)
  )`);

  // ── order_items ────────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS order_items (
    id           TEXT PRIMARY KEY,
    order_id     TEXT NOT NULL,
    menu_item_id TEXT NOT NULL,
    quantity     INTEGER NOT NULL DEFAULT 1,
    unit_price   REAL NOT NULL,
    subtotal     REAL NOT NULL,
    FOREIGN KEY (order_id)     REFERENCES orders(id),
    FOREIGN KEY (menu_item_id) REFERENCES menu_items(id)
  )`);

  // ── inventory ──────────────────────────────────────────────
  db.run(`CREATE TABLE IF NOT EXISTS inventory (
    id              TEXT PRIMARY KEY,
    item_name       TEXT UNIQUE NOT NULL,
    unit            TEXT NOT NULL,
    quantity        REAL NOT NULL DEFAULT 0,
    low_stock_alert REAL DEFAULT 10,
    cost_per_unit   REAL DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
  )`);

  saveToDisk();
  console.log("✅ All tables ready.");
}

// ─────────────────────────────────────────────────────────────
//  DB QUERY HELPERS
// ─────────────────────────────────────────────────────────────

function dbQuery(sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  return rows;
}

function dbRun(sql, params = []) {
  db.run(sql, params);
  saveToDisk();
  return { changes: db.getRowsModified() };
}

function dbOne(sql, params = []) {
  const rows = dbQuery(sql, params);
  return rows.length > 0 ? rows[0] : null;
}

// ─────────────────────────────────────────────────────────────
//  MIDDLEWARE
// ─────────────────────────────────────────────────────────────

//  MIDDLEWARE

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(morgan("dev"));

app.post("/debug", (req, res) => {
  console.log("HEADERS:", req.headers);
  console.log("BODY:", req.body);
  res.json({ received: req.body });
});

function authenticate(req, res, next) {
  const header = req.headers["authorization"];
  if (!header || !header.startsWith("Bearer ")) {
    return res.status(401).json({ success: false, message: "Access denied. No token provided." });
  }
  try {
    req.user = jwt.verify(header.split(" ")[1], JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ success: false, message: "Invalid or expired token." });
  }
}

function adminOnly(req, res, next) {
  if (req.user.role !== "admin") {
    return res.status(403).json({ success: false, message: "Forbidden. Admins only." });
  }
  next();
}

// ─────────────────────────────────────────────────────────────
//  AUTH ROUTES  /api/auth
// ─────────────────────────────────────────────────────────────

// POST /api/auth/register
app.post("/api/auth/register", async (req, res) => {
  try {
    const { name, email, password, role = "staff" } = req.body;

    if (!name || !email || !password)
      return res.status(400).json({ success: false, message: "Name, email, and password are required." });

    if (!["admin", "staff", "chef"].includes(role))
      return res.status(400).json({ success: false, message: "Role must be admin, staff, or chef." });

    if (dbOne("SELECT id FROM users WHERE email = ?", [email]))
      return res.status(409).json({ success: false, message: "An account with this email already exists." });

    const id = uuidv4();
    dbRun("INSERT INTO users (id, name, email, password, role) VALUES (?, ?, ?, ?, ?)",
      [id, name, email, await bcrypt.hash(password, 12), role]);

    res.status(201).json({ success: true, message: "Account created.", data: { id, name, email, role } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/auth/login
app.post("/api/auth/login", async (req, res) => {
  try {
    const { email, password } = req.body;
    if (!email || !password)
      return res.status(400).json({ success: false, message: "Email and password are required." });

    const user = dbOne("SELECT * FROM users WHERE email = ?", [email]);
    if (!user || !(await bcrypt.compare(password, user.password)))
      return res.status(401).json({ success: false, message: "Invalid email or password." });

    const token = jwt.sign(
      { id: user.id, name: user.name, email: user.email, role: user.role },
      JWT_SECRET,
      { expiresIn: JWT_EXPIRES }
    );

    res.json({ success: true, message: "Login successful.", data: { token, user: { id: user.id, name: user.name, email: user.email, role: user.role } } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  MENU ROUTES  /api/menu
// ─────────────────────────────────────────────────────────────

// GET /api/menu
app.get("/api/menu", (req, res) => {
  try {
    const { category, available } = req.query;
    let sql = "SELECT * FROM menu_items WHERE 1=1";
    const params = [];
    if (category)          { sql += " AND category = ?";    params.push(category); }
    if (available !== "all") { sql += " AND is_available = 1"; }
    sql += " ORDER BY category, name";

    const items = dbQuery(sql, params);
    const grouped = items.reduce((acc, item) => {
      if (!acc[item.category]) acc[item.category] = [];
      acc[item.category].push(item);
      return acc;
    }, {});

    res.json({ success: true, total: items.length, data: grouped });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/menu/:id
app.get("/api/menu/:id", (req, res) => {
  try {
    const item = dbOne("SELECT * FROM menu_items WHERE id = ?", [req.params.id]);
    if (!item) return res.status(404).json({ success: false, message: "Menu item not found." });
    res.json({ success: true, data: item });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/menu  (admin only)
app.post("/api/menu", authenticate, adminOnly, (req, res) => {
  try {
    const { name, description, category, price } = req.body;
    if (!name || !category || !price)
      return res.status(400).json({ success: false, message: "Name, category, and price are required." });

    const valid = ["starter", "main", "dessert", "drink"];
    if (!valid.includes(category))
      return res.status(400).json({ success: false, message: `Category must be: ${valid.join(", ")}` });

    if (isNaN(price) || price <= 0)
      return res.status(400).json({ success: false, message: "Price must be a positive number." });

    const id = uuidv4();
    dbRun("INSERT INTO menu_items (id, name, description, category, price) VALUES (?, ?, ?, ?, ?)",
      [id, name, description || "", category, parseFloat(price)]);

    res.status(201).json({ success: true, message: "Menu item added.", data: dbOne("SELECT * FROM menu_items WHERE id = ?", [id]) });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// PUT /api/menu/:id  (admin only)
app.put("/api/menu/:id", authenticate, adminOnly, (req, res) => {
  try {
    const item = dbOne("SELECT * FROM menu_items WHERE id = ?", [req.params.id]);
    if (!item) return res.status(404).json({ success: false, message: "Menu item not found." });

    const { name, description, category, price, is_available } = req.body;
    dbRun(
      "UPDATE menu_items SET name=?, description=?, category=?, price=?, is_available=? WHERE id=?",
      [
        name ?? item.name,
        description ?? item.description,
        category ?? item.category,
        price !== undefined ? parseFloat(price) : item.price,
        is_available !== undefined ? (is_available ? 1 : 0) : item.is_available,
        req.params.id,
      ]
    );
    res.json({ success: true, message: "Menu item updated.", data: dbOne("SELECT * FROM menu_items WHERE id = ?", [req.params.id]) });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// DELETE /api/menu/:id  (admin only)
app.delete("/api/menu/:id", authenticate, adminOnly, (req, res) => {
  try {
    const item = dbOne("SELECT * FROM menu_items WHERE id = ?", [req.params.id]);
    if (!item) return res.status(404).json({ success: false, message: "Menu item not found." });
    dbRun("DELETE FROM menu_items WHERE id = ?", [req.params.id]);
    res.json({ success: true, message: `"${item.name}" removed from menu.` });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  TABLE ROUTES  /api/tables
// ─────────────────────────────────────────────────────────────

// GET /api/tables
app.get("/api/tables", authenticate, (req, res) => {
  try {
    const { status } = req.query;
    let sql = "SELECT * FROM restaurant_tables WHERE 1=1";
    const params = [];
    if (status) { sql += " AND status = ?"; params.push(status); }
    sql += " ORDER BY table_number";

    const tables = dbQuery(sql, params);
    res.json({
      success: true,
      summary: {
        total:     tables.length,
        available: tables.filter(t => t.status === "available").length,
        occupied:  tables.filter(t => t.status === "occupied").length,
        reserved:  tables.filter(t => t.status === "reserved").length,
      },
      data: tables,
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/tables/available
app.get("/api/tables/available", authenticate, (req, res) => {
  try {
    const { party_size } = req.query;
    let sql = "SELECT * FROM restaurant_tables WHERE status = 'available'";
    const params = [];
    if (party_size) { sql += " AND capacity >= ?"; params.push(parseInt(party_size)); }
    sql += " ORDER BY capacity";

    const tables = dbQuery(sql, params);
    res.json({ success: true, message: `${tables.length} table(s) available.`, data: tables });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/tables  (admin only)
app.post("/api/tables", authenticate, adminOnly, (req, res) => {
  try {
    const { table_number, capacity, location } = req.body;
    if (!table_number || !capacity)
      return res.status(400).json({ success: false, message: "Table number and capacity are required." });

    if (dbOne("SELECT id FROM restaurant_tables WHERE table_number = ?", [table_number]))
      return res.status(409).json({ success: false, message: `Table ${table_number} already exists.` });

    const id = uuidv4();
    dbRun("INSERT INTO restaurant_tables (id, table_number, capacity, location) VALUES (?, ?, ?, ?)",
      [id, table_number, capacity, location || "main hall"]);

    res.status(201).json({ success: true, message: "Table added.", data: dbOne("SELECT * FROM restaurant_tables WHERE id = ?", [id]) });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// PATCH /api/tables/:id/status
app.patch("/api/tables/:id/status", authenticate, (req, res) => {
  try {
    const { status } = req.body;
    const valid = ["available", "occupied", "reserved"];
    if (!valid.includes(status))
      return res.status(400).json({ success: false, message: `Status must be: ${valid.join(", ")}` });

    const table = dbOne("SELECT * FROM restaurant_tables WHERE id = ?", [req.params.id]);
    if (!table) return res.status(404).json({ success: false, message: "Table not found." });

    dbRun("UPDATE restaurant_tables SET status = ? WHERE id = ?", [status, req.params.id]);
    res.json({ success: true, message: `Table ${table.table_number} is now ${status}.`, data: { ...table, status } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// DELETE /api/tables/:id  (admin only)
app.delete("/api/tables/:id", authenticate, adminOnly, (req, res) => {
  try {
    const table = dbOne("SELECT * FROM restaurant_tables WHERE id = ?", [req.params.id]);
    if (!table) return res.status(404).json({ success: false, message: "Table not found." });
    dbRun("DELETE FROM restaurant_tables WHERE id = ?", [req.params.id]);
    res.json({ success: true, message: `Table ${table.table_number} removed.` });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  RESERVATION ROUTES  /api/reservations
// ─────────────────────────────────────────────────────────────

// GET /api/reservations
app.get("/api/reservations", authenticate, (req, res) => {
  try {
    const { date, status } = req.query;
    let sql = `SELECT r.*, t.table_number, t.capacity
               FROM reservations r
               JOIN restaurant_tables t ON r.table_id = t.id
               WHERE 1=1`;
    const params = [];
    if (date)   { sql += " AND r.reserved_date = ?"; params.push(date); }
    if (status) { sql += " AND r.status = ?";        params.push(status); }
    sql += " ORDER BY r.reserved_date, r.reserved_time";

    const reservations = dbQuery(sql, params);
    res.json({ success: true, total: reservations.length, data: reservations });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/reservations
app.post("/api/reservations", authenticate, (req, res) => {
  try {
    const { table_id, customer_name, customer_phone, party_size, reserved_date, reserved_time, notes } = req.body;

    if (!table_id || !customer_name || !party_size || !reserved_date || !reserved_time)
      return res.status(400).json({ success: false, message: "table_id, customer_name, party_size, reserved_date, and reserved_time are required." });

    const table = dbOne("SELECT * FROM restaurant_tables WHERE id = ?", [table_id]);
    if (!table) return res.status(404).json({ success: false, message: "Table not found." });

    if (party_size > table.capacity)
      return res.status(400).json({ success: false, message: `Table ${table.table_number} seats ${table.capacity} max. Party size is ${party_size}.` });

    if (dbOne("SELECT id FROM reservations WHERE table_id=? AND reserved_date=? AND reserved_time=? AND status='confirmed'",
        [table_id, reserved_date, reserved_time]))
      return res.status(409).json({ success: false, message: `Table ${table.table_number} already reserved on ${reserved_date} at ${reserved_time}.` });

    const id = uuidv4();
    dbRun(`INSERT INTO reservations (id,table_id,customer_name,customer_phone,party_size,reserved_date,reserved_time,notes)
           VALUES (?,?,?,?,?,?,?,?)`,
      [id, table_id, customer_name, customer_phone || "", party_size, reserved_date, reserved_time, notes || ""]);

    dbRun("UPDATE restaurant_tables SET status='reserved' WHERE id=?", [table_id]);

    res.status(201).json({
      success: true,
      message: `Reservation confirmed for ${customer_name} on ${reserved_date} at ${reserved_time}.`,
      data: dbOne("SELECT * FROM reservations WHERE id=?", [id]),
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// PATCH /api/reservations/:id/cancel
app.patch("/api/reservations/:id/cancel", authenticate, (req, res) => {
  try {
    const reservation = dbOne("SELECT * FROM reservations WHERE id=?", [req.params.id]);
    if (!reservation) return res.status(404).json({ success: false, message: "Reservation not found." });
    if (reservation.status === "cancelled")
      return res.status(400).json({ success: false, message: "Already cancelled." });

    dbRun("UPDATE reservations SET status='cancelled' WHERE id=?", [req.params.id]);

    if (!dbOne("SELECT id FROM reservations WHERE table_id=? AND status='confirmed'", [reservation.table_id]))
      dbRun("UPDATE restaurant_tables SET status='available' WHERE id=?", [reservation.table_id]);

    res.json({ success: true, message: "Reservation cancelled. Table is now available." });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  ORDER ROUTES  /api/orders
// ─────────────────────────────────────────────────────────────

// GET /api/orders
app.get("/api/orders", authenticate, (req, res) => {
  try {
    const { status, order_type, date } = req.query;
    let sql = "SELECT * FROM orders WHERE 1=1";
    const params = [];
    if (status)     { sql += " AND status=?";           params.push(status); }
    if (order_type) { sql += " AND order_type=?";       params.push(order_type); }
    if (date)       { sql += " AND DATE(created_at)=?"; params.push(date); }
    sql += " ORDER BY created_at DESC";

    const orders = dbQuery(sql, params).map(order => ({
      ...order,
      items: dbQuery(
        `SELECT oi.*, mi.name as item_name, mi.category
         FROM order_items oi JOIN menu_items mi ON oi.menu_item_id=mi.id
         WHERE oi.order_id=?`, [order.id]
      ),
    }));

    res.json({ success: true, total: orders.length, data: orders });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/orders/:id
app.get("/api/orders/:id", authenticate, (req, res) => {
  try {
    const order = dbOne("SELECT * FROM orders WHERE id=?", [req.params.id]);
    if (!order) return res.status(404).json({ success: false, message: "Order not found." });

    const items = dbQuery(
      `SELECT oi.*, mi.name as item_name, mi.category, mi.description
       FROM order_items oi JOIN menu_items mi ON oi.menu_item_id=mi.id
       WHERE oi.order_id=?`, [order.id]
    );
    res.json({ success: true, data: { ...order, items } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/orders
app.post("/api/orders", authenticate, (req, res) => {
  try {
    const { table_id, order_type = "dine-in", customer_name, notes, items } = req.body;

    if (!items || !Array.isArray(items) || items.length === 0)
      return res.status(400).json({ success: false, message: "Order must include at least one item." });

    if (order_type === "dine-in" && !table_id)
      return res.status(400).json({ success: false, message: "Table ID required for dine-in orders." });

    let totalAmount = 0;
    const validatedItems = [];

    for (const item of items) {
      if (!item.menu_item_id || !item.quantity || item.quantity < 1)
        return res.status(400).json({ success: false, message: "Each item needs a menu_item_id and quantity (min 1)." });

      const menuItem = dbOne("SELECT * FROM menu_items WHERE id=? AND is_available=1", [item.menu_item_id]);
      if (!menuItem)
        return res.status(404).json({ success: false, message: `Item "${item.menu_item_id}" not found or unavailable.` });

      const subtotal = menuItem.price * item.quantity;
      totalAmount += subtotal;
      validatedItems.push({ id: uuidv4(), menu_item_id: item.menu_item_id, quantity: item.quantity, unit_price: menuItem.price, subtotal, name: menuItem.name });
    }

    const orderId = uuidv4();
    dbRun("INSERT INTO orders (id,table_id,order_type,total_amount,customer_name,notes) VALUES (?,?,?,?,?,?)",
      [orderId, table_id || null, order_type, totalAmount, customer_name || "Guest", notes || ""]);

    for (const item of validatedItems)
      dbRun("INSERT INTO order_items (id,order_id,menu_item_id,quantity,unit_price,subtotal) VALUES (?,?,?,?,?,?)",
        [item.id, orderId, item.menu_item_id, item.quantity, item.unit_price, item.subtotal]);

    if (table_id && order_type === "dine-in")
      dbRun("UPDATE restaurant_tables SET status='occupied' WHERE id=?", [table_id]);

    res.status(201).json({
      success: true,
      message: "Order placed!",
      data: {
        order_id: orderId, order_type, status: "pending", total_amount: totalAmount,
        items: validatedItems.map(i => ({ name: i.name, quantity: i.quantity, unit_price: i.unit_price, subtotal: i.subtotal })),
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// PATCH /api/orders/:id/status
app.patch("/api/orders/:id/status", authenticate, (req, res) => {
  try {
    const { status } = req.body;
    const valid = ["pending", "preparing", "ready", "served", "cancelled"];
    if (!valid.includes(status))
      return res.status(400).json({ success: false, message: `Status must be: ${valid.join(", ")}` });

    const order = dbOne("SELECT * FROM orders WHERE id=?", [req.params.id]);
    if (!order) return res.status(404).json({ success: false, message: "Order not found." });

    if (["served", "cancelled"].includes(order.status))
      return res.status(400).json({ success: false, message: `Order already ${order.status}.` });

    dbRun("UPDATE orders SET status=?, updated_at=datetime('now') WHERE id=?", [status, req.params.id]);

    // Free table when last order on it is served
    if (status === "served" && order.table_id) {
      if (!dbOne("SELECT id FROM orders WHERE table_id=? AND status NOT IN ('served','cancelled') AND id!=?",
          [order.table_id, order.id]))
        dbRun("UPDATE restaurant_tables SET status='available' WHERE id=?", [order.table_id]);
    }

    res.json({ success: true, message: `Order status → "${status}".`, data: { order_id: req.params.id, new_status: status } });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// DELETE /api/orders/:id  (pending orders only)
app.delete("/api/orders/:id", authenticate, (req, res) => {
  try {
    const order = dbOne("SELECT * FROM orders WHERE id=?", [req.params.id]);
    if (!order) return res.status(404).json({ success: false, message: "Order not found." });
    if (order.status !== "pending")
      return res.status(400).json({ success: false, message: "Only pending orders can be deleted." });

    dbRun("DELETE FROM order_items WHERE order_id=?", [req.params.id]);
    dbRun("DELETE FROM orders WHERE id=?", [req.params.id]);
    res.json({ success: true, message: "Order deleted." });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  INVENTORY ROUTES  /api/inventory
// ─────────────────────────────────────────────────────────────

// GET /api/inventory
app.get("/api/inventory", authenticate, (req, res) => {
  try {
    const items = dbQuery("SELECT * FROM inventory ORDER BY item_name")
      .map(item => ({ ...item, is_low_stock: item.quantity <= item.low_stock_alert }));
    res.json({ success: true, total_items: items.length, low_stock_alerts: items.filter(i => i.is_low_stock).length, data: items });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/inventory/low-stock
app.get("/api/inventory/low-stock", authenticate, (req, res) => {
  try {
    const items = dbQuery("SELECT * FROM inventory WHERE quantity <= low_stock_alert ORDER BY quantity ASC");
    res.json({ success: true, message: `${items.length} item(s) need restocking.`, data: items });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// POST /api/inventory  (admin only)
app.post("/api/inventory", authenticate, adminOnly, (req, res) => {
  try {
    const { item_name, unit, quantity, low_stock_alert, cost_per_unit } = req.body;
    if (!item_name || !unit)
      return res.status(400).json({ success: false, message: "item_name and unit are required." });

    if (dbOne("SELECT id FROM inventory WHERE item_name=?", [item_name]))
      return res.status(409).json({ success: false, message: `"${item_name}" already in inventory.` });

    const id = uuidv4();
    dbRun("INSERT INTO inventory (id,item_name,unit,quantity,low_stock_alert,cost_per_unit) VALUES (?,?,?,?,?,?)",
      [id, item_name, unit, parseFloat(quantity)||0, parseFloat(low_stock_alert)||10, parseFloat(cost_per_unit)||0]);

    res.status(201).json({ success: true, message: `"${item_name}" added.`, data: dbOne("SELECT * FROM inventory WHERE id=?", [id]) });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// PATCH /api/inventory/:id
app.patch("/api/inventory/:id", authenticate, (req, res) => {
  try {
    const item = dbOne("SELECT * FROM inventory WHERE id=?", [req.params.id]);
    if (!item) return res.status(404).json({ success: false, message: "Inventory item not found." });

    const { quantity, action, low_stock_alert, cost_per_unit } = req.body;
    let newQty = item.quantity;

    if (action === "add" && quantity)      newQty = item.quantity + parseFloat(quantity);
    else if (action === "subtract" && quantity) {
      newQty = item.quantity - parseFloat(quantity);
      if (newQty < 0)
        return res.status(400).json({ success: false, message: `Only ${item.quantity} ${item.unit} in stock.` });
    } else if (quantity !== undefined)     newQty = parseFloat(quantity);

    dbRun("UPDATE inventory SET quantity=?, low_stock_alert=?, cost_per_unit=?, updated_at=datetime('now') WHERE id=?",
      [newQty, low_stock_alert !== undefined ? parseFloat(low_stock_alert) : item.low_stock_alert,
              cost_per_unit  !== undefined ? parseFloat(cost_per_unit)  : item.cost_per_unit, req.params.id]);

    const updated = dbOne("SELECT * FROM inventory WHERE id=?", [req.params.id]);
    const isLow   = updated.quantity <= updated.low_stock_alert;
    res.json({
      success: true,
      message: isLow ? `⚠️ "${item.item_name}" is running low!` : `"${item.item_name}" updated.`,
      data: { ...updated, is_low_stock: isLow },
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// DELETE /api/inventory/:id  (admin only)
app.delete("/api/inventory/:id", authenticate, adminOnly, (req, res) => {
  try {
    const item = dbOne("SELECT * FROM inventory WHERE id=?", [req.params.id]);
    if (!item) return res.status(404).json({ success: false, message: "Inventory item not found." });
    dbRun("DELETE FROM inventory WHERE id=?", [req.params.id]);
    res.json({ success: true, message: `"${item.item_name}" removed.` });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  REPORT ROUTES  /api/reports  (admin only)
// ─────────────────────────────────────────────────────────────

// GET /api/reports/daily-sales
app.get("/api/reports/daily-sales", authenticate, adminOnly, (req, res) => {
  try {
    const date = req.query.date || new Date().toISOString().split("T")[0];

    const summary  = dbOne(
      `SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue,
              AVG(total_amount) as average_order_value,
              SUM(CASE WHEN status='served'    THEN 1 ELSE 0 END) as completed_orders,
              SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) as cancelled_orders
       FROM orders WHERE DATE(created_at)=?`, [date]);

    const byType   = dbQuery(
      `SELECT order_type, COUNT(*) as count, SUM(total_amount) as revenue
       FROM orders WHERE DATE(created_at)=? AND status!='cancelled' GROUP BY order_type`, [date]);

    const topItems = dbQuery(
      `SELECT mi.name, mi.category, SUM(oi.quantity) as total_sold, SUM(oi.subtotal) as revenue
       FROM order_items oi
       JOIN menu_items mi ON oi.menu_item_id=mi.id
       JOIN orders o      ON oi.order_id=o.id
       WHERE DATE(o.created_at)=? AND o.status!='cancelled'
       GROUP BY mi.id ORDER BY total_sold DESC LIMIT 5`, [date]);

    res.json({
      success: true, report_date: date,
      data: {
        summary: { ...summary, total_revenue: summary.total_revenue || 0,
          average_order_value: summary.average_order_value ? parseFloat(summary.average_order_value.toFixed(2)) : 0 },
        by_order_type: byType,
        top_selling_items: topItems,
      },
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/reports/stock-alerts
app.get("/api/reports/stock-alerts", authenticate, adminOnly, (req, res) => {
  try {
    const alerts = dbQuery(
      `SELECT *, ROUND((quantity / low_stock_alert) * 100, 1) as stock_percentage
       FROM inventory WHERE quantity <= low_stock_alert ORDER BY quantity ASC`);
    res.json({
      success: true, alert_count: alerts.length,
      message: alerts.length > 0 ? `⚠️ ${alerts.length} item(s) need restocking!` : "✅ All inventory healthy.",
      data: alerts,
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/reports/orders-summary
app.get("/api/reports/orders-summary", authenticate, adminOnly, (req, res) => {
  try {
    const today     = new Date().toISOString().split("T")[0];
    const startDate = req.query.from || today;
    const endDate   = req.query.to   || today;

    const breakdown = dbQuery(
      `SELECT status, COUNT(*) as count, SUM(total_amount) as total
       FROM orders WHERE DATE(created_at) BETWEEN ? AND ? GROUP BY status`,
      [startDate, endDate]);

    const overall = dbOne(
      `SELECT COUNT(*) as total_orders, SUM(total_amount) as total_revenue
       FROM orders WHERE DATE(created_at) BETWEEN ? AND ? AND status!='cancelled'`,
      [startDate, endDate]);

    res.json({
      success: true, period: { from: startDate, to: endDate },
      data: { total_orders: overall.total_orders || 0, total_revenue: overall.total_revenue || 0, breakdown },
    });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// GET /api/reports/table-utilization
app.get("/api/reports/table-utilization", authenticate, adminOnly, (req, res) => {
  try {
    const date = req.query.date || new Date().toISOString().split("T")[0];
    const data = dbQuery(
      `SELECT t.table_number, t.capacity, t.status,
              COUNT(o.id) as orders_today, SUM(o.total_amount) as revenue_today
       FROM restaurant_tables t
       LEFT JOIN orders o ON t.id=o.table_id AND DATE(o.created_at)=?
       GROUP BY t.id ORDER BY t.table_number`, [date]);

    res.json({ success: true, report_date: date, data });
  } catch (err) {
    res.status(500).json({ success: false, message: err.message });
  }
});

// ─────────────────────────────────────────────────────────────
//  HEALTH CHECK
// ─────────────────────────────────────────────────────────────

app.get("/", (req, res) => {
  res.json({
    message: "🍽️ Restaurant Management System — running!",
    version: "1.0.0",
    endpoints: {
      auth:         "POST /api/auth/register | /api/auth/login",
      menu:         "GET/POST/PUT/DELETE /api/menu",
      tables:       "GET/POST/DELETE /api/tables | PATCH /api/tables/:id/status",
      reservations: "GET/POST /api/reservations | PATCH /api/reservations/:id/cancel",
      orders:       "GET/POST /api/orders | PATCH /api/orders/:id/status",
      inventory:    "GET/POST/PATCH/DELETE /api/inventory | GET /api/inventory/low-stock",
      reports:      "/api/reports/daily-sales | /stock-alerts | /orders-summary | /table-utilization",
    },
  });
});

app.use((req, res) => res.status(404).json({ success: false, message: `Route "${req.originalUrl}" not found.` }));
app.use((err, req, res, next) => { console.error(err.stack); res.status(500).json({ success: false, message: "Server error." }); });

// ─────────────────────────────────────────────────────────────
//  SEED HELPER  (run: node main.js --seed)
// ─────────────────────────────────────────────────────────────

async function seedDatabase() {
  console.log("🌱 Seeding sample data...\n");

  const adminPw = await bcrypt.hash("admin123", 12);
  const staffPw = await bcrypt.hash("staff123", 12);

  for (const [name, email, pw, role] of [
    ["Admin User",   "admin@restaurant.com", adminPw, "admin"],
    ["Staff Member", "staff@restaurant.com", staffPw, "staff"],
  ]) {
    try { dbRun("INSERT INTO users (id,name,email,password,role) VALUES (?,?,?,?,?)", [uuidv4(), name, email, pw, role]); }
    catch { /* already exists */ }
  }
  console.log("✅ Users → admin@restaurant.com / admin123 | staff@restaurant.com / staff123");

  const menuItems = [
    ["Garlic Bread",       "Toasted with garlic butter",             "starter", 4.99],
    ["Caesar Salad",       "Romaine, parmesan, croutons",            "starter", 7.99],
    ["Grilled Chicken",    "Herb-marinated with vegetables",         "main",   14.99],
    ["Beef Burger",        "Angus patty, lettuce, tomato, cheese",   "main",   12.99],
    ["Margherita Pizza",   "Tomato, mozzarella, fresh basil",        "main",   11.99],
    ["Pasta Carbonara",    "Creamy pasta, bacon, parmesan",          "main",   13.49],
    ["Chocolate Lava Cake","Warm cake with vanilla ice cream",       "dessert",  6.49],
    ["Cheesecake",         "New York style with berry compote",      "dessert",  5.99],
    ["Lemonade",           "Fresh squeezed, served with ice",        "drink",    2.99],
    ["Iced Tea",           "Chilled black tea with lemon",           "drink",    2.49],
    ["Sparkling Water",    "500ml bottle",                           "drink",    1.99],
  ];
  let mc = 0;
  for (const [name, desc, cat, price] of menuItems) {
    try { dbRun("INSERT INTO menu_items (id,name,description,category,price) VALUES (?,?,?,?,?)", [uuidv4(), name, desc, cat, price]); mc++; }
    catch { /* skip */ }
  }
  console.log(`✅ ${mc} menu items`);

  const tables = [[1,2,"window"],[2,2,"window"],[3,4,"main hall"],[4,4,"main hall"],[5,6,"main hall"],[6,8,"private room"]];
  let tc = 0;
  for (const [num, cap, loc] of tables) {
    try { dbRun("INSERT INTO restaurant_tables (id,table_number,capacity,location) VALUES (?,?,?,?)", [uuidv4(), num, cap, loc]); tc++; }
    catch { /* skip */ }
  }
  console.log(`✅ ${tc} tables`);

  const inv = [
    ["Chicken Breast","kg",15,5,8],["Beef Mince","kg",8,3,10],["Flour","kg",25,10,1.5],
    ["Mozzarella Cheese","kg",4,5,12],["Tomato Sauce","liters",10,3,3],["Olive Oil","liters",6,2,7],
    ["Eggs","pieces",60,20,0.3],["Lemons","pieces",30,10,0.5],["Coffee Beans","kg",2,3,20],
  ];
  let ic = 0;
  for (const [name, unit, qty, alert, cost] of inv) {
    try { dbRun("INSERT INTO inventory (id,item_name,unit,quantity,low_stock_alert,cost_per_unit) VALUES (?,?,?,?,?,?)", [uuidv4(), name, unit, qty, alert, cost]); ic++; }
    catch { /* skip */ }
  }
  console.log(`✅ ${ic} inventory items`);
  console.log("\n🎉 Done! Run: node main.js\n");
  process.exit(0);
}

// ─────────────────────────────────────────────────────────────
//  BOOT
// ─────────────────────────────────────────────────────────────

initDatabase().then(async () => {
  if (process.argv.includes("--seed")) {
    await seedDatabase();
  } else {
    app.listen(PORT, () => {
      console.log(`\n🚀 http://localhost:${PORT}`);
      console.log(`📦 SQLite — no MySQL needed!`);
      console.log(`💡 First time? Run: node main.js --seed\n`);
    });
  }
}).catch(err => { console.error("Startup failed:", err); process.exit(1); });