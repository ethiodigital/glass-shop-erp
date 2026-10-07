import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker
import json
import os
from datetime import datetime
import uuid
import base64
import io
from PIL import Image
from github import Github, GithubException

st.set_page_config(page_title="Shop ERP", layout="wide", page_icon="🏭", initial_sidebar_state="expanded")

# =========================================================
# 1. GITHUB DATABASE LAYER (unchanged from previous version)
# =========================================================
DB_FILE_PATH = "shop_erp_data.json"

def get_default_db():
    return {
        "active_project": None,
        "low_stock_thresholds": {"glass_sheets": 3, "aluminum_meters": 20.0, "accessories": 5},
        "inventory": {"glass": {}, "remnants": [], "aluminum": {}, "accessories": {}},
        "projects": {},
        "recent": {"materials": [], "aluminum": [], "accessories": []}
    }

def migrate_db(db):
    default = get_default_db()
    for key in default:
        if key not in db: db[key] = default[key]
    for key in default["inventory"]:
        if key not in db["inventory"]: db["inventory"][key] = default["inventory"][key]
    if "recent" not in db: db["recent"] = default["recent"]
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
            return migrate_db(json.loads(base64.b64decode(f.content).decode('utf-8')))
        except GithubException as e:
            if e.status == 404:
                d = get_default_db(); save_db(d, silent=True); return d
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

if 'db' not in st.session_state:
    st.session_state.db = load_db()
db = st.session_state.db

def remember_recent(cat, val):
    if not val: return
    lst = db["recent"][cat]
    if val in lst: lst.remove(val)
    lst.insert(0, val)
    db["recent"][cat] = lst[:5]

# =========================================================
# 2. UTILITY: Compress uploaded images
# =========================================================
def compress_image(uploaded_file, max_w=800, quality=60):
    """Resize and compress to ~80KB base64."""
    try:
        img = Image.open(uploaded_file)
        if img.mode != 'RGB': img = img.convert('RGB')
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception as e:
        return None

