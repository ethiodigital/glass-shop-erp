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
# 1. CONFIG & GLOBAL STYLES
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Shop ERP",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* ---------- THEME ---------- */
:root {
    --brand-dark: #1F4E79;
    --brand: #2E75B6;
    --brand-light: #D4E6F1;
    --success: #27AE60;
    --warning: #E67E22;
    --danger: #C0392B;
    --muted: #666;
}

/* ---------- TOUCH-FRIENDLY CONTROLS ---------- */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
.stLinkButton > a {
    min-height: 52px !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    border-radius: 12px !important;
    padding: 0.6rem 1rem !important;
    transition: transform 0.1s ease !important;
}
.stButton > button:active { transform: scale(0.97) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-dark), var(--brand)) !important;
    color: white !important;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
}
input, textarea, select {
    font-size: 16px !important;
    min-height: 48px !important;
    border-radius: 10px !important;
}
[data-baseweb="select"] > div {
    min-height: 48px !important;
    font-size: 16px !important;
}
[data-testid="stMetricValue"] { font-size: 22px !important; }
[data-testid="stMetricLabel"] { font-size: 12px !important; }

/* ---------- TABS ---------- */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    overflow-x: auto;
    flex-wrap: nowrap;
}
.stTabs [data-baseweb="tab"] {
    min-height: 48px !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    white-space: nowrap !important;
    border-radius: 10px 10px 0 0 !important;
}

