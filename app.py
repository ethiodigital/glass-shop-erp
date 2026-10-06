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
# DATABASE SETUP
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

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return get_default_db()
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
        new_proj_name = st.text_input("Project Name")
        if st.button("Create"):
            if new_proj_name and new_proj_name not in db['projects']:
                db['projects'][new_proj_name] = {"glass": [], "aluminum": [], "accessories": []}
                db['active_project'] = new_proj_name
                save_db(db)
                st.rerun()

st.info(f"🟢 Active Project: **{db['active_project']}**")

# ==========================================
# SIDEBAR
# ==========================================
st.sidebar.header("📦 Live Inventory")
st.sidebar.subheader("🪟 Glass Sheets")
for mat, sizes in db['inventory']['glass'].items():
    st.sidebar.write(f"**{mat}**")
    for size, qty in sizes.items():
        color = "red" if qty <= 2 else "black"
        st.sidebar.markdown(f"<span style='color:{color}'>- {size}: {qty}</span>", unsafe_allow_html=True)

st.sidebar.subheader("✂️ Remnants (Offcuts)")
if not db['inventory'].get('remnants'): st.sidebar.write("No offcuts tracked.")
for rem in db['inventory'].get('remnants', []):
    st.sidebar.markdown(f"- {rem['material']}: {rem['width']}x{rem['height']}")

st.sidebar.subheader("📏 Aluminum & 🔧 Accessories")
st.sidebar.write("View in tabs below.")

st.sidebar.markdown("---")
st.sidebar.download_button("💾 Backup Data (.json)", json.dumps(db, indent=4), "shop_backup.json", "application/json")

# ==========================================
# MAIN TABS
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🪟 Cut Glass", "📏 Use Aluminum", "🔧 Use Accessories", "📦 Receive Stock", "📊 Project Report"])

# --- TAB 1: GLASS CUTTING ---
with tab1:
    st.header("Glass Cutting Optimizer")
    col1, col2 = st.columns(2)
    with col1: kerf = st.number_input("Blade Kerf (mm)", value=3, step=1)
    with col2: edge_trim = st.number_input("Edge Trim (mm)", value=5, step=1)
        
    stock_options = {"2140 x 3300": (2140 - edge_trim, 3300 - edge_trim), "2140 x 3660": (2140 - edge_trim, 3660 - edge_trim)}

    if 'glass_data' not in st.session_state:
        st.session_state.glass_data = pd.DataFrame([{"Location": "Door 1", "Material": "", "Width": 0, "Height": 0, "Quantity": 0}])

    edited_df = st.data_editor(st.session_state.glass_data, num_rows="dynamic", use_container_width=True)

    if st.button("🚀 Generate Cutting Plan", type="primary"):
        if edited_df.empty or edited_df['Material'].iloc[0] == "":
            st.warning("Please enter measurements and select a material.")
        else:
            materials = edited_df['Material'].unique()
            all_valid_bins = []
            
            for material in materials:
                mat_df = edited_df[edited_df['Material'] == material]
                packer = newPacker(rotation=True)
                
                # 1. ADD REMNANTS FIRST
                for rem in db['inventory'].get('remnants', []):
                    if rem['material'] == material:
                        packer.add_bin(rem['width'] - edge_trim, rem['height'] - edge_trim, bid=f"REMNANT | {rem['width']}x{rem['height']}")

                # 2. ADD STANDARD SHEETS
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
            
            # Save the generated bins to session state so they don't disappear on button click
            st.session_state.generated_bins = all_valid_bins
            st.session_state.current_material = materials[0] if len(materials) > 0 else ""

    # --- RENDER THE CUTTING MAPS & OFFCUT LOGGER ---
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
                # Calculate the largest rectangular offcut
                # Top strip vs Right strip
                top_w = abin.width
                top_h = abin.height - max_y
                
                right_w = abin.width - max_x
                right_h = abin.height
                
                # Choose the larger offcut area
                if (top_w * top_h) >= (right_w * right_h):
                    best_offcut = (int(top_w), int(top_h), "Top Strip")
                else:
                    best_offcut = (int(right_w), int(right_h), "Right Strip")
                
                st.write(f"Largest Leftover: **{best_offcut[0]} x {best_offcut[1]} mm** ({best_offcut[2]})")
                
                # Ask if it was cut
                cut_confirm = st.checkbox("Did you cut this sheet?", key=f"cut_{i}")
                
                if cut_confirm:
                    if st.button("Log Offcut to Inventory", key=f"log_{i}"):
                        # Extract material from bid (e.g., "6mm Clear | 2140 x 3660")
                        mat_name = abin.bid.split(" | ")[0]
                        
                        # Only log if it's larger than 300x300mm (otherwise it's trash)
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
