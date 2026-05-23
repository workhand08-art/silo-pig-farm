import streamlit as st
import json
import os
import datetime

# --- ตั้งค่ารหัสผ่าน ---
PASSWORD = "1234" # เปลี่ยนรหัสที่นี่

# --- ฟังก์ชันจัดการข้อมูล ---
DATA_FILE = "farm_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f: return json.load(f)
    return {str(i): {"wk": 22, "pigs": 600, "stock": 5000, "formula": "DG30M", "eat_per_head": 2.5, "actual_eat": 1500} for i in range(1, 21)}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

# --- ฟังก์ชันตรวจสอบรหัสผ่าน ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔒 กรุณาเข้าสู่ระบบ")
        input_pass = st.text_input("รหัสผ่าน", type="password")
        if st.button("เข้าสู่ระบบ"):
            if input_pass == PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")
        return False
    return True

# --- รันระบบ ---
if check_password():
    if 'farm_data' not in st.session_state: st.session_state.farm_data = load_data()

    today = datetime.date.today()
    st.set_page_config(page_title="ระบบบริหารไซโลครบวงจร", layout="wide")
    st.title(f"🐷 ระบบบริหารไซโล (อัปเดตล่าสุด: {today.strftime('%d/%m/%Y')})")

    # 1. เมนูบันทึกรถเข้า
    st.sidebar.header("🚚 บันทึกรถอาหารเข้า")
    truck_date = st.sidebar.date_input("วันที่รถส่งอาหาร", today)
    silo_in = st.sidebar.selectbox("เลือกเล้า", list(st.session_state.farm_data.keys()))
    new_formula_in = st.sidebar.text_input("ชื่อสูตรอาหารที่มาส่ง", st.session_state.farm_data[silo_in]["formula"])
    add_kg = st.sidebar.number_input("จำนวนที่เติม (กก.)", value=1000, step=500)

    if st.sidebar.button("📦 บันทึกรถเข้า"):
        st.session_state.farm_data[silo_in].update({
            "stock": st.session_state.farm_data[silo_in]["stock"] + add_kg,
            "formula": new_formula_in
        })
        save_data(st.session_state.farm_data)
        st.sidebar.success(f"บันทึกสำเร็จ! (วันที่ {truck_date.strftime('%d/%m/%Y')})")
        st.rerun()

    # 2. จัดการรายเล้า
    for silo, info in st.session_state.farm_data.items():
        with st.expander(f"เล้า {silo} | WK: {info.get('wk', 22)} | สต็อกจริง: {info['stock']:,} กก."):
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            
            wk = c1.number_input("อายุหมู (WK)", value=int(info.get('wk', 22)), key=f"wk_{silo}")
            pigs = c2.number_input("จำนวนหมู (ตัว)", value=int(info.get('pigs', 600)), key=f"p_{silo}")
            formula = c3.text_input("ชื่อสูตรอาหาร", value=info.get('formula', 'DG30M'), key=f"f_{silo}")
            stock = c4.number_input("สต็อกคงเหลือ (กก.)", value=int(info['stock']), key=f"s_{silo}")
            eat_per_head = c5.number_input("กินต่อตัว/วัน (กก.)", value=float(info.get('eat_per_head', 2.5)), format="%.2f", key=f"eh_{silo}")
            actual_eat = c6.number_input("กินจริงวันนี้ (กก.)", value=int(info.get('actual_eat', 1500)), key=f"ac_{silo}")
            
            if st.button("บันทึกข้อมูลวันนี้", key=f"b_{silo}"):
                st.session_state.farm_data[silo].update({
                    "wk": wk, "pigs": pigs, "formula": formula, 
                    "stock": stock - actual_eat, "eat_per_head": eat_per_head, "actual_eat": actual_eat
                })
                save_data(st.session_state.farm_data)
                st.rerun()

            daily_eat = pigs * eat_per_head
            days_left = (stock - actual_eat) / daily_eat if daily_eat > 0 else 99
            date_expire = today + datetime.timedelta(days=int(days_left))
            
            st.write(f"---")
            st.write(f"📊 **เปรียบเทียบ:** กินตามสแตท {daily_eat:,.1f} กก./วัน | **กินจริงวันนี้ {actual_eat:,.1f} กก.**")
            st.write(f"📅 **อาหารจะหมดประมาณวันที่:** {date_expire.strftime('%d/%m/%Y')}")
            
            if days_left <= 7:
                st.error(f"🚨 ต้องสั่งเพิ่มอย่างน้อย: {max(0, (daily_eat * 7) - (stock - actual_eat)):,.0f} กก. สำหรับสัปดาห์หน้า")
            else:
                st.success(f"✅ อาหารเพียงพอสำหรับอีก {days_left:.1f} วัน")