# =========================================================
# 3. PRINT MODE (early exit if active)
# =========================================================
if st.session_state.get('print_mode') and st.session_state.get('generated_bins'):
    st.markdown("""
    <style>
    @media print {
        header, [data-testid="stSidebar"], [data-testid="stToolbar"],
        [data-testid="stDecoration"], [data-testid="stStatusWidget"],
        footer, .stButton, .stCheckbox, .stAlert { display: none !important; }
        .main .block-container { padding: 0 !important; max-width: 100% !important; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🖨️ Cutting Sheet — Print Preview")
    st.caption(f"Project: **{db.get('active_project', 'N/A')}** — Printed {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.caption("Press Ctrl+P (or Cmd+P) to print. All UI elements are hidden.")
    if st.button("✖ Exit Print Mode"):
        st.session_state.print_mode = False
        st.rerun()
    st.divider()

    kerf = st.session_state.get('print_kerf', 3)
    edge_trim = st.session_state.get('print_edge', 5)

    for i, abin in enumerate(st.session_state.generated_bins):
        st.markdown(f"## Sheet {i+1}: `{abin.bid}`")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.set_xlim(0, abin.width + 5); ax.set_ylim(0, abin.height + 5)
        ax.set_aspect('equal')
        ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor='black', linewidth=2))
        used = 0
        for rect in abin:
            ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width - kerf, rect.height - kerf,
                                            facecolor='#D4E6F1', edgecolor='#1F4E79', linewidth=1.5))
            ax.text(rect.x + (rect.width - kerf)/2, rect.y + (rect.height - kerf)/2,
                    f"{int(rect.width-kerf)}×{int(rect.height-kerf)}\n{rect.rid}",
                    ha='center', va='center', fontsize=11,
                    rotation=90 if rect.height > rect.width else 0,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9))
            used += (rect.width - kerf) * (rect.height - kerf)
        waste = ((abin.width * abin.height - used) / (abin.width * abin.height)) * 100
        plt.title(f"Waste: {waste:.1f}%   |   Sheet size: {int(abin.width)} × {int(abin.height)} mm", fontsize=12)
        plt.tight_layout()
        st.pyplot(fig)
        st.markdown("---")
    st.stop()

# =========================================================
# 4. SIDEBAR
# =========================================================
st.sidebar.title("🏭 Shop ERP")
nav = st.sidebar.radio("Navigate", ["📦 Warehouse", "📋 Projects", "📊 Reports"], label_visibility="collapsed")
st.sidebar.divider()

project_names = list(db["projects"].keys())
active_projects = [p for p in project_names if db["projects"][p].get("status") not in ["Paid", "Cancelled"]]

if active_projects:
    if db["active_project"] not in active_projects: db["active_project"] = active_projects[0]
    active_project = st.sidebar.selectbox("🎯 Active Project", active_projects,
                                            index=active_projects.index(db["active_project"]) if db["active_project"] in active_projects else 0)
    if active_project != db["active_project"]:
        db["active_project"] = active_project; save_db(db, silent=True); st.rerun()
elif project_names:
    st.sidebar.info("All projects closed.")
else:
    st.sidebar.info("No projects yet.")

st.sidebar.divider()

# Low stock alerts
alerts = []
for mat, s in db["inventory"]["glass"].items():
    if sum(s.values()) <= db["low_stock_thresholds"]["glass_sheets"]: alerts.append(f"🪟 {mat}")
for p, m in db["inventory"]["aluminum"].items():
    if m <= db["low_stock_thresholds"]["aluminum_meters"]: alerts.append(f"📏 {p}")
for i, q in db["inventory"]["accessories"].items():
    if q <= db["low_stock_thresholds"]["accessories"]: alerts.append(f"🔧 {i}")

if alerts:
    st.sidebar.subheader("🚨 Low Stock")
    for a in alerts[:6]: st.sidebar.warning(a)

st.sidebar.divider()

with st.sidebar.expander("🔄 Data Sync"):
    st.caption("Auto-saves to GitHub after each action.")
    if st.button("🔄 Reload from GitHub", width='stretch'):
        get_github_client.clear(); st.session_state.db = load_db(); st.rerun()
    st.download_button("📥 Download Backup", json.dumps(db, indent=4),
                        f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json", "application/json", width='stretch')
    up = st.file_uploader("📤 Restore", type="json")
    if up:
        try:
            st.session_state.db = migrate_db(json.load(up)); save_db(st.session_state.db)
            st.success("Restored!"); st.rerun()
        except: st.error("Invalid file.")

# =========================================================
# 5. WAREHOUSE (same as before)
# =========================================================
if nav == "📦 Warehouse":
    st.title("📦 Warehouse")
    st.caption("Physical stock in your shop.")

    wtab1, wtab2 = st.tabs(["👁️ View Stock", "➕ Receive Stock"])

    with wtab1:
        search_term = st.text_input("🔍 Search", placeholder="Search by name...")

        st.subheader("🪟 Glass Sheets")
        if db["inventory"]["glass"]:
            rows = []
            for mat, sizes in db["inventory"]["glass"].items():
                if search_term and search_term.lower() not in mat.lower(): continue
                for size, qty in sizes.items():
                    rows.append({"Material": mat, "Size": size, "Qty": qty,
                                 "Status": "🔴 Low" if qty <= db["low_stock_thresholds"]["glass_sheets"] else "🟢 OK"})
            if rows:
                st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
                with st.expander("🗑️ Delete Glass"):
                    d = st.selectbox("Material", list(db["inventory"]["glass"].keys()))
                    if st.button("Delete", key="dg"):
                        del db["inventory"]["glass"][d]; save_db(db); st.rerun()
            else: st.info("No matches.")
        else: st.info("No glass in stock.")

        st.divider()
        st.subheader("✂️ Remnants")
        if db["inventory"]["remnants"]:
            st.dataframe(pd.DataFrame(db["inventory"]["remnants"]), width='stretch', hide_index=True)
        else: st.info("No offcuts.")

        st.divider()
        st.subheader("📏 Aluminum")
        if db["inventory"]["aluminum"]:
            rows = [{"Profile": k, "Meters": f"{v:.2f}",
                     "Status": "🔴 Low" if v <= db["low_stock_thresholds"]["aluminum_meters"] else "🟢 OK"}
                    for k, v in db["inventory"]["aluminum"].items()]
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
        else: st.info("No aluminum.")

        st.divider()
        st.subheader("🔧 Accessories")
        if db["inventory"]["accessories"]:
            rows = [{"Item": k, "Qty": v,
                     "Status": "🔴 Low" if v <= db["low_stock_thresholds"]["accessories"] else "🟢 OK"}
                    for k, v in db["inventory"]["accessories"].items()]
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
        else: st.info("No accessories.")

    with wtab2:
        st.subheader("🪟 Add Glass Sheets")
        c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
        with c1:
            recent = db["recent"]["materials"]
            choice = st.selectbox("Material", ["-- New --"] + recent, key="gm")
            g_mat = st.text_input("New name", key="gmn") if choice == "-- New --" else choice
        with c2: g_size = st.selectbox("Size", ["2140 x 3300", "2140 x 3660"], key="gs")
        with c3: g_qty = st.number_input("Qty", min_value=1, step=1, key="gq")
        with c4:
            st.write(""); st.write("")
            if st.button("➕ Add", key="ag", width='stretch'):
                if not g_mat or not g_mat.strip(): st.error("Name required.")
                else:
                    g_mat = g_mat.strip()
                    if g_mat not in db["inventory"]["glass"]:
                        db["inventory"]["glass"][g_mat] = {"2140 x 3300": 0, "2140 x 3660": 0}
                    db["inventory"]["glass"][g_mat][g_size] += g_qty
                    remember_recent("materials", g_mat); save_db(db); st.rerun()

        st.divider()
        st.subheader("✂️ Add Offcut")
        if db["inventory"]["glass"]:
            rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
            with rc1: r_mat = st.selectbox("Material", list(db["inventory"]["glass"].keys()), key="rm")
            with rc2: r_w = st.number_input("Width", min_value=100, step=10, key="rw")
            with rc3: r_h = st.number_input("Height", min_value=100, step=10, key="rh")
            with rc4:
                st.write(""); st.write("")
                if st.button("➕ Add", key="ar", width='stretch'):
                    db["inventory"]["remnants"].append({"id": str(uuid.uuid4())[:8], "material": r_mat,
                                                         "width": r_w, "height": r_h,
                                                         "date_added": datetime.now().strftime("%Y-%m-%d")})
                    save_db(db); st.rerun()
        else: st.warning("Add glass first.")

        st.divider()
        st.subheader("📏 Add Aluminum")
        ac1, ac2, ac3 = st.columns([3, 2, 1])
        with ac1:
            recent = db["recent"]["aluminum"]
            choice = st.selectbox("Profile", ["-- New --"] + recent, key="am")
            a_prof = st.text_input("New", key="amn") if choice == "-- New --" else choice
        with ac2: a_m = st.number_input("Meters", min_value=1.0, step=1.0, key="amtr")
        with ac3:
            st.write(""); st.write("")
            if st.button("➕ Add", key="aa", width='stretch'):
                if not a_prof or not a_prof.strip(): st.error("Name required.")
                else:
                    a_prof = a_prof.strip()
                    db["inventory"]["aluminum"][a_prof] = db["inventory"]["aluminum"].get(a_prof, 0) + a_m
                    remember_recent("aluminum", a_prof); save_db(db); st.rerun()

        st.divider()
        st.subheader("🔧 Add Accessories")
        xc1, xc2, xc3 = st.columns([3, 2, 1])
        with xc1:
            recent = db["recent"]["accessories"]
            choice = st.selectbox("Item", ["-- New --"] + recent, key="ac")
            acc = st.text_input("New", key="acn") if choice == "-- New --" else choice
        with xc2: a_q = st.number_input("Qty", min_value=1, step=1, key="acq")
        with xc3:
            st.write(""); st.write("")
            if st.button("➕ Add", key="ax", width='stretch'):
                if not acc or not acc.strip(): st.error("Name required.")
                else:
                    acc = acc.strip()
                    db["inventory"]["accessories"][acc] = db["inventory"]["accessories"].get(acc, 0) + a_q
                    remember_recent("accessories", acc); save_db(db); st.rerun()

# =========================================================
# 6. PROJECTS
# =========================================================
elif nav == "📋 Projects":
    st.title("📋 Projects")

    with st.expander("➕ Create New Project"):
        pc1, pc2 = st.columns([3, 1])
        with pc1: new_proj = st.text_input("Project Name", placeholder="e.g., Villa 4 - Bole")
        with pc2:
            st.write(""); st.write("")
            if st.button("Create", type="primary", width='stretch'):
                if not new_proj or not new_proj.strip(): st.error("Enter name.")
                elif new_proj.strip() in db["projects"]: st.error("Already exists.")
                else:
                    db["projects"][new_proj.strip()] = {
                        "status": "Measured", "created": datetime.now().strftime("%Y-%m-%d"),
                        "customer": {"name": "", "phone": "", "address": ""},
                        "photos": [], "glass": [], "aluminum": [], "accessories": []
                    }
                    db["active_project"] = new_proj.strip()
                    save_db(db); st.rerun()

    if not db["active_project"]:
        st.info("👆 Create a project above."); st.stop()

    proj = db["projects"][db["active_project"]]

    st.divider()
    st.markdown(f"## 🎯 {db['active_project']}")

    # ----- STATUS PROGRESS -----
    STATUSES = ["Measured", "Fabricated", "Delivered", "Installed", "Paid"]
    current_status = proj.get("status", "Measured")
    if current_status == "Cancelled":
        st.error("❌ Project Cancelled")
    else:
        current_idx = STATUSES.index(current_status) if current_status in STATUSES else 0
        progress = (current_idx + 1) / len(STATUSES)
        st.progress(progress, text=f"**{current_status}** — Step {current_idx+1} of {len(STATUSES)}")

    # ----- CUSTOMER INFO -----
    with st.expander("👤 Customer Info", expanded=(proj["customer"]["name"] == "")):
        cu1, cu2 = st.columns(2)
        with cu1:
            cname = st.text_input("Customer Name", value=proj["customer"].get("name", ""))
            cphone = st.text_input("Phone", value=proj["customer"].get("phone", ""))
        with cu2:
            caddr = st.text_input("Site Address", value=proj["customer"].get("address", ""))
        if st.button("💾 Save Customer Info"):
            proj["customer"] = {"name": cname, "phone": cphone, "address": caddr}
            save_db(db); st.success("Saved!")

    # ----- STATUS UPDATE -----
    sc1, sc2 = st.columns([2, 2])
    with sc1:
        new_status = st.selectbox("Update Status", STATUSES + ["Cancelled"],
                                   index=(STATUSES + ["Cancelled"]).index(current_status) if current_status in STATUSES + ["Cancelled"] else 0)
        if new_status != current_status:
            proj["status"] = new_status; save_db(db); st.rerun()

    st.divider()
    ptab1, ptab2, ptab3, ptab4, ptab5 = st.tabs(["🪟 Cut Glass", "📏 Use Aluminum", "🔧 Use Accessories", "📷 Photos", "📜 Log"])

    # ----- CUT GLASS -----
    with ptab1:
        if not db["inventory"]["glass"]:
            st.warning("No glass in warehouse.")
        else:
            entry_mode = st.radio("Entry Mode", ["📱 Form (Phone)", "📊 Table (Desktop)"], horizontal=True)

            col1, col2 = st.columns(2)
            with col1: kerf = st.number_input("Blade Kerf (mm)", value=3, step=1, key="kerf")
            with col2: edge_trim = st.number_input("Edge Trim (mm)", value=5, step=1, key="etrim")

            stock_options = {"2140 x 3300": (2140-edge_trim, 3300-edge_trim), "2140 x 3660": (2140-edge_trim, 3660-edge_trim)}
            material_options = list(db["inventory"]["glass"].keys())

            # --- FORM MODE ---
            if entry_mode == "📱 Form (Phone)":
                if 'form_list' not in st.session_state: st.session_state.form_list = []

                with st.form("add_piece_form", clear_on_submit=True):
                    fc1, fc2 = st.columns(2)
                    with fc1:
                        loc = st.text_input("Location (e.g., Door 1)")
                        mat = st.selectbox("Material", material_options)
                    with fc2:
                        w = st.number_input("Width (mm)", min_value=1, step=10, value=1000)
                        h = st.number_input("Height (mm)", min_value=1, step=10, value=2000)
                    q = st.number_input("Quantity", min_value=1, step=1, value=1)
                    if st.form_submit_button("➕ Add Piece", type="primary", width='stretch'):
                        st.session_state.form_list.append({"Location": loc, "Material": mat, "Width": w, "Height": h, "Quantity": q})
                        st.rerun()

                if st.session_state.form_list:
                    st.markdown(f"**📝 Pieces list ({len(st.session_state.form_list)})**")
                    for i, item in enumerate(st.session_state.form_list):
                        c1, c2 = st.columns([5, 1])
                        with c1:
                            st.write(f"{i+1}. **{item['Location'] or 'Unnamed'}** — {item['Material']} — {item['Width']}×{item['Height']} × {item['Quantity']}")
                        with c2:
                            if st.button("🗑️", key=f"dl_{i}"):
                                st.session_state.form_list.pop(i); st.rerun()
                else:
                    st.info("Add pieces above to begin.")

                has_data = len(st.session_state.form_list) > 0
                if has_data and st.button("🚀 Generate Cutting Plan", type="primary", width='stretch'):
                    edited_df = pd.DataFrame(st.session_state.form_list)
                elif not has_data:
                    edited_df = None
                else:
                    edited_df = None

            # --- TABLE MODE ---
            else:
                if "glass_data" not in st.session_state:
                    st.session_state.glass_data = pd.DataFrame([
                        {"Location": "", "Material": material_options[0] if material_options else "", "Width": 0, "Height": 0, "Quantity": 0}
                    ])
                edited_df = st.data_editor(st.session_state.glass_data, num_rows="dynamic", width='stretch', key="glass_editor")
                if st.button("🚀 Generate Cutting Plan", type="primary", key="gen1"):
                    pass  # handled below

            # --- UNIFIED GENERATION ---
            run_generation = False
            if entry_mode == "📱 Form (Phone)" and edited_df is not None:
                run_generation = True
            elif entry_mode == "📊 Table (Desktop)":
                run_generation = st.button("🚀 Generate Cutting Plan", type="primary", key="gen2", width='stretch')

            if run_generation and edited_df is not None and not edited_df.empty:
                errors = []
                for idx, row in edited_df.iterrows():
                    if not row["Material"]: errors.append(f"Row {idx+1}: No material")
                    if row["Width"] <= 0 or row["Height"] <= 0: errors.append(f"Row {idx+1}: Bad dimensions")
                    if row["Quantity"] <= 0: errors.append(f"Row {idx+1}: Bad quantity")
                if errors:
                    for e in errors[:5]: st.error(e)
                else:
                    all_valid_bins = []
                    for material in edited_df['Material'].unique():
                        mat_df = edited_df[edited_df['Material'] == material]
                        packer = newPacker(rotation=True)
                        for rem in db["inventory"].get('remnants', []):
                            if rem['material'] == material:
                                packer.add_bin(rem['width']-edge_trim, rem['height']-edge_trim,
                                               bid=f"REMNANT|{rem['id']}|{rem['width']}x{rem['height']}")
                        for sheet_name, dims in stock_options.items():
                            for _ in range(db["inventory"]["glass"][material].get(sheet_name, 0)):
                                packer.add_bin(dims[0], dims[1], bid=f"{material}|{sheet_name}")
                        for _, row in mat_df.iterrows():
                            for _ in range(int(row['Quantity'])):
                                packer.add_rect(float(row['Width'])+kerf, float(row['Height'])+kerf, rid=row['Location'] or "Unnamed")
                        packer.pack()
                        valid = [b for b in packer if len(b) > 0]
                        if not valid and not mat_df.empty:
                            st.error(f"❌ Not enough {material}!"); continue
                        for abin in valid:
                            if abin.bid.startswith("REMNANT|"):
                                parts = abin.bid.split("|")
                                db["inventory"]["remnants"] = [r for r in db["inventory"]["remnants"] if r["id"] != parts[1]]
                            else:
                                _, stype = abin.bid.split("|")
                                db["inventory"]["glass"][material][stype] -= 1
                            for rect in abin:
                                proj["glass"].append({"Material": material, "Size": f"{int(rect.width-kerf)}x{int(rect.height-kerf)}",
                                                       "Location": rect.rid, "Date": datetime.now().strftime("%Y-%m-%d")})
                        all_valid_bins.extend(valid)
                    save_db(db)
                    st.session_state.generated_bins = all_valid_bins
                    st.session_state.print_kerf = kerf
                    st.session_state.print_edge = edge_trim

            # --- RENDER MAPS ---
            if st.session_state.get("generated_bins"):
                colA, colB = st.columns([1, 3])
                with colA:
                    if st.button("🖨️ Open Print Mode", type="primary", width='stretch'):
                        st.session_state.print_mode = True; st.rerun()
                with colB:
                    if st.button("✅ Done Cutting — Clear Map", width='stretch'):
                        st.session_state.generated_bins = []
                        if entry_mode == "📱 Form (Phone)": st.session_state.form_list = []
                        st.rerun()

                for i, abin in enumerate(st.session_state.generated_bins):
                    st.markdown(f"#### Sheet {i+1}: `{abin.bid}`")
                    cm, ca = st.columns([3, 1])
                    with cm:
                        fig, ax = plt.subplots(figsize=(6, 6))
                        ax.set_xlim(0, abin.width + 5); ax.set_ylim(0, abin.height + 5); ax.set_aspect('equal')
                        ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor='black', linewidth=2))
                        mx = my = 0; used = 0
                        for rect in abin:
                            ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width-kerf, rect.height-kerf, facecolor='#ADD8E6', edgecolor='#00008B'))
                            ax.text(rect.x+(rect.width-kerf)/2, rect.y+(rect.height-kerf)/2,
                                    f"{int(rect.width-kerf)}x{int(rect.height-kerf)}\n{rect.rid}",
                                    ha='center', va='center', fontsize=7,
                                    rotation=90 if rect.height > rect.width else 0,
                                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
                            mx = max(mx, rect.x + rect.width); my = max(my, rect.y + rect.height)
                            used += (rect.width-kerf) * (rect.height-kerf)
                        wpct = ((abin.width*abin.height - used)/(abin.width*abin.height))*100
                        plt.title(f"Waste: {wpct:.1f}%", color='red', fontsize=10)
                        st.pyplot(fig)
                    with ca:
                        st.markdown("**Offcut**")
                        tw, th = abin.width, abin.height - my
                        rw, rh = abin.width - mx, abin.height
                        off = (int(tw), int(th)) if tw*th >= rw*rh else (int(rw), int(rh))
                        st.caption(f"Largest: **{off[0]}×{off[1]} mm**")
                        if off[0] > 300 and off[1] > 300:
                            if st.checkbox("Cut?", key=f"c_{i}"):
                                if st.button("📥 Save", key=f"s_{i}", width='stretch'):
                                    mat_name = abin.bid.split("|")[0]
                                    db["inventory"]["remnants"].append({"id": str(uuid.uuid4())[:8], "material": mat_name,
                                                                         "width": off[0], "height": off[1],
                                                                         "date_added": datetime.now().strftime("%Y-%m-%d")})
                                    save_db(db); st.success("Saved!")
                        else: st.caption("Too small.")
                    st.divider()

    # ----- ALUMINUM -----
    with ptab2:
        if not db["inventory"]["aluminum"]: st.warning("No aluminum in warehouse.")
        else:
            with st.form("alum_form"):
                profile = st.selectbox("Profile", list(db["inventory"]["aluminum"].keys()))
                st.caption(f"Available: {db['inventory']['aluminum'][profile]:.2f}m")
                meters = st.number_input("Meters Used", min_value=0.1, step=0.1, value=1.0)
                note = st.text_input("Note")
                if st.form_submit_button("📉 Deduct & Log", type="primary"):
                    if db["inventory"]["aluminum"][profile] >= meters:
                        db["inventory"]["aluminum"][profile] -= meters
                        proj["aluminum"].append({"Profile": profile, "Meters": meters, "Note": note, "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success(f"✅ {meters}m logged.")
                    else: st.error("Not enough.")

    # ----- ACCESSORIES -----
    with ptab3:
        if not db["inventory"]["accessories"]: st.warning("No accessories.")
        else:
            with st.form("acc_form"):
                item = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                st.caption(f"Available: {db['inventory']['accessories'][item]}")
                qty = st.number_input("Quantity", min_value=1, step=1, value=1)
                note = st.text_input("Note")
                if st.form_submit_button("📉 Deduct & Log", type="primary"):
                    if db["inventory"]["accessories"][item] >= qty:
                        db["inventory"]["accessories"][item] -= qty
                        proj["accessories"].append({"Item": item, "Qty": qty, "Note": note, "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db); st.success(f"✅ Logged.")
                    else: st.error("Not enough.")

    # ----- PHOTOS -----
    with ptab4:
        st.subheader("📷 Site Photos")
        st.caption("Photos are compressed automatically to ~80KB and stored securely in GitHub.")

        uploaded = st.file_uploader("Upload photos (JPG/PNG)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        if uploaded:
            if st.button("💾 Upload & Save", type="primary"):
                progress_bar = st.progress(0)
                for idx, file in enumerate(uploaded):
                    b64 = compress_image(file)
                    if b64:
                        proj["photos"].append({
                            "id": str(uuid.uuid4())[:8],
                            "name": file.name,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "data": b64
                        })
                    progress_bar.progress((idx + 1) / len(uploaded))
                save_db(db)
                st.success(f"✅ {len(uploaded)} photo(s) uploaded.")
                st.rerun()

        if proj.get("photos"):
            st.divider()
            st.markdown(f"**{len(proj['photos'])} photo(s)**")
            cols = st.columns(3)
            for i, photo in enumerate(proj["photos"]):
                with cols[i % 3]:
                    try:
                        img_bytes = base64.b64decode(photo["data"])
                        st.image(img_bytes, caption=f"{photo['name']} — {photo['date']}", width='stretch')
                    except: st.error("Failed to load")
                    if st.button("🗑️ Delete", key=f"ph_{i}"):
                        proj["photos"].pop(i); save_db(db); st.rerun()
        else:
            st.info("No photos yet.")

    # ----- LOG -----
    with ptab5:
        m1, m2, m3 = st.columns(3)
        m1.metric("Glass Pieces", len(proj["glass"]))
        m2.metric("Aluminum (m)", f"{sum(a['Meters'] for a in proj['aluminum']):.2f}")
        m3.metric("Accessories", sum(a["Qty"] for a in proj["accessories"]))

        st.divider()
        st.subheader("🪟 Glass")
        if proj["glass"]: st.dataframe(pd.DataFrame(proj["glass"]), width='stretch', hide_index=True)
        else: st.caption("None")

        st.subheader("📏 Aluminum")
        if proj["aluminum"]: st.dataframe(pd.DataFrame(proj["aluminum"]), width='stretch', hide_index=True)
        else: st.caption("None")

        st.subheader("🔧 Accessories")
        if proj["accessories"]: st.dataframe(pd.DataFrame(proj["accessories"]), width='stretch', hide_index=True)
        else: st.caption("None")

        st.divider()
        with st.expander("⚠️ Danger Zone"):
            if st.button("🗑️ Delete this project", type="secondary"):
                del db["projects"][db["active_project"]]
                db["active_project"] = None
                save_db(db); st.rerun()

# =========================================================
# 7. REPORTS
# =========================================================
elif nav == "📊 Reports":
    st.title("📊 Reports")

    if not db["projects"]: st.info("No projects."); st.stop()

    st.subheader("📁 All Projects")
    overview = []
    for name, proj in db["projects"].items():
        overview.append({
            "Project": name,
            "Customer": proj.get("customer", {}).get("name", ""),
            "Status": proj.get("status", "Measured"),
            "Created": proj.get("created", "-"),
            "Glass": len(proj["glass"]),
            "Alum (m)": round(sum(a["Meters"] for a in proj["aluminum"]), 2),
            "Acc": sum(a["Qty"] for a in proj["accessories"]),
            "Photos": len(proj.get("photos", []))
        })
    st.dataframe(pd.DataFrame(overview), width='stretch', hide_index=True)

    st.divider()
    st.subheader("📥 Export")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 All Projects (CSV)",
                            pd.DataFrame(overview).to_csv(index=False).encode('utf-8'),
                            "projects.csv", "text/csv", width='stretch')
    with c2:
        inv_rows = []
        for m, s in db["inventory"]["glass"].items():
            for sz, q in s.items(): inv_rows.append({"Type": "Glass", "Name": m, "Detail": sz, "Qty": q})
        for p, m in db["inventory"]["aluminum"].items(): inv_rows.append({"Type": "Aluminum", "Name": p, "Detail": "m", "Qty": m})
        for i, q in db["inventory"]["accessories"].items(): inv_rows.append({"Type": "Accessory", "Name": i, "Detail": "pcs", "Qty": q})
        for r in db["inventory"]["remnants"]: inv_rows.append({"Type": "Remnant", "Name": r["material"], "Detail": f"{r['width']}x{r['height']}", "Qty": 1})
        st.download_button("📥 Inventory (CSV)",
                            pd.DataFrame(inv_rows).to_csv(index=False).encode('utf-8'),
                            "inventory.csv", "text/csv", width='stretch')
