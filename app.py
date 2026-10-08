import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
from rectpack import newPacker
import json
from datetime import datetime
import uuid
import base64
import io
import zipfile
from urllib.parse import quote
from PIL import Image
from github import Github, GithubException, Auth

st.set_page_config(page_title="Abdiglass and ALM Shop ERP", layout="wide", page_icon="🏭", initial_sidebar_state="collapsed")

# ═══════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<style>
:root {
    --brand-dark: #14344F; --brand: #2E75B6; --brand-light: #D4E6F1;
    --success: #27AE60; --warning: #E67E22; --danger: #C0392B;
    --muted: #6B7280; --bg-soft: #F7F9FC;
}
.block-container { padding-top: 1rem !important; }
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    min-height: 52px !important; font-size: 16px !important; font-weight: 600 !important;
    border-radius: 12px !important; padding: 0.55rem 1rem !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--brand-dark), var(--brand)) !important; color: white !important;
}
input, textarea, select { font-size: 16px !important; min-height: 50px !important; border-radius: 10px !important; }
[data-baseweb="select"] > div { min-height: 50px !important; font-size: 16px !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 2px solid #E5E7EB; overflow-x: auto; flex-wrap: nowrap; }
.stTabs [data-baseweb="tab"] { min-height: 48px !important; font-size: 14px !important; padding: 10px 14px !important; font-weight: 600 !important; white-space: nowrap !important; }
.topbar { display: flex; align-items: center; gap: 12px; padding: 12px 4px; margin-bottom: 12px; border-bottom: 2px solid #EEF2F6; }
.topbar .title { font-size: 20px; font-weight: 800; color: var(--brand-dark); margin: 0; }
.topbar .subtitle { font-size: 12px; color: var(--muted); }
.brand-hero { background: linear-gradient(135deg, var(--brand-dark), var(--brand)); color: white; padding: 26px 24px; border-radius: 20px; margin-bottom: 22px; box-shadow: 0 8px 24px rgba(20,52,79,0.2); }
.brand-hero .logo { font-size: 42px; }
.brand-hero .title { font-size: 24px; font-weight: 800; margin-top: 6px; }
.brand-hero .sub { font-size: 13px; opacity: 0.85; }
.card { background: white; border: 2px solid #E5E7EB; border-radius: 14px; padding: 16px 18px; margin-bottom: 12px; }
.card .title { font-weight: 700; font-size: 16px; color: var(--brand-dark); margin-bottom: 6px; }
.card .meta { color: var(--muted); font-size: 13.5px; line-height: 1.6; }
.card.low { border-color: #FECACA; background: #FEF2F2; }
.card.warn { border-color: #FED7AA; background: #FFF7ED; }
.card.good { border-color: #A7F3D0; background: #F0FDF4; }
.pill { padding: 6px 14px; border-radius: 20px; font-size: 12px; font-weight: 700; display: inline-block; white-space: nowrap; }
.pill-started { background: #DBEAFE; color: #1E40AF; }
.pill-ongoing { background: #FEF3C7; color: #92400E; }
.pill-completed { background: #D1FAE5; color: #065F46; }
.h-sec { font-size: 15px; font-weight: 800; color: var(--brand-dark); margin: 22px 0 10px 0; letter-spacing: 0.3px; }
.empty { text-align: center; padding: 40px 20px; background: var(--bg-soft); border-radius: 14px; border: 2px dashed #CBD5E1; color: var(--muted); }
.empty .icon { font-size: 48px; }
.empty .msg { font-size: 15px; margin-top: 8px; }
.job-card { background: white; border: 2px solid #E5E7EB; border-radius: 14px; padding: 16px 18px; margin-bottom: 10px; }
.job-card .name { font-size: 16px; font-weight: 700; color: var(--brand-dark); }
.job-card .sub { font-size: 13px; color: var(--muted); margin-top: 4px; }
.job-card .row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
@media (max-width: 768px) {
    .block-container { padding: 0.8rem 0.9rem !important; }
    h1, .topbar .title { font-size: 20px !important; }
    .stButton > button { width: 100% !important; }
    .brand-hero { padding: 20px 18px; }
    .brand-hero .title { font-size: 20px; }
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════
DB_FILE_PATH = "shop_erp_data.json"

def get_default_db():
    return {
        "offcut_warning_days": 60,
        "low_stock_thresholds": {"glass_sheets": 3, "aluminum_meters": 20.0, "accessories": 5},
        "settings": {"kerf": 3, "edge_trim": 5},
        "features": {"photos": True, "offcut_tracking": True, "sharing": True,
                     "low_stock_alerts": True, "stale_offcut_alerts": True,
                     "print_mode": True, "customer_search": True, "auto_save": True},
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
    status_map = {"Measured": "Started", "Fabricated": "Ongoing", "Delivered": "Ongoing",
                  "Installed": "Ongoing", "Paid": "Completed"}
    for name, proj in db["projects"].items():
        s = proj.get("status", "Started")
        if s in status_map: proj["status"] = status_map[s]
        if "status" not in proj: proj["status"] = "Started"
        if "created" not in proj: proj["created"] = datetime.now().strftime("%Y-%m-%d")
        if "customer" not in proj: proj["customer"] = {"name": "", "phone": "", "address": ""}
        if "photos" not in proj: proj["photos"] = []
        for key in ["glass", "aluminum", "accessories"]:
            if key not in proj: proj[key] = []
    return db

@st.cache_resource
def get_github_client():
    try:
        return Github(auth=Auth.Token(st.secrets["github"]["token"]))
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
    if not db.get("features", {}).get("auto_save", True) and not silent: return True
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

if "db" not in st.session_state: st.session_state.db = load_db()
db = st.session_state.db
feat = db.get("features", {})

# ═══════════════════════════════════════════════════════════════
# NAVIGATION
# ═══════════════════════════════════════════════════════════════
if "view" not in st.session_state: st.session_state.view = "home"
if "active_job" not in st.session_state: st.session_state.active_job = None

def goto(view, job=None):
    st.session_state.view = view
    if job is not None: st.session_state.active_job = job

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
    try: return (datetime.now().date() - datetime.strptime(date_str, "%Y-%m-%d").date()).days
    except Exception: return 0

def offcut_badge(days, warn):
    if days >= int(warn * 1.5): return f"🔴 {days}d", "low"
    if days >= warn: return f"🟠 {days}d", "warn"
    if days >= warn / 2: return f"🟡 {days}d", ""
    return f"🟢 {days}d", ""

def get_stale_offcuts():
    if not feat.get("stale_offcut_alerts", True): return []
    warn = db.get("offcut_warning_days", 60)
    return sorted([r for r in db["inventory"]["remnants"] if days_old(r.get("date_added", "")) >= warn],
                  key=lambda r: r.get("date_added", ""))

def get_low_stock_items():
    if not feat.get("low_stock_alerts", True): return []
    items = []
    for m, s in db["inventory"]["glass"].items():
        if sum(s.values()) <= db["low_stock_thresholds"]["glass_sheets"]:
            items.append({"type": "glass", "name": m, "qty": sum(s.values())})
    for p, mm in db["inventory"]["aluminum"].items():
        if mm <= db["low_stock_thresholds"]["aluminum_meters"]:
            items.append({"type": "aluminum", "name": p, "qty": mm})
    for i, q in db["inventory"]["accessories"].items():
        if q <= db["low_stock_thresholds"]["accessories"]:
            items.append({"type": "accessory", "name": i, "qty": q})
    return items

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
    except Exception: return None

# ═══════════════════════════════════════════════════════════════
# CUTTING MAP — ruler, numbered pieces, cut lines, dimensions
# ═══════════════════════════════════════════════════════════════
def _build_sheet_figure(abin, kerf, title_prefix="Sheet"):
    """Build one cutting sheet figure (used for PNG + PDF)."""
    fig = plt.figure(figsize=(14, 10), dpi=130)
    ax = fig.add_axes([0.09, 0.07, 0.87, 0.86])
    ax.set_xlim(-180, abin.width + 180)
    ax.set_ylim(-180, abin.height + 180)
    ax.set_aspect("equal")

    # Sheet background
    ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height,
                                    facecolor="#FAFBFC", edgecolor="black", linewidth=3))

    # Rulers on all 4 sides
    step = 100 if abin.width < 2500 else 200
    for x in range(0, int(abin.width) + 1, step):
        is_major = (x % 500 == 0)
        ax.plot([x, x], [abin.height, abin.height + (50 if is_major else 25)],
                color="#333" if is_major else "#999", linewidth=1.2 if is_major else 0.8)
        ax.plot([x, x], [0, -(50 if is_major else 25)],
                color="#333" if is_major else "#999", linewidth=1.2 if is_major else 0.8)
        if is_major:
            ax.text(x, abin.height + 65, str(x), ha="center", va="bottom", fontsize=9, color="#333", weight="bold")
            ax.text(x, -65, str(x), ha="center", va="top", fontsize=9, color="#333", weight="bold")

    for y in range(0, int(abin.height) + 1, step):
        is_major = (y % 500 == 0)
        ax.plot([0, -(50 if is_major else 25)], [y, y],
                color="#333" if is_major else "#999", linewidth=1.2 if is_major else 0.8)
        ax.plot([abin.width, abin.width + (50 if is_major else 25)], [y, y],
                color="#333" if is_major else "#999", linewidth=1.2 if is_major else 0.8)
        if is_major:
            ax.text(-65, y, str(y), ha="right", va="center", fontsize=9, color="#333", weight="bold")
            ax.text(abin.width + 65, y, str(y), ha="left", va="center", fontsize=9, color="#333", weight="bold")

    # Red dashed cut lines
    for rect in abin:
        if 0 < rect.x + rect.width < abin.width:
            ax.plot([rect.x + rect.width, rect.x + rect.width], [0, abin.height],
                    color="#E74C3C", linestyle="--", linewidth=1, alpha=0.55)
        if 0 < rect.y + rect.height < abin.height:
            ax.plot([0, abin.width], [rect.y + rect.height, rect.y + rect.height],
                    color="#E74C3C", linestyle="--", linewidth=1, alpha=0.55)

    # Numbered pieces
    sorted_rects = sorted(abin, key=lambda r: (-(r.y + r.height), r.x))
    used = 0
    for idx, rect in enumerate(sorted_rects, start=1):
        pw = rect.width - kerf
        ph = rect.height - kerf
        ax.add_patch(patches.Rectangle((rect.x, rect.y), pw, ph,
                                        facecolor="#D6EAF8", edgecolor="#1F4E79", linewidth=2))
        badge_r = 42
        bx = rect.x + badge_r + 4
        by = rect.y + ph - badge_r - 4
        ax.add_patch(patches.Circle((bx, by), radius=badge_r, facecolor="#1F4E79",
                                     edgecolor="white", linewidth=2, zorder=5))
        ax.text(bx, by, str(idx), ha="center", va="center",
                fontsize=18, color="white", weight="bold", zorder=6)

        cx, cy = rect.x + pw / 2, rect.y + ph / 2
        w_int, h_int = int(pw), int(ph)
        if pw > 250:
            ax.text(cx, rect.y + 12, f"W: {w_int} mm", ha="center", va="bottom",
                    fontsize=10, color="#B03A2E", weight="bold")
        if ph > 250:
            ax.text(rect.x + 12, cy, f"H: {h_int}", ha="left", va="center",
                    fontsize=10, color="#B03A2E", weight="bold", rotation=90)
        if pw > 350 and ph > 200:
            ax.text(cx, cy, f"{w_int} × {h_int}", ha="center", va="center",
                    fontsize=11, color="#1F4E79", weight="bold")
            if rect.rid and rect.rid != "Unnamed":
                ax.text(cx, cy - 30, f"📍 {rect.rid[:24]}", ha="center", va="top",
                        fontsize=8, color="#555", style="italic")
        elif pw > 200 and ph > 100:
            ax.text(cx, cy, f"{w_int}×{h_int}", ha="center", va="center",
                    fontsize=9, color="#1F4E79", weight="bold")
        used += pw * ph

    waste_pct = ((abin.width * abin.height - used) / (abin.width * abin.height)) * 100
    ax.set_title(f"{title_prefix}  ·  Sheet: {int(abin.width)} × {int(abin.height)} mm"
                 f"  ·  {len(abin)} pieces  ·  Waste: {waste_pct:.1f}%",
                 fontsize=13, weight="bold", pad=22)
    ax.axis("off")
    return fig


def render_sheet_png(abin, kerf, title_prefix="Sheet"):
    """Render one sheet as PNG (kept for preview)."""
    fig = _build_sheet_figure(abin, kerf, title_prefix)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def render_all_sheets_pdf(bins, kerf, job_name):
    """Generate ONE PDF containing every cutting sheet. Also returns summary stats."""
    buf = io.BytesIO()
    total_pieces = 0
    total_waste_area = 0
    total_sheet_area = 0

    with PdfPages(buf) as pdf:
        for i, abin in enumerate(bins):
            fig = _build_sheet_figure(abin, kerf, f"Sheet {i+1}")
            pdf.savefig(fig, bbox_inches="tight", facecolor="white")
            plt.close(fig)

            total_pieces += len(abin)
            used = sum((r.width - kerf) * (r.height - kerf) for r in abin)
            total_waste_area += (abin.width * abin.height) - used
            total_sheet_area += abin.width * abin.height

        d = pdf.infodict()
        d['Title'] = f'{job_name} — Cutting Plan'
        d['Author'] = 'Abdiglass and ALM Shop ERP'
        d['Subject'] = f'{len(bins)} sheet(s) · {total_pieces} pieces'
        d['Keywords'] = 'cutting plan glass fabrication'

    buf.seek(0)
    avg_waste = (total_waste_area / total_sheet_area * 100) if total_sheet_area else 0
    return buf.getvalue(), {
        "sheets": len(bins),
        "pieces": total_pieces,
        "avg_waste": avg_waste,
        "total_area_m2": total_sheet_area / 1_000_000,
    }


def parse_bulk_text(text, available_materials):
    """Parse bulk input. Accepts lines: Location, Material, Width, Height, Qty"""
    rows, errors = [], []
    for i, line in enumerate(text.strip().splitlines(), start=1):
        line = line.strip()
        if not line: continue
        parts = [p.strip() for p in line.replace("\t", ",").replace(";", ",").split(",")]
        if len(parts) < 5:
            errors.append(f"Line {i}: need 5 values (Location, Material, Width, Height, Qty)")
            continue
        loc, mat = parts[0], parts[1]
        try:
            w = float(parts[2]); h = float(parts[3]); q = int(float(parts[4]))
        except ValueError:
            errors.append(f"Line {i}: numbers invalid")
            continue
        if w <= 0 or h <= 0 or q <= 0:
            errors.append(f"Line {i}: dimensions/qty must be > 0")
            continue
        if mat not in available_materials:
            errors.append(f"Line {i}: material '{mat}' not in stock")
            continue
        rows.append({"Location": loc or "Unnamed", "Material": mat,
                     "Width": w, "Height": h, "Quantity": q})
    return rows, errors

def empty_state(icon, msg):
    st.markdown(f'<div class="empty"><div class="icon">{icon}</div><div class="msg">{msg}</div></div>',
                unsafe_allow_html=True)

def hsec(text):
    st.markdown(f'<div class="h-sec">{text}</div>', unsafe_allow_html=True)

def status_pill_class(s):
    return {"Started": "pill-started", "Ongoing": "pill-ongoing",
            "Completed": "pill-completed"}.get(s, "pill-started")

# ═══════════════════════════════════════════════════════════════
# PRINT MODE
# ═══════════════════════════════════════════════════════════════
if st.session_state.get("print_mode") and st.session_state.get("generated_bins"):
    st.markdown("""
    <style>
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        footer, .stButton, .stCheckbox, .stAlert, .stLinkButton { display: none !important; }
        .main .block-container { padding: 0 !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.title("🖨️ Cutting Sheets")
    st.caption(f"Job: **{st.session_state.active_job}** — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if st.button("✖ Exit Print Mode", width="stretch"):
        st.session_state.print_mode = False; st.rerun()
    st.divider()
    kerf = st.session_state.get("print_kerf", 3)
    for i, abin in enumerate(st.session_state.generated_bins):
        st.image(render_sheet_png(abin, kerf, f"Sheet {i+1}"), use_container_width=True)
        st.markdown("---")
    st.stop()

# ═══════════════════════════════════════════════════════════════
# ROUTE GUARD
# ═══════════════════════════════════════════════════════════════
if st.session_state.view == "job":
    if not st.session_state.active_job or st.session_state.active_job not in db["projects"]:
        st.session_state.view = "home"; st.session_state.active_job = None

# ═══════════════════════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════════════════════
if st.session_state.view == "home":
    st.markdown(f"""
    <div class="brand-hero">
        <div class="logo">🏭</div>
        <div class="title">Abdiglass and ALM Shop ERP</div>
        <div class="sub">{datetime.now().strftime('%A, %d %b %Y')} · Glass & Aluminum Fabrication</div>
    </div>
    """, unsafe_allow_html=True)

    low = get_low_stock_items()
    stale = get_stale_offcuts()
    if low or stale:
        parts = []
        if low: parts.append(f"🚨 {len(low)} low stock")
        if stale: parts.append(f"⏰ {len(stale)} stale offcuts")
        st.warning(" · ".join(parts))

    jobs = db["projects"]
    active_jobs = [(n, p) for n, p in jobs.items() if p.get("status") in ["Started", "Ongoing"]]
    active_jobs.sort(key=lambda x: x[1].get("created", ""), reverse=True)

    hsec(f"🛠️ Active Jobs ({len(active_jobs)})")
    if not active_jobs:
        empty_state("✅", "No active jobs.")
    else:
        for name, p in active_jobs[:10]:
            status = p.get("status", "Started")
            cust = p.get("customer", {}).get("name", "")
            glass_n = len(p["glass"]); alum_m = sum(a["Meters"] for a in p["aluminum"])
            c1, c2 = st.columns([5, 2])
            with c1:
                st.markdown(f"""<div class="job-card"><div class="row">
                    <div style="flex:1;"><div class="name">🏗️ {name}</div>
                    <div class="sub">{('👤 '+cust+' · ') if cust else ''}🪟 {glass_n} · 📏 {alum_m:.1f}m</div></div>
                    <span class="pill {status_pill_class(status)}">{status}</span>
                </div></div>""", unsafe_allow_html=True)
            with c2:
                st.write("")
                if st.button("Open →", key=f"open_{name}", type="primary", width="stretch"):
                    goto("job", job=name); st.rerun()

    hsec("⚡ Quick Actions")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ New Job", type="primary", width="stretch"):
            st.session_state.show_new_project = True; goto("job"); st.rerun()
    with c2:
        if st.button("📦 Warehouse", width="stretch"):
            goto("warehouse"); st.rerun()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📊 Reports", width="stretch"): goto("reports"); st.rerun()
    with c2:
        if st.button("⚙️ Settings", width="stretch"): goto("settings"); st.rerun()

    hsec("📊 Overview")
    completed = sum(1 for p in jobs.values() if p.get("status") == "Completed")
    glass_sheets = sum(sum(s.values()) for s in db["inventory"]["glass"].values())
    aluminum_m = sum(db["inventory"]["aluminum"].values())
    c1, c2, c3 = st.columns(3)
    c1.metric("Active", len(active_jobs)); c2.metric("Completed", completed); c3.metric("Total", len(jobs))
    c1, c2, c3 = st.columns(3)
    c1.metric("🪟 Sheets", glass_sheets); c2.metric("📏 Alum (m)", f"{aluminum_m:.1f}")
    c3.metric("✂️ Offcuts", len(db["inventory"]["remnants"]))

# ═══════════════════════════════════════════════════════════════
# JOB VIEW
# ═══════════════════════════════════════════════════════════════
elif st.session_state.view == "job":
    if st.session_state.get("show_new_project"):
        c1, c2 = st.columns([1, 9])
        with c1:
            if st.button("←", key="cancel_new"): st.session_state.show_new_project = False; st.rerun()
        with c2: st.markdown('<div class="topbar"><div class="title">New Job</div></div>', unsafe_allow_html=True)
        new_name = st.text_input("Job Name", placeholder="e.g., Villa 4 - Bole")
        if st.button("Create", type="primary", width="stretch"):
            if new_name and new_name.strip() and new_name.strip() not in db["projects"]:
                db["projects"][new_name.strip()] = {
                    "status": "Started", "created": datetime.now().strftime("%Y-%m-%d"),
                    "customer": {"name": "", "phone": "", "address": ""},
                    "photos": [], "glass": [], "aluminum": [], "accessories": []}
                save_db(db)
                st.session_state.show_new_project = False
                goto("job", job=new_name.strip()); st.rerun()
            else: st.error("Invalid or duplicate.")
        st.stop()

    proj = db["projects"][st.session_state.active_job]
    status = proj.get("status", "Started")
    cust = proj.get("customer", {})

    c1, c2 = st.columns([1, 9])
    with c1:
        if st.button("←", key="back_job"): goto("home"); st.rerun()
    with c2:
        st.markdown(f"""<div style="padding:6px 0;">
        <div style="font-size:20px;font-weight:800;color:#14344F;">🏗️ {st.session_state.active_job}</div>
        <div style="font-size:12px;color:#6B7280;">{('👤 '+cust.get('name','')) if cust.get('name') else 'No customer'} · {proj.get('created','-')}</div>
        </div>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    status_icons = {"Started": "🟢", "Ongoing": "🟠", "Completed": "✅"}
    for i, s in enumerate(["Started", "Ongoing", "Completed"]):
        with [c1, c2, c3][i]:
            if st.button(f"{status_icons[s]} {s}", key=f"st_{s}",
                         type="primary" if s == status else "secondary", width="stretch"):
                proj["status"] = s; save_db(db); st.rerun()
    st.divider()

    t_info, t_cut, t_mat, t_photo, t_hist = st.tabs(["📋 Info", "🪟 Cut", "📦 Materials", "📸 Photos", "📜 History"])

    # ===== INFO =====
    with t_info:
        hsec("👤 Customer")
        cname = st.text_input("Name", value=cust.get("name", ""))
        cphone = st.text_input("Phone", value=cust.get("phone", ""))
        caddr = st.text_input("Site Address", value=cust.get("address", ""))
        if st.button("💾 Save Customer", type="primary", width="stretch"):
            proj["customer"] = {"name": cname, "phone": cphone, "address": caddr}
            save_db(db); st.success("Saved!")
        if cphone and feat.get("sharing", True):
            pc = cphone.replace(" ", "").replace("-", "")
            st.link_button("📱 WhatsApp", f"https://wa.me/{pc}?text={quote(f'Hello {cname}, regarding {st.session_state.active_job}')}", width="stretch")
        st.divider()
        with st.expander("⚠️ Danger Zone"):
            if st.button("🗑️ Delete This Job", type="secondary", width="stretch"):
                del db["projects"][st.session_state.active_job]; save_db(db); goto("home"); st.rerun()

    # ===== CUT =====
    with t_cut:
        if not db["inventory"]["glass"]:
            empty_state("🪟", "No glass in warehouse.")
        else:
            mats = list(db["inventory"]["glass"].keys())
            with st.expander("⚙️ Cutting Settings"):
                c1, c2 = st.columns(2)
                with c1: kerf = st.number_input("Kerf (mm)", value=int(db["settings"].get("kerf", 3)), step=1)
                with c2: etrim = st.number_input("Edge Trim (mm)", value=int(db["settings"].get("edge_trim", 5)), step=1)
                if kerf != db["settings"]["kerf"] or etrim != db["settings"]["edge_trim"]:
                    db["settings"]["kerf"] = kerf; db["settings"]["edge_trim"] = etrim
                    save_db(db, silent=True)

            if "form_list" not in st.session_state: st.session_state.form_list = []

            input_mode = st.radio("Input method", ["⚡ Quick Add", "📋 Bulk Paste"], horizontal=True, key="input_mode")

            if input_mode == "⚡ Quick Add":
                hsec("➕ Add One Piece")
                with st.form("add_piece", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        loc = st.text_input("Location", placeholder="e.g., Door 1")
                        mat = st.selectbox("Material", mats)
                    with c2:
                        w = st.number_input("Width (mm)", min_value=1, step=10, value=1000)
                        h = st.number_input("Height (mm)", min_value=1, step=10, value=2000)
                    q = st.number_input("Qty", min_value=1, step=1, value=1)
                    if st.form_submit_button("➕ Add Piece", type="primary", width="stretch"):
                        st.session_state.form_list.append({"Location": loc or "Unnamed", "Material": mat,
                                                            "Width": w, "Height": h, "Quantity": q})
                        st.rerun()
            else:
                hsec("📋 Bulk Paste")
                st.caption("Paste one piece per line. Format: **Location, Material, Width, Height, Qty**")
                st.code("Door 1, 6mm Clear, 915, 1845, 1\nDoor 2, 6mm Clear, 915, 1845, 1\nWindow 1, 4mm Clear, 1070, 2140, 2", language="text")
                bulk_text = st.text_area("Bulk input", height=180, placeholder="Paste here...", key="bulk_area")
                if st.button("📥 Parse & Add All", type="primary", width="stretch"):
                    rows, errs = parse_bulk_text(bulk_text, mats)
                    for e in errs: st.error(e)
                    if rows:
                        st.session_state.form_list.extend(rows)
                        st.success(f"✅ Added {len(rows)} piece(s)")
                        st.rerun()

            if st.session_state.form_list:
                hsec(f"📝 Pieces ({len(st.session_state.form_list)})")
                df = pd.DataFrame(st.session_state.form_list)
                total_area = (df["Width"] * df["Height"] * df["Quantity"]).sum() / 1_000_000
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Pieces", int(df["Quantity"].sum()))
                c2.metric("Total Area", f"{total_area:.2f} m²")
                c3.metric("Unique", df["Material"].nunique())

                for i, item in enumerate(st.session_state.form_list):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"""<div class="card">
                        <div class="title">{i+1}. {item['Location']}</div>
                        <div class="meta">{item['Material']} · {item['Width']} × {item['Height']} mm · Qty <b>{item['Quantity']}</b></div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        if st.button("🗑️", key=f"dl_{i}", width="stretch"):
                            st.session_state.form_list.pop(i); st.rerun()

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ Clear All", width="stretch"):
                        st.session_state.form_list = []; st.rerun()
                with c2:
                    if st.button("🚀 Generate Cutting Plan", type="primary", width="stretch"):
                        df_plan = pd.DataFrame(st.session_state.form_list)
                        bins = []
                        stock = {"2140 x 3300": (2140-etrim, 3300-etrim),
                                 "2140 x 3660": (2140-etrim, 3660-etrim)}
                        for material in df_plan["Material"].unique():
                            mdf = df_plan[df_plan["Material"] == material]
                            p = newPacker(rotation=True)
                            if feat.get("offcut_tracking", True):
                                rems = [r for r in db["inventory"].get("remnants", []) if r["material"] == material]
                                rems.sort(key=lambda r: r.get("date_added", "9999-99-99"))
                                for rem in rems:
                                    p.add_bin(rem["width"]-etrim, rem["height"]-etrim,
                                              bid=f"REMNANT|{rem['id']}|{rem['width']}x{rem['height']}")
                            for sn, d in stock.items():
                                for _ in range(db["inventory"]["glass"][material].get(sn, 0)):
                                    p.add_bin(d[0], d[1], bid=f"{material}|{sn}")
                            for _, row in mdf.iterrows():
                                for _ in range(int(row["Quantity"])):
                                    p.add_rect(float(row["Width"])+kerf, float(row["Height"])+kerf, rid=row["Location"])
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
                empty_state("📐", "Add pieces above.")

            # ===== CUTTING MAPS — ONE PDF + ONE SHARE =====
            if st.session_state.get("generated_bins"):
                st.divider()
                hsec(f"🗺️ Cutting Plan ({len(st.session_state.generated_bins)} sheets)")

                pdf_bytes, stats = render_all_sheets_pdf(
                    st.session_state.generated_bins, kerf, st.session_state.active_job
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("📄 Sheets", stats["sheets"])
                c2.metric("🔢 Pieces", stats["pieces"])
                c3.metric("♻️ Avg Waste", f"{stats['avg_waste']:.1f}%")

                st.download_button(
                    "📥 Download Cutting Plan (PDF · all sheets)",
                    pdf_bytes,
                    f"{st.session_state.active_job}_CuttingPlan.pdf",
                    "application/pdf",
                    type="primary",
                    width="stretch",
                    key="dl_pdf_all",
                )

                c1, c2 = st.columns(2)
                with c1:
                    if feat.get("print_mode", True):
                        if st.button("🖨️ Print Mode", width="stretch"):
                            st.session_state.print_mode = True; st.rerun()
                with c2:
                    if st.button("✅ Done Cutting", width="stretch"):
                        st.session_state.generated_bins = []; st.rerun()

                if feat.get("sharing", True):
                    share_text = (
                        f"🪟 *Cutting Plan — {st.session_state.active_job}*\n"
                        f"📄 Sheets: {stats['sheets']}\n"
                        f"🔢 Pieces: {stats['pieces']}\n"
                        f"♻️ Waste: {stats['avg_waste']:.1f}%\n\n"
                        f"_PDF attached separately._"
                    )
                    enc = quote(share_text)
                    st.caption("📎 **Download the PDF above, then attach it in WhatsApp/Telegram.**")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.link_button("📱 Share on WhatsApp", f"https://wa.me/?text={enc}", width="stretch")
                    with c2:
                        st.link_button("✈️ Share on Telegram", f"https://t.me/share/url?url=&text={enc}", width="stretch")

                # Preview — tabs if multiple sheets, no per-sheet download
                st.divider()
                hsec("👀 Preview")

                if len(st.session_state.generated_bins) > 1:
                    sheet_tabs = st.tabs([f"Sheet {i+1}" for i in range(len(st.session_state.generated_bins))])
                else:
                    sheet_tabs = [st.container()]

                for i, abin in enumerate(st.session_state.generated_bins):
                    with sheet_tabs[i]:
                        png = render_sheet_png(abin, kerf, f"Sheet {i+1}")
                        st.image(png, use_container_width=True)

                        if feat.get("offcut_tracking", True):
                            mx = my = 0
                            for rect in abin:
                                mx = max(mx, rect.x + rect.width)
                                my = max(my, rect.y + rect.height)
                            tw, th = abin.width, abin.height - my
                            rw, rh = abin.width - mx, abin.height
                            off = (int(tw), int(th)) if tw * th >= rw * rh else (int(rw), int(rh))
                            st.caption(f"♻️ Largest leftover: **{off[0]}×{off[1]} mm**")
                            if off[0] > 300 and off[1] > 300:
                                if st.checkbox("Sheet cut? Save offcut?", key=f"c_{i}"):
                                    if st.button("📥 Save Offcut", key=f"sv_{i}", width="stretch"):
                                        mn = abin.bid.split("|")[0]
                                        db["inventory"]["remnants"].append({
                                            "id": str(uuid.uuid4())[:8],
                                            "material": mn,
                                            "width": off[0],
                                            "height": off[1],
                                            "date_added": datetime.now().strftime("%Y-%m-%d"),
                                        })
                                        save_db(db)
                                        st.success("Saved!")

    # ===== MATERIALS =====
    with t_mat:
        hsec("📏 Use Aluminum")
        if not db["inventory"]["aluminum"]:
            empty_state("📏", "No aluminum.")
        else:
            with st.form("use_alum"):
                profile = st.selectbox("Profile", list(db["inventory"]["aluminum"].keys()))
                st.caption(f"Available: **{db['inventory']['aluminum'][profile]:.2f} m**")
                meters = st.number_input("Meters Used", min_value=0.1, step=0.5, value=1.0)
                note = st.text_input("Note")
                if st.form_submit_button("📉 Deduct & Log", type="primary", width="stretch"):
                    if db["inventory"]["aluminum"][profile] >= meters:
                        db["inventory"]["aluminum"][profile] -= meters
                        proj["aluminum"].append({"Profile": profile, "Meters": meters, "Note": note,
                                                  "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success("Logged.")
                    else: st.error("Not enough.")
        st.divider()
        hsec("🔧 Use Accessory")
        if not db["inventory"]["accessories"]:
            empty_state("🔧", "No accessories.")
        else:
            with st.form("use_acc"):
                item = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                st.caption(f"Available: **{db['inventory']['accessories'][item]}**")
                qty = st.number_input("Quantity", min_value=1, step=1, value=1)
                note = st.text_input("Note")
                if st.form_submit_button("📉 Deduct & Log", type="primary", width="stretch"):
                    if db["inventory"]["accessories"][item] >= qty:
                        db["inventory"]["accessories"][item] -= qty
                        proj["accessories"].append({"Item": item, "Qty": qty, "Note": note,
                                                     "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success("Logged.")
                    else: st.error("Not enough.")

    # ===== PHOTOS =====
    with t_photo:
        if not feat.get("photos", True): st.info("Photos disabled in Settings.")
        else:
            hsec("📸 Photos")
            ct, ut = st.tabs(["📷 Camera", "🖼️ Upload"])
            with ct:
                cam = st.camera_input("Take photo")
                if cam and st.button("💾 Save Photo", type="primary", width="stretch"):
                    b64 = compress_image(cam)
                    if b64:
                        proj["photos"].append({"id": str(uuid.uuid4())[:8],
                            "name": f"Cam_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "data": b64})
                        save_db(db); st.rerun()
            with ut:
                ups = st.file_uploader("Upload", type=["jpg","jpeg","png"], accept_multiple_files=True)
                if ups and st.button("💾 Save Uploads", type="primary", width="stretch"):
                    prog = st.progress(0)
                    for idx, f in enumerate(ups):
                        b64 = compress_image(f)
                        if b64:
                            proj["photos"].append({"id": str(uuid.uuid4())[:8], "name": f.name,
                                "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "data": b64})
                        prog.progress((idx+1)/len(ups))
                    save_db(db); st.rerun()
            if proj.get("photos"):
                hsec(f"Photos ({len(proj['photos'])})")
                for i in range(len(proj["photos"])-1, -1, -1):
                    ph = proj["photos"][i]
                    try:
                        st.image(base64.b64decode(ph["data"]), caption=f"{ph['name']} — {ph['date']}", use_container_width=True)
                    except Exception: st.error("Failed")
                    if st.button("🗑️ Delete", key=f"ph_{i}", width="stretch"):
                        proj["photos"].pop(i); save_db(db); st.rerun()
            else: empty_state("📸", "No photos.")

    # ===== HISTORY =====
    with t_hist:
        hsec("🕒 Full Timeline")
        tl = []
        for g in proj["glass"]: tl.append({"Date": g["Date"], "Type": "🪟 Glass", "Detail": f"{g['Location']} — {g['Material']} — {g['Size']}"})
        for a in proj["aluminum"]: tl.append({"Date": a["Date"], "Type": "📏 Aluminum", "Detail": f"{a['Profile']} — {a['Meters']}m"})
        for a in proj["accessories"]: tl.append({"Date": a["Date"], "Type": "🔧 Accessory", "Detail": f"{a['Item']} × {a['Qty']}"})
        if not tl: empty_state("📜", "No activity.")
        else:
            tl.sort(key=lambda x: x["Date"], reverse=True)
            for d in sorted(set(t["Date"] for t in tl), reverse=True):
                st.markdown(f"##### 📅 {d}")
                for t in [x for x in tl if x["Date"] == d]:
                    st.markdown(f'<div class="card"><div class="title">{t["Type"]}</div><div class="meta">{t["Detail"]}</div></div>', unsafe_allow_html=True)
            st.download_button("📥 Export Log", pd.DataFrame(tl).to_csv(index=False).encode("utf-8"),
                                f"{st.session_state.active_job}_Log.csv", "text/csv", width="stretch")

# ═══════════════════════════════════════════════════════════════
# WAREHOUSE
# ═══════════════════════════════════════════════════════════════
elif st.session_state.view == "warehouse":
    c1, c2 = st.columns([1, 9])
    with c1:
        if st.button("←", key="back_wh"): goto("home"); st.rerun()
    with c2:
        st.markdown('<div class="topbar"><div><div class="title">📦 Warehouse</div><div class="subtitle">Stock management</div></div></div>', unsafe_allow_html=True)

    tabs = st.tabs(["🪟 Glass", "✂️ Offcuts", "📏 Aluminum", "🔧 Accessories", "➕ Add Stock"])

    with tabs[0]:
        hsec("🪟 Glass Sheets")
        if db["inventory"]["glass"]:
            for mat, sizes in db["inventory"]["glass"].items():
                total = sum(sizes.values())
                is_low = total <= db["low_stock_thresholds"]["glass_sheets"]
                css = "low" if is_low else "good"
                badge = "🔴 Low" if is_low else "🟢 In Stock"
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""<div class="card {css}">
                    <div class="title">{badge} — {mat}</div>
                    <div class="meta">2140×3300: <b>{sizes.get('2140 x 3300',0)}</b> · 2140×3660: <b>{sizes.get('2140 x 3660',0)}</b> · Total: <b>{total}</b> sheets</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.write("")
                    if st.button("🗑️", key=f"delg_{mat}", width="stretch", help=f"Delete {mat}"):
                        st.session_state[f"confirm_del_g_{mat}"] = True
                if st.session_state.get(f"confirm_del_g_{mat}"):
                    st.warning(f"Delete **{mat}** entirely? ({total} sheets)")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Yes, delete", key=f"yesg_{mat}", type="primary", width="stretch"):
                            del db["inventory"]["glass"][mat]
                            st.session_state[f"confirm_del_g_{mat}"] = False
                            save_db(db); st.rerun()
                    with cc2:
                        if st.button("❌ Cancel", key=f"nog_{mat}", width="stretch"):
                            st.session_state[f"confirm_del_g_{mat}"] = False; st.rerun()
        else: empty_state("🪟", "No glass in stock.")

    with tabs[1]:
        if not feat.get("offcut_tracking", True): st.info("Offcut tracking disabled.")
        else:
            hsec(f"✂️ Offcuts ({len(db['inventory']['remnants'])})")
            if db["inventory"]["remnants"]:
                for r in sorted(db["inventory"]["remnants"], key=lambda x: x.get("date_added", "")):
                    age = days_old(r.get("date_added", ""))
                    label, css = offcut_badge(age, db["offcut_warning_days"])
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"""<div class="card {css}">
                        <div class="title">{r['material']}</div>
                        <div class="meta">{r['width']}×{r['height']} mm · <b>{label}</b> · Added {r.get('date_added','-')}</div>
                        </div>""", unsafe_allow_html=True)
                    with c2:
                        st.write("")
                        if st.button("🗑️", key=f"delr_{r['id']}", width="stretch"):
                            db["inventory"]["remnants"] = [x for x in db["inventory"]["remnants"] if x["id"] != r["id"]]
                            save_db(db); st.rerun()
            else: empty_state("✂️", "No offcuts.")

    with tabs[2]:
        hsec("📏 Aluminum Profiles")
        if db["inventory"]["aluminum"]:
            for k, v in db["inventory"]["aluminum"].items():
                is_low = v <= db["low_stock_thresholds"]["aluminum_meters"]
                css = "low" if is_low else "good"
                badge = "🔴 Low" if is_low else "🟢 OK"
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""<div class="card {css}">
                    <div class="title">{badge} — {k}</div>
                    <div class="meta"><b>{v:.2f} m</b> available</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.write("")
                    if st.button("🗑️", key=f"dela_{k}", width="stretch"):
                        st.session_state[f"confirm_del_a_{k}"] = True
                if st.session_state.get(f"confirm_del_a_{k}"):
                    st.warning(f"Delete **{k}** ({v:.2f}m)?")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Yes", key=f"yesa_{k}", type="primary", width="stretch"):
                            del db["inventory"]["aluminum"][k]
                            st.session_state[f"confirm_del_a_{k}"] = False
                            save_db(db); st.rerun()
                    with cc2:
                        if st.button("❌ No", key=f"noa_{k}", width="stretch"):
                            st.session_state[f"confirm_del_a_{k}"] = False; st.rerun()
        else: empty_state("📏", "No aluminum.")

    with tabs[3]:
        hsec("🔧 Accessories")
        if db["inventory"]["accessories"]:
            for k, v in db["inventory"]["accessories"].items():
                is_low = v <= db["low_stock_thresholds"]["accessories"]
                css = "low" if is_low else "good"
                badge = "🔴 Low" if is_low else "🟢 OK"
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"""<div class="card {css}">
                    <div class="title">{badge} — {k}</div>
                    <div class="meta"><b>{v}</b> pcs</div>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    st.write("")
                    if st.button("🗑️", key=f"delacc_{k}", width="stretch"):
                        st.session_state[f"confirm_del_acc_{k}"] = True
                if st.session_state.get(f"confirm_del_acc_{k}"):
                    st.warning(f"Delete **{k}** ({v} pcs)?")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        if st.button("✅ Yes", key=f"yesacc_{k}", type="primary", width="stretch"):
                            del db["inventory"]["accessories"][k]
                            st.session_state[f"confirm_del_acc_{k}"] = False
                            save_db(db); st.rerun()
                    with cc2:
                        if st.button("❌ No", key=f"noacc_{k}", width="stretch"):
                            st.session_state[f"confirm_del_acc_{k}"] = False; st.rerun()
        else: empty_state("🔧", "No accessories.")

    with tabs[4]:
        hsec("🪟 Add Glass")
        with st.form("add_glass", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Material", ["-- New --"] + db["recent"]["materials"])
                gm = st.text_input("New name", placeholder="e.g., 6mm Clear") if ch == "-- New --" else ch
            with c2:
                gsz = st.selectbox("Sheet Size", ["2140 x 3300", "2140 x 3660"])
                gq = st.number_input("Qty", min_value=1, step=1, value=1)
            if st.form_submit_button("➕ Add Glass", type="primary", width="stretch"):
                if not gm or not gm.strip(): st.error("Name required.")
                else:
                    gm = gm.strip()
                    if gm not in db["inventory"]["glass"]:
                        db["inventory"]["glass"][gm] = {"2140 x 3300": 0, "2140 x 3660": 0}
                    db["inventory"]["glass"][gm][gsz] += gq
                    remember_recent("materials", gm); save_db(db); st.rerun()

        if feat.get("offcut_tracking", True):
            hsec("✂️ Add Offcut")
            if db["inventory"]["glass"]:
                with st.form("add_rem", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        rm = st.selectbox("Material", list(db["inventory"]["glass"].keys()))
                        rw = st.number_input("Width", min_value=100, step=10, value=1000)
                    with c2:
                        rh = st.number_input("Height", min_value=100, step=10, value=1000)
                    if st.form_submit_button("➕ Add Offcut", type="primary", width="stretch"):
                        db["inventory"]["remnants"].append({"id": str(uuid.uuid4())[:8], "material": rm,
                            "width": rw, "height": rh, "date_added": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.rerun()

        hsec("📏 Add Aluminum")
        with st.form("add_alum", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Profile", ["-- New --"] + db["recent"]["aluminum"])
                apr = st.text_input("New profile", placeholder="e.g., 60mm Frame") if ch == "-- New --" else ch
            with c2:
                am = st.number_input("Meters", min_value=1.0, step=1.0, value=6.0)
            if st.form_submit_button("➕ Add Aluminum", type="primary", width="stretch"):
                if not apr or not apr.strip(): st.error("Name required.")
                else:
                    apr = apr.strip()
                    db["inventory"]["aluminum"][apr] = db["inventory"]["aluminum"].get(apr, 0) + am
                    remember_recent("aluminum", apr); save_db(db); st.rerun()

        hsec("🔧 Add Accessory")
        with st.form("add_acc", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                ch = st.selectbox("Item", ["-- New --"] + db["recent"]["accessories"])
                ac = st.text_input("New item", placeholder="e.g., Door Handles") if ch == "-- New --" else ch
            with c2:
                aq = st.number_input("Qty", min_value=1, step=1, value=1)
            if st.form_submit_button("➕ Add Accessory", type="primary", width="stretch"):
                if not ac or not ac.strip(): st.error("Name required.")
                else:
                    ac = ac.strip()
                    db["inventory"]["accessories"][ac] = db["inventory"]["accessories"].get(ac, 0) + aq
                    remember_recent("accessories", ac); save_db(db); st.rerun()

# ═══════════════════════════════════════════════════════════════
# REPORTS
# ═══════════════════════════════════════════════════════════════
elif st.session_state.view == "reports":
    c1, c2 = st.columns([1, 9])
    with c1:
        if st.button("←", key="back_rp"): goto("home"); st.rerun()
    with c2:
        st.markdown('<div class="topbar"><div class="title">📊 Reports</div></div>', unsafe_allow_html=True)

    if not db["projects"]: empty_state("📊", "No jobs yet."); st.stop()

    if feat.get("customer_search", True):
        hsec("🔍 Search")
        q = st.text_input("Search", placeholder="Customer, phone, address", label_visibility="collapsed")
        matched = []
        for n, p in db["projects"].items():
            c = p.get("customer", {})
            hay = f"{n} {c.get('name','')} {c.get('phone','')} {c.get('address','')}".lower()
            if not q or q.lower() in hay: matched.append((n, p))
        if q: st.caption(f"**{len(matched)}** match")
        for n, p in matched[:20]:
            c = p.get("customer", {})
            s = p.get("status", "Started")
            c1, c2 = st.columns([5, 2])
            with c1:
                st.markdown(f"""<div class="job-card"><div class="row">
                    <div style="flex:1;"><div class="name">🏗️ {n}</div>
                    <div class="sub">👤 {c.get('name','—')} · 📞 {c.get('phone','—')}</div></div>
                    <span class="pill {status_pill_class(s)}">{s}</span>
                </div></div>""", unsafe_allow_html=True)
            with c2:
                st.write("")
                if st.button("Open →", key=f"ro_{n}", width="stretch"):
                    goto("job", job=n); st.rerun()

    st.divider()
    hsec("📁 All Jobs")
    ov = []
    for n, p in db["projects"].items():
        ov.append({"Job": n, "Customer": p.get("customer", {}).get("name", ""),
                   "Status": p.get("status", "Started"), "Glass": len(p["glass"]),
                   "Alum m": round(sum(a["Meters"] for a in p["aluminum"]), 1),
                   "Acc": sum(a["Qty"] for a in p["accessories"])})
    st.dataframe(pd.DataFrame(ov), width="stretch", hide_index=True)
    st.download_button("📥 Jobs CSV", pd.DataFrame(ov).to_csv(index=False).encode("utf-8"),
                        "jobs.csv", "text/csv", width="stretch")

# ═══════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════
elif st.session_state.view == "settings":
    c1, c2 = st.columns([1, 9])
    with c1:
        if st.button("←", key="back_st"): goto("home"); st.rerun()
    with c2:
        st.markdown('<div class="topbar"><div class="title">⚙️ Settings</div></div>', unsafe_allow_html=True)

    hsec("🎛️ Features")
    def feat_row(key, name, desc):
        cur = feat.get(key, True)
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f'<div style="padding:8px 0;"><div style="font-weight:700;font-size:14.5px;color:#14344F;">{name}</div><div style="font-size:12.5px;color:#6B7280;">{desc}</div></div>', unsafe_allow_html=True)
        with c2:
            nv = st.toggle("Enable", value=cur, key=f"tog_{key}", label_visibility="collapsed")
            if nv != cur:
                db["features"][key] = nv; save_db(db, silent=True); st.rerun()

    feat_row("photos", "📷 Photos", "Site photos per job")
    feat_row("offcut_tracking", "✂️ Offcuts", "Reuse oldest offcuts first")
    feat_row("sharing", "📱 WhatsApp & Telegram", "Share sheets")
    feat_row("low_stock_alerts", "🚨 Low Stock Alerts", "Warn below thresholds")
    feat_row("stale_offcut_alerts", "⏰ Stale Offcut Alerts", "Warn about old offcuts")
    feat_row("print_mode", "🖨️ Print Mode", "Printable sheets")
    feat_row("customer_search", "🔍 Customer Search", "Search all jobs")
    feat_row("auto_save", "💾 Auto-Save", "Save to GitHub")

    st.divider()
    hsec("📊 Thresholds")
    c1, c2, c3 = st.columns(3)
    with c1: ngs = st.number_input("Glass sheets", min_value=0, max_value=100, value=int(db["low_stock_thresholds"]["glass_sheets"]))
    with c2: nam = st.number_input("Aluminum (m)", min_value=0.0, max_value=1000.0, value=float(db["low_stock_thresholds"]["aluminum_meters"]), step=1.0)
    with c3: nac = st.number_input("Accessories", min_value=0, max_value=1000, value=int(db["low_stock_thresholds"]["accessories"]))
    if ngs != db["low_stock_thresholds"]["glass_sheets"] or nam != db["low_stock_thresholds"]["aluminum_meters"] or nac != db["low_stock_thresholds"]["accessories"]:
        db["low_stock_thresholds"] = {"glass_sheets": ngs, "aluminum_meters": nam, "accessories": nac}
        save_db(db, silent=True)
    nw = st.number_input("⏰ Offcut warning (days)", min_value=7, max_value=365, value=int(db.get("offcut_warning_days", 60)), step=5)
    if nw != db.get("offcut_warning_days", 60): db["offcut_warning_days"] = nw; save_db(db, silent=True)

    st.divider()
    hsec("🔪 Cutting Defaults")
    c1, c2 = st.columns(2)
    with c1: nk = st.number_input("Blade Kerf (mm)", min_value=1, max_value=20, value=int(db["settings"].get("kerf", 3)))
    with c2: ne = st.number_input("Edge Trim (mm)", min_value=0, max_value=50, value=int(db["settings"].get("edge_trim", 5)))
    if nk != db["settings"]["kerf"] or ne != db["settings"]["edge_trim"]:
        db["settings"]["kerf"] = nk; db["settings"]["edge_trim"] = ne; save_db(db, silent=True)

    st.divider()
    hsec("💾 Data")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Backup", json.dumps(db, indent=4),
                            f"abdiglass_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                            "application/json", width="stretch")
    with c2:
        if st.button("🔄 Reload Cloud", width="stretch"):
            get_github_client.clear(); st.session_state.db = load_db(); st.rerun()

    with st.expander("📤 Restore"):
        up = st.file_uploader("Upload backup", type="json")
        if up:
            try:
                st.session_state.db = migrate_db(json.load(up)); save_db(st.session_state.db)
                st.success("Restored!"); st.rerun()
            except Exception as e: st.error(f"Invalid: {e}")

    st.caption(f"**Abdiglass and ALM Shop ERP** · v3.2 · {datetime.now().strftime('%Y')}")
