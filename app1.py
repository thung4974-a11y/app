# app.py - Ứng dụng phân tích kết quả học tập sinh viên (Cập nhật theo yêu cầu)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
from datetime import datetime
import traceback

premium_sidebar = """
<style>
[data-testid="stSidebar"] {
    background: rgba(15, 32, 65, 0.65) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border-right: 1px solid rgba(255,255,255,0.12);
    box-shadow: 4px 0 25px rgba(0,0,0,0.55);
    padding-top: 20px !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding: 10px;
    border-radius: 20px;
}

[data-testid="stSidebar"] * {
    color: #ffffff !important;
    font-weight: 500 !important;
    font-family: "Segoe UI", sans-serif;
}

div[role="radiogroup"] > label {
    background: rgba(255, 255, 255, 0.06);
    padding: 10px 14px;
    border-radius: 12px;
    margin-bottom: 6px;
    transition: 0.25s ease;
    border: 1px solid rgba(255,255,255,0.08);
}

div[role="radiogroup"] > label:hover {
    background: rgba(255, 255, 255, 0.15);
    transform: translateX(4px);
}

div[role="radiogroup"] > label[data-testid="stRadioOption"]:has(input:checked) {
    background: rgba(0, 168, 255, 0.25) !important;
    border: 1px solid rgba(0,168,255,0.6) !important;
    box-shadow: 0 0 10px rgba(0,168,255,0.6);
    transform: translateX(6px);
}

button[kind="primary"] {
    background: linear-gradient(135deg, #0abde3, #0984e3) !important;
    padding: 10px 20px !important;
    border-radius: 12px !important;
    border: none !important;
    transition: 0.25s ease;
}

button[kind="primary"]:hover {
    transform: scale(1.04);
    box-shadow: 0 4px 20px rgba(0,150,255,0.45);
}

[data-testid="stSidebar"] ::-webkit-scrollbar {
    width: 8px;
}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.25);
    border-radius: 10px;
}
[data-testid="stSidebar"] ::-webkit-scrollbar-thumb:hover {
    background: rgba(255,255,255,0.45);
}
</style>
"""
st.markdown(premium_sidebar, unsafe_allow_html=True)

# ======================== CẤU HÌNH MÔN HỌC ========================
SUBJECTS = {
    'triet': {'name': 'Triết', 'counts_gpa': True, 'semester': 1},
    'giai_tich_1': {'name': 'Giải tích 1', 'counts_gpa': True, 'semester': 1, 'mandatory': True},
    'giai_tich_2': {'name': 'Giải tích 2', 'counts_gpa': True, 'semester': 2, 'prerequisite': 'giai_tich_1'},
    'tieng_an_do_1': {'name': 'Tiếng Ấn Độ 1', 'counts_gpa': True, 'semester': 1, 'mandatory': True},
    'tieng_an_do_2': {'name': 'Tiếng Ấn Độ 2', 'counts_gpa': True, 'semester': 2, 'prerequisite': 'tieng_an_do_1'},
    'gdtc': {'name': 'GDTC', 'counts_gpa': False, 'semester': 1},
    'thvp': {'name': 'THVP', 'counts_gpa': True, 'semester': 1},
    'tvth': {'name': 'TVTH', 'counts_gpa': True, 'semester': 2},
    'phap_luat': {'name': 'Pháp luật', 'counts_gpa': True, 'semester': 2},
    'logic': {'name': 'Logic và suy luận toán học', 'counts_gpa': True, 'semester': 2},
}

# Môn học tiếp theo (cho gợi ý học tập)
NEXT_SUBJECTS = {
    'triet': 'phap_luat',
    'giai_tich_1': 'giai_tich_2',
    'tieng_an_do_1': 'tieng_an_do_2',
    'phap_luat': 'tu_tuong',  # Môn năm sau
    'giai_tich_2': 'giai_tich_3',  # Môn năm sau
    'tieng_an_do_2': 'tieng_an_do_3',  # Môn năm sau
}

SEMESTER_1_SUBJECTS = ['triet', 'giai_tich_1', 'tieng_an_do_1', 'gdtc', 'thvp']
SEMESTER_2_SUBJECTS = ['giai_tich_2', 'tieng_an_do_2', 'tvth', 'phap_luat', 'logic']
ACADEMIC_YEAR = 1

# ======================== CẤU HÌNH DATABASE ========================
def init_db(db_path='student_grades.db'):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        role TEXT NOT NULL,
        student_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mssv TEXT NOT NULL,
        student_name TEXT NOT NULL,
        class_name TEXT,
        semester INTEGER DEFAULT 1,
        triet REAL,
        giai_tich_1 REAL,
        giai_tich_2 REAL,
        tieng_an_do_1 REAL,
        tieng_an_do_2 REAL,
        gdtc REAL,
        thvp REAL,
        tvth REAL,
        phap_luat REAL,
        logic REAL,
        diem_tb REAL,
        xep_loai TEXT,
        academic_year INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO users (username, password, fullname, role) VALUES (?, ?, ?, ?)",
                  ('admin', admin_pass, 'Quản trị viên', 'teacher'))
    
    conn.commit()
    return conn

# ======================== HÀM TIỆN ÍCH ========================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(conn, username, password):
    c = conn.cursor()
    hashed = hash_password(password)
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
    return c.fetchone()

def calculate_grade(score):
    try:
        s = float(score)
    except Exception:
        s = 0.0
    if s >= 9.5: return 'Xuất sắc'
    elif s >= 8.5: return 'Giỏi'
    elif s >= 7.0: return 'Khá'
    elif s >= 5.5: return 'Trung bình'
    elif s >= 4.0: return 'Yếu'
    else: return 'Kém'

def calculate_average(row):
    scores = []
    for key, info in SUBJECTS.items():
        if info['counts_gpa']:
            val = row.get(key)
            try:
                num = float(val) if pd.notna(val) else np.nan
            except Exception:
                num = np.nan
            if pd.notna(num) and num >= 0:
                scores.append(num)
    return round(float(np.mean(scores)), 2) if scores else 0.0

def can_take_semester_2(conn, mssv):
    df = load_grades(conn)
    student_sem1 = df[(df['mssv'] == mssv) & (df['semester'] == 1)]
    
    if student_sem1.empty:
        return False, "Chưa có điểm học kỳ 1"
    
    row = student_sem1.iloc[0]
    try:
        giai_tich_1 = float(row.get('giai_tich_1') or 0)
    except Exception:
        giai_tich_1 = 0
    try:
        tieng_an_do_1 = float(row.get('tieng_an_do_1') or 0)
    except Exception:
        tieng_an_do_1 = 0
    avg = (giai_tich_1 + tieng_an_do_1) / 2.0
    
    if avg >= 4:
        return True, f"Đủ điều kiện (TB: {avg:.2f})"
    else:
        return False, f"Chưa đủ điều kiện (TB: {avg:.2f} < 4)"

