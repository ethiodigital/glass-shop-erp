import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker
import json
from datetime import datetime
import uuid
import base64
import io
import zipfile
from urllib.parse import quote
from PIL import Image
from github import Github, GithubException

# ═══════════════════════════════════════════════════════════════
# CONFIG & GLOBAL STYLES
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Abdiglass and ALM Shop ERP",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
:root {
    --brand-dark: #14344F;
    --brand: #2E75B6;
    --brand-light: #D4E6F1;
    --success: #27AE60;
    --warning: #E67E22;
    --danger: #C0392B;
    --muted: #6B7280;
    --bg-soft: #F7F9FC;
}

/* ---------- LARGER, TOUCH-FRIENDLY CONTROLS ---------- */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
.stLinkButton > a {
    min-height: 56px !important;
    font-size: 17px !important;
    font-weight: 600 !important;
    border-radius: 14px !important;
    padding: 0.7rem 1.2rem !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-dark), var(--brand)) !important;
    color: white !important;
    box-shadow: 0 3px 10px rgba(20,52,79,0.25) !important;
}
input, textarea, select {
    font-size: 17px !important;
    min-height: 54px !important;
    border-radius: 12px !important;
}
[data-baseweb="select"] > div {
    min-height: 54px !important;
    font-size: 17px !important;
}
[data-testid="stMetricValue"] { font-size: 26px !important; }
[data-testid="stMetricLabel"] { font-size: 13px !important; }

/* ---------- TABS — CLEANER, BIGGER ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 6px;
    padding: 4px 0;
    border-bottom: 2px solid #E5E7EB;
}
.stTabs [data-baseweb="tab"] {
    min-height: 52px !important;
    font-size: 15px !important;
    padding: 12px 18px !important;
    border-radius: 10px 10px 0 0 !important;
    white-space: nowrap !important;
    font-weight: 600 !important;
}

/* ---------- BRAND HEADER ---------- */
.brand-header {
    background: linear-gradient(135deg, var(--brand-dark), var(--brand));
    color: white;
    padding: 22px 24px;
    margin: -16px -16px 24px -16px;
    border-radius: 0 0 22px 22px;
    box-shadow: 0 6px 20px rgba(20,52,79,0.2);
}
.brand-header .brand {
    display: flex;
    align-items: center;
    gap: 14px;
}
.brand-header .logo {
    font-size: 36px;
    background: rgba(255,255,255,0.15);
    padding: 8px 12px;
    border-radius: 14px;
}
.brand-header .title {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 0.3px;
}
.brand-header .subtitle {
    font-size: 13px;
    opacity: 0.85;
    margin-top: 2px;
}
.brand-header .right {
    text-align: right;
    font-size: 13px;
    opacity: 0.9;
}

/* ---------- PROJECT BANNER (inside Jobs) ---------- */
.project-banner {
    background: white;
    border: 2px solid var(--brand-light);
    border-radius: 16px;
    padding: 18px 22px;
    margin-bottom: 20px;
    box-shadow: 0 2px 10px rgba(20,52,79,0.05);
}
.project-banner .row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
}
.project-banner .label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--muted);
    font-weight: 600;
}
.project-banner .name {
    font-size: 20px;
    font-weight: 800;
    color: var(--brand-dark);
    margin-top: 2px;
}
.project-stats {
    display: flex;
    gap: 22px;
    margin-top: 14px;
    flex-wrap: wrap;
}
.project-stats .stat {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--brand-dark);
}
.project-stats .stat b { font-size: 18px; }
.project-stats .stat .icon { font-size: 20px; }

