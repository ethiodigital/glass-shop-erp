import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from rectpack import newPacker
import json
import os
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Fabrication Shop ERP", layout="wide", page_icon="🏭")

# ==========================================
# DATABASE SETUP (JSON)
# ==========================================
DB_FILE = "shop_erp_data.json"

def get_default_db():
    return {
        "active_project": "General / Unassigned",
        "inventory": {
            "glass": {
                "4mm Clear": {"2140 x 3300": 10, "2140 x 3660": 5},
                "6mm Clear": {"2140 x 3300": 5, "2140 x 3660": 5},
                "6mm Tempered": {"Custom Ordered": 0}
            },
            "aluminum": {
                "60mm Frame Profile": 60.0,
                "40mm Sash Profile": 45.0,
                "20mm Bead": 100.0
            },
            "accessories": {
                "Door Handles": 50,
                "Door Locks": 30,
                "Hinges": 120,
                "Rubber Gasket (m)": 200.0
            }
        },
        "projects": {
            "General / Unassigned": {"glass": [], "aluminum": [], "accessories": []}
        }
    }

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return get_default_db()

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

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
    if db['active_project'] not in project_list:
        db['active_project'] = project_list[0]
        
    active_project = st.selectbox("Select Active Project for this Session", project_list, index=project_list.index(db['active_project']))
    
    if active_project != db['active_project']:
        db['active_project'] = active_project
        save_db(db)
        st.rerun()

with col2:
    with st.popover("➕ Create New Project"):
        new_proj_name = st.text_input("Project Name (e.g., Villa 4 - Bole)")
        if st.button("Create Project"):
            if new_proj_name and new_proj_name not in db['projects']:
                db['projects'][new_proj_name] = {"glass": [], "aluminum": [], "accessories": []}
                db['active_project'] = new_proj_name
                save_db(db)
                st.success(f"Project '{new_proj_name}' created!")
                st.rerun()
            elif new_proj_name in db['projects']:
                st.error("Project already exists.")

st.info(f"🟢 Currently working on: **{db['active_project']}**")

# ==========================================
# SIDEBAR: LIVE WAREHOUSE INVENTORY
# ==========================================
st.sidebar.header("📦 Warehouse Inventory")
st.sidebar.markdown("---")

