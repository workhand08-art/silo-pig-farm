import streamlit as st
import json
import os
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- ตั้งค่า ---
PASSWORD = "1234"
DATA_FILE = "farm_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: pass
    return {str(i): {"wk": 22, "pigs": 600, "stock": 5000, "formula": "DG30M", "eat_per_head": 2.5, "actual_eat": 1500} for i in range(1, 21)}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- ฟังก์ชันบันทึกไป Google Sheets (รองรับวันที่) ---
def save_to_google_sheet(date_val, silo, wk, pigs, formula, stock, eat_per_head, actual_eat):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("farm_database").sheet1
        row = [str(date_val), silo, wk, pigs, formula, stock, eat_per_head, actual_eat]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการบันทึก Google Sheet: {e}")
        return False

# --- หน้าแอป ---
st.set_page_config(page_title="ระบบบริหารไซโล", layout="wide")

if "password_correct" not in st.session_state: st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🔒 กรุณาเข้าสู่ระบบ")
    if st.text_input("รหัสผ่าน", type="password") == PASSWORD:
        st.session_state["password_correct"] = True
        st.rerun()
else:
    if 'farm_data' not in st.session_state: st.session_state.farm_data = load_data()
    today = datetime.date.today()
    st.title(f"🐷 ระบบบริหารไซโล (อัปเดต: {today.strftime('%d/%m/%Y')})")

    # บันทึกรถเข้า
    st.sidebar.header("🚚 บันทึกรถอาหารเข้า")
    silo_in = st.sidebar.selectbox("เลือกเล้า", list(st.session_state.farm_data.keys()))
    date_in = st.sidebar.date_input("วันที่อาหารเข้า", today)
    new_formula_in = st.sidebar.text_input("ชื่อสูตรอาหาร", st.session_state.farm_data[silo_in]["formula"])
    add_kg = st.sidebar.number_input("จำนวนที่เติม (กก.)", value=1000, step=500)
    
    if st.sidebar.button("📦 บันทึกรถเข้า"):
        info = st.session_state.farm_data[silo_in]
        new_stock = info["stock"] + add_kg
        st.session_state.farm_data[silo_in].update({"stock": new_stock, "formula": new_formula_in})
        save_data(st.session_state.farm_data)
        if save_to_google_sheet(date_in, silo_in, info["wk"], info["pigs"], new_formula_in, new_stock, info["eat_per_head"], 0):
            st.success("บันทึกรถเข้าเรียบร้อย!")
        st.rerun()

    # รายเล้า
    for silo, info in st.session_state.farm_data.items():
        with st.expander(f"เล้า {silo} | สต็อกปัจจุบัน: {info['stock']:,} กก."):
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            wk = c1.number_input("WK", value=int(info.get('wk', 22)), key=f"wk_{silo}")
            pigs = c2.number_input("ตัว", value=int(info.get('pigs', 600)), key=f"p_{silo}")
            form = c3.text_input("สูตร", value=info.get('formula', 'DG30M'), key=f"f_{silo}")
            stock = c4.number_input("คงเหลือ (จดจริง)", value=int(info['stock']), key=f"s_{silo}")
            eph = c5.number_input("กิน/ตัว", value=float(info.get('eat_per_head', 2.5)), key=f"eh_{silo}")
            ac = c6.number_input("กินจริง", value=int(info.get('actual_eat', 1500)), key=f"ac_{silo}")
            
            if st.button("บันทึกข้อมูลวันนี้", key=f"b_{silo}"):
                st.session_state.farm_data[silo].update({"wk": wk, "pigs": pigs, "formula": form, "stock": stock, "eat_per_head": eph, "actual_eat": ac})
                save_data(st.session_state.farm_data)
                if save_to_google_sheet(today, silo, wk, pigs, form, stock, eph, ac):
                    st.success("บันทึกข้อมูลสำเร็จ!")
                st.rerun()

            daily_eat_stat = pigs * eph
            effective_eat = (daily_eat_stat * 0.4) + (ac * 0.6)
            days_left = (stock / effective_eat) if effective_eat > 0 else 99
            date_expire = today + datetime.timedelta(days=int(days_left))
            st.write(f"📊 **เปรียบเทียบ:** สแตท {daily_eat_stat:,.1f} | **กินจริง {ac:,.1f}** | **ใช้จริงเฉลี่ย {effective_eat:,.1f} กก./วัน**")
            st.write(f"📅 **อาหารจะหมดประมาณ:** {date_expire.strftime('%d/%m/%Y')}")
            if days_left <= 7: st.error(f"🚨 ต้องสั่งเพิ่ม: {max(0, (effective_eat * 7) - stock):,.0f} กก.")
            else: st.success(f"✅ อาหารพอสำหรับอีก {days_left:.1f} วัน")