# ======================== CHỨC NĂNG DATABASE ========================
def load_grades(conn):
    try:
        df = pd.read_sql_query("SELECT * FROM grades", conn)
        for key in SUBJECTS.keys():
            if key in df.columns:
                df[key] = pd.to_numeric(df[key], errors='coerce')
        if 'diem_tb' in df.columns:
            df['diem_tb'] = pd.to_numeric(df['diem_tb'], errors='coerce').fillna(0.0)
        return df
    except Exception:
        cols = ['id','mssv','student_name','class_name','semester'] + list(SUBJECTS.keys()) + ['diem_tb','xep_loai','academic_year','updated_at']
        return pd.DataFrame(columns=cols)

def get_ranking_by_semester(df, semester=None):
    """Xếp hạng sinh viên theo điểm GPA - ĐÃ SỬA THEO YÊU CẦU"""
    if df.empty:
        return pd.DataFrame()
    
    if semester == 'all' or semester is None:
        # Xếp hạng tổng hợp - CHỈ những sinh viên có ĐỦ CẢ 2 KỲ
        grouped = df.groupby('mssv')
        
        combined_rows = []
        for mssv, group in grouped:
            semesters = group['semester'].unique().tolist()
            
            # Chỉ lấy sinh viên có cả 2 kỳ
            if len(semesters) == 2 and 1 in semesters and 2 in semesters:
                sem1_row = group[group['semester'] == 1].iloc[0]
                sem2_row = group[group['semester'] == 2].iloc[0]
                
                diem_tb_1 = float(sem1_row['diem_tb']) if pd.notna(sem1_row['diem_tb']) else 0
                diem_tb_2 = float(sem2_row['diem_tb']) if pd.notna(sem2_row['diem_tb']) else 0
                diem_tb_combined = round((diem_tb_1 + diem_tb_2) / 2, 2)
                
                combined_rows.append({
                    'mssv': mssv,
                    'student_name': sem1_row['student_name'],
                    'class_name': sem1_row['class_name'],
                    'semester': 'Cả 2 kỳ',
                    'diem_tb': diem_tb_combined,
                    'xep_loai': calculate_grade(diem_tb_combined),
                    'diem_tb_hk1': diem_tb_1,
                    'diem_tb_hk2': diem_tb_2
                })
        
        if not combined_rows:
            return pd.DataFrame()
        
        result_df = pd.DataFrame(combined_rows)
        result_df = result_df.sort_values('diem_tb', ascending=False).reset_index(drop=True)
        result_df['xep_hang'] = range(1, len(result_df) + 1)
        return result_df
    else:
        # Xếp hạng theo kỳ cụ thể - CHỈ lấy điểm của kỳ đó
        semester_df = df[df['semester'] == semester].copy()
        if semester_df.empty:
            return pd.DataFrame()
        semester_df = semester_df.sort_values('diem_tb', ascending=False).reset_index(drop=True)
        semester_df['xep_hang'] = range(1, len(semester_df) + 1)
        return semester_df

def save_grade(conn, data):
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester, 
                     triet, giai_tich_1, giai_tich_2, tieng_an_do_1, tieng_an_do_2,
                     gdtc, thvp, tvth, phap_luat, logic,
                     diem_tb, xep_loai, academic_year)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)

def delete_grade(conn, grade_id):
    c = conn.cursor()
    c.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    conn.commit()

def delete_grades_batch(conn, grade_ids):
    c = conn.cursor()
    for grade_id in grade_ids:
        c.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    conn.commit()

