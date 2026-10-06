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
from github import Github, GithubException

st.set_page_config(page_title="Shop ERP", layout="wide", page_icon="🏭", initial_sidebar_state="expanded")

# =========================================================
# 1. GITHUB DATABASE LAYER
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
        if "status" not in proj: proj["status"] = "Active"
        if "created" not in proj: proj["created"] = datetime.now().strftime("%Y-%m-%d")
        for key in ["glass", "aluminum", "accessories"]:
            if key not in proj: proj[key] = []
    return db

@st.cache_resource
def get_github_client():
    """Cached GitHub client (reuses connection)."""
    try:
        token = st.secrets["github"]["token"]
        return Github(token)
    except Exception as e:
        st.error(f"❌ GitHub token not configured. See sidebar setup guide.")
        return None

def load_db():
    """Load data from GitHub repo. Falls back to default if not found."""
    client = get_github_client()
    if client is None:
        return get_default_db()
    
    try:
        repo_name = st.secrets["github"]["repo"]
        repo = client.get_repo(repo_name)
        try:
            file = repo.get_contents(DB_FILE_PATH)
            content = base64.b64decode(file.content).decode('utf-8')
            return migrate_db(json.loads(content))
        except GithubException as e:
            if e.status == 404:
                # File doesn't exist yet — create it with defaults
                default = get_default_db()
                save_db(default, silent=True)
                return default
            raise e
    except Exception as e:
        st.warning(f"⚠️ Could not load from GitHub. Using temporary session data. Error: {e}")
        return get_default_db()

def save_db(db, silent=False):
    """Save data to GitHub repo."""
    client = get_github_client()
    if client is None:
        return False
    
    try:
        repo_name = st.secrets["github"]["repo"]
        repo = client.get_repo(repo_name)
        content = json.dumps(db, indent=4)
        commit_msg = f"Update data — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            file = repo.get_contents(DB_FILE_PATH)
            repo.update_file(DB_FILE_PATH, commit_msg, content, file.sha)
        except GithubException as e:
            if e.status == 404:
                repo.create_file(DB_FILE_PATH, commit_msg, content)
            else:
                raise e
        
        if not silent:
            st.toast("💾 Saved to GitHub", icon="✅")
        return True
    except Exception as e:
        if not silent:
            st.error(f"❌ Failed to save: {e}")
        return False

def force_reload():
    """Clear cache and reload from GitHub."""
    get_github_client.clear()
    st.session_state.db = load_db()
    st.rerun()

if 'db' not in st.session_state:
    st.session_state.db = load_db()

db = st.session_state.db

def remember_recent(category, value):
    if not value: return
    lst = db["recent"][category]
    if value in lst: lst.remove(value)
    lst.insert(0, value)
    db["recent"][category] = lst[:5]

# =========================================================
# 2. SIDEBAR
# =========================================================
st.sidebar.title("🏭 Shop ERP")

nav = st.sidebar.radio(
    "Navigate",
    ["📦 Warehouse", "📋 Projects", "📊 Reports"],
    label_visibility="collapsed"
)

st.sidebar.divider()

project_names = list(db["projects"].keys())
active_projects = [p for p in project_names if db["projects"][p].get("status", "Active") == "Active"]

if active_projects:
    if db["active_project"] not in active_projects:
        db["active_project"] = active_projects[0]
    active_project = st.sidebar.selectbox(
        "🎯 Active Project",
        active_projects,
        index=active_projects.index(db["active_project"]) if db["active_project"] in active_projects else 0
    )
    if active_project != db["active_project"]:
        db["active_project"] = active_project
        save_db(db, silent=True)
        st.rerun()
elif project_names:
    st.sidebar.warning("No active projects.")
else:
    st.sidebar.info("No projects yet.")

st.sidebar.divider()

# Low stock alerts
alerts = []
for mat, sizes in db["inventory"]["glass"].items():
    if sum(sizes.values()) <= db["low_stock_thresholds"]["glass_sheets"]:
        alerts.append(f"🪟 {mat}")
for profile, meters in db["inventory"]["aluminum"].items():
    if meters <= db["low_stock_thresholds"]["aluminum_meters"]:
        alerts.append(f"📏 {profile}")
