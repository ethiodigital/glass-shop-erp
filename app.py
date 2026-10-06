import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker
import json
import os
from datetime import datetime

st.set_page_config(page_title="Fabrication Shop ERP", layout="wide", page_icon="🏭")

# ==========================================
# DATABASE SETUP & MIGRATION (FIXES CRASHES)
# ==========================================
DB_FILE = "shop_erp_data.json"

def get_default_db():
    return {
        "active_project": "General / Unassigned",
        "inventory": {
            "glass": {},      
            "remnants": [],   
            "aluminum": {},   
            "accessories": {} 
        },
        "projects": {
            "General / Unassigned": {"glass": [], "aluminum": [], "accessories": []}
        }
    }

def migrate_db(db):
    """Ensures old database files have the new required keys."""
    default = get_default_db()
    
    for key in default.keys():
        if key not in db: db[key] = default[key]
            
    if "inventory" not in db: db["inventory"] = default["inventory"]
    for key in default["inventory"].keys():
        if key not in db["inventory"]: db["inventory"][key] = default["inventory"][key]
            
    if "projects" not in db: db["projects"] = default["projects"]
    for proj in db["projects"].values():
        for key in ["glass", "aluminum", "accessories"]:
            if key not in proj: proj[key] = []
    return db

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: 
                return migrate_db(json.load(f))
        except: 
            return get_default_db()
    return get_default_db()

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

if 'db' not in st.session_state:
    st.session_state.db = load_db()

db = st.session_state.db

# ==========================================
# TOP BAR: PROJECT MANAGEMENT
# ==========================================
st.markdown("### 📁 Project Management")
col1, col2 = st.columns([2, 1])

with col1:
    project_list = list(db['projects'].keys())
    if db['active_project'] not in project_list: db['active_project'] = project_list[0]
    active_project = st.selectbox("Select Active Project", project_list, index=project_list.index(db['active_project']))
    if active_project != db['active_project']:
        db['active_project'] = active_project
        save_db(db)
        st.rerun()

with col2:
    with st.popover("➕ New Project"):
        new_proj_name = st.text_input("Project Name (e.g., Villa 4)")
        if st.button("Create"):
            if new_proj_name and new_proj_name not in db['projects']:
                db['projects'][new_proj_name] = {"glass": [], "aluminum": [], "accessories": []}
                db['active_project'] = new_proj_name
                save_db(db)
                st.success(f"Project '{new_proj_name}' created!")
                st.rerun()
            elif new_proj_name in db['projects']:
                st.error("Project already exists.")

st.info(f"🟢 Active Project: **{db['active_project']}**")

# ==========================================
# SIDEBAR: LIVE WAREHOUSE INVENTORY
# ==========================================
st.sidebar.header("📦 Live Inventory")

st.sidebar.subheader("🪟 Glass Sheets")
if not db['inventory']['glass']: st.sidebar.write("No glass stock added.")
for mat, sizes in db['inventory']['glass'].items():
    st.sidebar.write(f"**{mat}**")
    for size, qty in sizes.items():
        color = "red" if qty <= 2 else "black"
        st.sidebar.markdown(f"<span style='color:{color}'>- {size}: {qty}</span>", unsafe_allow_html=True)

st.sidebar.subheader("✂️ Remnants (Offcuts)")
if not db['inventory'].get('remnants'): st.sidebar.write("No offcuts tracked.")
for rem in db['inventory'].get('remnants', []):
    st.sidebar.markdown(f"- {rem['material']}: {rem['width']}x{rem['height']}")

st.sidebar.subheader("📏 Aluminum Profiles")
if not db['inventory']['aluminum']: st.sidebar.write("No aluminum stock added.")
for profile, meters in db['inventory']['aluminum'].items():
    color = "red" if meters <= 10 else "black"
    st.sidebar.markdown(f"<span style='color:{color}'>**{profile}**: {meters:.1f} m</span>", unsafe_allow_html=True)

st.sidebar.subheader("🔧 Accessories")
if not db['inventory']['accessories']: st.sidebar.write("No accessories added.")
for item, qty in db['inventory']['accessories'].items():
    color = "red" if qty <= 5 else "black"
    st.sidebar.markdown(f"<span style='color:{color}'>**{item}**: {qty}</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💾 Data Backup")
db_json = json.dumps(db, indent=4)
st.sidebar.download_button("Download Backup (.json)", db_json, "shop_erp_backup.json", "application/json")

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🪟 Cut Glass", 
    "📏 Use Aluminum", 
    "🔧 Use Accessories", 
    "📦 Receive Stock", 
    "📊 Project Report",
    "📋 Stock View"  # NEW TAB
])

