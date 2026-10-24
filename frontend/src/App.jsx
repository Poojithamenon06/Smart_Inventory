import { useEffect, useRef, useState } from "react";
import { api, getToken, setToken } from "./api";

const gbp = (n) => "₹" + Number(n).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const day = (s) => new Date(s + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

function useApi(path) {
  const [s, setS] = useState({ data: null, error: "", loading: true });
  useEffect(() => {
    let live = true;
    setS({ data: null, error: "", loading: true });
    api(path)
      .then((data) => live && setS({ data, error: "", loading: false }))
      .catch((e) => live && setS({ data: null, error: e.message, loading: false }));
    return () => { live = false; };
  }, [path]);
  return s;
}
const State = ({ s, children }) =>
  s.loading ? <p className="muted">Loading…</p> : s.error ? <p className="err">{s.error}</p> : children(s.data);

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ username: "", password: "" });
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault(); setErr("");
    try {
      if (mode === "register") await api("/auth/register", { method: "POST", json: f });
      const r = await api("/auth/login", { method: "POST", form: f });
      setToken(r.access_token); onAuth();
    } catch (x) { setErr(x.message); }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <div className="auth">
      <form className="card authbox" onSubmit={submit}>
        <h1>{mode === "login" ? "Sign in" : "Create your account"}</h1>
        <p className="muted">{mode === "login" ? "Use the account you registered for your shop." : "Username 3–30 characters, password 6–72."}</p>
        <label>Username<input value={f.username} onChange={set("username")} required minLength={3} maxLength={30} autoFocus /></label>
        <label>Password<input type="password" value={f.password} onChange={set("password")} required minLength={6} maxLength={72} /></label>
        {err && <p className="err">{err}</p>}
        <button className="btn">{mode === "login" ? "Sign in" : "Register and sign in"}</button>
        <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}>
          {mode === "login" ? "No account yet? Register" : "Have an account? Sign in"}
        </button>
      </form>
    </div>
  );
}

const P = {
  stock: "M12 5v14M5 12h14",
  dash: "M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z",
  inv: "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  sell: "M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2M7 8v8M11 8v8M15 8v8",
  reorder: "M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 3h6v4H9zM9 12h6M9 16h4",
  expiry: "M12 6v6l4 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
  ask: "M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  moon: "M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z",
  sun: "M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4",
  out: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16v-4M12 8h.01",
  rupee: "M6 3h12M6 8h12M6 13l8.5 8M6 13h3a4 4 0 0 0 0-8",
};
const Icon = ({ n, s = 18 }) => (
  <svg width={s} height={s} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={P[n]} /></svg>
);

const Kpi = ({ icon, tone, label, value, note, onClick }) => {
  const T = onClick ? "button" : "div";
  return (
    <T className={"card kpi" + (onClick ? " click" : "")} onClick={onClick}>
      <i className={"ico " + tone}><Icon n={icon} /></i><span>{label}</span><b>{value}</b><small>{note}</small>
    </T>
  );
};