st.sidebar.subheader("🪟 Glass Sheets")
for mat, sizes in db['inventory']['glass'].items():
    st.sidebar.write(f"**{mat}**")
    for size, qty in sizes.items():
        color = "red" if qty <= 2 else "black"
        st.sidebar.markdown(f"<span style='color:{color}'>- {size}: {qty} sheets</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("📏 Aluminum Profiles")
for profile, meters in db['inventory']['aluminum'].items():
    color = "red" if meters <= 10 else "black"
    st.sidebar.markdown(f"<span style='color:{color}'>**{profile}**: {meters:.1f} m</span>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Accessories")
for item, qty in db['inventory']['accessories'].items():
    color = "red" if qty <= 5 else "black"
    st.sidebar.markdown(f"<span style='color:{color}'>**{item}**: {qty}</span>", unsafe_allow_html=True)

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🪟 Glass Cutting", "📏 Aluminum Usage", "🔧 Accessories Usage", "📊 Project Dashboard"])

# --- TAB 1: GLASS CUTTING ---
with tab1:
    st.header("Glass Cutting Optimizer")
    
    col1, col2 = st.columns(2)
    with col1: kerf = st.number_input("Blade Kerf (mm)", value=3, step=1, help="Thickness of the cutting wheel")
    with col2: edge_trim = st.number_input("Edge Trim (mm)", value=5, step=1, help="Amount trimmed off raw sheet edges")
        
    stock_options = {"2140 x 3300": (2140 - edge_trim, 3300 - edge_trim), "2140 x 3660": (2140 - edge_trim, 3660 - edge_trim)}

    if 'glass_data' not in st.session_state:
        st.session_state.glass_data = pd.DataFrame([{"Location": "Door 1", "Material": "6mm Clear", "Width": 915, "Height": 1845, "Quantity": 1}])

    edited_df = st.data_editor(st.session_state.glass_data, num_rows="dynamic", use_container_width=True)

    if st.button("🚀 Generate Glass Cutting Plan", type="primary"):
        materials = edited_df['Material'].unique()
        all_valid_bins = []
        
        for material in materials:
            mat_df = edited_df[edited_df['Material'] == material]
            packer = newPacker(rotation=True)
            
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
                st.error(f"❌ Not enough {material} in stock to fulfill this order!")
            else:
                for abin in valid_bins:
                    sheet_type = abin.bid.split(" | ")[1]
                    db['inventory']['glass'][material][sheet_type] -= 1
                    
                    for rect in abin:
                        db['projects'][db['active_project']]['glass'].append({
                            "Material": material, "Size": f"{int(rect.width - kerf)}x{int(rect.height - kerf)}", "Location": rect.rid, "Date": datetime.now().strftime("%Y-%m-%d")
                        })
                save_db(db)
                all_valid_bins.extend(valid_bins)

        if all_valid_bins:
            st.success(f"✅ Cutting Plan Generated! Material logged to {db['active_project']}.")
            cols_per_row = 2
            for i in range(0, len(all_valid_bins), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(all_valid_bins):
                        abin = all_valid_bins[i+j]
                        with cols[j]:
                            fig, ax = plt.subplots(figsize=(6, 8))
                            ax.set_xlim(0, abin.width + edge_trim)
                            ax.set_ylim(0, abin.height + edge_trim)
                            ax.set_title(f"SHEET {i+j+1}: {abin.bid}", fontsize=12, weight='bold')
                            ax.set_aspect('equal')
                            ax.add_patch(patches.Rectangle((0, 0), abin.width, abin.height, fill=False, edgecolor='black', linewidth=2))
                            
                            used_area = 0
                            for rect in abin:
                                ax.add_patch(patches.Rectangle((rect.x, rect.y), rect.width - kerf, rect.height - kerf, facecolor='#ADD8E6', edgecolor='#00008B'))
                                ax.text(rect.x + (rect.width - kerf)/2, rect.y + (rect.height - kerf)/2, f"{int(rect.width - kerf)}x{int(rect.height - kerf)}\n{rect.rid}", ha='center', va='center', fontsize=8, rotation=90 if rect.height > rect.width else 0, bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))
                                used_area += (rect.width - kerf) * (rect.height - kerf)
                                
                            total_area = abin.width * abin.height
                            waste_percent = ((total_area - used_area) / total_area) * 100
                            ax.text(abin.width/2, -150, f"Waste: {waste_percent:.1f}%", ha='center', fontsize=10, color='red', weight='bold')
                            plt.tight_layout()
                            st.pyplot(fig)

# --- TAB 2: ALUMINUM USAGE ---
with tab2:
    st.header("Aluminum Profile Usage")
    with st.form("aluminum_form"):
        profile = st.selectbox("Select Profile", list(db['inventory']['aluminum'].keys()))
        meters_used = st.number_input("Total Meters Used (m)", min_value=0.1, step=0.1)
        
        if st.form_submit_button("📉 Deduct & Log to Project"):
            if db['inventory']['aluminum'][profile] >= meters_used:
                db['inventory']['aluminum'][profile] -= meters_used
                db['projects'][db['active_project']]['aluminum'].append({"Profile": profile, "Meters": meters_used, "Date": datetime.now().strftime("%Y-%m-%d")})
                save_db(db)
                st.success(f"✅ Logged {meters_used}m of {profile} to {db['active_project']}.")
            else:
                st.error(f"❌ Not enough {profile} in stock! Only {db['inventory']['aluminum'][profile]:.1f}m available.")

    st.markdown("---")
    st.subheader("Receive New Aluminum Stock")
    with st.form("add_aluminum_form"):
        new_profile = st.text_input("Profile Name")
        new_meters = st.number_input("Total Meters Received", min_value=1.0, step=1.0)
        if st.form_submit_button("➕ Add to Warehouse"):
            if new_profile in db['inventory']['aluminum']: db['inventory']['aluminum'][new_profile] += new_meters
            else: db['inventory']['aluminum'][new_profile] = new_meters
            save_db(db)
            st.success(f"Added {new_meters}m to {new_profile}.")
            st.rerun()

# --- TAB 3: ACCESSORIES USAGE ---
with tab3:
    st.header("Accessories & Hardware Usage")
    with st.form("accessories_form"):
        item = st.selectbox("Select Accessory", list(db['inventory']['accessories'].keys()))
        qty_used = st.number_input("Quantity Used", min_value=1, step=1)
        
        if st.form_submit_button("📉 Deduct & Log to Project"):
            if db['inventory']['accessories'][item] >= qty_used:
                db['inventory']['accessories'][item] -= qty_used
                db['projects'][db['active_project']]['accessories'].append({"Item": item, "Qty": qty_used, "Date": datetime.now().strftime("%Y-%m-%d")})
                save_db(db)
                st.success(f"✅ Logged {qty_used} x {item} to {db['active_project']}.")
            else:
                st.error(f"❌ Not enough {item} in stock! Only {db['inventory']['accessories'][item]} available.")

    st.markdown("---")
    st.subheader("Receive New Accessories")
    with st.form("add_accessories_form"):
        new_item = st.text_input("Accessory Name")
        new_qty = st.number_input("Quantity Received", min_value=1, step=1)
        if st.form_submit_button("➕ Add to Warehouse"):
            if new_item in db['inventory']['accessories']: db['inventory']['accessories'][new_item] += new_qty
            else: db['inventory']['accessories'][new_item] = new_qty
            save_db(db)
            st.success(f"Added {new_qty} of {new_item}.")
            st.rerun()

# --- TAB 4: PROJECT DASHBOARD ---
with tab4:
    st.header(f"📊 Project Report: {db['active_project']}")
    
    proj_data = db['projects'][db['active_project']]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Glass Pieces Cut", len(proj_data['glass']))
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
    if proj_data['glass']: st.dataframe(pd.DataFrame(proj_data['glass']), use_container_width=True)
    else: st.write("No glass logged yet.")

    st.subheader("📏 Aluminum Usage Log")
    if proj_data['aluminum']: st.dataframe(pd.DataFrame(proj_data['aluminum']), use_container_width=True)
    else: st.write("No aluminum logged yet.")

    st.subheader("🔧 Accessories Usage Log")
    if proj_data['accessories']: st.dataframe(pd.DataFrame(proj_data['accessories']), use_container_width=True)
    else: st.write("No accessories logged yet.")