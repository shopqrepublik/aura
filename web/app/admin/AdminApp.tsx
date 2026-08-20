"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CircleDot,
  Database,
  Download,
  Eye,
  Landmark,
  LogOut,
  RefreshCw,
  Search,
  Shield,
  Users,
  Zap,
} from "lucide-react";
import { BACKEND_URL } from "@/lib/api";

type Period = "today" | "7d" | "30d" | "90d" | "all";
type JsonRecord = Record<string, unknown>;

interface Dashboard {
  period: { key: string; start: string | null; end: string; previous_start: string | null; previous_end: string | null };
  users: JsonRecord;
  activation: JsonRecord;
  funnel: { stages: Array<JsonRecord>; biggest_dropoff?: JsonRecord | null };
  retention: { d1: number | null; d7: number | null; d30: number | null; cohorts: Array<JsonRecord> };
  recognition: JsonRecord;
  catalog: JsonRecord;
  museums: Array<JsonRecord>;
  top_artworks: Array<JsonRecord>;
  acquisition: { sources?: Array<JsonRecord> };
  segments: JsonRecord;
  system: JsonRecord;
  data_gaps: string[];
  updated_at: string;
}

const nav = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "users", label: "Users", icon: Users },
  { id: "funnel", label: "Funnel", icon: Activity },
  { id: "retention", label: "Retention", icon: RefreshCw },
  { id: "recognition", label: "Recognition", icon: Zap },
  { id: "artworks", label: "Artworks", icon: Eye },
  { id: "catalog", label: "Catalog", icon: Database },
  { id: "museums", label: "Museums", icon: Landmark },
  { id: "acquisition", label: "Acquisition", icon: CircleDot },
  { id: "system", label: "System", icon: Shield },
];

function formatValue(value: unknown) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) return "—";
    if (Math.abs(value) >= 1000) return new Intl.NumberFormat("en-US").format(value);
    return Number.isInteger(value) ? String(value) : String(value);
  }
  if (typeof value === "object") {
    const obj = value as JsonRecord;
    if ("value" in obj) return formatValue(obj.value);
  }
  return String(value);
}

function percent(value: unknown) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return `${value}%`;
}

function numberValue(obj: JsonRecord | undefined, key: string) {
  const value = obj?.[key];
  if (typeof value === "object" && value && "value" in value) return (value as JsonRecord).value;
  return value;
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, { ...init, credentials: "include" });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api("/v1/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      onLogin();
    } catch {
      setError("Invalid admin credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="admin-login-shell">
      <form className="admin-login-card" onSubmit={submit}>
        <div className="admin-brand">ELYIO</div>
        <h1>Control Center</h1>
        <p>Founder analytics, recognition operations and catalog health.</p>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="username" required />
        </label>
        <label>
          Password
          <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" required />
        </label>
        {error && <div className="admin-error">{error}</div>}
        <button disabled={loading}>{loading ? "Signing in..." : "Sign in"}</button>
      </form>
    </main>
  );
}

function Kpi({ label, value, note, accent }: { label: string; value: unknown; note?: string; accent?: boolean }) {
  return (
    <div className={accent ? "admin-kpi admin-kpi-accent" : "admin-kpi"}>
      <span>{label}</span>
      <strong>{formatValue(value)}</strong>
      {note && <small>{note}</small>}
    </div>
  );
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="admin-section">
      <div className="admin-section-title">
        <h2>{title}</h2>
      </div>
      {children}
    </section>
  );
}