for item, qty in db["inventory"]["accessories"].items():
    if qty <= db["low_stock_thresholds"]["accessories"]:
        alerts.append(f"🔧 {item}")

if alerts:
    st.sidebar.subheader("🚨 Low Stock")
    for a in alerts[:6]: st.sidebar.warning(a)

st.sidebar.divider()

# Data sync controls
with st.sidebar.expander("🔄 Data Sync"):
    st.caption("Data auto-saves to GitHub after every action.")
    if st.button("🔄 Reload from GitHub", width='stretch'):
        force_reload()
    st.download_button(
        "📥 Download Backup",
        json.dumps(db, indent=4),
        f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        "application/json",
        width='stretch'
    )
    uploaded = st.file_uploader("📤 Restore from Backup", type="json")
    if uploaded:
        try:
            new_db = migrate_db(json.load(uploaded))
            st.session_state.db = new_db
            save_db(new_db)
            st.success("Restored!")
            st.rerun()
        except:
            st.error("Invalid file.")

# =========================================================
# 3. WAREHOUSE
# =========================================================
if nav == "📦 Warehouse":
    st.title("📦 Warehouse")
    st.caption("Physical stock in your shop.")

    wtab1, wtab2 = st.tabs(["👁️ View Stock", "➕ Receive Stock"])

    with wtab1:
        col_search, _ = st.columns([2, 3])
        with col_search:
            search_term = st.text_input("🔍 Search", placeholder="Search by name...")

        st.subheader("🪟 Glass Sheets")
        if db["inventory"]["glass"]:
            rows = []
            for mat, sizes in db["inventory"]["glass"].items():
                if search_term and search_term.lower() not in mat.lower(): continue
                for size, qty in sizes.items():
                    rows.append({"Material": mat, "Sheet Size": size, "Qty": qty,
                                 "Status": "🔴 Low" if qty <= db["low_stock_thresholds"]["glass_sheets"] else "🟢 OK"})
            if rows:
                st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
                with st.expander("🗑️ Delete a Glass Material"):
                    del_glass = st.selectbox("Select material", list(db["inventory"]["glass"].keys()), key="del_glass")
                    if st.button("Delete", type="secondary"):
                        del db["inventory"]["glass"][del_glass]
                        save_db(db); st.rerun()
            else: st.info("No matches.")
        else: st.info("No glass in stock.")

        st.divider()
        st.subheader("✂️ Remnants (Offcuts)")
        if db["inventory"]["remnants"]:
            st.dataframe(pd.DataFrame(db["inventory"]["remnants"]), width='stretch', hide_index=True)
            with st.expander("🗑️ Delete a Remnant"):
                rem_options = {f"{r['material']} - {r['width']}x{r['height']}": r["id"] for r in db["inventory"]["remnants"]}
                to_del = st.selectbox("Select remnant", list(rem_options.keys()))
                if st.button("Delete Remnant", key="del_rem_btn"):
                    db["inventory"]["remnants"] = [r for r in db["inventory"]["remnants"] if r["id"] != rem_options[to_del]]
                    save_db(db); st.rerun()
        else: st.info("No offcuts tracked.")

        st.divider()
        st.subheader("📏 Aluminum Profiles")
        if db["inventory"]["aluminum"]:
            rows = [{"Profile": k, "Meters": f"{v:.2f}",
                     "Status": "🔴 Low" if v <= db["low_stock_thresholds"]["aluminum_meters"] else "🟢 OK"}
                    for k, v in db["inventory"]["aluminum"].items() if not search_term or search_term.lower() in k.lower()]
            if rows: st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
            with st.expander("🗑️ Delete Aluminum"):
                del_alum = st.selectbox("Profile", list(db["inventory"]["aluminum"].keys()))
                if st.button("Delete", key="del_alum_btn"):
                    del db["inventory"]["aluminum"][del_alum]
                    save_db(db); st.rerun()
        else: st.info("No aluminum.")

        st.divider()
        st.subheader("🔧 Accessories")
        if db["inventory"]["accessories"]:
            rows = [{"Item": k, "Qty": v,
                     "Status": "🔴 Low" if v <= db["low_stock_thresholds"]["accessories"] else "🟢 OK"}
                    for k, v in db["inventory"]["accessories"].items() if not search_term or search_term.lower() in k.lower()]
            if rows: st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)
            with st.expander("🗑️ Delete Accessory"):
                del_acc = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                if st.button("Delete", key="del_acc_btn"):
                    del db["inventory"]["accessories"][del_acc]
                    save_db(db); st.rerun()
        else: st.info("No accessories.")

    with wtab2:
        st.caption("Add new materials.")

        st.subheader("🪟 Add Glass Sheets")
        gc1, gc2, gc3, gc4 = st.columns([3, 2, 1, 1])
        with gc1:
            recent_mats = db["recent"]["materials"]
            g_mat_choice = st.selectbox("Material", ["-- New --"] + recent_mats, key="g_mat_choice")
            g_mat = st.text_input("New name", key="g_mat_new") if g_mat_choice == "-- New --" else g_mat_choice
        with gc2: g_size = st.selectbox("Size", ["2140 x 3300", "2140 x 3660"], key="g_size")
        with gc3: g_qty = st.number_input("Qty", min_value=1, step=1, key="g_qty")
        with gc4:
            st.write(""); st.write("")
            if st.button("➕ Add", key="add_glass_btn", width='stretch'):
                if not g_mat or not g_mat.strip(): st.error("Enter name.")
                else:
                    g_mat = g_mat.strip()
                    if g_mat not in db["inventory"]["glass"]:
                        db["inventory"]["glass"][g_mat] = {"2140 x 3300": 0, "2140 x 3660": 0}
                    db["inventory"]["glass"][g_mat][g_size] += g_qty
                    remember_recent("materials", g_mat)
                    save_db(db); st.rerun()

        st.divider()
        st.subheader("✂️ Add Offcut")
        if not db["inventory"]["glass"]:
            st.warning("Add glass first.")
        else:
            rc1, rc2, rc3, rc4 = st.columns([3, 2, 2, 1])
            with rc1: r_mat = st.selectbox("Material", list(db["inventory"]["glass"].keys()))
            with rc2: r_width = st.number_input("Width (mm)", min_value=100, step=10)
            with rc3: r_height = st.number_input("Height (mm)", min_value=100, step=10)
            with rc4:
                st.write(""); st.write("")
                if st.button("➕ Add", key="add_rem_btn", width='stretch'):
                    db["inventory"]["remnants"].append({
                        "id": str(uuid.uuid4())[:8], "material": r_mat,
                        "width": r_width, "height": r_height,
                        "date_added": datetime.now().strftime("%Y-%m-%d")
                    })
                    save_db(db); st.rerun()

        st.divider()
        st.subheader("📏 Add Aluminum")
        ac1, ac2, ac3 = st.columns([3, 2, 1])
        with ac1:
            recent_alum = db["recent"]["aluminum"]
            a_prof_choice = st.selectbox("Profile", ["-- New --"] + recent_alum)
            a_prof = st.text_input("New profile", key="a_prof_new") if a_prof_choice == "-- New --" else a_prof_choice
        with ac2: a_meters = st.number_input("Meters", min_value=1.0, step=1.0)
        with ac3:
            st.write(""); st.write("")
            if st.button("➕ Add", key="add_alum_btn", width='stretch'):
                if not a_prof or not a_prof.strip(): st.error("Enter name.")
                else:
                    a_prof = a_prof.strip()
                    db["inventory"]["aluminum"][a_prof] = db["inventory"]["aluminum"].get(a_prof, 0) + a_meters
                    remember_recent("aluminum", a_prof)
                    save_db(db); st.rerun()

        st.divider()
        st.subheader("🔧 Add Accessories")
        xc1, xc2, xc3 = st.columns([3, 2, 1])
        with xc1:
            recent_acc = db["recent"]["accessories"]
            acc_choice = st.selectbox("Accessory", ["-- New --"] + recent_acc)
            acc_item = st.text_input("New name", key="acc_new") if acc_choice == "-- New --" else acc_choice
        with xc2: acc_qty = st.number_input("Qty", min_value=1, step=1)
        with xc3:
            st.write(""); st.write("")
            if st.button("➕ Add", key="add_acc_btn", width='stretch'):
                if not acc_item or not acc_item.strip(): st.error("Enter name.")
                else:
                    acc_item = acc_item.strip()
                    db["inventory"]["accessories"][acc_item] = db["inventory"]["accessories"].get(acc_item, 0) + acc_qty
                    remember_recent("accessories", acc_item)
                    save_db(db); st.rerun()