function Trend({ rows }) {
  const W = 600, H = 220, p = 28, max = Math.max(...rows.map((r) => r.revenue)) * 1.1;
  const x = (i) => p + (i * (W - 2 * p)) / Math.max(rows.length - 1, 1);
  const y = (v) => H - p - (Math.max(v, 0) / max) * (H - 2 * p);
  const line = (k) => rows.map((r, i) => `${i ? "L" : "M"}${x(i)},${y(r[k])}`).join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="trend">
      <path d={`${line("revenue")} L${x(rows.length - 1)},${H - p} L${x(0)},${H - p}Z`} fill="var(--blue)" opacity=".12" />
      <path d={line("revenue")} fill="none" stroke="var(--blue)" strokeWidth="3" />
      <path d={line("profit")} fill="none" stroke="var(--amber)" strokeWidth="3" />
      {rows.map((r, i) => (
        <g key={r.sale_date}>
          <circle cx={x(i)} cy={y(r.revenue)} r="4.5" fill="var(--blue)"><title>{`${day(r.sale_date)}: ${gbp(r.revenue)} revenue, ${gbp(r.profit)} profit`}</title></circle>
          <text x={x(i)} y={H - 6} textAnchor="middle" fontSize="11" fill="var(--muted)">{new Date(r.sale_date + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</text>
        </g>
      ))}
    </svg>
  );
}

function Dashboard({ go, name }) {
  const sum = useApi("/summary/daily?days=7");
  const re = useApi("/reorder");
  const ex = useApi("/alerts/expiry");
  const h = new Date().getHours();
  const greet = h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  return (
    <State s={sum}>{(rows) => {
      if (!rows.length) return <p className="muted">No sales recorded yet.</p>;
      const last = rows[rows.length - 1];
      const week = rows.reduce((a, r) => a + r.revenue, 0);
      return (
        <>
          <section className="hero">
            <div><p>{greet}{name ? ", " + name : ""}</p><h1>{gbp(last.revenue)}</h1><p>sold on {day(last.sale_date)} · {last.units} units</p></div>
            <div className="heroside"><span>Last 7 trading days</span><b>{gbp(week)}</b><span>{last.margin_pct}% margin on the latest day</span></div>
          </section>
          <div className="grid3">
            <Kpi icon="rupee" tone="blue" label="Profit, latest day" value={gbp(last.profit)} note="Uses simulated supplier costs" />
            <Kpi icon="reorder" tone="amber" label="Needs reordering" value={re.data ? re.data.length : "…"} note="Open the reorder list" onClick={() => go("reorder")} />
            <Kpi icon="expiry" tone="red" label="Expiring soon" value={ex.data ? ex.data.length : "…"} note="Within the next 30 days" onClick={() => go("expiry")} />
          </div>
          <div className="row">
            <div className="card chart">
              <h2>Revenue and profit</h2>
              <Trend rows={rows} />
              <p className="legend"><i className="b1" /> Revenue <i className="b2" /> Profit</p>
            </div>
            <div className="card pad side2">
              <h2>Needs attention</h2>
              {(re.data || []).slice(0, 4).map((r) => (
                <div key={r.stock_code} className="li"><span>{r.description}</span><span className={"pill " + (r.days_of_cover < 6 ? "bad" : "warn")}>{r.days_of_cover} days left</span></div>
              ))}
              {(ex.data || []).slice(0, 3).map((r) => (
                <div key={r.batch_id} className="li"><span>{r.description}</span><span className={"pill " + (r.days_left < 8 ? "bad" : "warn")}>{r.days_left < 0 ? "expired" : r.days_left + " days to expiry"}</span></div>
              ))}
              {!re.data && !ex.data && <p className="muted">Loading…</p>}
            </div>
          </div>
        </>
      );
    }}</State>
  );
}

function Inventory() {
  const s = useApi("/products");
  const [q, setQ] = useState("");
  const [sort, setSort] = useState({ k: "description", dir: 1 });
  const cols = [["stock_code", "Stock code"], ["description", "Description"], ["unit_price", "Unit price"], ["stock", "Stock"]];
  return (
    <>
      <h1>Inventory</h1>
      <State s={s}>{(rows) => {
        const list = rows
          .filter((r) => (r.stock_code + r.description).toLowerCase().includes(q.toLowerCase()))
          .sort((a, b) => (a[sort.k] > b[sort.k] ? 1 : -1) * sort.dir);
        return (
          <div className="card">
            <div className="bar"><input placeholder="Search by stock code or description" value={q} onChange={(e) => setQ(e.target.value)} /><span className="muted">{list.length} of {rows.length}</span></div>
            <div className="scroll"><table>
              <thead><tr>{cols.map(([k, l]) => <th key={k} onClick={() => setSort({ k, dir: sort.k === k ? -sort.dir : 1 })}>{l}{sort.k === k ? (sort.dir > 0 ? " ↑" : " ↓") : ""}</th>)}</tr></thead>
              <tbody>{list.map((r) => (
                <tr key={r.stock_code}><td>{r.stock_code}</td><td>{r.description}</td><td>{gbp(r.unit_price)}</td>
                  <td>{r.stock} {r.stock < 100 && <span className="pill warn">Low</span>}</td></tr>
              ))}</tbody>
            </table></div>
          </div>
        );
      }}</State>
    </>
  );
}

function Camera({ onCode, onFail }) {
  const v = useRef();
  useEffect(() => {
    let ctl, done = false;
    import("@zxing/browser").then(({ BrowserMultiFormatReader }) =>
      new BrowserMultiFormatReader()
        .decodeFromVideoDevice(undefined, v.current, (res) => { if (res && !done) { done = true; ctl?.stop(); onCode(res.getText()); } })
        .then((c) => { ctl = c; if (done) c.stop(); })
    ).catch(() => onFail("The camera is unavailable or permission was denied."));
    return () => { done = true; ctl?.stop(); };
  }, []);
  return <video ref={v} className="cam" muted playsInline />;
}

function Sell() {
  const prods = useApi("/products");
  const [code, setCode] = useState("");
  const [item, setItem] = useState(null);
  const [qty, setQty] = useState(1);
  const [msg, setMsg] = useState(null);
  const [log, setLog] = useState([]);
  const [cam, setCam] = useState(false);
  const find = (c) => {
    const p = prods.data?.find((x) => x.stock_code.toLowerCase() === c.trim().toLowerCase());
    if (!p) { setItem(null); setMsg({ err: "Product not found" }); } else { setItem(p); setMsg(null); setQty(1); }
  };
  const sell = async () => {
    try {
      const r = await api("/sales", { method: "POST", json: { stock_code: item.stock_code, quantity: Number(qty) } });
      setLog([r, ...log]); setItem({ ...item, stock: r.stock_left });
      setMsg({ ok: `Sold ${r.quantity} × ${r.product} for ${gbp(r.total)}. ${r.stock_left} left.` });
    } catch (e) { setMsg({ err: e.message }); }
  };
  return (
    <>
      <h1>Record a sale</h1>
      <div className="row">
        <div className="card pad grow">
          <form className="bar" onSubmit={(e) => { e.preventDefault(); find(code); }}>
            <input autoFocus placeholder="Scan or type a stock code, e.g. 85123A" value={code} onChange={(e) => setCode(e.target.value)} />
            <button className="btn">Look up</button>
          </form>
          <button className="btn ghost" onClick={() => setCam(!cam)}>{cam ? "Close camera" : "Scan with camera"}</button>
          {cam && <Camera onCode={(c) => { setCode(c); setCam(false); find(c); }} onFail={(t) => { setCam(false); setMsg({ err: t }); }} />}
          {item && (
            <div className="found">
              <div><b>{item.description}</b><p className="muted">{item.stock_code} · {gbp(item.unit_price)} · {item.stock} in stock</p></div>
              <div className="bar"><input type="number" min="1" max="10000" value={qty} onChange={(e) => setQty(e.target.value)} className="qty" /><button className="btn" onClick={sell}>Record sale</button></div>
            </div>
          )}
          {msg?.ok && <p className="ok">{msg.ok}</p>}
          {msg?.err && <p className="err">{msg.err}</p>}
        </div>
        <div className="card pad grow">
          <h2>This session</h2>
          {!log.length ? <p className="muted">No sales yet. Scan a barcode or type a code to start.</p> :
            log.map((r, i) => <p key={i}>{r.quantity} × {r.product} <b>{gbp(r.total)}</b></p>)}
        </div>
      </div>
    </>
  );
}

function Reorder() {
  const s = useApi("/reorder?only_needed=true");
  const csv = (rows) => {
    const keys = Object.keys(rows[0]);
    const text = [keys.join(","), ...rows.map((r) => keys.map((k) => `"${String(r[k]).replace(/"/g, '""')}"`).join(","))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = "reorder.csv"; a.click();
  };
  return (
    <>
      <h1>What to order</h1>
      <State s={s}>{(rows) => !rows.length ? <p className="muted">Nothing needs ordering right now.</p> : (
        <>
          <div className="grid3">
            <div className="card stat"><span>Total order cost</span><b>{gbp(rows.reduce((a, r) => a + r.order_cost, 0))}</b></div>
            <div className="card stat"><span>Products to order</span><b>{rows.length}</b></div>
            <div className="card stat"><span>Units to order</span><b>{rows.reduce((a, r) => a + r.order_qty, 0)}</b></div>
          </div>
          <div className="card"><div className="bar end"><button className="btn ghost" onClick={() => csv(rows)}>Download CSV</button></div>
            <div className="scroll"><table>
              <thead><tr><th>Product</th><th>In stock</th><th>Days of cover</th><th>Reorder point</th><th>Order qty</th><th>Supplier</th><th>Order cost</th></tr></thead>
              <tbody>{rows.map((r) => (
                <tr key={r.stock_code}><td>{r.description}<br /><small className="muted">{r.stock_code}</small></td><td>{r.current_stock}</td>
                  <td><span className={"pill " + (r.days_of_cover < 6 ? "bad" : r.days_of_cover <= 8 ? "warn" : "mid")}>{r.days_of_cover} d</span></td>
                  <td>{r.reorder_point}</td><td><b>{r.order_qty}</b></td><td>{r.supplier}<br /><small className="muted">{r.lead_time_days} day lead time</small></td><td>{gbp(r.order_cost)}</td></tr>
              ))}</tbody>
            </table></div></div>
        </>
      )}</State>
    </>
  );
}

function Expiry() {
  const s = useApi("/alerts/expiry");
  const cls = { expired: "bad", critical: "bad", warning: "warn", watch: "mid" };
  return (
    <>
      <h1>Expiry alerts</h1>
      <State s={s}>{(rows) => !rows.length ? <p className="muted">No batches with an expiry date. Expiry tracking applies only to perishable products such as food or medicine.</p> : (
        <>
          <div className="grid3">
            <div className="card stat"><span>Value at risk</span><b>{gbp(rows.reduce((a, r) => a + r.value_at_risk, 0))}</b></div>
            <div className="card stat"><span>Units at risk</span><b>{rows.reduce((a, r) => a + r.units_at_risk, 0)}</b></div>
            <div className="card stat"><span>Batches flagged</span><b>{rows.length}</b></div>
          </div>
          <div className="card scroll"><table>
            <thead><tr><th>Product</th><th>Batch</th><th>Quantity</th><th>Expires</th><th>Days left</th><th>Status</th><th>Units at risk</th></tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.batch_id}><td>{r.description}<br /><small className="muted">{r.stock_code}</small></td><td>#{r.batch_id}</td><td>{r.quantity}</td>
                <td>{day(r.expiry_date)}</td><td>{r.days_left}</td><td><span className={"pill " + cls[r.status]}>{r.status}</span></td><td>{r.units_at_risk}</td></tr>
            ))}</tbody>
          </table></div>
        </>
      )}</State>
    </>
  );
}