function Table({ rows, columns }: { rows: Array<JsonRecord>; columns: Array<{ key: string; label: string }> }) {
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length}>No rows for this period.</td>
            </tr>
          )}
          {rows.map((row, idx) => (
            <tr key={String(row.id ?? row.artwork_id ?? row.event_id ?? idx)}>
              {columns.map((column) => <td key={column.key}>{formatValue(row[column.key])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminApp() {
  const [period, setPeriod] = useState<Period>("30d");
  const [active, setActive] = useState("overview");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [failures, setFailures] = useState<Array<JsonRecord>>([]);
  const [artworks, setArtworks] = useState<Array<JsonRecord>>([]);
  const [users, setUsers] = useState<Array<JsonRecord>>([]);
  const [loading, setLoading] = useState(true);
  const [authed, setAuthed] = useState<boolean | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  const periodLabel = useMemo(() => ({ today: "Today", "7d": "7 days", "30d": "30 days", "90d": "90 days", all: "All time" }[period]), [period]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      await api("/v1/admin/me");
      const data = await api<Dashboard>(`/v1/admin/dashboard?period=${period}`);
      setDashboard(data);
      setFailures((await api<{ rows: Array<JsonRecord> }>(`/v1/admin/recognition/failures?period=${period}&limit=25`)).rows);
      setArtworks((await api<{ rows: Array<JsonRecord> }>(`/v1/admin/artworks?limit=25${search ? `&q=${encodeURIComponent(search)}` : ""}`)).rows);
      setUsers((await api<{ rows: Array<JsonRecord> }>(`/v1/admin/users?limit=25${search ? `&q=${encodeURIComponent(search)}` : ""}`)).rows);
      setAuthed(true);
    } catch (e) {
      if (e instanceof Error && e.message === "unauthorized") setAuthed(false);
      else setError(e instanceof Error ? e.message : "Admin load failed");
    } finally {
      setLoading(false);
    }
  }, [period, search]);

  useEffect(() => {
    const id = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(id);
  }, [load]);

  async function logout() {
    await api("/v1/admin/logout", { method: "POST" }).catch(() => undefined);
    setAuthed(false);
  }

  if (authed === false) return <Login onLogin={load} />;

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div>
          <div className="admin-logo">ELYIO</div>
          <div className="admin-subtitle">Control Center</div>
        </div>
        <nav>
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.id} className={active === item.id ? "active" : ""} onClick={() => setActive(item.id)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <button className="admin-logout" onClick={logout}>
          <LogOut size={16} />
          Logout
        </button>
      </aside>

      <div className="admin-main">
        <header className="admin-topbar">
          <div>
            <h1>ELYIO operating dashboard</h1>
            <p>Real production data. Period: {periodLabel}. Updated {dashboard ? new Date(dashboard.updated_at).toLocaleString() : "—"}.</p>
          </div>
          <div className="admin-actions">
            <div className="admin-periods">
              {(["today", "7d", "30d", "90d", "all"] as Period[]).map((item) => (
                <button key={item} className={period === item ? "selected" : ""} onClick={() => setPeriod(item)}>{item === "all" ? "All" : item}</button>
              ))}
            </div>
            <button className="admin-refresh" onClick={load}><RefreshCw size={16} /> Refresh</button>
          </div>
        </header>

        {loading && <div className="admin-loading">Loading live production metrics...</div>}
        {error && <div className="admin-error">{error}</div>}
        {dashboard && (
          <div className="admin-content">
            <Section id="overview" title="Overview">
              <div className="admin-kpi-grid">
                <Kpi label="Active users" value={numberValue(dashboard.users, "active_users")} note="Meaningful activity" accent />
                <Kpi label="New users" value={dashboard.users.new_users} />
                <Kpi label="Activated users" value={dashboard.activation.activated_users} note={`${percent(dashboard.activation.activation_rate)} activation`} />
                <Kpi label="Returning users" value={dashboard.users.returning_users} note={`${percent(dashboard.users.returning_user_pct)} of active`} />
                <Kpi label="Recognition attempts" value={dashboard.recognition.attempts} />
                <Kpi label="Success rate" value={percent(dashboard.recognition.success_rate)} />
                <Kpi label="Sessions" value={dashboard.users.sessions} />
                <Kpi label="D7 retention" value={percent(dashboard.retention.d7)} />
              </div>
              <div className="admin-two-col">
                <div className="admin-card">
                  <h3>Funnel</h3>
                  <div className="admin-funnel">
                    {dashboard.funnel.stages.map((stage) => (
                      <div key={String(stage.event)} className="admin-funnel-row">
                        <span>{String(stage.label)}</span>
                        <strong>{formatValue(stage.users)}</strong>
                        <em>{stage.from_start_pct ? `${stage.from_start_pct}% of start` : "—"}</em>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="admin-card">
                  <h3>Problems requiring attention</h3>
                  <ul className="admin-warnings">
                    {dashboard.data_gaps.map((gap) => <li key={gap}><AlertTriangle size={15} /> {gap}</li>)}
                    {dashboard.recognition.success_rate !== null && Number(dashboard.recognition.success_rate) < 75 && <li><AlertTriangle size={15} /> Recognition success rate is below 75% for this period.</li>}
                    {Number(dashboard.catalog.works_missing_images) > 0 && <li><AlertTriangle size={15} /> {formatValue(dashboard.catalog.works_missing_images)} active catalog works are missing artwork images.</li>}
                  </ul>
                </div>
              </div>
            </Section>

            <Section id="users" title="Users">
              <div className="admin-kpi-grid compact">
                <Kpi label="Total users" value={dashboard.users.total_users} />
                <Kpi label="Registered" value={dashboard.users.registered_users} />
                <Kpi label="Anonymous" value={dashboard.users.anonymous_visitors} />
                <Kpi label="DAU / MAU" value={dashboard.users.dau_mau} />
              </div>
              <div className="admin-search">
                <Search size={16} />
                <input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void load(); }} placeholder="Search users or artworks" />
                <button onClick={load}>Search</button>
              </div>
              <Table rows={users} columns={[
                { key: "id", label: "User" },
                { key: "type", label: "Type" },
                { key: "email", label: "Email" },
                { key: "first_seen", label: "First seen" },
                { key: "last_seen", label: "Last seen" },
                { key: "sessions", label: "Sessions" },
                { key: "scans", label: "Scans" },
              ]} />
            </Section>

            <Section id="funnel" title="Product funnel">
              <Table rows={dashboard.funnel.stages} columns={[
                { key: "label", label: "Stage" },
                { key: "users", label: "Users" },
                { key: "from_previous_pct", label: "From previous" },
                { key: "from_start_pct", label: "From start" },
              ]} />
            </Section>

            <Section id="retention" title="Retention">
              <div className="admin-kpi-grid compact">
                <Kpi label="D1 retention" value={percent(dashboard.retention.d1)} />
                <Kpi label="D7 retention" value={percent(dashboard.retention.d7)} />
                <Kpi label="D30 retention" value={percent(dashboard.retention.d30)} />
              </div>
              <Table rows={dashboard.retention.cohorts} columns={[
                { key: "cohort", label: "Cohort" },
                { key: "users", label: "Users" },
                { key: "d1", label: "D1 %" },
                { key: "d7", label: "D7 %" },
                { key: "d30", label: "D30 %" },
              ]} />
            </Section>

            <Section id="recognition" title="Recognition">
              <div className="admin-kpi-grid compact">
                <Kpi label="Attempts" value={dashboard.recognition.attempts} />
                <Kpi label="Successful" value={dashboard.recognition.successful} />
                <Kpi label="Failed" value={dashboard.recognition.failed} />
                <Kpi label="No match" value={dashboard.recognition.unknown_no_match} />
                <Kpi label="p50 latency" value={dashboard.recognition.latency_p50_ms ? `${dashboard.recognition.latency_p50_ms} ms` : "—"} />
                <Kpi label="p95 latency" value={dashboard.recognition.latency_p95_ms ? `${dashboard.recognition.latency_p95_ms} ms` : "—"} />
              </div>
              <h3>Failures</h3>
              <Table rows={failures} columns={[
                { key: "timestamp", label: "Time" },
                { key: "museum_id", label: "Museum" },
                { key: "confidence", label: "Confidence" },
                { key: "failure_reason", label: "Reason" },
                { key: "latency_ms", label: "Latency" },
                { key: "status", label: "Status" },
              ]} />
            </Section>

            <Section id="catalog" title="Catalog health">
              <div className="admin-kpi-grid compact">
                <Kpi label="Knowledge catalog" value={dashboard.catalog.knowledge_catalog_total} />
                <Kpi label="Active visitor catalog" value={dashboard.catalog.active_visitor_catalog_total} />
                <Kpi label="VISION_PLUS_ASSET" value={dashboard.catalog.vision_plus_asset} />
                <Kpi label="VISION_READY" value={dashboard.catalog.vision_ready} />
                <Kpi label="NOT_READY" value={dashboard.catalog.not_ready} />
                <Kpi label="Missing images" value={dashboard.catalog.works_missing_images} />
              </div>
            </Section>

            <Section id="museums" title="Museums">
              <Table rows={dashboard.museums} columns={[
                { key: "name", label: "Museum" },
                { key: "city", label: "City" },
                { key: "experience_level", label: "Level" },
                { key: "catalog_size", label: "Catalog" },
                { key: "unique_visitors", label: "Visitors" },
                { key: "scans", label: "Scans" },
                { key: "successful_recognitions", label: "Success" },
                { key: "success_rate", label: "Success %" },
              ]} />
            </Section>

            <Section id="artworks" title="Artworks">
              <div className="admin-card">
                <h3>Top artworks</h3>
                <Table rows={dashboard.top_artworks} columns={[
                  { key: "title", label: "Artwork" },
                  { key: "artist", label: "Artist" },
                  { key: "museum_id", label: "Museum" },
                  { key: "events", label: "Events" },
                ]} />
              </div>
              <div className="admin-card">
                <h3>Artwork explorer</h3>
                <Table rows={artworks} columns={[
                  { key: "title", label: "Artwork" },
                  { key: "artist", label: "Artist" },
                  { key: "museum_id", label: "Museum" },
                  { key: "catalog_status", label: "Catalog" },
                  { key: "recognition_readiness", label: "Vision" },
                  { key: "recognitions", label: "Recognitions" },
                  { key: "last_recognized", label: "Last recognized" },
                ]} />
              </div>
            </Section>

            <Section id="acquisition" title="Acquisition, device and language">
              <div className="admin-two-col">
                <div className="admin-card">
                  <h3>Sources</h3>
                  <Table rows={dashboard.acquisition.sources ?? []} columns={[
                    { key: "source", label: "Source" },
                    { key: "users", label: "Users" },
                  ]} />
                </div>
                <div className="admin-card">
                  <h3>Devices</h3>
                  <Table rows={(dashboard.segments.devices as Array<JsonRecord>) ?? []} columns={[
                    { key: "label", label: "Device" },
                    { key: "events", label: "Events" },
                  ]} />
                </div>
              </div>
            </Section>

            <Section id="system" title="System">
              <div className="admin-kpi-grid compact">
                <Kpi label="API" value={dashboard.system.api_status} />
                <Kpi label="Database" value={dashboard.system.db_status} />
                <Kpi label="Latest recognition" value={dashboard.system.latest_successful_recognition} />
                <Kpi label="Tracking since" value={dashboard.system.tracking_available_since} />
              </div>
              <a className="admin-export" href={`${BACKEND_URL}/v1/admin/export/failures?period=${period}`}><Download size={15} /> Export failures CSV</a>
            </Section>
          </div>
        )}
      </div>
    </main>
  );
}