/* ---------- STATUS PILL ---------- */
.status-pill {
    padding: 8px 18px;
    border-radius: 24px;
    font-size: 14px;
    font-weight: 700;
    display: inline-block;
}
.status-started { background: #DBEAFE; color: #1E40AF; }
.status-ongoing { background: #FEF3C7; color: #92400E; }
.status-completed { background: #D1FAE5; color: #065F46; }

/* ---------- CARDS ---------- */
.big-card {
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 14px;
    transition: all 0.15s ease;
}
.big-card:hover {
    border-color: var(--brand);
    box-shadow: 0 4px 14px rgba(20,52,79,0.08);
}
.big-card .title { font-weight: 700; font-size: 16px; margin-bottom: 6px; color: var(--brand-dark); }
.big-card .meta { color: var(--muted); font-size: 14px; line-height: 1.6; }
.big-card.orange { border-color: #FED7AA; background: #FFF7ED; }
.big-card.red { border-color: #FECACA; background: #FEF2F2; }
.big-card.green { border-color: #A7F3D0; background: #F0FDF4; }

/* ---------- NAV MENU (sidebar) ---------- */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 6px !important;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 17px !important;
    padding: 14px 16px !important;
    border-radius: 12px !important;
    background: #F7F9FC;
    margin-bottom: 4px;
    font-weight: 600 !important;
    border: 2px solid transparent;
    transition: all 0.15s ease;
    cursor: pointer;
}
section[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--brand-light);
}

/* ---------- SECTION TITLE ---------- */
.section-title {
    font-size: 18px;
    font-weight: 800;
    color: var(--brand-dark);
    margin: 26px 0 14px 0;
    letter-spacing: 0.2px;
}

/* ---------- EMPTY STATE ---------- */
.empty-state {
    text-align: center;
    padding: 46px 24px;
    background: var(--bg-soft);
    border-radius: 16px;
    border: 2px dashed #CBD5E1;
    color: var(--muted);
    margin: 20px 0;
}
.empty-state .icon { font-size: 56px; margin-bottom: 12px; }
.empty-state .msg { font-size: 16px; font-weight: 500; }

/* ---------- FEATURE TOGGLE CARD ---------- */
.feature-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: white;
    border: 2px solid #E5E7EB;
    border-radius: 12px;
    margin-bottom: 10px;
}
.feature-row .info { flex: 1; }
.feature-row .info .name { font-weight: 700; font-size: 15px; color: var(--brand-dark); }
.feature-row .info .desc { font-size: 13px; color: var(--muted); margin-top: 2px; }

/* ---------- MOBILE ---------- */
@media (max-width: 768px) {
    .block-container { padding: 0.5rem 0.9rem !important; }
    h1 { font-size: 26px !important; }
    h2 { font-size: 22px !important; }
    h3 { font-size: 18px !important; }
    .brand-header { padding: 16px 18px; margin: -8px -12px 16px -12px; }
    .brand-header .title { font-size: 18px; }
    .brand-header .logo { font-size: 28px; padding: 6px 10px; }
    .project-banner { padding: 14px 16px; }
    .project-banner .name { font-size: 17px; }
    .project-stats { gap: 14px; }
    .project-stats .stat { font-size: 12px; }
    .project-stats .stat b { font-size: 15px; }
    .stButton > button { width: 100% !important; }
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════
DB_FILE_PATH = "shop_erp_data.json"

def get_default_db():
    return {
        "active_project": None,
        "offcut_warning_days": 60,
        "low_stock_thresholds": {"glass_sheets": 3, "aluminum_meters": 20.0, "accessories": 5},
        "settings": {"kerf": 3, "edge_trim": 5},
        "features": {
            "photos": True,
            "offcut_tracking": True,
            "sharing": True,
            "low_stock_alerts": True,
            "stale_offcut_alerts": True,
            "print_mode": True,
            "customer_search": True,
            "auto_save": True,
        },
        "inventory": {"glass": {}, "remnants": [], "aluminum": {}, "accessories": {}},
        "projects": {},
        "recent": {"materials": [], "aluminum": [], "accessories": []},
    }

def migrate_db(db):
    default = get_default_db()
    for key in default:
        if key not in db: db[key] = default[key]
    for key in default["features"]:
        if key not in db.get("features", {}): db.setdefault("features", {})[key] = default["features"][key]
    for key in default["inventory"]:
        if key not in db["inventory"]: db["inventory"][key] = default["inventory"][key]
    if "recent" not in db: db["recent"] = default["recent"]
    if "settings" not in db: db["settings"] = default["settings"]
    for rem in db["inventory"]["remnants"]:
        if "id" not in rem: rem["id"] = str(uuid.uuid4())[:8]
        if "date_added" not in rem: rem["date_added"] = datetime.now().strftime("%Y-%m-%d")
    # Migrate old status values to 3-state
    status_map = {
        "Measured": "Started",
        "Fabricated": "Ongoing",
        "Delivered": "Ongoing",
        "Installed": "Ongoing",
        "Paid": "Completed",
    }
    for name, proj in db["projects"].items():
        s = proj.get("status", "Started")
        if s in status_map:
            proj["status"] = status_map[s]
        if "status" not in proj:
            proj["status"] = "Started"
        if "created" not in proj: proj["created"] = datetime.now().strftime("%Y-%m-%d")
        if "customer" not in proj: proj["customer"] = {"name": "", "phone": "", "address": ""}
        if "photos" not in proj: proj["photos"] = []
        for key in ["glass", "aluminum", "accessories"]:
            if key not in proj: proj[key] = []
    return db

@st.cache_resource
def get_github_client():
    try:
        return Github(st.secrets["github"]["token"])
    except Exception:
        return None

def load_db():
    client = get_github_client()
    if client is None: return get_default_db()
    try:
        repo = client.get_repo(st.secrets["github"]["repo"])
        try:
            f = repo.get_contents(DB_FILE_PATH)
            return migrate_db(json.loads(base64.b64decode(f.content).decode("utf-8")))
        except GithubException as e:
            if e.status == 404:
                d = get_default_db(); save_db(d, silent=True); return d
            raise
    except Exception as e:
        st.warning(f"⚠️ Load failed: {e}")
        return get_default_db()

def save_db(db, silent=False):
    if not db.get("features", {}).get("auto_save", True) and not silent:
        return True
    client = get_github_client()
    if client is None: return False
    try:
        repo = client.get_repo(st.secrets["github"]["repo"])
        content = json.dumps(db, indent=4)
        msg = f"Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        try:
            f = repo.get_contents(DB_FILE_PATH)
            repo.update_file(DB_FILE_PATH, msg, content, f.sha)
        except GithubException as e:
            if e.status == 404: repo.create_file(DB_FILE_PATH, msg, content)
            else: raise
        if not silent: st.toast("💾 Saved", icon="✅")
        return True
    except Exception as e:
        if not silent: st.error(f"❌ Save failed: {e}")
        return False

if "db" not in st.session_state:
    st.session_state.db = load_db()
db = st.session_state.db
feat = db.get("features", {})

# ═══════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════
def remember_recent(cat, val):
    if not val: return
    lst = db["recent"][cat]
    if val in lst: lst.remove(val)
    lst.insert(0, val)
    db["recent"][cat] = lst[:5]

def days_old(date_str):
    try:
        return (datetime.now().date() - datetime.strptime(date_str, "%Y-%m-%d").date()).days
    except Exception:
        return 0

def offcut_badge(days, warn):
    if days >= int(warn * 1.5): return f"🔴 {days}d", "red"
    if days >= warn:            return f"🟠 {days}d", "orange"
    if days >= warn / 2:        return f"🟡 {days}d", ""
    return f"🟢 {days}d", ""

def get_stale_offcuts():
    if not feat.get("stale_offcut_alerts", True): return []
    warn = db.get("offcut_warning_days", 60)
    stale = [r for r in db["inventory"]["remnants"] if days_old(r.get("date_added", "")) >= warn]
    return sorted(stale, key=lambda r: r.get("date_added", ""))

def compress_image(uploaded_file, max_w=1000, quality=65):
    try:
        img = Image.open(uploaded_file)
        if img.mode != "RGB": img = img.convert("RGB")
        if img.width > max_w:
            r = max_w / img.width
            img = img.resize((max_w, int(img.height * r)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None

def render_sheet_png(abin, kerf, title_prefix="Sheet"):
    fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
    ax.set_xlim(0, abin.width + 5); ax.set_ylim(0, abin.height + 5)
    ax.set_aspect("equal")
    ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor="black", linewidth=2))
    used = 0
    for rect in abin:
        ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width - kerf, rect.height - kerf,
                                        facecolor="#D4E6F1", edgecolor="#1F4E79", linewidth=1.5))
        ax.text(rect.x + (rect.width - kerf) / 2, rect.y + (rect.height - kerf) / 2,
                f"{int(rect.width - kerf)}×{int(rect.height - kerf)}\n{rect.rid}",
                ha="center", va="center", fontsize=11,
                rotation=90 if rect.height > rect.width else 0,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9))
        used += (rect.width - kerf) * (rect.height - kerf)
    waste = ((abin.width * abin.height - used) / (abin.width * abin.height)) * 100
    plt.title(f"{title_prefix} | {abin.bid}\nSize: {int(abin.width)} × {int(abin.height)} mm  |  Waste: {waste:.1f}%", fontsize=12)
    plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    return buf.getvalue()

def empty_state(icon, msg):
    st.markdown(f'<div class="empty-state"><div class="icon">{icon}</div><div class="msg">{msg}</div></div>', unsafe_allow_html=True)

def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# PRINT MODE (early exit)
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("print_mode") and st.session_state.get("generated_bins"):
    st.markdown("""
    <style>
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        footer, .stButton, .stCheckbox, .stAlert, .stLinkButton { display: none !important; }
        .main .block-container { padding: 0 !important; max-width: 100% !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.title("🖨️ Cutting Sheet")
    st.caption(f"Project: **{db.get('active_project', 'N/A')}** — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if st.button("✖ Exit Print Mode", width="stretch"):
        st.session_state.print_mode = False; st.rerun()
    st.divider()
    kerf = st.session_state.get("print_kerf", 3)
    for i, abin in enumerate(st.session_state.generated_bins):
        st.image(render_sheet_png(abin, kerf, f"Sheet {i+1}"), use_column_width=True)
        st.markdown("---")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# BRAND HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="brand-header">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div class="brand">
            <div class="logo">🏭</div>
            <div>
                <div class="title">Abdiglass and ALM Shop ERP</div>
                <div class="subtitle">Glass & Aluminum Fabrication Management</div>
            </div>
        </div>
        <div class="right">
            {datetime.now().strftime('%A, %d %b %Y')}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    nav = st.radio(
        "Navigate",
        ["🏠 Dashboard", "📦 Warehouse", "🛠️ Jobs", "📊 Reports", "⚙️ Settings"],
        label_visibility="collapsed",
        key="nav"
    )
    st.divider()

    # Alerts (compact)
    if feat.get("low_stock_alerts", True):
        alerts = []
        for m, s in db["inventory"]["glass"].items():
            if sum(s.values()) <= db["low_stock_thresholds"]["glass_sheets"]:
                alerts.append(f"🪟 {m}")
        for p, mm in db["inventory"]["aluminum"].items():
            if mm <= db["low_stock_thresholds"]["aluminum_meters"]:
                alerts.append(f"📏 {p}")
        for i, q in db["inventory"]["accessories"].items():
            if q <= db["low_stock_thresholds"]["accessories"]:
                alerts.append(f"🔧 {i}")

        if alerts:
            with st.expander(f"🚨 Low Stock ({len(alerts)})"):
                for a in alerts: st.write(a)

    stale = get_stale_offcuts()
    if stale:
        with st.expander(f"⏰ Stale Offcuts ({len(stale)})"):
            warn = db.get("offcut_warning_days", 60)
            for r in stale[:8]:
                age = days_old(r.get("date_added", ""))
                badge = "🔴" if age >= warn * 1.5 else "🟠"
                st.write(f"{badge} {r['material']} {r['width']}×{r['height']} ({age}d)")

    st.divider()
    with st.expander("🔄 Data"):
        if st.button("🔄 Reload from Cloud", width="stretch"):
            get_github_client.clear()
            st.session_state.db = load_db(); st.rerun()
        st.download_button("📥 Backup", json.dumps(db, indent=4),
                            f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                            "application/json", width="stretch")

# ═══════════════════════════════════════════════════════════════
# MODULE — 🏠 DASHBOARD
# ═══════════════════════════════════════════════════════════════
if nav == "🏠 Dashboard":
    st.markdown("## 🏠 Dashboard")

    # Quick stats
    total_projects = len(db["projects"])
    active_count = sum(1 for p in db["projects"].values() if p.get("status") in ["Started", "Ongoing"])
    completed_count = sum(1 for p in db["projects"].values() if p.get("status") == "Completed")
    glass_sheets = sum(sum(s.values()) for s in db["inventory"]["glass"].values())
    aluminum_m = sum(db["inventory"]["aluminum"].values())
    offcut_count = len(db["inventory"]["remnants"])

    c1, c2, c3 = st.columns(3)
    c1.metric("📁 Active Jobs", active_count)
    c2.metric("✅ Completed", completed_count)
    c3.metric("✂️ Offcuts", offcut_count)

    c1, c2, c3 = st.columns(3)
    c1.metric("🪟 Glass Sheets", glass_sheets)
    c2.metric("📏 Aluminum (m)", f"{aluminum_m:.1f}")
    c3.metric("🔧 Accessory Items", len(db["inventory"]["accessories"]))

    st.divider()

    # Quick actions
    section_title("⚡ Quick Actions")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ Create New Job", type="primary", width="stretch"):
            st.session_state.nav = "🛠️ Jobs"
            st.session_state.show_new_project = True
            st.rerun()
    with c2:
        if st.button("📦 Add Stock", width="stretch"):
            st.session_state.nav = "📦 Warehouse"
            st.rerun()

    # Recent projects
    section_title("🕒 Recent Jobs")
    if db["projects"]:
        recent = sorted(db["projects"].items(),
                        key=lambda x: x[1].get("created", ""), reverse=True)[:5]
        for name, p in recent:
            status = p.get("status", "Started")
            pill_class = {"Started": "status-started", "Ongoing": "status-ongoing",
                          "Completed": "status-completed"}.get(status, "status-started")
            cust = p.get("customer", {}).get("name", "—")
            st.markdown(f"""<div class="big-card">
            <div style="display:flex; justify-content:space-between; align-items:start; gap:12px;">
                <div style="flex:1;">
                    <div class="title">🏗️ {name}</div>
                    <div class="meta">👤 {cust} · Glass: {len(p['glass'])} · Alum: {sum(a['Meters'] for a in p['aluminum']):.1f}m</div>
                </div>
                <span class="status-pill {pill_class}">{status}</span>
            </div>
            </div>""", unsafe_allow_html=True)
    else:
        empty_state("📋", "No jobs yet. Create your first job to get started.")

# ═══════════════════════════════════════════════════════════════
# MODULE — 📦 WAREHOUSE
# ═══════════════════════════════════════════════════════════════
elif nav == "📦 Warehouse":
    st.markdown("## 📦 Warehouse")
    st.caption("Physical stock in your shop")

    wtab1, wtab2 = st.tabs(["👁️ View Stock", "➕ Receive Stock"])

    with wtab1:
        search = st.text_input("🔍 Search", placeholder="Search materials...")

        # Stale offcuts
        stale = get_stale_offcuts()
        if stale and not search and feat.get("offcut_tracking", True):
            section_title(f"⏰ Stale Offcuts ({len(stale)})")
            st.caption(f"Older than {db['offcut_warning_days']} days — oldest first.")
            for r in stale:
                age = days_old(r.get("date_added", ""))
                _, css = offcut_badge(age, db["offcut_warning_days"])
                st.markdown(f"""<div class="big-card {css}">
                <div class="title">{r['material']} — {r['width']}×{r['height']} mm</div>
                <div class="meta">Age: <b>{age} days</b> · Added: {r.get('date_added','-')}</div>
                </div>""", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ Scrap", key=f"sc_{r['id']}", width="stretch"):
                        db["inventory"]["remnants"] = [x for x in db["inventory"]["remnants"] if x["id"] != r["id"]]
                        save_db(db); st.rerun()
                with c2:
                    if st.button("✅ Keep 30d", key=f"kp_{r['id']}", width="stretch"):
                        r["date_added"] = datetime.now().strftime("%Y-%m-%d")
                        save_db(db); st.rerun()

        section_title("🪟 Glass Sheets")
        if db["inventory"]["glass"]:
            for mat, sizes in db["inventory"]["glass"].items():
                if search and search.lower() not in mat.lower(): continue
                total = sum(sizes.values())
                is_low = total <= db["low_stock_thresholds"]["glass_sheets"]
                badge = "🔴 Low" if is_low else "🟢 In Stock"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="big-card {css}">
                <div class="title">{badge} — {mat}</div>
                <div class="meta">2140×3300: <b>{sizes.get('2140 x 3300',0)}</b> · 2140×3660: <b>{sizes.get('2140 x 3660',0)}</b> · Total: <b>{total}</b></div>
                </div>""", unsafe_allow_html=True)
        else: empty_state("🪟", "No glass in stock.")

        if feat.get("offcut_tracking", True):
            section_title("✂️ All Offcuts")
            if db["inventory"]["remnants"]:
                for r in sorted(db["inventory"]["remnants"], key=lambda x: x.get("date_added", "")):
                    age = days_old(r.get("date_added", ""))
                    label, css = offcut_badge(age, db["offcut_warning_days"])
                    st.markdown(f"""<div class="big-card {css}">
                    <div class="title">{r['material']}</div>
                    <div class="meta">{r['width']}×{r['height']} mm · Age: <b>{label}</b> · {r.get('date_added','-')}</div>
                    </div>""", unsafe_allow_html=True)
            else: empty_state("✂️", "No offcuts tracked.")

        section_title("📏 Aluminum Profiles")
        if db["inventory"]["aluminum"]:
            for k, v in db["inventory"]["aluminum"].items():
                is_low = v <= db["low_stock_thresholds"]["aluminum_meters"]
                badge = "🔴 Low" if is_low else "🟢 OK"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="big-card {css}">
                <div class="title">{badge} — {k}</div>
                <div class="meta"><b>{v:.2f} m</b> available</div>
                </div>""", unsafe_allow_html=True)
        else: empty_state("📏", "No aluminum in stock.")

        section_title("🔧 Accessories")
        if db["inventory"]["accessories"]:
            for k, v in db["inventory"]["accessories"].items():
                is_low = v <= db["low_stock_thresholds"]["accessories"]
                badge = "🔴 Low" if is_low else "🟢 OK"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="big-card {css}">
                <div class="title">{badge} — {k}</div>
                <div class="meta"><b>{v}</b> pcs</div>
                </div>""", unsafe_allow_html=True)
        else: empty_state("🔧", "No accessories in stock.")

    with wtab2:
        section_title("🪟 Add Glass Sheets")
        with st.form("add_glass", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Material", ["-- New --"] + db["recent"]["materials"])
                gm = st.text_input("New name", placeholder="e.g., 6mm Clear") if ch == "-- New --" else ch
            with c2:
                gsz = st.selectbox("Sheet Size", ["2140 x 3300", "2140 x 3660"])
                gq = st.number_input("Qty", min_value=1, step=1, value=1)
            if st.form_submit_button("➕ Add Glass", type="primary", width="stretch"):
                if not gm or not gm.strip():
                    st.error("Enter a name.")
                else:
                    gm = gm.strip()
                    if gm not in db["inventory"]["glass"]:
                        db["inventory"]["glass"][gm] = {"2140 x 3300": 0, "2140 x 3660": 0}
                    db["inventory"]["glass"][gm][gsz] += gq
                    remember_recent("materials", gm)
                    save_db(db); st.rerun()

        if feat.get("offcut_tracking", True):
            section_title("✂️ Add Offcut")
            if db["inventory"]["glass"]:
                with st.form("add_rem", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        rm = st.selectbox("Material", list(db["inventory"]["glass"].keys()))
                        rw = st.number_input("Width (mm)", min_value=100, step=10, value=1000)
                    with c2:
                        rh = st.number_input("Height (mm)", min_value=100, step=10, value=1000)
                    if st.form_submit_button("➕ Add Offcut", type="primary", width="stretch"):
                        db["inventory"]["remnants"].append({
                            "id": str(uuid.uuid4())[:8], "material": rm,
                            "width": rw, "height": rh,
                            "date_added": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.rerun()
            else:
                st.info("Add glass first.")

        section_title("📏 Add Aluminum")
        with st.form("add_alum", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Profile", ["-- New --"] + db["recent"]["aluminum"])
                apr = st.text_input("New profile", placeholder="e.g., 60mm Frame") if ch == "-- New --" else ch
            with c2:
                am = st.number_input("Meters", min_value=1.0, step=1.0, value=6.0)
            if st.form_submit_button("➕ Add Aluminum", type="primary", width="stretch"):
                if not apr or not apr.strip():
                    st.error("Enter a name.")
                else:
                    apr = apr.strip()
                    db["inventory"]["aluminum"][apr] = db["inventory"]["aluminum"].get(apr, 0) + am
                    remember_recent("aluminum", apr)
                    save_db(db); st.rerun()

        section_title("🔧 Add Accessory")
        with st.form("add_acc", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Item", ["-- New --"] + db["recent"]["accessories"])
                ac = st.text_input("New item", placeholder="e.g., Door Handles") if ch == "-- New --" else ch
            with c2:
                aq = st.number_input("Qty", min_value=1, step=1, value=1)
            if st.form_submit_button("➕ Add Accessory", type="primary", width="stretch"):
                if not ac or not ac.strip():
                    st.error("Enter a name.")
                else:
                    ac = ac.strip()
                    db["inventory"]["accessories"][ac] = db["inventory"]["accessories"].get(ac, 0) + aq
                    remember_recent("accessories", ac)
                    save_db(db); st.rerun()

# ═══════════════════════════════════════════════════════════════
# MODULE — 🛠️ JOBS
# ═══════════════════════════════════════════════════════════════
elif nav == "🛠️ Jobs":
    st.markdown("## 🛠️ Jobs")

    # Show create option first if requested
    if st.session_state.get("show_new_project"):
        with st.expander("➕ Create New Job", expanded=True):
            new_proj = st.text_input("Job Name", placeholder="e.g., Villa 4 - Bole")
            if st.button("Create Job", type="primary", width="stretch"):
                if not new_proj or not new_proj.strip():
                    st.error("Enter a name.")
                elif new_proj.strip() in db["projects"]:
                    st.error("Already exists.")
                else:
                    db["projects"][new_proj.strip()] = {
                        "status": "Started",
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "customer": {"name": "", "phone": "", "address": ""},
                        "photos": [], "glass": [], "aluminum": [], "accessories": [],
                    }
                    db["active_project"] = new_proj.strip()
                    save_db(db)
                    st.session_state.show_new_project = False
                    st.rerun()
        st.divider()

    # Project selector
    project_names = list(db["projects"].keys())
    if not project_names:
        empty_state("🛠️", "No jobs yet.")
        with st.expander("➕ Create your first job", expanded=True):
            new_proj = st.text_input("Job Name")
            if st.button("Create Job", type="primary", width="stretch"):
                if new_proj and new_proj.strip():
                    db["projects"][new_proj.strip()] = {
                        "status": "Started",
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "customer": {"name": "", "phone": "", "address": ""},
                        "photos": [], "glass": [], "aluminum": [], "accessories": [],
                    }
                    db["active_project"] = new_proj.strip()
                    save_db(db); st.rerun()
        st.stop()

    if db["active_project"] not in project_names:
        db["active_project"] = project_names[0]

    # Project selector + create button
    col1, col2 = st.columns([3, 1])
    with col1:
        selected = st.selectbox(
            "🎯 Choose Job",
            project_names,
            index=project_names.index(db["active_project"]) if db["active_project"] in project_names else 0,
        )
        if selected != db["active_project"]:
            db["active_project"] = selected
            save_db(db, silent=True); st.rerun()
    with col2:
        st.write(""); st.write("")
        if st.button("➕ New", width="stretch"):
            st.session_state.show_new_project = True
            st.rerun()

    proj = db["projects"][db["active_project"]]

    # ---- Project banner ----
    status = proj.get("status", "Started")
    pill_class = {"Started": "status-started", "Ongoing": "status-ongoing",
                  "Completed": "status-completed"}.get(status, "status-started")
    cust = proj.get("customer", {})
    glass_count = len(proj["glass"])
    alum_m = sum(a["Meters"] for a in proj["aluminum"])
    acc_qty = sum(a["Qty"] for a in proj["accessories"])

    st.markdown(f"""
    <div class="project-banner">
        <div class="row">
            <div style="flex:1; min-width:200px;">
                <div class="label">Active Job</div>
                <div class="name">🏗️ {db['active_project']}</div>
            </div>
            <span class="status-pill {pill_class}">{status}</span>
        </div>
        <div class="project-stats">
            <div class="stat"><span class="icon">🪟</span><b>{glass_count}</b> pieces</div>
            <div class="stat"><span class="icon">📏</span><b>{alum_m:.1f}</b> m</div>
            <div class="stat"><span class="icon">🔧</span><b>{acc_qty}</b> items</div>
            <div class="stat"><span class="icon">👤</span>{cust.get('name') or 'No customer'}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Status buttons (3 states) ----
    section_title("📌 Job Status")
    STATUS_OPTIONS = ["Started", "Ongoing", "Completed"]
    cols = st.columns(3)
    status_icons = {"Started": "🟢", "Ongoing": "🟠", "Completed": "✅"}
    for i, s in enumerate(STATUS_OPTIONS):
        with cols[i]:
            is_act = (s == status)
            if st.button(f"{status_icons[s]} {s}", key=f"st_{s}", width="stretch",
                         type="primary" if is_act else "secondary"):
                proj["status"] = s
                save_db(db); st.rerun()

    st.divider()

    # ---- Project tabs ----
    pt1, pt2, pt3, pt4, pt5 = st.tabs(["📋 Info", "🪟 Cut Glass", "📦 Materials", "📸 Photos", "📜 History"])

    # ---- INFO TAB ----
    with pt1:
        section_title("👤 Customer Information")
        cname = st.text_input("Customer Name", value=cust.get("name", ""))
        cphone = st.text_input("Phone", value=cust.get("phone", ""))
        caddr = st.text_input("Site Address", value=cust.get("address", ""))
        if st.button("💾 Save Customer", type="primary", width="stretch"):
            proj["customer"] = {"name": cname, "phone": cphone, "address": caddr}
            save_db(db); st.success("Saved!")

        if cphone and feat.get("sharing", True):
            phone_clean = cphone.replace(" ", "").replace("-", "")
            wa_msg = quote(f"Hello {cname or ''}, regarding your project {db['active_project']}...")
            st.link_button("📱 Message on WhatsApp", f"https://wa.me/{phone_clean}?text={wa_msg}",
                            width="stretch")

        st.divider()
        with st.expander("⚠️ Danger Zone"):
            if st.button("🗑️ Delete This Job", type="secondary", width="stretch"):
                del db["projects"][db["active_project"]]
                db["active_project"] = None
                save_db(db); st.rerun()

    # ---- CUT GLASS TAB ----
    with pt2:
        if not db["inventory"]["glass"]:
            empty_state("🪟", "No glass in warehouse. Add stock first.")
        else:
            mats = list(db["inventory"]["glass"].keys())

            # Settings (kerf, edge trim)
            with st.expander("⚙️ Cutting Settings"):
                c1, c2 = st.columns(2)
                with c1:
                    kerf = st.number_input("Blade Kerf (mm)",
                                            value=int(db["settings"].get("kerf", 3)), step=1)
                with c2:
                    etrim = st.number_input("Edge Trim (mm)",
                                             value=int(db["settings"].get("edge_trim", 5)), step=1)
                if kerf != db["settings"]["kerf"] or etrim != db["settings"]["edge_trim"]:
                    db["settings"]["kerf"] = kerf
                    db["settings"]["edge_trim"] = etrim
                    save_db(db, silent=True)

            if "form_list" not in st.session_state:
                st.session_state.form_list = []

            section_title("➕ Add a Piece")
            with st.form("add_piece", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    loc = st.text_input("Location", placeholder="e.g., Door 1")
                    mat = st.selectbox("Material", mats)
                with c2:
                    w = st.number_input("Width (mm)", min_value=1, step=10, value=1000)
                    h = st.number_input("Height (mm)", min_value=1, step=10, value=2000)
                q = st.number_input("Quantity", min_value=1, step=1, value=1)
                if st.form_submit_button("➕ Add Piece", type="primary", width="stretch"):
                    st.session_state.form_list.append({
                        "Location": loc or "Unnamed", "Material": mat,
                        "Width": w, "Height": h, "Quantity": q})
                    st.rerun()

            if st.session_state.form_list:
                section_title(f"📝 Pieces ({len(st.session_state.form_list)})")
                for i, item in enumerate(st.session_state.form_list):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"""<div class="big-card">
                        <div class="title">{item['Location']}</div>
                        <div class="meta">{item['Material']} — {item['Width']}×{item['Height']} mm × {item['Quantity']}</div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"dl_{i}", width="stretch"):
                            st.session_state.form_list.pop(i); st.rerun()

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ Clear All", width="stretch"):
                        st.session_state.form_list = []; st.rerun()
                with c2:
                    if st.button("🚀 Generate Cutting Plan", type="primary", width="stretch"):
                        df = pd.DataFrame(st.session_state.form_list)
                        bins = []
                        stock = {"2140 x 3300": (2140-etrim, 3300-etrim),
                                 "2140 x 3660": (2140-etrim, 3660-etrim)}
                        for material in df["Material"].unique():
                            mdf = df[df["Material"] == material]
                            p = newPacker(rotation=True)

                            # Add offcuts (oldest first) if feature enabled
                            if feat.get("offcut_tracking", True):
                                mat_remnants = [r for r in db["inventory"].get("remnants", []) if r["material"] == material]
                                mat_remnants.sort(key=lambda r: r.get("date_added", "9999-99-99"))
                                for rem in mat_remnants:
                                    p.add_bin(rem["width"]-etrim, rem["height"]-etrim,
                                              bid=f"REMNANT|{rem['id']}|{rem['width']}x{rem['height']}")

                            for sn, d in stock.items():
                                for _ in range(db["inventory"]["glass"][material].get(sn, 0)):
                                    p.add_bin(d[0], d[1], bid=f"{material}|{sn}")
                            for _, row in mdf.iterrows():
                                for _ in range(int(row["Quantity"])):
                                    p.add_rect(float(row["Width"])+kerf, float(row["Height"])+kerf,
                                               rid=row["Location"])
                            p.pack()
                            valid = [b for b in p if len(b) > 0]
                            if not valid and not mdf.empty:
                                st.error(f"❌ Not enough {material}!"); continue
                            for abin in valid:
                                if abin.bid.startswith("REMNANT|"):
                                    parts = abin.bid.split("|")
                                    db["inventory"]["remnants"] = [r for r in db["inventory"]["remnants"] if r["id"] != parts[1]]
                                else:
                                    _, stype = abin.bid.split("|")
                                    db["inventory"]["glass"][material][stype] -= 1
                                for rect in abin:
                                    proj["glass"].append({
                                        "Material": material,
                                        "Size": f"{int(rect.width-kerf)}x{int(rect.height-kerf)}",
                                        "Location": rect.rid,
                                        "Date": datetime.now().strftime("%Y-%m-%d")})
                            bins.extend(valid)
                        save_db(db)
                        st.session_state.generated_bins = bins
                        st.session_state.print_kerf = kerf
                        st.session_state.form_list = []
                        st.rerun()
            else:
                empty_state("📐", "Add pieces above to start cutting.")

            # Cutting maps
            if st.session_state.get("generated_bins"):
                st.divider()
                section_title("🗺️ Cutting Plan")

                c1, c2 = st.columns(2)
                with c1:
                    if feat.get("print_mode", True):
                        if st.button("🖨️ Print Mode", type="primary", width="stretch"):
                            st.session_state.print_mode = True; st.rerun()
                with c2:
                    if st.button("✅ Done Cutting", width="stretch"):
                        st.session_state.generated_bins = []; st.rerun()

                # Sharing
                if feat.get("sharing", True):
                    proj_label = db["active_project"]
                    pieces_summary = " | ".join([f"{g['Location']}:{g['Size']}" for g in proj["glass"][-20:]])
                    share_text = f"🪟 Cutting Plan — {proj_label}\n{len(st.session_state.generated_bins)} sheet(s). Pieces: {pieces_summary[:200]}"
                    enc = quote(share_text)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.link_button("📱 WhatsApp", f"https://wa.me/?text={enc}", width="stretch")
                    with c2:
                        st.link_button("✈️ Telegram", f"https://t.me/share/url?url=&text={enc}", width="stretch")

                # Download zip
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, abin in enumerate(st.session_state.generated_bins):
                        zf.writestr(f"Sheet{i+1}.png", render_sheet_png(abin, kerf, f"Sheet {i+1}"))
                st.download_button("📥 Download All Sheets (.zip)", zip_buf.getvalue(),
                                    f"{db['active_project']}_CuttingSheets.zip",
                                    "application/zip", width="stretch")

                # Per sheet
                for i, abin in enumerate(st.session_state.generated_bins):
                    section_title(f"Sheet {i+1}")
                    png = render_sheet_png(abin, kerf, f"Sheet {i+1}")
                    st.image(png, use_column_width=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 Download PNG", png,
                                            f"Sheet{i+1}.png", "image/png",
                                            key=f"dl_{i}", width="stretch")
                    with c2:
                        if feat.get("sharing", True):
                            st.link_button("📱 Share",
                                            f"https://wa.me/?text={quote(f'🪟 Sheet {i+1}')}",
                                            key=f"wa_{i}", width="stretch")

                    # Offcut saving
                    if feat.get("offcut_tracking", True):
                        mx = my = 0
                        for rect in abin:
                            mx = max(mx, rect.x + rect.width)
                            my = max(my, rect.y + rect.height)
                        tw, th = abin.width, abin.height - my
                        rw, rh = abin.width - mx, abin.height
                        off = (int(tw), int(th)) if tw*th >= rw*rh else (int(rw), int(rh))
                        st.caption(f"Largest leftover: **{off[0]}×{off[1]} mm**")
                        if off[0] > 300 and off[1] > 300:
                            if st.checkbox("Sheet cut? Save offcut?", key=f"c_{i}"):
                                if st.button("📥 Save Offcut", key=f"sv_{i}", width="stretch"):
                                    mat_name = abin.bid.split("|")[0]
                                    db["inventory"]["remnants"].append({
                                        "id": str(uuid.uuid4())[:8], "material": mat_name,
                                        "width": off[0], "height": off[1],
                                        "date_added": datetime.now().strftime("%Y-%m-%d")})
                                    save_db(db); st.success("Saved!")
                    st.divider()

    # ---- MATERIALS TAB ----
    with pt3:
        section_title("📏 Use Aluminum")
        if not db["inventory"]["aluminum"]:
            empty_state("📏", "No aluminum in warehouse.")
        else:
            with st.form("use_alum"):
                profile = st.selectbox("Profile", list(db["inventory"]["aluminum"].keys()))
                st.caption(f"Available: **{db['inventory']['aluminum'][profile]:.2f} m**")
                meters = st.number_input("Meters Used", min_value=0.1, step=0.5, value=1.0)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("📉 Deduct & Log", type="primary", width="stretch"):
                    if db["inventory"]["aluminum"][profile] >= meters:
                        db["inventory"]["aluminum"][profile] -= meters
                        proj["aluminum"].append({"Profile": profile, "Meters": meters, "Note": note,
                                                  "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success("✅ Logged.")
                    else:
                        st.error("Not enough.")

        st.divider()
        section_title("🔧 Use Accessory")
        if not db["inventory"]["accessories"]:
            empty_state("🔧", "No accessories in warehouse.")
        else:
            with st.form("use_acc"):
                item = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                st.caption(f"Available: **{db['inventory']['accessories'][item]}**")
                qty = st.number_input("Quantity", min_value=1, step=1, value=1)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("📉 Deduct & Log", type="primary", width="stretch"):
                    if db["inventory"]["accessories"][item] >= qty:
                        db["inventory"]["accessories"][item] -= qty
                        proj["accessories"].append({"Item": item, "Qty": qty, "Note": note,
                                                     "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success("✅ Logged.")
                    else:
                        st.error("Not enough.")

    # ---- PHOTOS TAB ----
    with pt4:
        if not feat.get("photos", True):
            st.info("📷 Photo attachments are disabled in Settings.")
        else:
            section_title("📸 Site Photos")
            cam_tab, up_tab = st.tabs(["📷 Camera", "🖼️ Upload"])

            with cam_tab:
                cam = st.camera_input("Take photo")
                if cam:
                    if st.button("💾 Save Photo", type="primary", width="stretch"):
                        b64 = compress_image(cam)
                        if b64:
                            proj["photos"].append({
                                "id": str(uuid.uuid4())[:8],
                                "name": f"Cam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "data": b64})
                            save_db(db); st.rerun()

            with up_tab:
                uploaded = st.file_uploader("Upload photos", type=["jpg", "jpeg", "png"],
                                             accept_multiple_files=True)
                if uploaded:
                    if st.button("💾 Save Uploads", type="primary", width="stretch"):
                        prog = st.progress(0)
                        for idx, f in enumerate(uploaded):
                            b64 = compress_image(f)
                            if b64:
                                proj["photos"].append({
                                    "id": str(uuid.uuid4())[:8], "name": f.name,
                                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "data": b64})
                            prog.progress((idx + 1) / len(uploaded))
                        save_db(db); st.rerun()

            if proj.get("photos"):
                section_title(f"Photos ({len(proj['photos'])})")
                for i in range(len(proj["photos"]) - 1, -1, -1):
                    photo = proj["photos"][i]
                    try:
                        st.image(base64.b64decode(photo["data"]),
                                 caption=f"{photo['name']} — {photo['date']}",
                                 use_column_width=True)
                    except Exception:
                        st.error("Failed to load.")
                    if st.button("🗑️ Delete", key=f"ph_{i}", width="stretch"):
                        proj["photos"].pop(i); save_db(db); st.rerun()
            else:
                empty_state("📸", "No photos yet.")

    # ---- HISTORY TAB ----
    with pt5:
        section_title("🕒 Full Activity Timeline")
        timeline = []
        for g in proj["glass"]:
            timeline.append({"Date": g["Date"], "Type": "🪟 Glass",
                              "Detail": f"{g['Location']} — {g['Material']} — {g['Size']}"})
        for a in proj["aluminum"]:
            timeline.append({"Date": a["Date"], "Type": "📏 Aluminum",
                              "Detail": f"{a['Profile']} — {a['Meters']}m" + (f" ({a['Note']})" if a.get("Note") else "")})
        for a in proj["accessories"]:
            timeline.append({"Date": a["Date"], "Type": "🔧 Accessory",
                              "Detail": f"{a['Item']} × {a['Qty']}" + (f" ({a['Note']})" if a.get("Note") else "")})

        if not timeline:
            empty_state("📜", "No activity yet.")
        else:
            timeline.sort(key=lambda x: x["Date"], reverse=True)
            filter_type = st.multiselect("Filter by type",
                                          ["🪟 Glass", "📏 Aluminum", "🔧 Accessory"],
                                          default=["🪟 Glass", "📏 Aluminum", "🔧 Accessory"])
            filtered = [t for t in timeline if t["Type"] in filter_type]

            for d in sorted(set(t["Date"] for t in filtered), reverse=True):
                st.markdown(f"##### 📅 {d}")
                for t in [x for x in filtered if x["Date"] == d]:
                    st.markdown(f"""<div class="big-card">
                    <div class="title">{t['Type']}</div>
                    <div class="meta">{t['Detail']}</div>
                    </div>""", unsafe_allow_html=True)

            st.divider()
            st.download_button("📥 Export Full Log (CSV)",
                                pd.DataFrame(filtered).to_csv(index=False).encode("utf-8"),
                                f"{db['active_project']}_FullLog.csv",
                                "text/csv", width="stretch")

# ═══════════════════════════════════════════════════════════════
# MODULE — 📊 REPORTS
# ═══════════════════════════════════════════════════════════════
elif nav == "📊 Reports":
    st.markdown("## 📊 Reports")

    if not db["projects"]:
        empty_state("📊", "No jobs yet.")
        st.stop()

    # Customer search
    if feat.get("customer_search", True):
        section_title("🔍 Customer Search")
        search = st.text_input("Search by customer, phone, or address",
                                placeholder="e.g., Ahmed / 0911223344 / Bole")

        filtered_projects = []
        for name, p in db["projects"].items():
            c = p.get("customer", {})
            hay = f"{name} {c.get('name','')} {c.get('phone','')} {c.get('address','')}".lower()
            if not search or search.lower() in hay:
                filtered_projects.append((name, p))

        if search:
            st.caption(f"**{len(filtered_projects)}** job(s) match")

        for name, p in filtered_projects:
            c = p.get("customer", {})
            status = p.get("status", "Started")
            pill_class = {"Started": "status-started", "Ongoing": "status-ongoing",
                          "Completed": "status-completed"}.get(status, "status-started")
            st.markdown(f"""<div class="big-card">
            <div style="display:flex; justify-content:space-between; align-items:start; gap:12px;">
                <div style="flex:1;">
                    <div class="title">🏗️ {name}</div>
                    <div class="meta">👤 {c.get('name','—')} · 📞 {c.get('phone','—')} · 📍 {c.get('address','—')}<br>
                    Glass: {len(p['glass'])} · Alum: {sum(a['Meters'] for a in p['aluminum']):.1f}m · Acc: {sum(a['Qty'] for a in p['accessories'])}</div>
                </div>
                <span class="status-pill {pill_class}">{status}</span>
            </div>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button(f"📋 Open", key=f"open_{name}", width="stretch"):
                    db["active_project"] = name
                    save_db(db, silent=True)
                    st.session_state.nav = "🛠️ Jobs"
                    st.rerun()
            with c2:
                if c.get("phone"):
                    phone = c["phone"].replace(" ", "").replace("-", "")
                    wa_text = quote(f"Hello {c.get('name','')}, regarding your project {name}...")
                    st.link_button("📱 WhatsApp", f"https://wa.me/{phone}?text={wa_text}",
                                    key=f"w_{name}", width="stretch")

    # All projects summary
    st.divider()
    section_title("📁 All Jobs Overview")
    overview = []
    for name, p in db["projects"].items():
        overview.append({
            "Job": name,
            "Customer": p.get("customer", {}).get("name", ""),
            "Phone": p.get("customer", {}).get("phone", ""),
            "Status": p.get("status", "Started"),
            "Glass": len(p["glass"]),
            "Alum m": round(sum(a["Meters"] for a in p["aluminum"]), 1),
            "Acc": sum(a["Qty"] for a in p["accessories"]),
        })
    st.dataframe(pd.DataFrame(overview), width="stretch", hide_index=True)

    st.divider()
    section_title("📥 Export")
    st.download_button("📥 Jobs (CSV)",
                        pd.DataFrame(overview).to_csv(index=False).encode("utf-8"),
                        "jobs.csv", "text/csv", width="stretch")

    inv_rows = []
    for m, s in db["inventory"]["glass"].items():
        for sz, q in s.items():
            inv_rows.append({"Type": "Glass", "Name": m, "Detail": sz, "Qty": q})
    for p, mm in db["inventory"]["aluminum"].items():
        inv_rows.append({"Type": "Aluminum", "Name": p, "Detail": "m", "Qty": mm})
    for i, q in db["inventory"]["accessories"].items():
        inv_rows.append({"Type": "Accessory", "Name": i, "Detail": "pcs", "Qty": q})
    st.download_button("📥 Inventory (CSV)",
                        pd.DataFrame(inv_rows).to_csv(index=False).encode("utf-8"),
                        "inventory.csv", "text/csv", width="stretch")

# ═══════════════════════════════════════════════════════════════
# MODULE — ⚙️ SETTINGS
# ═══════════════════════════════════════════════════════════════
elif nav == "⚙️ Settings":
    st.markdown("## ⚙️ Settings")

    # ---- FEATURES ----
    section_title("🎛️ Features")

    def feature_toggle(key, name, desc):
        current = feat.get(key, True)
        st.markdown(f"""<div class="feature-row">
        <div class="info"><div class="name">{name}</div><div class="desc">{desc}</div></div>
        </div>""", unsafe_allow_html=True)
        new_val = st.toggle("Enable", value=current, key=f"tog_{key}", label_visibility="collapsed")
        if new_val != current:
            db["features"][key] = new_val
            save_db(db, silent=True)
            st.rerun()

    feature_toggle("photos", "📷 Photo Attachments", "Take and store site photos per job")
    feature_toggle("offcut_tracking", "✂️ Offcut Tracking", "Auto-use oldest offcuts first, save new offcuts")
    feature_toggle("sharing", "📱 WhatsApp & Telegram Sharing", "Share cutting sheets and contact customers")
    feature_toggle("low_stock_alerts", "🚨 Low Stock Alerts", "Warn when stock falls below thresholds")
    feature_toggle("stale_offcut_alerts", "⏰ Stale Offcut Alerts", "Warn about offcuts older than threshold")
    feature_toggle("print_mode", "🖨️ Print Mode", "Clean printable cutting sheets")
    feature_toggle("customer_search", "🔍 Customer Search", "Search across all jobs by customer info")
    feature_toggle("auto_save", "💾 Auto-Save to Cloud", "Save every action automatically to GitHub")

    # ---- THRESHOLDS ----
    st.divider()
    section_title("📊 Thresholds")

    st.markdown("**Low Stock Warnings**")
    c1, c2, c3 = st.columns(3)
    with c1:
        new_gs = st.number_input("Glass Sheets",
                                  min_value=0, max_value=100,
                                  value=int(db["low_stock_thresholds"]["glass_sheets"]))
    with c2:
        new_am = st.number_input("Aluminum (m)",
                                  min_value=0.0, max_value=1000.0,
                                  value=float(db["low_stock_thresholds"]["aluminum_meters"]),
                                  step=1.0)
    with c3:
        new_ac = st.number_input("Accessories",
                                  min_value=0, max_value=1000,
                                  value=int(db["low_stock_thresholds"]["accessories"]))

    if (new_gs != db["low_stock_thresholds"]["glass_sheets"] or
        new_am != db["low_stock_thresholds"]["aluminum_meters"] or
        new_ac != db["low_stock_thresholds"]["accessories"]):
        db["low_stock_thresholds"] = {
            "glass_sheets": new_gs,
            "aluminum_meters": new_am,
            "accessories": new_ac,
        }
        save_db(db, silent=True)

    new_warn = st.number_input("⏰ Offcut warning (days)",
                                min_value=7, max_value=365,
                                value=int(db.get("offcut_warning_days", 60)), step=5)
    if new_warn != db.get("offcut_warning_days", 60):
        db["offcut_warning_days"] = new_warn
        save_db(db, silent=True)

    # ---- CUTTING DEFAULTS ----
    st.divider()
    section_title("🔪 Cutting Defaults")
    c1, c2 = st.columns(2)
    with c1:
        new_kerf = st.number_input("Blade Kerf (mm)",
                                    min_value=1, max_value=20,
                                    value=int(db["settings"].get("kerf", 3)))
    with c2:
        new_etrim = st.number_input("Edge Trim (mm)",
                                     min_value=0, max_value=50,
                                     value=int(db["settings"].get("edge_trim", 5)))
    if new_kerf != db["settings"]["kerf"] or new_etrim != db["settings"]["edge_trim"]:
        db["settings"]["kerf"] = new_kerf
        db["settings"]["edge_trim"] = new_etrim
        save_db(db, silent=True)

    # ---- DATA MANAGEMENT ----
    st.divider()
    section_title("💾 Data Management")

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Download Backup", json.dumps(db, indent=4),
                            f"abdiglass_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                            "application/json", width="stretch")
    with c2:
        if st.button("🔄 Reload from Cloud", width="stretch"):
            get_github_client.clear()
            st.session_state.db = load_db(); st.rerun()

    st.markdown("**Restore from Backup**")
    up = st.file_uploader("Upload a backup file", type="json")
    if up:
        try:
            new_db = migrate_db(json.load(up))
            st.session_state.db = new_db
            save_db(new_db)
            st.success("Restored!"); st.rerun()
        except Exception as e:
            st.error(f"Invalid file: {e}")

    st.divider()
    section_title("ℹ️ About")
    st.markdown(f"""
    **Abdiglass and ALM Shop ERP**  
    Version 2.0 · {datetime.now().strftime('%Y')}  
    Glass & Aluminum Fabrication Management System
    """)