# --- TAB 1: GLASS CUTTING ---
with tab1:
    st.header("Glass Cutting Optimizer")
    col1, col2 = st.columns(2)
    with col1: kerf = st.number_input("Blade Kerf (mm)", value=3, step=1)
    with col2: edge_trim = st.number_input("Edge Trim (mm)", value=5, step=1)
        
    stock_options = {"2140 x 3300": (2140 - edge_trim, 3300 - edge_trim), "2140 x 3660": (2140 - edge_trim, 3660 - edge_trim)}

    if 'glass_data' not in st.session_state:
        st.session_state.glass_data = pd.DataFrame([{"Location": "Door 1", "Material": "", "Width": 0, "Height": 0, "Quantity": 0}])

    edited_df = st.data_editor(st.session_state.glass_data, num_rows="dynamic", width='stretch')

    if st.button("🚀 Generate Cutting Plan", type="primary"):
        if edited_df.empty or edited_df['Material'].iloc[0] == "":
            st.warning("Please enter measurements and select a material.")
        else:
            materials = edited_df['Material'].unique()
            all_valid_bins = []
            
            for material in materials:
                mat_df = edited_df[edited_df['Material'] == material]
                packer = newPacker(rotation=True)
                
                for rem in db['inventory'].get('remnants', []):
                    if rem['material'] == material:
                        packer.add_bin(rem['width'] - edge_trim, rem['height'] - edge_trim, bid=f"REMNANT | {rem['width']}x{rem['height']}")

                if material in db['inventory']['glass']:
                    for sheet_name, dims in stock_options.items():
                        w, h = dims
                        qty_available = db['inventory']['glass'][material].get(sheet_name, 0)
                        for _ in range(qty_available):
                            packer.add_bin(w, h, bid=f"{material} | {sheet_name}")
                
                for index, row in mat_df.iterrows():
                    for _ in range(int(row['Quantity'])):
                        packer.add_rect(float(row['Width']) + kerf, float(row['Height']) + kerf, rid=row['Location'])

                packer.pack()
                valid_bins = [abin for abin in packer if len(abin) > 0]
                
                if len(valid_bins) == 0 and not mat_df.empty:
                    st.error(f"❌ Not enough {material} in stock!")
                else:
                    for abin in valid_bins:
                        if "REMNANT" in abin.bid:
                            rem_w = int(abin.bid.split("|")[1].strip().split("x")[0])
                            rem_h = int(abin.bid.split("|")[1].strip().split("x")[1])
                            db['inventory']['remnants'] = [r for r in db['inventory']['remnants'] if not (r['material'] == material and r['width'] == rem_w and r['height'] == rem_h)]
                        else:
                            sheet_type = abin.bid.split(" | ")[1]
                            db['inventory']['glass'][material][sheet_type] -= 1
                            
                        for rect in abin:
                            db['projects'][db['active_project']]['glass'].append({
                                "Material": material, "Size": f"{int(rect.width - kerf)}x{int(rect.height - kerf)}", "Location": rect.rid, "Date": datetime.now().strftime("%Y-%m-%d")
                            })
                    save_db(db)
                    all_valid_bins.extend(valid_bins)
            
            st.session_state.generated_bins = all_valid_bins
            st.session_state.current_material = materials[0] if len(materials) > 0 else ""

    if 'generated_bins' in st.session_state and st.session_state.generated_bins:
        st.success("✅ Cutting Plan Generated! Review and log offcuts below.")
        
        for i, abin in enumerate(st.session_state.generated_bins):
            st.markdown(f"### Sheet {i+1}: {abin.bid}")
            
            col_map, col_actions = st.columns([3, 1])
            
            with col_map:
                fig, ax = plt.subplots(figsize=(6, 6))
                ax.set_xlim(0, abin.width + edge_trim)
                ax.set_ylim(0, abin.height + edge_trim)
                ax.set_aspect('equal')
                ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor='black', linewidth=2))
                
                max_x = 0
                max_y = 0
                used_area = 0
                
                for rect in abin:
                    ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width - kerf, rect.height - kerf, facecolor='#ADD8E6', edgecolor='#00008B'))
                    ax.text(rect.x + (rect.width - kerf)/2, rect.y + (rect.height - kerf)/2, f"{int(rect.width - kerf)}x{int(rect.height - kerf)}\n{rect.rid}", ha='center', va='center', fontsize=8, rotation=90 if rect.height > rect.width else 0, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
                    max_x = max(max_x, rect.x + rect.width)
                    max_y = max(max_y, rect.y + rect.height)
                    used_area += (rect.width - kerf) * (rect.height - kerf)
                
                total_area = abin.width * abin.height
                waste_percent = ((total_area - used_area) / total_area) * 100
                plt.title(f"Waste: {waste_percent:.1f}%", color='red')
                st.pyplot(fig)
            
            with col_actions:
                st.write("**Offcut Manager**")
                top_w = abin.width
                top_h = abin.height - max_y
                right_w = abin.width - max_x
                right_h = abin.height
                
                if (top_w * top_h) >= (right_w * right_h):
                    best_offcut = (int(top_w), int(top_h), "Top Strip")
                else:
                    best_offcut = (int(right_w), int(right_h), "Right Strip")
                
                st.write(f"Largest Leftover: **{best_offcut[0]} x {best_offcut[1]} mm** ({best_offcut[2]})")
                
                cut_confirm = st.checkbox("Did you cut this sheet?", key=f"cut_{i}")
                
                if cut_confirm:
                    if st.button("Log Offcut to Inventory", key=f"log_{i}"):
                        mat_name = abin.bid.split(" | ")[0]
                        
                        if best_offcut[0] > 300 and best_offcut[1] > 300:
                            db['inventory']['remnants'].append({
                                "material": mat_name,
                                "width": best_offcut[0],
                                "height": best_offcut[1]
                            })
                            save_db(db)
                            st.success(f"Logged {best_offcut[0]}x{best_offcut[1]} offcut for {mat_name}!")
                        else:
                            st.info("Offcut is too small to keep (< 300mm). Discarded.")
            
            st.markdown("---")

# --- TAB 2: ALUMINUM USAGE ---
with tab2:
    st.header("Use Aluminum Profile")
    if not db['inventory']['aluminum']: st.warning("No aluminum in stock.")
    else:
        with st.form("aluminum_form"):
            profile = st.selectbox("Select Profile", list(db['inventory']['aluminum'].keys()))
            meters_used = st.number_input("Total Meters Used (m)", min_value=0.1, step=0.1)
            if st.form_submit_button("📉 Deduct & Log"):
                if db['inventory']['aluminum'][profile] >= meters_used:
                    db['inventory']['aluminum'][profile] -= meters_used
                    db['projects'][db['active_project']]['aluminum'].append({"Profile": profile, "Meters": meters_used, "Date": datetime.now().strftime("%Y-%m-%d")})
                    save_db(db)
                    st.success(f"✅ Logged {meters_used}m of {profile}.")
                else: st.error(f"❌ Not enough stock! Only {db['inventory']['aluminum'][profile]:.1f}m available.")

# --- TAB 3: ACCESSORIES USAGE ---
with tab3:
    st.header("Use Accessories")
    if not db['inventory']['accessories']: st.warning("No accessories in stock.")
    else:
        with st.form("accessories_form"):
            item = st.selectbox("Select Accessory", list(db['inventory']['accessories'].keys()))
            qty_used = st.number_input("Quantity Used", min_value=1, step=1)
            if st.form_submit_button("📉 Deduct & Log"):
                if db['inventory']['accessories'][item] >= qty_used:
                    db['inventory']['accessories'][item] -= qty_used
                    db['projects'][db['active_project']]['accessories'].append({"Item": item, "Qty": qty_used, "Date": datetime.now().strftime("%Y-%m-%d")})
                    save_db(db)
                    st.success(f"✅ Logged {qty_used} x {item}.")
                else: st.error(f"❌ Not enough stock! Only {db['inventory']['accessories'][item]} available.")

# --- TAB 4: RECEIVE STOCK ---
with tab4:
    st.header("📦 Receive Stock (Warehouse)")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🪟 Add Glass Sheets")
        g_mat = st.text_input("Material Name (e.g., 6mm Clear)")
        g_size = st.selectbox("Sheet Size", ["2140 x 3300", "2140 x 3660"])
        g_qty = st.number_input("Quantity (Sheets)", min_value=1, step=1)
        if st.button("Add Glass to Stock"):
            if g_mat:
                if g_mat not in db['inventory']['glass']: db['inventory']['glass'][g_mat] = {"2140 x 3300": 0, "2140 x 3660": 0}
                db['inventory']['glass'][g_mat][g_size] += g_qty
                save_db(db)
                st.success(f"Added {g_qty} sheets of {g_mat}")
                st.rerun()
            else: st.error("Please enter a material name.")

        st.markdown("---")
        st.subheader("✂️ Add an Offcut / Remnant")
        r_mat = st.selectbox("Remnant Material", list(db['inventory']['glass'].keys()) if db['inventory']['glass'] else ["6mm Clear"])
        r_width = st.number_input("Remnant Width (mm)", min_value=100, step=10)
        r_height = st.number_input("Remnant Height (mm)", min_value=100, step=10)
        if st.button("Add Remnant to Stock"):
            db['inventory']['remnants'].append({"material": r_mat, "width": r_width, "height": r_height})
            save_db(db)
            st.success(f"Added remnant {r_width}x{r_height} of {r_mat}")
            st.rerun()

    with col2:
        st.subheader("📏 Add Aluminum")
        a_prof = st.text_input("Profile Name (e.g., 60mm Frame)")
        a_meters = st.number_input("Total Meters Received", min_value=1.0, step=1.0)
        if st.button("Add Aluminum to Stock"):
            if a_prof:
                if a_prof in db['inventory']['aluminum']: db['inventory']['aluminum'][a_prof] += a_meters
                else: db['inventory']['aluminum'][a_prof] = a_meters
                save_db(db)
                st.success(f"Added {a_meters}m of {a_prof}")
                st.rerun()
            else: st.error("Please enter a profile name.")

        st.markdown("---")
        st.subheader("🔧 Add Accessories")
        acc_item = st.text_input("Accessory Name (e.g., Door Handles)")
        acc_qty = st.number_input("Quantity Received", min_value=1, step=1)
        if st.button("Add Accessory to Stock"):
            if acc_item:
                if acc_item in db['inventory']['accessories']: db['inventory']['accessories'][acc_item] += acc_qty
                else: db['inventory']['accessories'][acc_item] = acc_qty
                save_db(db)
                st.success(f"Added {acc_qty} of {acc_item}")
                st.rerun()
            else: st.error("Please enter an accessory name.")

# --- TAB 5: PROJECT DASHBOARD ---
with tab5:
    st.header(f"📊 Project Report: {db['active_project']}")
    proj_data = db['projects'][db['active_project']]
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Glass Pieces Cut", len(proj_data['glass']))
    with col2: 
        total_alum = sum(item['Meters'] for item in proj_data['aluminum'])
        st.metric("Aluminum Used", f"{total_alum:.1f} m")
    with col3: 
        total_acc = sum(item['Qty'] for item in proj_data['accessories'])
        st.metric("Accessories Used", total_acc)

    st.markdown("---")
    if st.button("📥 Export Project Report (CSV)"):
        export_data = []
        for g in proj_data['glass']: export_data.append({"Category": "Glass", "Item": f"{g['Material']} - {g['Size']}", "Qty/Meters": 1, "Location": g['Location']})
        for a in proj_data['aluminum']: export_data.append({"Category": "Aluminum", "Item": a['Profile'], "Qty/Meters": a['Meters'], "Location": ""})
        for ac in proj_data['accessories']: export_data.append({"Category": "Accessory", "Item": ac['Item'], "Qty/Meters": ac['Qty'], "Location": ""})
        df_export = pd.DataFrame(export_data)
        csv = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, f"{db['active_project']}_Report.csv", "text/csv")

    st.subheader("🪟 Glass Cut Log")
    if proj_data['glass']: st.dataframe(pd.DataFrame(proj_data['glass']), width='stretch')
    else: st.write("No glass logged yet.")

    st.subheader("📏 Aluminum Usage Log")
    if proj_data['aluminum']: st.dataframe(pd.DataFrame(proj_data['aluminum']), width='stretch')
    else: st.write("No aluminum logged yet.")

    st.subheader("🔧 Accessories Usage Log")
    if proj_data['accessories']: st.dataframe(pd.DataFrame(proj_data['accessories']), width='stretch')
    else: st.write("No accessories logged yet.")