# =========================================================
# 4. PROJECTS
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
                        "status": "Active",
                        "created": datetime.now().strftime("%Y-%m-%d"),
                        "glass": [], "aluminum": [], "accessories": []
                    }
                    db["active_project"] = new_proj.strip()
                    save_db(db); st.rerun()

    if not db["active_project"]:
        st.info("👆 Create a project above.")
        st.stop()

    st.divider()
    st.markdown(f"### 🎯 Working on: **{db['active_project']}**")
    proj = db["projects"][db["active_project"]]

    sc1, _ = st.columns([2, 3])
    with sc1:
        new_status = st.selectbox("Status", ["Active", "Completed", "Archived"],
                                   index=["Active", "Completed", "Archived"].index(proj.get("status", "Active")))
        if new_status != proj.get("status"):
            proj["status"] = new_status
            save_db(db); st.rerun()

    ptab1, ptab2, ptab3, ptab4 = st.tabs(["🪟 Cut Glass", "📏 Use Aluminum", "🔧 Use Accessories", "📜 Log"])

    with ptab1:
        if not db["inventory"]["glass"]:
            st.warning("No glass in warehouse.")
        else:
            col1, col2 = st.columns(2)
            with col1: kerf = st.number_input("Blade Kerf (mm)", value=3, step=1, key="kerf")
            with col2: edge_trim = st.number_input("Edge Trim (mm)", value=5, step=1, key="etrim")

            stock_options = {
                "2140 x 3300": (2140 - edge_trim, 3300 - edge_trim),
                "2140 x 3660": (2140 - edge_trim, 3660 - edge_trim)
            }
            material_options = list(db["inventory"]["glass"].keys())

            if "glass_data" not in st.session_state:
                st.session_state.glass_data = pd.DataFrame([
                    {"Location": "", "Material": material_options[0] if material_options else "",
                     "Width": 0, "Height": 0, "Quantity": 0}
                ])

            edited_df = st.data_editor(st.session_state.glass_data, num_rows="dynamic",
                                        width='stretch', key="glass_editor")

            if st.button("🚀 Generate Cutting Plan", type="primary"):
                errors = []
                for idx, row in edited_df.iterrows():
                    if not row["Material"]: errors.append(f"Row {idx+1}: No material")
                    if row["Width"] <= 0 or row["Height"] <= 0: errors.append(f"Row {idx+1}: Bad dimensions")
                    if row["Quantity"] <= 0: errors.append(f"Row {idx+1}: Bad quantity")
                if errors:
                    for e in errors[:5]: st.error(e)
                else:
                    materials = edited_df['Material'].unique()
                    all_valid_bins = []

                    for material in materials:
                        mat_df = edited_df[edited_df['Material'] == material]
                        packer = newPacker(rotation=True)

                        for rem in db["inventory"].get('remnants', []):
                            if rem['material'] == material:
                                packer.add_bin(rem['width'] - edge_trim, rem['height'] - edge_trim,
                                               bid=f"REMNANT|{rem['id']}|{rem['width']}x{rem['height']}")

                        for sheet_name, dims in stock_options.items():
                            w, h = dims
                            for _ in range(db["inventory"]["glass"][material].get(sheet_name, 0)):
                                packer.add_bin(w, h, bid=f"{material}|{sheet_name}")

                        for _, row in mat_df.iterrows():
                            for _ in range(int(row['Quantity'])):
                                packer.add_rect(float(row['Width']) + kerf, float(row['Height']) + kerf,
                                                rid=row['Location'] or "Unnamed")

                        packer.pack()
                        valid_bins = [b for b in packer if len(b) > 0]

                        if not valid_bins and not mat_df.empty:
                            st.error(f"❌ Not enough {material}!")
                            continue

                        for abin in valid_bins:
                            if abin.bid.startswith("REMNANT|"):
                                parts = abin.bid.split("|")
                                db["inventory"]["remnants"] = [r for r in db["inventory"]["remnants"] if r["id"] != parts[1]]
                            else:
                                _, sheet_type = abin.bid.split("|")
                                db["inventory"]["glass"][material][sheet_type] -= 1
                            for rect in abin:
                                proj["glass"].append({
                                    "Material": material,
                                    "Size": f"{int(rect.width - kerf)}x{int(rect.height - kerf)}",
                                    "Location": rect.rid,
                                    "Date": datetime.now().strftime("%Y-%m-%d")
                                })
                        all_valid_bins.extend(valid_bins)

                    save_db(db)
                    st.session_state.generated_bins = all_valid_bins

            if st.session_state.get("generated_bins"):
                st.success("✅ Plan generated! Log offcuts before cutting next sheet.")
                for i, abin in enumerate(st.session_state.generated_bins):
                    st.markdown(f"#### Sheet {i+1}: `{abin.bid}`")
                    col_map, col_actions = st.columns([3, 1])
                    with col_map:
                        fig, ax = plt.subplots(figsize=(6, 6))
                        ax.set_xlim(0, abin.width + 5); ax.set_ylim(0, abin.height + 5)
                        ax.set_aspect('equal')
                        ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor='black', linewidth=2))
                        max_x = max_y = 0; used_area = 0
                        for rect in abin:
                            ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width - kerf, rect.height - kerf, facecolor='#ADD8E6', edgecolor='#00008B'))
                            ax.text(rect.x + (rect.width - kerf)/2, rect.y + (rect.height - kerf)/2,
                                    f"{int(rect.width-kerf)}x{int(rect.height-kerf)}\n{rect.rid}",
                                    ha='center', va='center', fontsize=7,
                                    rotation=90 if rect.height > rect.width else 0,
                                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
                            max_x = max(max_x, rect.x + rect.width); max_y = max(max_y, rect.y + rect.height)
                            used_area += (rect.width - kerf) * (rect.height - kerf)
                        waste_pct = ((abin.width * abin.height - used_area) / (abin.width * abin.height)) * 100
                        plt.title(f"Waste: {waste_pct:.1f}%", color='red', fontsize=10)
                        st.pyplot(fig)

                    with col_actions:
                        st.markdown("**Offcut**")
                        top_w, top_h = abin.width, abin.height - max_y
                        right_w, right_h = abin.width - max_x, abin.height
                        offcut = (int(top_w), int(top_h)) if top_w * top_h >= right_w * right_h else (int(right_w), int(right_h))
                        st.caption(f"Largest: **{offcut[0]}×{offcut[1]} mm**")
                        if offcut[0] > 300 and offcut[1] > 300:
                            if st.checkbox("Sheet cut?", key=f"cut_{i}"):
                                if st.button("📥 Save offcut", key=f"log_{i}", width='stretch'):
                                    mat_name = abin.bid.split("|")[0]
                                    db["inventory"]["remnants"].append({
                                        "id": str(uuid.uuid4())[:8], "material": mat_name,
                                        "width": offcut[0], "height": offcut[1],
                                        "date_added": datetime.now().strftime("%Y-%m-%d")
                                    })
                                    save_db(db)
                                    st.success("Saved!")
                        else:
                            st.caption("Too small.")
                    st.divider()

                if st.button("✅ Done Cutting"):
                    st.session_state.generated_bins = []
                    st.rerun()

    with ptab2:
        if not db["inventory"]["aluminum"]:
            st.warning("No aluminum in warehouse.")
        else:
            with st.form("use_alum_form"):
                profile = st.selectbox("Profile", list(db["inventory"]["aluminum"].keys()))
                st.caption(f"Available: {db['inventory']['aluminum'][profile]:.2f}m")
                meters = st.number_input("Meters Used", min_value=0.1, step=0.1, value=1.0)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("📉 Deduct & Log", type="primary"):
                    if db["inventory"]["aluminum"][profile] >= meters:
                        db["inventory"]["aluminum"][profile] -= meters
                        proj["aluminum"].append({"Profile": profile, "Meters": meters, "Note": note,
                                                  "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db)
                        st.success(f"✅ {meters}m logged.")
                    else:
                        st.error(f"❌ Only {db['inventory']['aluminum'][profile]:.2f}m available.")

    with ptab3:
        if not db["inventory"]["accessories"]:
            st.warning("No accessories in warehouse.")
        else:
            with st.form("use_acc_form"):
                item = st.selectbox("Accessory", list(db["inventory"]["accessories"].keys()))
                st.caption(f"Available: {db['inventory']['accessories'][item]}")
                qty = st.number_input("Quantity", min_value=1, step=1, value=1)
                note = st.text_input("Note (optional)")
                if st.form_submit_button("📉 Deduct & Log", type="primary"):
                    if db["inventory"]["accessories"][item] >= qty:
                        db["inventory"]["accessories"][item] -= qty
                        proj["accessories"].append({"Item": item, "Qty": qty, "Note": note,
                                                     "Date": datetime.now().strftime("%Y-%m-%d")})
                        save_db(db)
                        st.success(f"✅ {qty}× logged.")
                    else:
                        st.error(f"❌ Only {db['inventory']['accessories'][item]} available.")

    with ptab4:
        st.markdown(f"**Glass:** {len(proj['glass'])} | **Alum:** {sum(a['Meters'] for a in proj['aluminum']):.2f}m | **Acc:** {sum(a['Qty'] for a in proj['accessories'])}")

        if proj["glass"]: st.dataframe(pd.DataFrame(proj["glass"]), width='stretch', hide_index=True)
        else: st.caption("No glass yet.")

        if proj["aluminum"]: st.dataframe(pd.DataFrame(proj["aluminum"]), width='stretch', hide_index=True)
        else: st.caption("No aluminum yet.")

        if proj["accessories"]: st.dataframe(pd.DataFrame(proj["accessories"]), width='stretch', hide_index=True)
        else: st.caption("No accessories yet.")

        with st.expander("⚠️ Danger Zone"):
            if st.button("🗑️ Delete project", type="secondary"):
                del db["projects"][db["active_project"]]
                db["active_project"] = None
                save_db(db); st.rerun()

# =========================================================
# 5. REPORTS
# =========================================================
elif nav == "📊 Reports":
    st.title("📊 Reports")

    if not db["projects"]:
        st.info("No projects yet.")
        st.stop()

    st.subheader("📁 All Projects")
    overview = []
    for name, proj in db["projects"].items():
        overview.append({
            "Project": name, "Status": proj.get("status", "Active"),
            "Created": proj.get("created", "-"),
            "Glass Pieces": len(proj["glass"]),
            "Aluminum (m)": round(sum(a["Meters"] for a in proj["aluminum"]), 2),
            "Accessories": sum(a["Qty"] for a in proj["accessories"])
        })
    st.dataframe(pd.DataFrame(overview), width='stretch', hide_index=True)

    st.divider()
    st.subheader("📥 Export")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 All Projects (CSV)",
                            pd.DataFrame(overview).to_csv(index=False).encode('utf-8'),
                            "all_projects.csv", "text/csv", width='stretch')
    with c2:
        inv_rows = []
        for mat, sizes in db["inventory"]["glass"].items():
            for size, qty in sizes.items():
                inv_rows.append({"Type": "Glass", "Name": mat, "Detail": size, "Qty": qty})
        for profile, m in db["inventory"]["aluminum"].items():
            inv_rows.append({"Type": "Aluminum", "Name": profile, "Detail": "m", "Qty": m})
        for item, q in db["inventory"]["accessories"].items():
            inv_rows.append({"Type": "Accessory", "Name": item, "Detail": "pcs", "Qty": q})
        for r in db["inventory"]["remnants"]:
            inv_rows.append({"Type": "Remnant", "Name": r["material"], "Detail": f"{r['width']}x{r['height']}", "Qty": 1})
        st.download_button("📥 Inventory (CSV)",
                            pd.DataFrame(inv_rows).to_csv(index=False).encode('utf-8'),
                            "inventory.csv", "text/csv", width='stretch')