function Ask() {
  const [q, setQ] = useState("");
  const [chat, setChat] = useState([]);
  const send = async (text) => {
    if (!text.trim()) return;
    setChat((c) => [...c, { who: "me", text }]); setQ("");
    try {
      const r = await api("/ask", { method: "POST", json: { question: text } });
      setChat((c) => [...c, { who: "bot", text: r.answer }]);
    } catch (e) { setChat((c) => [...c, { who: "bot", text: e.message, err: true }]); }
  };
  const ideas = ["What should I order tomorrow?", "Which lines are expiring this week?", "What sold best last week?"];
  return (
    <>
      <h1>Ask your shop</h1>
      <div className="card pad">
        <div className="chat">{!chat.length ? <p className="muted">Pick a question below or type your own.</p> :
          chat.map((m, i) => <p key={i} className={"msg " + m.who + (m.err ? " err" : "")}>{m.text}</p>)}</div>
        <div className="chips">{ideas.map((i) => <button key={i} className="chip" onClick={() => send(i)}>{i}</button>)}</div>
        <form className="bar" onSubmit={(e) => { e.preventDefault(); send(q); }}>
          <input placeholder="Ask about your stock or sales" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn">Ask</button>
        </form>
      </div>
    </>
  );
}

function Stock() {
  const [tick, setTick] = useState(0);
  const prods = useApi("/products?v=" + tick);
  const blank = { stock_code: "", description: "", unit_price: "", category: "", perishable: false, shelf: "" };
  const [np, setNp] = useState(blank);
  const [rc, setRc] = useState({ stock_code: "", quantity: "", cost_price: "", expiry_date: "" });
  const [m1, setM1] = useState(null);
  const [m2, setM2] = useState(null);
  const chosen = prods.data?.find((p) => p.stock_code === rc.stock_code);
  const perishable = chosen && chosen.shelf_life_days != null;
  const addProduct = async (e) => {
    e.preventDefault(); setM1(null);
    try {
      await api("/products", { method: "POST", json: {
        stock_code: np.stock_code.trim(), description: np.description.trim(), unit_price: Number(np.unit_price),
        category: np.category || null, shelf_life_days: np.perishable ? Number(np.shelf) : null } });
      setM1({ ok: `${np.description} added. Now receive its first stock on the right.` });
      setRc({ stock_code: np.stock_code.trim(), quantity: "", cost_price: "", expiry_date: "" });
      setNp(blank); setTick(tick + 1);
    } catch (x) { setM1({ err: x.message }); }
  };
  const receive = async (e) => {
    e.preventDefault(); setM2(null);
    try {
      const r = await api("/stock/receive", { method: "POST", json: {
        stock_code: rc.stock_code, quantity: Number(rc.quantity), cost_price: Number(rc.cost_price), expiry_date: rc.expiry_date || null } });
      setM2({ ok: `${r.product}: ${r.stock} units in stock now.` });
      setRc({ stock_code: rc.stock_code, quantity: "", cost_price: "", expiry_date: "" }); setTick(tick + 1);
    } catch (x) { setM2({ err: x.message }); }
  };
  const n = (k) => (e) => setNp({ ...np, [k]: e.target.value });
  const r = (k) => (e) => setRc({ ...rc, [k]: e.target.value });
  return (
    <>
      <h1>Add stock</h1>
      <div className="row">
        <form className="card pad grow form" onSubmit={addProduct}>
          <h2>New product</h2>
          <label className="fld">Stock code or barcode<input value={np.stock_code} onChange={n("stock_code")} required minLength={2} maxLength={30} /></label>
          <label className="fld">Name<input value={np.description} onChange={n("description")} required minLength={2} maxLength={80} /></label>
          <label className="fld">Selling price (₹)<input type="number" min="0.01" step="0.01" value={np.unit_price} onChange={n("unit_price")} required /></label>
          <label className="fld">Category<input list="cats" value={np.category} onChange={n("category")} maxLength={40} />
            <datalist id="cats">{["Dairy", "Bakery", "Produce", "Snacks", "Beverages", "Staples", "Gifts & home"].map((c) => <option key={c} value={c} />)}</datalist></label>
          <label className="fld chk"><input type="checkbox" checked={np.perishable} onChange={(e) => setNp({ ...np, perishable: e.target.checked })} />Perishable (food, medicine)</label>
          {np.perishable && <label className="fld">Shelf life (days)<input type="number" min="1" max="3650" value={np.shelf} onChange={n("shelf")} required /></label>}
          <button className="btn">Add product</button>
          {m1?.ok && <p className="ok">{m1.ok}</p>}{m1?.err && <p className="err">{m1.err}</p>}
        </form>
        <form className="card pad grow form" onSubmit={receive}>
          <h2>Receive stock</h2>
          <label className="fld">Product
            <select value={rc.stock_code} onChange={r("stock_code")} required>
              <option value="">Choose a product</option>
              {(prods.data || []).map((p) => <option key={p.stock_code} value={p.stock_code}>{p.stock_code} · {p.description}</option>)}
            </select></label>
          <label className="fld">Quantity received<input type="number" min="1" value={rc.quantity} onChange={r("quantity")} required /></label>
          <label className="fld">Cost price per unit (₹)<input type="number" min="0.01" step="0.01" value={rc.cost_price} onChange={r("cost_price")} required /></label>
          {perishable
            ? <label className="fld">Expiry date<input type="date" min={new Date().toISOString().slice(0, 10)} value={rc.expiry_date} onChange={r("expiry_date")} required /></label>
            : chosen && <p className="muted">This product does not expire, so no expiry date is needed.</p>}
          <button className="btn" disabled={!rc.stock_code}>Receive stock</button>
          {m2?.ok && <p className="ok">{m2.ok}</p>}{m2?.err && <p className="err">{m2.err}</p>}
        </form>
      </div>
    </>
  );
}