def clean_data(conn):
    df = load_grades(conn)
    c = conn.cursor()
    
    original_count = len(df)
    if original_count == 0:
        return 0, 0, 0
    
    # Chuyển về numeric
    for key in SUBJECTS.keys():
        if key in df.columns:
            df[key] = pd.to_numeric(df[key], errors='coerce')
    
    # Xử lý điểm âm → NaN
    negative_fixed = 0
    for key in SUBJECTS.keys():
        if key in df.columns:
            count = int((df[key] < 0).sum())
            negative_fixed += count
            df.loc[df[key] < 0, key] = np.nan
    
    # Xóa MSSV + học kỳ
    df_clean = df.drop_duplicates(subset=['mssv', 'semester'], keep='first')
    removed_semester = original_count - len(df_clean)

    # Lọc MSSV trùng nhưng tên khác
    before = len(df_clean)
    df_clean = (
        df_clean.sort_values(["mssv", "student_name"])
                .groupby("mssv", as_index=False)
                .first()
    )
    removed_name_conflict = before - len(df_clean)
    
    # Ghi lại DB
    try:
        c.execute("DELETE FROM grades")
        for _, row in df_clean.iterrows():
            diem_tb = calculate_average(row)
            xep_loai = calculate_grade(diem_tb)

            def safe_val(k):
                v = row.get(k)
                if pd.isna(v):
                    return None
                return float(v) if v != '' else None

            params = (
                row.get('mssv', ''), row.get('student_name', ''), row.get('class_name', None),
                int(row.get('semester', 1)) if not pd.isna(row.get('semester', 1)) else 1,
                safe_val('triet'), safe_val('giai_tich_1'), safe_val('giai_tich_2'),
                safe_val('tieng_an_do_1'), safe_val('tieng_an_do_2'),
                safe_val('gdtc'), safe_val('thvp'), safe_val('tvth'),
                safe_val('phap_luat'), safe_val('logic'),
                float(diem_tb), xep_loai, int(ACADEMIC_YEAR)
            )

            c.execute(
                '''INSERT INTO grades (mssv, student_name, class_name, semester,
                triet, giai_tich_1, giai_tich_2, tieng_an_do_1, tieng_an_do_2,
                gdtc, thvp, tvth, phap_luat, logic,
                diem_tb, xep_loai, academic_year)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                params
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    
    return removed_semester, removed_name_conflict, negative_fixed

# ======================== QUẢN LÝ USER ========================
def create_user(conn, username, password, fullname, role, student_id=None):
    c = conn.cursor()
    try:
        hashed = hash_password(password)
        c.execute("INSERT INTO users (username, password, fullname, role, student_id) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed, fullname, role, student_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def get_all_users(conn):
    return pd.read_sql_query("SELECT id, username, fullname, role, student_id, created_at FROM users", conn)

def delete_user(conn, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id = ? AND username != 'admin'", (user_id,))
    conn.commit()

# ======================== GỢI Ý HỌC TẬP ========================
def generate_study_suggestions(row, semester):
    """Tạo gợi ý học tập dựa trên điểm số"""
    suggestions = {
        'hoc_lai': [],      # Điểm < 4
        'cai_thien': [],    # Điểm 4-6
        'can_hoc': [],      # Chưa có điểm
        'hoc_tiep': []      # Đủ điều kiện học tiếp
    }
    
    current_subjects = SEMESTER_1_SUBJECTS if semester == 1 else SEMESTER_2_SUBJECTS
    
    for key in current_subjects:
        info = SUBJECTS[key]
        score = row.get(key)
        
        try:
            score_val = float(score) if pd.notna(score) else None
        except:
            score_val = None
        
        if score_val is None:
            suggestions['can_hoc'].append(info['name'])
        elif score_val < 4:
            suggestions['hoc_lai'].append(f"{info['name']} ({score_val:.1f})")
        elif score_val < 6:
            suggestions['cai_thien'].append(f"{info['name']} ({score_val:.1f})")
        
        # Gợi ý học tiếp nếu đạt >= 4
        if score_val is not None and score_val >= 4 and key in NEXT_SUBJECTS:
            next_subject = NEXT_SUBJECTS[key]
            if semester == 1:
                # HK1: gợi ý các môn HK2
                next_name = {
                    'phap_luat': 'Pháp luật',
                    'giai_tich_2': 'Giải tích 2',
                    'tieng_an_do_2': 'Tiếng Ấn Độ 2'
                }.get(next_subject, next_subject)
            else:
                # HK2: gợi ý các môn năm sau
                next_name = {
                    'tu_tuong': 'Tư tưởng (Năm 2)',
                    'giai_tich_3': 'Giải tích 3 (Năm 2)',
                    'tieng_an_do_3': 'Tiếng Ấn Độ 3 (Năm 2)'
                }.get(next_subject, next_subject)
            suggestions['hoc_tiep'].append(f"{next_name}")
    
    return suggestions

def display_study_suggestions(suggestions, semester):
    """Hiển thị gợi ý học tập"""
    st.markdown(f"###Gợi ý học tập - Học kỳ {semester}")
    
    has_suggestions = False
    
    if suggestions['hoc_lai']:
        has_suggestions = True
        st.error(f"**🔴 Cần học lại (điểm < 4):** {', '.join(suggestions['hoc_lai'])}")
    
    if suggestions['cai_thien']:
        has_suggestions = True
        st.warning(f"**🟡 Nên cải thiện (điểm 4-6):** {', '.join(suggestions['cai_thien'])}")
    
    if suggestions['can_hoc']:
        has_suggestions = True
        st.info(f"**🔵 Cần phải học (chưa có điểm):** {', '.join(suggestions['can_hoc'])}")
    
    if suggestions['hoc_tiep']:
        has_suggestions = True
        st.success(f"**🟢 Đủ điều kiện học tiếp:** {', '.join(suggestions['hoc_tiep'])}")
    
    if not has_suggestions:
        st.success("Bạn đã hoàn thành tốt học kỳ này!")

# ======================== GIAO DIỆN ========================
def login_page(conn):
    page_bg = """
    <style>
    [data-testid="stAppViewContainer"] {
        background-image: url("https://sf-static.upanhlaylink.com/img/image_2025120700f9fd552eecbc6c73df72a9cb906ab6.jpg");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
    }
    [data-testid="stHeader"], [data-testid="stFooter"] {
        background: rgba(0,0,0,0);
    }
    </style>
    """
    st.markdown(page_bg, unsafe_allow_html=True)

    custom_css = """
    <style>
    h1, h2 {
        text-align: center !important;
    }
    input[type="text"], input[type="password"] {
        background-color: white !important;
        color: black !important;
        border-radius: 8px;
        border: 1px solid #cccccc !important;
    }
    button[kind="primary"] {
        background-color: white !important;
        color: black !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: bold !important;
    }
    button[kind="primary"]:hover {
        background-color: #e6e6e6 !important;
        color: black !important;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
    
    st.title("Hệ thống Quản lý Điểm Sinh viên")
    
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        
        if st.button("Đăng nhập", use_container_width=True):
            user = verify_user(conn, username, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_id'] = user[0]
                st.session_state['fullname'] = user[3]
                st.session_state['role'] = user[4]
                st.session_state['student_id'] = user[5]
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")

def teacher_dashboard(conn):
    st.sidebar.title(f"{st.session_state.get('fullname','')}")
    st.sidebar.write("Vai trò: **Giáo viên**")
    
    if st.sidebar.button("Đăng xuất", type = "primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", [
        "Dashboard",
        "Quản lý điểm",
        "Xếp hạng theo GPA",
        "Thêm điểm",
        "Import dữ liệu",
        "Export dữ liệu",
        "Làm sạch dữ liệu",
        "Quản lý tài khoản",
        "Biểu đồ phân tích"
    ])
    
    df = load_grades(conn)
    
    if menu == "Dashboard":
        show_dashboard(df)
    elif menu == "Quản lý điểm":
        manage_grades_new(conn, df)
    elif menu == "Xếp hạng theo GPA":
        show_ranking(df)
    elif menu == "Thêm điểm":
        add_grade_form(conn)
    elif menu == "Import dữ liệu":
        import_data(conn)
    elif menu == "Export dữ liệu":
        export_data(df)
    elif menu == "Làm sạch dữ liệu":
        clean_data_page(conn, df)
    elif menu == "Quản lý tài khoản":
        manage_users(conn)
    elif menu == "Biểu đồ phân tích":
        show_charts(df)

def show_ranking(df):
    """Hiển thị bảng xếp hạng theo GPA - ĐÃ SỬA"""
    st.title("Xếp hạng theo điểm GPA")
    
    if df.empty:
        st.warning("Chưa có dữ liệu để xếp hạng.")
        return
    
    semester_option = st.radio(
        "Chọn học kỳ",
        ["Tổng hợp (cả 2 kỳ)", "Học kỳ 1", "Học kỳ 2"],
        horizontal=True
    )
    
    if semester_option == "Học kỳ 1":
        ranking_df = get_ranking_by_semester(df, semester=1)
        if ranking_df.empty:
            st.info("Không có dữ liệu điểm Học kỳ 1.")
            return
        display_cols = ['xep_hang', 'mssv', 'student_name', 'class_name', 'diem_tb', 'xep_loai']
    elif semester_option == "Học kỳ 2":
        ranking_df = get_ranking_by_semester(df, semester=2)
        if ranking_df.empty:
            st.info("Không có dữ liệu điểm Học kỳ 2.")
            return
        display_cols = ['xep_hang', 'mssv', 'student_name', 'class_name', 'diem_tb', 'xep_loai']
    else:
        ranking_df = get_ranking_by_semester(df, semester='all')
        if ranking_df.empty:
            st.info("Chưa có sinh viên nào hoàn thành đủ cả 2 học kỳ.")
            return
        display_cols = ['xep_hang', 'mssv', 'student_name', 'class_name', 'diem_tb_hk1', 'diem_tb_hk2', 'diem_tb', 'xep_loai']
    
    # Hiển thị top 3
    st.subheader("Top 3 sinh viên xuất sắc")
    top3 = ranking_df.head(3)
    
    cols = st.columns(3)
    medals = ["🥇", "🥈", "🥉"]
    for i, (_, row) in enumerate(top3.iterrows()):
        if i < 3:
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; color: white;">
                    <h1>{medals[i]}</h1>
                    <h3>{row['student_name']}</h3>
                    <p><strong>MSSV:</strong> {row['mssv']}</p>
                    <p><strong>Điểm TB:</strong> {row['diem_tb']:.2f}</p>
                    <p><strong>Xếp loại:</strong> {row['xep_loai']}</p>
                </div>
                """, unsafe_allow_html=True)
    
    st.divider()
    
    # Bảng xếp hạng đầy đủ
    st.subheader("Bảng xếp hạng đầy đủ")
    
    # Bộ lọc
    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Tìm kiếm (MSSV/Tên)", key="ranking_search")
    with col2:
        xep_loai_filter = st.selectbox("Lọc theo xếp loại", 
                                       ['Tất cả'] + list(ranking_df['xep_loai'].dropna().unique()))
    
    filtered_df = ranking_df.copy()
    if search:
        filtered_df = filtered_df[
            filtered_df['mssv'].astype(str).str.contains(search, case=False, na=False) |
            filtered_df['student_name'].str.contains(search, case=False, na=False)
        ]
    if xep_loai_filter != 'Tất cả':
        filtered_df = filtered_df[filtered_df['xep_loai'] == xep_loai_filter]
    
    # Rename columns cho dễ đọc
    display_df = filtered_df[display_cols].copy()
    if semester_option == "Tổng hợp (cả 2 kỳ)":
        display_df.columns = ['Xếp hạng', 'MSSV', 'Họ tên', 'Lớp', 'ĐTB HK1', 'ĐTB HK2', 'Điểm TB', 'Xếp loại']
    else:
        display_df.columns = ['Xếp hạng', 'MSSV', 'Họ tên', 'Lớp', 'Điểm TB', 'Xếp loại']
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Thống kê
    st.subheader("Thống kê xếp hạng")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng số SV", len(ranking_df))
    with col2:
        st.metric("Điểm TB cao nhất", f"{ranking_df['diem_tb'].max():.2f}")
    with col3:
        st.metric("Điểm TB thấp nhất", f"{ranking_df['diem_tb'].min():.2f}")
    with col4:
        excellent_count = len(ranking_df[ranking_df['xep_loai'].isin(['Giỏi', 'Xuất sắc'])])
        st.metric("Số SV Giỏi/Xuất sắc", excellent_count)

def show_dashboard(df):
    st.title("Dashboard Tổng quan")
    
    if df.empty:
        st.warning("Chưa có dữ liệu. Vui lòng import hoặc thêm dữ liệu.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng sinh viên", df['mssv'].nunique())
    with col2:
        st.metric("Điểm TB", f"{df['diem_tb'].mean():.2f}")
    with col3:
        st.metric("Cao nhất", f"{df['diem_tb'].max():.2f}")
    with col4:
        st.metric("Thấp nhất", f"{df['diem_tb'].min():.2f}")
    
    st.subheader("Thống kê theo học kỳ")
    col1, col2 = st.columns(2)
    with col1:
        sem1_count = len(df[df['semester'] == 1])
        st.metric("Học kỳ 1", f"{sem1_count} bản ghi")
    with col2:
        sem2_count = len(df[df['semester'] == 2])
        st.metric("Học kỳ 2", f"{sem2_count} bản ghi")
    
    st.subheader("Thống kê theo xếp loại")
    xep_loai_counts = df['xep_loai'].fillna('Chưa xếp loại').value_counts()
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(values=xep_loai_counts.values, names=xep_loai_counts.index, 
                    title='Phân bố xếp loại')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(x=xep_loai_counts.index, y=xep_loai_counts.values,
                    title='Số lượng theo xếp loại', labels={'x': 'Xếp loại', 'y': 'Số lượng'})
        st.plotly_chart(fig, use_container_width=True)

def manage_grades_new(conn, df):
    """Quản lý điểm - GIAO DIỆN MỚI THEO YÊU CẦU"""
    st.title("Quản lý điểm sinh viên")
    
    if df.empty:
        st.warning("Chưa có dữ liệu điểm.")
        return
    
    # Bộ lọc học kỳ
    semester_filter = st.radio(
        "Chọn học kỳ hiển thị",
        ['Tất cả từng kỳ', 'Học kỳ 1', 'Học kỳ 2', 'Tổng hợp'],
        horizontal=True
    )
    
    # Lọc dữ liệu theo học kỳ
    if semester_filter == 'Học kỳ 1':
        filtered_df = df[df['semester'] == 1].copy()
    elif semester_filter == 'Học kỳ 2':
        filtered_df = df[df['semester'] == 2].copy()
    elif semester_filter == 'Tổng hợp':
        # Chỉ lấy sinh viên có cả 2 kỳ
        grouped = df.groupby('mssv')
        combined_rows = []
        for mssv, group in grouped:
            semesters = group['semester'].unique().tolist()
            if len(semesters) == 2 and 1 in semesters and 2 in semesters:
                sem1_row = group[group['semester'] == 1].iloc[0]
                sem2_row = group[group['semester'] == 2].iloc[0]
                diem_tb_1 = float(sem1_row['diem_tb']) if pd.notna(sem1_row['diem_tb']) else 0
                diem_tb_2 = float(sem2_row['diem_tb']) if pd.notna(sem2_row['diem_tb']) else 0
                diem_tb_combined = round((diem_tb_1 + diem_tb_2) / 2, 2)
                combined_rows.append({
                    'mssv': mssv,
                    'student_name': sem1_row['student_name'],
                    'class_name': sem1_row['class_name'],
                    'semester': 'Cả 2 kỳ',
                    'diem_tb_hk1': diem_tb_1,
                    'diem_tb_hk2': diem_tb_2,
                    'diem_tb': diem_tb_combined,
                    'xep_loai': calculate_grade(diem_tb_combined)
                })
        filtered_df = pd.DataFrame(combined_rows) if combined_rows else pd.DataFrame()
    else:
        filtered_df = df.copy()
    
    # Hiển thị bảng điểm (không có cột ID)
    if not filtered_df.empty:
        if semester_filter == 'Tổng hợp':
            display_cols = ['mssv', 'student_name', 'class_name', 'diem_tb_hk1', 'diem_tb_hk2', 'diem_tb', 'xep_loai']
            display_df = filtered_df[display_cols].copy()
            display_df.columns = ['MSSV', 'Họ tên', 'Lớp', 'ĐTB HK1', 'ĐTB HK2', 'Điểm TB', 'Xếp loại']
        else:
            display_cols = ['mssv', 'student_name', 'class_name', 'semester', 'diem_tb', 'xep_loai']
            display_df = filtered_df[display_cols].copy()
            display_df.columns = ['MSSV', 'Họ tên', 'Lớp', 'Học kỳ', 'Điểm TB', 'Xếp loại']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption(f"Tổng số: {len(display_df)} bản ghi")
    else:
        st.info("Không có dữ liệu phù hợp với bộ lọc.")
    
    st.divider()
    
    # Tìm kiếm và Xóa điểm cùng hàng
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_term = st.text_input("Tìm kiếm sinh viên (MSSV hoặc Tên)", key="manage_search")
    
    with col2:
        st.write("")
        st.write("")
        show_delete = st.checkbox("Hiển thị chức năng Xóa điểm", value=True)
    
    # Kết quả tìm kiếm
    search_results = pd.DataFrame()
    if search_term:
        search_results = df[
            df['mssv'].astype(str).str.contains(search_term, case=False, na=False) |
            df['student_name'].str.contains(search_term, case=False, na=False)
        ]
        
        if not search_results.empty:
            st.success(f"Tìm thấy {len(search_results)} bản ghi")
            display_search = search_results[['mssv', 'student_name', 'class_name', 'semester', 'diem_tb', 'xep_loai']].copy()
            display_search.columns = ['MSSV', 'Họ tên', 'Lớp', 'Học kỳ', 'Điểm TB', 'Xếp loại']
            st.dataframe(display_search, use_container_width=True, hide_index=True)
            
            # Chức năng SỬA ĐIỂM
            st.subheader("Sửa điểm sinh viên")
            
            # Lấy danh sách MSSV duy nhất từ kết quả tìm kiếm
            unique_students = search_results['mssv'].unique().tolist()
            selected_mssv = st.selectbox("Chọn sinh viên để sửa điểm", unique_students)
            
            if selected_mssv:
                student_data = df[df['mssv'] == selected_mssv]
                student_name = student_data.iloc[0]['student_name']
                class_name = student_data.iloc[0]['class_name'] or ''
                
                st.info(f"**Sinh viên:** {student_name} | **MSSV:** {selected_mssv} | **Lớp:** {class_name}")
                
                # Hiển thị 2 bảng điểm theo từng học kỳ
                col_hk1, col_hk2 = st.columns(2)
                
                with col_hk1:
                    st.markdown("### Học kỳ 1")
                    sem1_data = student_data[student_data['semester'] == 1]
                    
                    sem1_scores = {}
                    if not sem1_data.empty:
                        row = sem1_data.iloc[0]
                        for key in SEMESTER_1_SUBJECTS:
                            current_val = row.get(key)
                            current_val = float(current_val) if pd.notna(current_val) else 0.0
                            sem1_scores[key] = st.number_input(
                                SUBJECTS[key]['name'],
                                0.0, 10.0, current_val,
                                key=f"edit_sem1_{key}"
                            )
                    else:
                        st.warning("Chưa có điểm HK1")
                        for key in SEMESTER_1_SUBJECTS:
                            sem1_scores[key] = st.number_input(
                                SUBJECTS[key]['name'],
                                0.0, 10.0, 0.0,
                                key=f"edit_sem1_{key}",
                                disabled=True
                            )
                
                with col_hk2:
                    st.markdown("###Học kỳ 2")
                    sem2_data = student_data[student_data['semester'] == 2]
                    
                    sem2_scores = {}
                    if not sem2_data.empty:
                        row = sem2_data.iloc[0]
                        for key in SEMESTER_2_SUBJECTS:
                            current_val = row.get(key)
                            current_val = float(current_val) if pd.notna(current_val) else 0.0
                            sem2_scores[key] = st.number_input(
                                SUBJECTS[key]['name'],
                                0.0, 10.0, current_val,
                                key=f"edit_sem2_{key}"
                            )
                    else:
                        st.warning("Chưa có điểm HK2 (Sinh viên chưa học)")
                        for key in SEMESTER_2_SUBJECTS:
                            sem2_scores[key] = st.number_input(
                                SUBJECTS[key]['name'],
                                0.0, 10.0, 0.0,
                                key=f"edit_sem2_{key}",
                                disabled=True
                            )
                
                # Nút lưu
                if st.button("Lưu thay đổi", type="primary"):
                    c = conn.cursor()
                    
                    # Cập nhật HK1 nếu có
                    if not sem1_data.empty:
                        sem1_id = sem1_data.iloc[0]['id']
                        scores_for_avg = {k: v for k, v in sem1_scores.items() if SUBJECTS[k]['counts_gpa'] and v > 0}
                        new_diem_tb = round(np.mean(list(scores_for_avg.values())), 2) if scores_for_avg else 0.0
                        new_xep_loai = calculate_grade(new_diem_tb)
                        
                        update_query = f"""UPDATE grades SET 
                            {', '.join([f'{k} = ?' for k in SEMESTER_1_SUBJECTS])},
                            diem_tb = ?, xep_loai = ?, updated_at = ?
                            WHERE id = ?"""
                        values = [float(sem1_scores[k]) if sem1_scores[k] > 0 else None for k in SEMESTER_1_SUBJECTS]
                        values.extend([new_diem_tb, new_xep_loai, datetime.now(), sem1_id])
                        c.execute(update_query, values)
                    
                    # Cập nhật HK2 nếu có
                    if not sem2_data.empty:
                        sem2_id = sem2_data.iloc[0]['id']
                        scores_for_avg = {k: v for k, v in sem2_scores.items() if SUBJECTS[k]['counts_gpa'] and v > 0}
                        new_diem_tb = round(np.mean(list(scores_for_avg.values())), 2) if scores_for_avg else 0.0
                        new_xep_loai = calculate_grade(new_diem_tb)
                        
                        update_query = f"""UPDATE grades SET 
                            {', '.join([f'{k} = ?' for k in SEMESTER_2_SUBJECTS])},
                            diem_tb = ?, xep_loai = ?, updated_at = ?
                            WHERE id = ?"""
                        values = [float(sem2_scores[k]) if sem2_scores[k] > 0 else None for k in SEMESTER_2_SUBJECTS]
                        values.extend([new_diem_tb, new_xep_loai, datetime.now(), sem2_id])
                        c.execute(update_query, values)
                    
                    conn.commit()
                    st.success("Đã cập nhật điểm thành công!")
                    st.rerun()
        else:
            st.warning("Không tìm thấy sinh viên phù hợp.")
    
    # Chức năng XÓA ĐIỂM (luôn hiển thị)
    if show_delete:
        st.divider()
        st.subheader(" Xóa điểm sinh viên")
        
        # Tạo danh sách options để xóa
        delete_options = []
        for _, row in df.iterrows():
            label = f"{row['mssv']} - {row['student_name']} - HK{int(row['semester'])} - ĐTB: {row['diem_tb']:.2f}"
            delete_options.append((row['id'], label))
        
        # Xóa đơn lẻ hoặc nhiều
        delete_mode = st.radio("Chế độ xóa", ["Xóa 1 sinh viên", "Xóa nhiều sinh viên"], horizontal=True)
        
        if delete_mode == "Xóa 1 sinh viên":
            selected_delete = st.selectbox(
                "Chọn bản ghi cần xóa",
                options=[opt[0] for opt in delete_options],
                format_func=lambda x: next(opt[1] for opt in delete_options if opt[0] == x)
            )
            
            if selected_delete:
                delete_row = df[df['id'] == selected_delete].iloc[0]
                st.warning(f"Bạn sắp xóa: **{delete_row['student_name']}** - MSSV: **{delete_row['mssv']}** - HK{int(delete_row['semester'])}")
                
                confirm = st.checkbox("Tôi xác nhận muốn xóa bản ghi này", key="confirm_single_delete")
                if st.button("Xóa", type="primary", disabled=not confirm):
                    delete_grade(conn, selected_delete)
                    st.success(f"Đã xóa bản ghi của {delete_row['student_name']}!")
                    st.rerun()
        else:
            multi_delete_ids = st.multiselect(
                "Chọn các bản ghi cần xóa",
                options=[opt[0] for opt in delete_options],
                format_func=lambda x: next(opt[1] for opt in delete_options if opt[0] == x)
            )
            
            if multi_delete_ids:
                st.error(f"Bạn đã chọn {len(multi_delete_ids)} bản ghi để xóa!")
                confirm_multi = st.checkbox("Tôi xác nhận muốn xóa TẤT CẢ các bản ghi đã chọn", key="confirm_multi_delete")
                
                if st.button("Xóa tất cả đã chọn", type="primary", disabled=not confirm_multi):
                    delete_grades_batch(conn, multi_delete_ids)
                    st.success(f"Đã xóa {len(multi_delete_ids)} bản ghi!")
                    st.rerun()

def add_grade_form(conn):
    st.title("Thêm điểm sinh viên")
    
    semester = st.radio("Chọn học kỳ", [1, 2], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        mssv = st.text_input("MSSV *")
        student_name = st.text_input("Họ tên *")
        class_name = st.text_input("Lớp")
    
    can_sem2 = True
    if semester == 2 and mssv:
        can_sem2, message = can_take_semester_2(conn, mssv)
        if can_sem2:
            st.success(f"{message}")
        else:
            st.error(f"{message}")
    
    st.subheader(f"Điểm các môn - Học kỳ {semester}")
    
    current_subjects = SEMESTER_1_SUBJECTS if semester == 1 else SEMESTER_2_SUBJECTS
    
    subject_scores = {}
    cols = st.columns(3)
    for i, key in enumerate(current_subjects):
        info = SUBJECTS[key]
        with cols[i % 3]:
            label = info['name']
            if not info['counts_gpa']:
                label += " (Không tính GPA)"
            if info.get('mandatory'):
                label += " *"
            subject_scores[key] = st.number_input(label, 0.0, 10.0, 0.0, key=f"add_{key}")
    
    st.info(f"Năm học: **{ACADEMIC_YEAR}** (cố định)")
    
    if st.button("Thêm điểm", type="primary", disabled=(semester == 2 and not can_sem2)):
        if mssv and student_name:
            scores_for_avg = {k: v for k, v in subject_scores.items() 
                           if SUBJECTS[k]['counts_gpa'] and v > 0}
            diem_tb = round(np.mean(list(scores_for_avg.values())), 2) if scores_for_avg else 0.0
            xep_loai = calculate_grade(diem_tb)
            
            all_scores = {k: None for k in SUBJECTS.keys()}
            all_scores.update(subject_scores)
            
            params = (
                mssv, student_name, class_name, int(semester),
                float(all_scores['triet']) if all_scores['triet'] is not None else None,
                float(all_scores['giai_tich_1']) if all_scores['giai_tich_1'] is not None else None,
                float(all_scores['giai_tich_2']) if all_scores['giai_tich_2'] is not None else None,
                float(all_scores['tieng_an_do_1']) if all_scores['tieng_an_do_1'] is not None else None,
                float(all_scores['tieng_an_do_2']) if all_scores['tieng_an_do_2'] is not None else None,
                float(all_scores['gdtc']) if all_scores['gdtc'] is not None else None,
                float(all_scores['thvp']) if all_scores['thvp'] is not None else None,
                float(all_scores['tvth']) if all_scores['tvth'] is not None else None,
                float(all_scores['phap_luat']) if all_scores['phap_luat'] is not None else None,
                float(all_scores['logic']) if all_scores['logic'] is not None else None,
                float(diem_tb), xep_loai, int(ACADEMIC_YEAR)
            )
            ok, err = save_grade(conn, params)
            if ok:
                st.success(f"Đã thêm điểm cho {student_name} - ĐTB: {diem_tb} - Xếp loại: {xep_loai}")
            else:
                st.error(f"Lỗi khi lưu vào DB: {err}")
        else:
            st.error("Vui lòng nhập MSSV và Họ tên!")

def clean_data_page(conn, df):
    st.title("Làm sạch dữ liệu")
    
    st.subheader("Phân tích dữ liệu hiện tại")
    
    # Đếm trùng MSSV + học kỳ
    duplicate_semester = int(df.duplicated(subset=['mssv', 'semester'], keep='first').sum()) if not df.empty else 0
    
    # Đếm MSSV trùng nhưng TÊN KHÁC nhau
    duplicate_name = 0
    if not df.empty:
        name_conflict_groups = df.groupby("mssv")["student_name"].nunique()
        duplicate_name = int((name_conflict_groups > 1).sum())   # số MSSV có nhiều tên
    
    # Điểm âm
    negative_count = 0
    for key in SUBJECTS.keys():
        if key in df.columns:
            negative_count += int((pd.to_numeric(df[key], errors='coerce') < 0).sum())
    
    col1, col2 = st.columns(2)
    with col1:
        if duplicate_semester > 0 or duplicate_name > 0:
            st.error(
                f"- {duplicate_semester} bản ghi trùng **MSSV + Học kỳ**\n"
                f"- {duplicate_name} MSSV có **nhiều tên khác nhau**"
            )
        else:
            st.success("Không có bản ghi trùng lặp")
    
    with col2:
        if negative_count > 0:
            st.error(f"Có **{negative_count}** điểm âm (không hợp lệ)")
        else:
            st.success("Không có điểm âm")
    
    st.divider()
    
    st.subheader("Thực hiện làm sạch")
    st.write("Quá trình này sẽ:")
    st.write("- Xóa các bản ghi trùng **MSSV + Học kỳ** (giữ bản ghi đầu tiên)")
    st.write("- Xóa các bản ghi **MSSV có nhiều tên**, giữ tên xuất hiện nhiều nhất")
    st.write("- Xóa các điểm có giá trị âm")
    st.write("- Tính lại điểm TB và xếp loại")
    
    if st.button(
        "Làm sạch dữ liệu", type="primary", 
        disabled=(duplicate_semester == 0 and duplicate_name == 0 and negative_count == 0)
    ):
        try:
            duplicates_removed, name_removed, negatives_fixed = clean_data(conn)
            st.success(
                f"Hoàn thành!\n"
                f"- Xóa {duplicates_removed} bản ghi trùng MSSV + học kỳ\n"
                f"- Xóa {name_removed} bản ghi do **MSSV có nhiều tên**\n"
                f"- Sửa {negatives_fixed} điểm âm."
            )
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi làm sạch: {e}")

def import_data(conn):
    st.title("Import dữ liệu")

    # ==========================
    #   CHỌN LOẠI DỮ LIỆU IMPORT
    # ==========================
    option = st.radio(
        "Chọn loại dữ liệu cần nhập:",
        ["Thêm sinh viên", "Học kỳ 1", "Học kỳ 2", "Cả hai kỳ"],
        horizontal=True
    )

    # ==========================
    #     MÔ TẢ TƯƠNG ỨNG
    # ==========================
    if option == "Thêm sinh viên tuyển sinh":
        st.info("""
Định dạng CSV cho Thêm Sinh Viên (Không có điểm):
- mssv, student_name, class_name, semester
- Tất cả điểm để trống
- semester = 1 hoặc 2 đều được
- GPA và Xếp loại sẽ được set = NULL và 'Chưa có điểm'
        """)

    elif option == "Học kỳ 1":
        st.info(f"""
Định dạng CSV cho Học kỳ 1:
- mssv, student_name, class_name, semester (=1)
- triet, giai_tich_1, tieng_an_do_1, gdtc, thvp
- Các môn khác để trống
        """)

    elif option == "Học kỳ 2":
        st.info(f"""
Định dạng CSV cho Học kỳ 2:
- mssv, student_name, class_name, semester (=2)
- giai_tich_2, tieng_an_do_2, tvth, phap_luat, logic
- Các môn khác để trống
        """)
    else:
        st.info("""
CSV cho cả hai kỳ:
- mssv, student_name, class_name, semester
- Điểm theo từng kỳ được lưu mỗi dòng
        """)

    # ==========================
    #       UPLOAD FILE
    # ==========================
    uploaded_file = st.file_uploader("Chọn file CSV", type=['csv'])

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Xem trước dữ liệu:")
            st.dataframe(df.head(10))

            # ==========================
            #       IMPORT BUTTON
            # ==========================
            if st.button("Import vào database"):
                c = conn.cursor()

                # Đảm bảo tất cả môn đều tồn tại
                for key in SUBJECTS.keys():
                    if key not in df.columns:
                        df[key] = np.nan
                    else:
                        df[key] = pd.to_numeric(df[key], errors='coerce')

                count_inserted = 0

                # ==========================
                #       IMPORT LOGIC
                # ==========================
                for _, row in df.iterrows():

                    # --- Xử lý thêm sinh viên ---
                    if option == "Thêm sinh viên":
                        semester = int(row.get("semester", 1))
                        params = (
                            row.get('mssv', ''),
                            row.get('student_name', ''),
                            row.get('class_name', ''),
                            semester,
                            None, None, None, None, None,  # 10 môn học
                            None, None, None, None, None,
                            None,        # GPA
                            "Chưa có điểm",
                            int(ACADEMIC_YEAR)
                        )
                        try:
                            c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester,
                                         triet, giai_tich_1, giai_tich_2, tieng_an_do_1, tieng_an_do_2,
                                         gdtc, thvp, tvth, phap_luat, logic,
                                         diem_tb, xep_loai, academic_year)
                                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', params)
                            count_inserted += 1
                        except Exception as e:
                            print("Lỗi insert SV:", e)
                        continue

                    # --- Import theo học kỳ ---
                    semester = int(row.get("semester", 1))

                    if option == "Học kỳ 1" and semester != 1:
                        continue
                    if option == "Học kỳ 2" and semester != 2:
                        continue

                    diem_tb = calculate_average(row)
                    xep_loai = calculate_grade(diem_tb)

                    params = (
                        row.get('mssv', ''), row.get('student_name', ''), row.get('class_name', ''),
                        semester,
                        None if pd.isna(row['triet']) else float(row['triet']),
                        None if pd.isna(row['giai_tich_1']) else float(row['giai_tich_1']),
                        None if pd.isna(row['giai_tich_2']) else float(row['giai_tich_2']),
                        None if pd.isna(row['tieng_an_do_1']) else float(row['tieng_an_do_1']),
                        None if pd.isna(row['tieng_an_do_2']) else float(row['tieng_an_do_2']),
                        None if pd.isna(row['gdtc']) else float(row['gdtc']),
                        None if pd.isna(row['thvp']) else float(row['thvp']),
                        None if pd.isna(row['tvth']) else float(row['tvth']),
                        None if pd.isna(row['phap_luat']) else float(row['phap_luat']),
                        None if pd.isna(row['logic']) else float(row['logic']),
                        float(diem_tb),
                        xep_loai,
                        int(ACADEMIC_YEAR)
                    )

                    try:
                        c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester,
                                     triet, giai_tich_1, giai_tich_2, tieng_an_do_1, tieng_an_do_2,
                                     gdtc, thvp, tvth, phap_luat, logic,
                                     diem_tb, xep_loai, academic_year)
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', params)
                        count_inserted += 1
                    except Exception as e:
                        print("Lỗi khi insert:", e)

                conn.commit()
                st.success(f"Đã import {count_inserted} bản ghi thành công!")
                st.rerun()

        except Exception as e:
            st.error(f"Lỗi khi đọc file: {e}")


def export_data(df):
    st.title("Export dữ liệu")
    
    if df.empty:
        st.warning("Không có dữ liệu để export.")
        return
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Tải file CSV", csv, "student_grades.csv", "text/csv")

def manage_users(conn):
    st.title("Quản lý tài khoản")

    tab_list, tab_create = st.tabs(["Danh sách", "Thêm mới"])

    # ============================================
    #              TAB 1: DANH SÁCH USER
    # ============================================
    with tab_list:
        users_df = get_all_users(conn)
        st.dataframe(users_df, use_container_width=True)

        deletable = users_df[users_df["username"] != "admin"]

        if not deletable.empty:
            user_id = st.selectbox(
                "Chọn user để xóa",
                deletable["id"].tolist()
            )

            if st.button("Xóa user",type="primary"):
                with st.spinner("Đang xóa tài khoản..."):
                    delete_user(conn, user_id)
                st.success("Đã xóa tài khoản!")
                st.rerun()

    # ============================================
    #              TAB 2: THÊM USER
    # ============================================
    with tab_create:
        st.subheader("Thêm tài khoản mới")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        fullname = st.text_input("Họ tên")
        role = st.selectbox("Vai trò", ["student", "teacher"])

        student_id = st.text_input("MSSV") if role == "student" else None

        if st.button("Tạo tài khoản", type="primary"):
            if not username or not password or not fullname:
                st.error("Vui lòng điền đầy đủ thông tin!")
                return

            with st.spinner("Đang tạo tài khoản..."):
                created = create_user(conn, username, password, fullname, role, student_id)

            if created:
                st.success("Tạo tài khoản thành công!")
                st.rerun()
            else:
                st.error("Username đã tồn tại!")

def show_charts(df):
    st.title("Biểu đồ phân tích")
    
    if df.empty:
        st.warning("Chưa có dữ liệu để phân tích.")
        return
    
    st.subheader("Điểm trung bình theo lớp")
    class_avg = df.groupby('class_name')['diem_tb'].mean().reset_index()
    fig1 = px.bar(class_avg, x='class_name', y='diem_tb', 
                  title='Điểm TB theo lớp', color='diem_tb',
                  labels={'class_name': 'Lớp', 'diem_tb': 'Điểm TB'})
    st.plotly_chart(fig1, use_container_width=True)
    
    st.subheader("Phân bố xếp loại")
    fig2 = px.pie(df, names='xep_loai', title='Tỷ lệ xếp loại học lực')
    st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("Điểm trung bình các môn học")
    subject_avg = []
    for key, info in SUBJECTS.items():
        if info['counts_gpa'] and key in df.columns:
            avg = pd.to_numeric(df[key], errors='coerce').mean()
            if pd.notna(avg):
                subject_avg.append({'Môn': info['name'], 'Điểm TB': float(avg)})
    
    if subject_avg:
        subject_df = pd.DataFrame(subject_avg)
        fig3 = px.line(subject_df, x='Môn', y='Điểm TB', markers=True, title='Điểm TB các môn')
        st.plotly_chart(fig3, use_container_width=True)
    
    st.subheader("So sánh theo học kỳ")
    semester_avg = df.groupby('semester')['diem_tb'].mean().reset_index()
    semester_avg['semester'] = semester_avg['semester'].map({1: 'Học kỳ 1', 2: 'Học kỳ 2'})
    fig4 = px.bar(semester_avg, x='semester', y='diem_tb', 
                  title='Điểm TB theo học kỳ', color='diem_tb')
    st.plotly_chart(fig4, use_container_width=True)
    
    st.subheader("Phân bố điểm trung bình")
    fig5 = px.histogram(df, x='diem_tb', nbins=20, title='Phân bố điểm TB')
    st.plotly_chart(fig5, use_container_width=True)

def student_dashboard(conn):
    st.sidebar.title(f"{st.session_state.get('fullname','')}")
    st.sidebar.write("Vai trò: **Học sinh**")
    
    if st.sidebar.button("Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    # Đổi thứ tự menu: Tra cứu điểm lên trước Xếp hạng theo GPA
    menu = st.sidebar.radio("Menu", [
        "Bảng điểm của tôi",
        "Tra cứu điểm",
        "Xếp hạng theo GPA",
        "Thống kê chung"
    ])
    
    df = load_grades(conn)
    student_id = st.session_state.get('student_id', '')
    
    if menu == "Bảng điểm của tôi":
        st.title("Bảng điểm của tôi")
        my_grades = df[df['mssv'] == student_id]
        
        if not my_grades.empty:
            for _, row in my_grades.iterrows():
                semester = int(row.get('semester', 1))
                st.subheader(f"Học kỳ {semester}")
                
                current_subjects = SEMESTER_1_SUBJECTS if semester == 1 else SEMESTER_2_SUBJECTS
                cols = st.columns(5)
                for i, key in enumerate(current_subjects):
                    with cols[i % 5]:
                        score = row.get(key)
                        st.metric(SUBJECTS[key]['name'][:12], f"{score:.1f}" if pd.notna(score) else "-")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Điểm TB", f"{row['diem_tb']:.2f}")
                with col2:
                    st.metric("Xếp loại", row['xep_loai'])
                
                # Gợi ý học tập cho từng học kỳ
                suggestions = generate_study_suggestions(row, semester)
                display_study_suggestions(suggestions, semester)
                
                st.divider()
        else:
            st.warning("Chưa có dữ liệu điểm của bạn.")
    
    elif menu == "Tra cứu điểm":
        st.title("Tra cứu điểm sinh viên")
        search_term = st.text_input("Nhập MSSV hoặc tên sinh viên")
        if search_term:
            results = df[df['mssv'].str.contains(search_term, case=False, na=False) | 
                        df['student_name'].str.contains(search_term, case=False, na=False)]
            if not results.empty:
                st.dataframe(results[['mssv', 'student_name', 'class_name', 'semester', 'diem_tb', 'xep_loai']], 
                           use_container_width=True)
            else:
                st.info("Không tìm thấy kết quả.")
    
    elif menu == "Xếp hạng theo GPA":
        show_ranking(df)
        
        # Hiển thị vị trí của sinh viên hiện tại
        if student_id:
            st.divider()
            st.subheader("Vị trí của bạn")
            
            for sem_name, sem_val in [("Học kỳ 1", 1), ("Học kỳ 2", 2), ("Tổng hợp", 'all')]:
                ranking_df = get_ranking_by_semester(df, semester=sem_val)
                if not ranking_df.empty:
                    student_rank = ranking_df[ranking_df['mssv'] == student_id]
                    
                    if not student_rank.empty:
                        rank = student_rank['xep_hang'].values[0]
                        total = len(ranking_df)
                        gpa = student_rank['diem_tb'].values[0]
                        st.info(f"**{sem_name}:** Xếp hạng **{rank}/{total}** - Điểm TB: **{gpa:.2f}**")
                    else:
                        if sem_val == 'all':
                            st.warning(f"**{sem_name}:** Bạn chưa hoàn thành đủ 2 học kỳ")
                        else:
                            st.warning(f"**{sem_name}:** Chưa có điểm")
    
    elif menu == "Thống kê chung":
        st.title("Thống kê chung")
        if not df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Tổng SV", df['mssv'].nunique())
            with col2:
                st.metric("Điểm TB", f"{df['diem_tb'].mean():.2f}")
            with col3:
                excellent_rate = (df['xep_loai'].isin(['Giỏi', 'Xuất sắc'])).sum() / len(df) * 100
                st.metric("Tỷ lệ Giỏi/Xuất sắc", f"{excellent_rate:.1f}%")
            with col4:
                st.metric("Số lớp", df['class_name'].nunique())
            
            fig = px.pie(df, names='xep_loai', title='Phân bố xếp loại')
            st.plotly_chart(fig, use_container_width=True)
# ======================== MAIN ========================
def main():
    st.set_page_config(page_title="Quản lý điểm sinh viên", page_icon="logotl.jpg", layout="wide")

    conn = init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if not st.session_state['logged_in']:
        login_page(conn)
    else:
        if st.session_state['role'] == 'teacher':
            teacher_dashboard(conn)
        else:
            student_dashboard(conn)

if __name__ == "__main__":
    main()
