# --- TAB 6: FULL STOCK VIEW ---
with tab6:
    st.header("📋 Full Warehouse Stock View")
    st.write("Here is a detailed list of all materials currently in your warehouse.")

    st.subheader("🪟 Glass Sheets")
    if db['inventory']['glass']:
        glass_list = []
        for mat, sizes in db['inventory']['glass'].items():
            for size, qty in sizes.items():
                glass_list.append({"Material": mat, "Sheet Size": size, "Quantity in Stock": qty})
        st.dataframe(pd.DataFrame(glass_list), width='stretch')
    else:
        st.info("No glass sheets currently in stock. Go to 'Receive Stock' to add.")

    st.subheader("✂️ Remnants (Offcuts)")
    if db['inventory'].get('remnants'):
        st.dataframe(pd.DataFrame(db['inventory']['remnants']), width='stretch')
    else:
        st.info("No offcuts currently tracked.")

    st.subheader("📏 Aluminum Profiles")
    if db['inventory']['aluminum']:
        alum_list = [{"Profile Name": k, "Total Meters": v} for k, v in db['inventory']['aluminum'].items()]
        st.dataframe(pd.DataFrame(alum_list), width='stretch')
    else:
        st.info("No aluminum profiles currently in stock.")

    st.subheader("🔧 Accessories")
    if db['inventory']['accessories']:
        acc_list = [{"Item Name": k, "Quantity": v} for k, v in db['inventory']['accessories'].items()]
        st.dataframe(pd.DataFrame(acc_list), width='stretch')
    else:
        st.info("No accessories currently in stock.")