const NAV = [["dash", "Dashboard"], ["inv", "Inventory"], ["stock", "Add stock"], ["sell", "Sell"], ["reorder", "Reorder"], ["expiry", "Expiry"], ["ask", "Ask your shop"]];

function Shell({ onLogout }) {
  const [page, setPage] = useState("dash");
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "light");
  const me = useApi("/auth/me");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  useEffect(() => {
    const close = () => setOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  const name = me.data?.username || "";
  const initial = (name[0] || "?").toUpperCase();
  const Page = { dash: <Dashboard go={setPage} name={name} />, inv: <Inventory />, stock: <Stock />, sell: <Sell />, reorder: <Reorder />, expiry: <Expiry />, ask: <Ask /> }[page];
  return (
    <div className="shell">
      <aside>
        <div className="brand"><i className="logo">S</i>Smart Inventory</div>
        <nav>{NAV.map(([k, l]) => <button key={k} className={page === k ? "on" : ""} onClick={() => setPage(k)}><Icon n={k} />{l}</button>)}</nav>
      </aside>
      <div className="main">
        <header>
          <span className="today">{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</span>
          <div className="profile">
            <button className="avatar" aria-label="Profile menu" onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>{initial}</button>
            {open && (
              <div className="menu" onClick={(e) => e.stopPropagation()}>
                <div className="who"><i className="avatar big">{initial}</i><div><b>{name}</b><p className="muted">Signed in</p></div></div>
                <button className="mi" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}><Icon n={theme === "dark" ? "sun" : "moon"} />{theme === "dark" ? "Light mode" : "Dark mode"}</button>
                <button className="mi" onClick={() => setInfo(!info)}><Icon n="info" />About this data</button>
                {info && <p className="note">Sales come from the Online Retail II dataset, converted to ₹ and re-dated to 2026. Suppliers, costs, stock and expiry dates are simulated.</p>}
                <button className="mi out" onClick={onLogout}><Icon n="out" />Log out</button>
              </div>
            )}
          </div>
        </header>
        <main>{Page}</main>
      </div>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!getToken());
  const out = () => { setToken(null); setAuthed(false); };
  useEffect(() => { window.addEventListener("logout", out); return () => window.removeEventListener("logout", out); }, []);
  return authed ? <Shell onLogout={out} /> : <Auth onAuth={() => setAuthed(true)} />;
}