/* ---------- SMART HEADER ---------- */
.smart-header {
    background: linear-gradient(135deg, var(--brand-dark), var(--brand));
    color: white;
    padding: 14px 18px;
    margin: -16px -16px 16px -16px;
    border-radius: 0 0 18px 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.18);
    position: sticky;
    top: 0;
    z-index: 999;
}
.smart-header .row1 {
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.smart-header .label {
    opacity: 0.85;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.smart-header .name {
    font-weight: 700;
    font-size: 18px;
    margin-top: 2px;
}
.smart-header .chip {
    background: rgba(255,255,255,0.22);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
}
.smart-stats {
    display: flex;
    gap: 14px;
    margin-top: 10px;
    font-size: 12px;
    opacity: 0.95;
}
.smart-stats .stat {
    display: flex;
    align-items: center;
    gap: 4px;
}
.smart-stats .stat b { font-size: 14px; }

/* ---------- CARDS ---------- */
.card {
    background: #f8f9fa;
    border-left: 4px solid var(--brand);
    padding: 12px 16px;
    margin-bottom: 10px;
    border-radius: 10px;
    font-size: 14px;
    transition: box-shadow 0.15s ease;
}
.card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.card .title { font-weight: 700; margin-bottom: 4px; font-size: 15px; }
.card .meta { color: var(--muted); font-size: 12.5px; line-height: 1.5; }
.card.orange { border-left-color: var(--warning); background: #FEF5E7; }
.card.red    { border-left-color: var(--danger); background: #FADBD8; }
.card.green  { border-left-color: var(--success); background: #EAFAF1; }

/* ---------- SECTION TITLES ---------- */
.section-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--brand-dark);
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 2px solid var(--brand-light);
}

/* ---------- EMPTY STATE ---------- */
.empty-state {
    text-align: center;
    padding: 30px 20px;
    background: #f8f9fa;
    border-radius: 12px;
    border: 2px dashed #d0d7de;
    color: var(--muted);
}
.empty-state .icon { font-size: 42px; margin-bottom: 8px; }
.empty-state .msg { font-size: 14px; }

/* ---------- MOBILE ---------- */
@media (max-width: 768px) {
    .block-container { padding: 0.5rem 0.75rem !important; }
    h1 { font-size: 22px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    .stSidebar { width: 88% !important; }
    .stButton > button { width: 100% !important; }
    .smart-header { margin: -8px -12px 12px -12px; padding: 12px 14px; }
    .smart-header .name { font-size: 16px; }
    .smart-stats { flex-wrap: wrap; gap: 10px; }
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 2. DATABASE LAYER
# ═══════════════════════════════════════════════════════════════
DB_FILE_PATH = "shop_erp_data.json"

def get_default_db():
    return {
        "active_project": None,
        "low_stock_thresholds": {
            "glass_sheets": 3,
            "aluminum_meters": 20.0,
            "accessories": 5,
        },
        "offcut_warning_days": 60,
        "settings": {"kerf": 3, "edge_trim": 5},
        "inventory": {
            "glass": {},
            "remnants": [],
            "aluminum": {},
            "accessories": {},
        },
        "projects": {},
        "recent": {"materials": [], "aluminum": [], "accessories": []},
    }

def migrate_db(db):
    default = get_default_db()
    for key in default:
        if key not in db: db[key] = default[key]
    for key in default["inventory"]:
        if key not in db["inventory"]: db["inventory"][key] = default["inventory"][key]
    if "recent" not in db: db["recent"] = default["recent"]
    if "settings" not in db: db["settings"] = default["settings"]
    for rem in db["inventory"]["remnants"]:
        if "id" not in rem: rem["id"] = str(uuid.uuid4())[:8]
        if "date_added" not in rem: rem["date_added"] = datetime.now().strftime("%Y-%m-%d")
    for name, proj in db["projects"].items():
        if "status" not in proj: proj["status"] = "Measured"
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
                d = get_default_db()
                save_db(d, silent=True)
                return d
            raise
    except Exception as e:
        st.warning(f"⚠️ Load failed: {e}")
        return get_default_db()

def save_db(db, silent=False):
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

# ═══════════════════════════════════════════════════════════════
# 3. UTILITIES
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
    ax.set_xlim(0, abin.width + 5)
    ax.set_ylim(0, abin.height + 5)
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
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()

def empty_state(icon, msg):
    st.markdown(f'<div class="empty-state"><div class="icon">{icon}</div><div class="msg">{msg}</div></div>',
                unsafe_allow_html=True)

def section_title(text):
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 4. PRINT MODE (early exit)
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
        st.session_state.print_mode = False
        st.rerun()
    st.divider()
    kerf = st.session_state.get("print_kerf", 3)
    for i, abin in enumerate(st.session_state.generated_bins):
        st.image(render_sheet_png(abin, kerf, f"Sheet {i+1}"), use_column_width=True)
        st.markdown("---")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# 5. SMART HEADER
# ═══════════════════════════════════════════════════════════════
active_name = db.get("active_project") or "No project"
if active_name != "No project" and active_name in db["projects"]:
    proj = db["projects"][active_name]
    cur_status = proj.get("status", "")
    glass_count = len(proj["glass"])
    alum_m = sum(a["Meters"] for a in proj["aluminum"])
    acc_qty = sum(a["Qty"] for a in proj["accessories"])
    chip = f'<span class="chip">{cur_status}</span>' if cur_status else ""
    stats_html = f"""
    <div class="smart-stats">
        <div class="stat">🪟 <b>{glass_count}</b> pieces</div>
        <div class="stat">📏 <b>{alum_m:.1f}</b> m</div>
        <div class="stat">🔧 <b>{acc_qty}</b> items</div>
    </div>
    """
else:
    chip = ""
    stats_html = ""

st.markdown(f"""
<div class="smart-header">
    <div class="row1">
        <div>
            <span class="label">Active Project</span>
            <div class="name">🏗️ {active_name}</div>
        </div>
        {chip}
    </div>
    {stats_html}
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 6. SIDEBAR
# ═══════════════════════════════════════════════════════════════
st.sidebar.title("🏭 Shop ERP")
nav = st.sidebar.radio(
    "Navigate",
    ["📦 Warehouse", "📋 Projects", "📊 Reports"],
    label_visibility="collapsed",
)
st.sidebar.divider()

# --- Project picker ---
project_names = list(db["projects"].keys())
active_projects = [p for p in project_names if db["projects"][p].get("status") not in ["Paid", "Cancelled"]]

if active_projects:
    if db["active_project"] not in active_projects:
        db["active_project"] = active_projects[0]
    ap = st.sidebar.selectbox(
        "🎯 Active Project",
        active_projects,
        index=active_projects.index(db["active_project"]) if db["active_project"] in active_projects else 0,
    )
    if ap != db["active_project"]:
        db["active_project"] = ap
        save_db(db, silent=True)
        st.rerun()
elif project_names:
    st.sidebar.info("All projects closed.")
else:
    st.sidebar.info("No projects yet.")

# --- Alerts ---
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

stale = get_stale_offcuts()

if alerts or stale:
    st.sidebar.divider()
    st.sidebar.subheader("🚨 Alerts")
    if alerts:
        with st.sidebar.expander(f"Low Stock ({len(alerts)})", expanded=False):
            for a in alerts: st.write(a)
    if stale:
        with st.sidebar.expander(f"Stale Offcuts ({len(stale)})", expanded=False):
            warn = db.get("offcut_warning_days", 60)
            for r in stale[:8]:
                age = days_old(r.get("date_added", ""))
                badge = "🔴" if age >= warn * 1.5 else "🟠"
                st.write(f"{badge} {r['material']} {r['width']}×{r['height']} — {age}d")

# --- Settings & Sync ---
st.sidebar.divider()
with st.sidebar.expander("⚙️ Settings"):
    new_warn = st.number_input(
        "Offcut warning (days)",
        min_value=7, max_value=365,
        value=int(db.get("offcut_warning_days", 60)),
        step=5,
    )
    if new_warn != db.get("offcut_warning_days", 60):
        db["offcut_warning_days"] = new_warn
        save_db(db, silent=True)

with st.sidebar.expander("🔄 Data Sync"):
    if st.button("🔄 Reload from GitHub", width="stretch"):
        get_github_client.clear()
        st.session_state.db = load_db()
        st.rerun()
    st.download_button(
        "📥 Download Backup",
        json.dumps(db, indent=4),
        f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        "application/json",
        width="stretch",
    )
    up = st.file_uploader("📤 Restore", type="json")
    if up:
        try:
            st.session_state.db = migrate_db(json.load(up))
            save_db(st.session_state.db)
            st.success("Restored!")
            st.rerun()
        except Exception:
            st.error("Invalid file.")

# ═══════════════════════════════════════════════════════════════
# 7. MODULE — WAREHOUSE
# ═══════════════════════════════════════════════════════════════
if nav == "📦 Warehouse":
    st.title("📦 Warehouse")

    if stale:
        st.warning(f"⏰ **{len(stale)} offcut(s) older than {db['offcut_warning_days']} days.** Review below.")

    wtab1, wtab2 = st.tabs(["👁️ Stock", "➕ Receive"])

    # ------- VIEW STOCK -------
    with wtab1:
        search = st.text_input("🔍 Search", placeholder="Search materials...")

        # Stale offcuts panel
        if stale and not search:
            section_title(f"⏰ Stale Offcuts ({len(stale)})")
            st.caption(f"Older than {db['offcut_warning_days']} days. Oldest first.")
            for r in stale:
                age = days_old(r.get("date_added", ""))
                _, css = offcut_badge(age, db["offcut_warning_days"])
                st.markdown(f"""<div class="card {css}">
                <div class="title">{r['material']} — {r['width']} × {r['height']} mm</div>
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

        # Glass sheets
        section_title("🪟 Glass Sheets")
        if db["inventory"]["glass"]:
            for mat, sizes in db["inventory"]["glass"].items():
                if search and search.lower() not in mat.lower(): continue
                total = sum(sizes.values())
                is_low = total <= db["low_stock_thresholds"]["glass_sheets"]
                badge = "🔴" if is_low else "🟢"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="card {css}">
                <div class="title">{badge} {mat}</div>
                <div class="meta">2140×3300: {sizes.get('2140 x 3300',0)} · 2140×3660: {sizes.get('2140 x 3660',0)} · Total: <b>{total}</b></div>
                </div>""", unsafe_allow_html=True)
        else:
            empty_state("🪟", "No glass in stock yet. Add via Receive tab.")

        # Remnants
        section_title("✂️ All Offcuts")
        if db["inventory"]["remnants"]:
            warn = db["offcut_warning_days"]
            for r in sorted(db["inventory"]["remnants"], key=lambda x: x.get("date_added", "")):
                age = days_old(r.get("date_added", ""))
                label, css = offcut_badge(age, warn)
                st.markdown(f"""<div class="card {css}">
                <div class="title">{r['material']}</div>
                <div class="meta">{r['width']} × {r['height']} mm · Age: <b>{label}</b> · Added {r.get('date_added','-')}</div>
                </div>""", unsafe_allow_html=True)
        else:
            empty_state("✂️", "No offcuts tracked yet.")

        # Aluminum
        section_title("📏 Aluminum Profiles")
        if db["inventory"]["aluminum"]:
            for k, v in db["inventory"]["aluminum"].items():
                is_low = v <= db["low_stock_thresholds"]["aluminum_meters"]
                badge = "🔴" if is_low else "🟢"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="card {css}">
                <div class="title">{badge} {k}</div>
                <div class="meta"><b>{v:.2f} m</b> available</div>
                </div>""", unsafe_allow_html=True)
        else:
            empty_state("📏", "No aluminum in stock.")

        # Accessories
        section_title("🔧 Accessories")
        if db["inventory"]["accessories"]:
            for k, v in db["inventory"]["accessories"].items():
                is_low = v <= db["low_stock_thresholds"]["accessories"]
                badge = "🔴" if is_low else "🟢"
                css = "red" if is_low else ""
                st.markdown(f"""<div class="card {css}">
                <div class="title">{badge} {k}</div>
                <div class="meta"><b>{v}</b> pcs</div>
                </div>""", unsafe_allow_html=True)
        else:
            empty_state("🔧", "No accessories in stock.")

    # ------- RECEIVE STOCK -------
    with wtab2:
        st.caption("Add new materials when a delivery arrives.")

        # -- Add Glass --
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
                    st.error("Name required.")
                else:
                    gm = gm.strip()
                    if gm not in db["inventory"]["glass"]:
                        db["inventory"]["glass"][gm] = {"2140 x 3300": 0, "2140 x 3660": 0}
                    db["inventory"]["glass"][gm][gsz] += gq
                    remember_recent("materials", gm)
                    save_db(db); st.rerun()

        # -- Add Offcut --
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
                        "id": str(uuid.uuid4())[:8],
                        "material": rm,
                        "width": rw, "height": rh,
                        "date_added": datetime.now().strftime("%Y-%m-%d"),
                    })
                    save_db(db); st.rerun()
        else:
            st.info("Add glass first, then record offcuts.")

        # -- Add Aluminum --
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
                    st.error("Name required.")
                else:
                    apr = apr.strip()
                    db["inventory"]["aluminum"][apr] = db["inventory"]["aluminum"].get(apr, 0) + am
                    remember_recent("aluminum", apr)
                    save_db(db); st.rerun()

        # -- Add Accessory --
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
                    st.error("Name required.")
                else:
                    ac = ac.strip()
                    db["inventory"]["accessories"][ac] = db["inventory"]["accessories"].get(ac, 0) + aq
                    remember_recent("accessories", ac)
                    save_db(db); st.rerun()

# ═══════════════════════════════════════════════════════════════
# 8. MODULE — PROJECTS
# ═══════════════════════════════════════════════════════════════
elif nav == "📋 Projects":
    st.title("📋 Projects")

    # -- Create project --
    with st.expander("➕ Create New Project"):
        new_proj = st.text_input("Project Name", placeholder="e.g., Villa 4 - Bole")
        if st.button("Create Project", type="primary", width="stretch"):
            if not new_proj or not new_proj.strip():
                st.error("Enter a name.")
            elif new_proj.strip() in db["projects"]:
                st.error("Already exists.")
            else:
                db["projects"][new_proj.strip()] = {
                    "status": "Measured",
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "customer": {"name": "", "phone": "", "address": ""},
                    "photos": [], "glass": [], "aluminum": [], "accessories": [],
                }
                db["active_project"] = new_proj.strip()
                save_db(db); st.rerun()

    if not db["active_project"]:
        empty_state("📋", "Create a project above to begin.")
        st.stop()

    proj = db["projects"][db["active_project"]]

    # -- Status flow --
    STATUSES = ["Measured", "Fabricated", "Delivered", "Installed", "Paid"]
    cs = proj.get("status", "Measured")
    if cs == "Cancelled":
        st.error("❌ Project Cancelled")
    else:
        idx = STATUSES.index(cs) if cs in STATUSES else 0
        st.progress((idx + 1) / len(STATUSES), text=f"Step {idx+1}/{len(STATUSES)} — **{cs}**")
        cols = st.columns(len(STATUSES))
        for i, s in enumerate(STATUSES):
            with cols[i]:
                is_act = (s == cs)
                if st.button(("● " if is_act else "") + s, key=f"st_{s}", width="stretch",
                             type="primary" if is_act else "secondary"):
                    proj["status"] = s
                    save_db(db); st.rerun()

    # -- Tabs --
    ptab1, ptab2, ptab3, ptab4, ptab5 = st.tabs(
        ["📷 Info", "🪟 Cut Glass", "📏 Alum", "🔧 Acc", "📸 Photos & Log"]
    )

    # ------- INFO -------
    with ptab1:
        section_title("👤 Customer")
        cname = st.text_input("Name", value=proj["customer"].get("name", ""))
        cphone = st.text_input("Phone", value=proj["customer"].get("phone", ""))
        caddr = st.text_input("Site Address", value=proj["customer"].get("address", ""))
        if st.button("💾 Save Customer", type="primary", width="stretch"):
            proj["customer"] = {"name": cname, "phone": cphone, "address": caddr}
            save_db(db); st.success("Saved!")

        if cphone:
            phone_clean = cphone.replace(" ", "").replace("-", "")
            wa_msg = quote(f"Hello {cname or ''}, regarding your project {db['active_project']}...")
            st.link_button("📱 Message on WhatsApp", f"https://wa.me/{phone_clean}?text={wa_msg}",
                            width="stretch")

        st.divider()
        with st.expander("⚠️ Danger Zone"):
            if st.button("🗑️ Delete this project", type="secondary", width="stretch"):
                del db["projects"][db["active_project"]]
                db["active_project"] = None
                save_db(db); st.rerun()

    # ------- CUT GLASS -------
    with ptab2:
        if not db["inventory"]["glass"]:
            empty_state("🪟", "No glass in warehouse. Add stock first.")
        else:
            mats = list(db["inventory"]["glass"].keys())

            # Smart: remember last settings
            with st.expander("⚙️ Cutting Settings", expanded=False):
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

            # Add piece form
            with st.form("add_piece", clear_on_submit=True):
                section_title("➕ Add a Piece")
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
                        "Width": w, "Height": h, "Quantity": q,
                    })
                    st.rerun()

            # List of pieces
            if st.session_state.form_list:
                section_title(f"📝 Pieces ({len(st.session_state.form_list)})")
                for i, item in enumerate(st.session_state.form_list):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"""<div class="card">
                        <div class="title">{item['Location']}</div>
                        <div class="meta">{item['Material']} — {item['Width']}×{item['Height']} × {item['Quantity']}</div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"dl_{i}", width="stretch"):
                            st.session_state.form_list.pop(i)
                            st.rerun()

                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ Clear All", width="stretch"):
                        st.session_state.form_list = []
                        st.rerun()
                with c2:
                    if st.button("🚀 Generate Plan", type="primary", width="stretch"):
                        df = pd.DataFrame(st.session_state.form_list)
                        bins = []
                        stock = {
                            "2140 x 3300": (2140 - etrim, 3300 - etrim),
                            "2140 x 3660": (2140 - etrim, 3660 - etrim),
                        }
                        for material in df["Material"].unique():
                            mdf = df[df["Material"] == material]
                            p = newPacker(rotation=True)

                            # Add offcuts first (oldest first)
                            mat_remnants = [r for r in db["inventory"].get("remnants", []) if r["material"] == material]
                            mat_remnants.sort(key=lambda r: r.get("date_added", "9999-99-99"))
                            for rem in mat_remnants:
                                p.add_bin(rem["width"] - etrim, rem["height"] - etrim,
                                          bid=f"REMNANT|{rem['id']}|{rem['width']}x{rem['height']}")

                            for sn, d in stock.items():
                                for _ in range(db["inventory"]["glass"][material].get(sn, 0)):
                                    p.add_bin(d[0], d[1], bid=f"{material}|{sn}")

                            for _, row in mdf.iterrows():
                                for _ in range(int(row["Quantity"])):
                                    p.add_rect(float(row["Width"]) + kerf, float(row["Height"]) + kerf,
                                               rid=row["Location"])
                            p.pack()
                            valid = [b for b in p if len(b) > 0]
                            if not valid and not mdf.empty:
                                st.error(f"❌ Not enough {material}!")
                                continue
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
                                        "Size": f"{int(rect.width - kerf)}x{int(rect.height - kerf)}",
                                        "Location": rect.rid,
                                        "Date": datetime.now().strftime("%Y-%m-%d"),
                                    })
                            bins.extend(valid)
                        save_db(db)
                        st.session_state.generated_bins = bins
                        st.session_state.print_kerf = kerf
                        st.session_state.form_list = []
                        st.rerun()
            else:
                empty_state("📐", "Add pieces above to begin cutting.")

            # ------- Cutting maps -------
            if st.session_state.get("generated_bins"):
                st.divider()
                section_title("🗺️ Cutting Plan")

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🖨️ Print Mode", type="primary", width="stretch"):
                        st.session_state.print_mode = True
                        st.rerun()
                with c2:
                    if st.button("✅ Done Cutting", width="stretch"):
                        st.session_state.generated_bins = []
                        st.rerun()

                # Share sheet
                proj_label = db["active_project"]
                pieces_summary = " | ".join([f"{g['Location']}:{g['Size']}" for g in proj["glass"][-20:]])
                share_text = f"🪟 Cutting Plan — {proj_label}\n{len(st.session_state.generated_bins)} sheet(s). Pieces: {pieces_summary[:200]}"
                enc = quote(share_text)

                c1, c2 = st.columns(2)
                with c1:
                    st.link_button("📱 WhatsApp", f"https://wa.me/?text={enc}", width="stretch")
                with c2:
                    st.link_button("✈️ Telegram", f"https://t.me/share/url?url=&text={enc}", width="stretch")

                # Download all
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, abin in enumerate(st.session_state.generated_bins):
                        zf.writestr(f"{proj_label}_Sheet{i+1}.png",
                                     render_sheet_png(abin, kerf, f"Sheet {i+1}"))
                st.download_button("📥 Download All Sheets (.zip)", zip_buf.getvalue(),
                                    f"{proj_label}_CuttingSheets.zip", "application/zip",
                                    width="stretch")

                # Per-sheet
                for i, abin in enumerate(st.session_state.generated_bins):
                    section_title(f"Sheet {i+1}")
                    png = render_sheet_png(abin, kerf, f"Sheet {i+1}")
                    st.image(png, use_column_width=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        st.download_button("📥 PNG", png, f"{proj_label}_Sheet{i+1}.png",
                                            "image/png", key=f"dlpng_{i}", width="stretch")
                    with c2:
                        st.link_button("📱 Share",
                                        f"https://wa.me/?text={quote(f'🪟 Sheet {i+1} — {proj_label}')}",
                                        key=f"wapp_{i}", width="stretch")

                    mx = my = 0
                    for rect in abin:
                        mx = max(mx, rect.x + rect.width)
                        my = max(my, rect.y + rect.height)
                    tw, th = abin.width, abin.height - my
                    rw, rh = abin.width - mx, abin.height
                    off = (int(tw), int(th)) if tw * th >= rw * rh else (int(rw), int(rh))
                    st.caption(f"Largest leftover: **{off[0]}×{off[1]} mm**")

                    if off[0] > 300 and off[1] > 300:
                        if st.checkbox("Sheet cut? Save offcut?", key=f"c_{i}"):
                            if st.button("📥 Save Offcut", key=f"sv_{i}", width="stretch"):
                                mat_name = abin.bid.split("|")[0]
                                db["inventory"]["remnants"].append({
                                    "id": str(uuid.uuid4())[:8],
                                    "material": mat_name,
                                    "width": off[0], "height": off[1],
                                    "date_added": datetime.now().strftime("%Y-%m-%d"),
                                })
                                save_db(db); st.success("Saved!")
                    st.divider()

    # ------- USE ALUMINUM -------
    with ptab3:
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
                        proj["aluminum"].append({
                            "Profile": profile, "Meters": meters, "Note": note,
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                        })
                        save_db(db); st.success("✅ Logged.")
                    else:
                        st.error("Not enough.")

    # ------- USE ACCESSORIES -------
    with ptab4:
        if not db["inventory"]["accessories"]:
            empty_state("🔧", "No accessories in warehouse.")
        else:
            with st.form("use_acc"):
                item = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                st.caption(f"Available: **{db['inventory']['accessories'][item]}**")
                qty = st.number_input("Quantity Used", min_value=1, step=1, value=1)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("📉 Deduct & Log", type="primary", width="stretch"):
                    if db["inventory"]["accessories"][item] >= qty:
                        db["inventory"]["accessories"][item] -= qty
                        proj["accessories"].append({
                            "Item": item, "Qty": qty, "Note": note,
                            "Date": datetime.now().strftime("%Y-%m-%d"),
                        })
                        save_db(db); st.success("✅ Logged.")
                    else:
                        st.error("Not enough.")

    # ------- PHOTOS & LOG -------
    with ptab5:
        photo_tab, log_tab, full_log_tab = st.tabs(["📸 Photos", "📜 Log", "🕒 Full Timeline"])

        with photo_tab:
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
                                "data": b64,
                            })
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
                                    "data": b64,
                                })
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
                        st.error("Failed to load photo.")
                    if st.button("🗑️ Delete", key=f"ph_{i}", width="stretch"):
                        proj["photos"].pop(i)
                        save_db(db); st.rerun()
            else:
                empty_state("📸", "No photos yet.")

        with log_tab:
            m1, m2, m3 = st.columns(3)
            m1.metric("Glass", len(proj["glass"]))
            m2.metric("Alum m", f"{sum(a['Meters'] for a in proj['aluminum']):.1f}")
            m3.metric("Acc", sum(a["Qty"] for a in proj["accessories"]))

            if proj["glass"]:
                section_title("🪟 Glass")
                for g in proj["glass"]:
                    st.markdown(f"""<div class="card">
                    <div class="title">{g['Location']}</div>
                    <div class="meta">{g['Material']} — {g['Size']} — {g['Date']}</div>
                    </div>""", unsafe_allow_html=True)

            if proj["aluminum"]:
                section_title("📏 Aluminum")
                for a in proj["aluminum"]:
                    st.markdown(f"""<div class="card">
                    <div class="title">{a['Profile']}</div>
                    <div class="meta">{a['Meters']}m {('· ' + a['Note']) if a.get('Note') else ''} — {a['Date']}</div>
                    </div>""", unsafe_allow_html=True)

            if proj["accessories"]:
                section_title("🔧 Accessories")
                for a in proj["accessories"]:
                    st.markdown(f"""<div class="card">
                    <div class="title">{a['Item']} × {a['Qty']}</div>
                    <div class="meta">{('Note: ' + a['Note'] + ' — ') if a.get('Note') else ''}{a['Date']}</div>
                    </div>""", unsafe_allow_html=True)

        with full_log_tab:
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
                empty_state("🕒", "No activity yet.")
            else:
                timeline.sort(key=lambda x: x["Date"], reverse=True)

                filter_type = st.multiselect(
                    "Filter by type",
                    ["🪟 Glass", "📏 Aluminum", "🔧 Accessory"],
                    default=["🪟 Glass", "📏 Aluminum", "🔧 Accessory"],
                )
                filtered = [t for t in timeline if t["Type"] in filter_type]

                for d in sorted(set(t["Date"] for t in filtered), reverse=True):
                    st.markdown(f"##### 📅 {d}")
                    for t in [x for x in filtered if x["Date"] == d]:
                        st.markdown(f"""<div class="card">
                        <div class="title">{t['Type']}</div>
                        <div class="meta">{t['Detail']}</div>
                        </div>""", unsafe_allow_html=True)

                st.divider()
                st.download_button("📥 Export Full Log (CSV)",
                                    pd.DataFrame(filtered).to_csv(index=False).encode("utf-8"),
                                    f"{db['active_project']}_FullLog.csv", "text/csv",
                                    width="stretch")

# ═══════════════════════════════════════════════════════════════
# 9. MODULE — REPORTS
# ═══════════════════════════════════════════════════════════════
elif nav == "📊 Reports":
    st.title("📊 Reports")

    if not db["projects"]:
        empty_state("📊", "No projects yet.")
        st.stop()

    # -- Customer search --
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
        st.caption(f"**{len(filtered_projects)}** project(s) match")

    if not filtered_projects:
        st.warning("No matches.")

    for name, p in filtered_projects:
        c = p.get("customer", {})
        st.markdown(f"""<div class="card">
        <div class="title">🏗️ {name}</div>
        <div class="meta">
        👤 {c.get('name','—')} · 📞 {c.get('phone','—')} · 📍 {c.get('address','—')}<br>
        Status: <b>{p.get('status','Measured')}</b> · Glass: {len(p['glass'])} ·
        Alum: {sum(a['Meters'] for a in p['aluminum']):.1f}m ·
        Acc: {sum(a['Qty'] for a in p['accessories'])}
        </div></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📋 Open", key=f"open_{name}", width="stretch"):
                db["active_project"] = name
                save_db(db, silent=True); st.rerun()
        with c2:
            if c.get("phone"):
                phone = c["phone"].replace(" ", "").replace("-", "")
                wa_text = quote(f"Hello {c.get('name','')}, regarding your project {name}...")
                st.link_button("📱 WhatsApp", f"https://wa.me/{phone}?text={wa_text}",
                                key=f"w_{name}", width="stretch")

    # -- All projects table --
    st.divider()
    section_title("📁 All Projects")
    overview = []
    for name, p in db["projects"].items():
        overview.append({
            "Project": name,
            "Customer": p.get("customer", {}).get("name", ""),
            "Phone": p.get("customer", {}).get("phone", ""),
            "Status": p.get("status", "Measured"),
            "Glass": len(p["glass"]),
            "Alum m": round(sum(a["Meters"] for a in p["aluminum"]), 1),
            "Acc": sum(a["Qty"] for a in p["accessories"]),
        })
    st.dataframe(pd.DataFrame(overview), width="stretch", hide_index=True)

    # -- Exports --
    st.divider()
    section_title("📥 Export")
    st.download_button("📥 Projects (CSV)",
                        pd.DataFrame(overview).to_csv(index=False).encode("utf-8"),
                        "projects.csv", "text/csv", width="stretch")

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
