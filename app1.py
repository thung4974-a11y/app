# app.py - Ứng dụng phân tích kết quả học tập sinh viên (Cập nhật)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
from datetime import datetime

# ======================== CẤU HÌNH MÔN HỌC ========================
SUBJECTS = {
    'triet_hoc': {'name': 'Triết học Mác-Lênin', 'counts_gpa': True, 'semester': 1},
    'tieng_anh_1': {'name': 'Tiếng Anh cơ sở 1', 'counts_gpa': True, 'semester': 1, 'mandatory': True},
    'tieng_anh_2': {'name': 'Tiếng Anh cơ sở 2', 'counts_gpa': True, 'semester': 2, 'prerequisite': 'tieng_anh_1'},
    'tieng_an_do_1': {'name': 'Tiếng Ấn Độ 1', 'counts_gpa': True, 'semester': 1, 'mandatory': True},
    'tieng_an_do_2': {'name': 'Tiếng Ấn Độ 2', 'counts_gpa': True, 'semester': 2, 'prerequisite': 'tieng_an_do_1'},
    'gdtc': {'name': 'Giáo dục thể chất', 'counts_gpa': False, 'semester': 1},
    'tin_hoc_vp': {'name': 'Tin học văn phòng', 'counts_gpa': True, 'semester': 1},
    'tieng_viet_th': {'name': 'Tiếng Việt thực hành', 'counts_gpa': True, 'semester': 2},
    'phap_luat': {'name': 'Pháp luật đại cương', 'counts_gpa': True, 'semester': 2},
    'logic': {'name': 'Logic và suy luận toán học', 'counts_gpa': True, 'semester': 2},
}

SEMESTER_1_SUBJECTS = ['triet_hoc', 'tieng_anh_1', 'tieng_an_do_1', 'gdtc', 'tin_hoc_vp']
SEMESTER_2_SUBJECTS = ['tieng_anh_2', 'tieng_an_do_2', 'tieng_viet_th', 'phap_luat', 'logic']
ACADEMIC_YEAR = 1  # Năm học cố định

# ======================== CẤU HÌNH DATABASE ========================
def init_db():
    conn = sqlite3.connect('student_grades.db', check_same_thread=False)
    c = conn.cursor()
    
    # Bảng users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        role TEXT NOT NULL,
        student_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Bảng điểm sinh viên (cập nhật với môn học mới)
    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mssv TEXT NOT NULL,
        student_name TEXT NOT NULL,
        class_name TEXT,
        semester INTEGER DEFAULT 1,
        triet_hoc REAL,
        tieng_anh_1 REAL,
        tieng_anh_2 REAL,
        tieng_an_do_1 REAL,
        tieng_an_do_2 REAL,
        gdtc REAL,
        tin_hoc_vp REAL,
        tieng_viet_th REAL,
        phap_luat REAL,
        logic REAL,
        diem_tb REAL,
        xep_loai TEXT,
        academic_year INTEGER DEFAULT 1,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tạo tài khoản admin mặc định
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
    if score >= 8.5: return 'Giỏi'
    elif score >= 7.0: return 'Khá'
    elif score >= 5.5: return 'Trung bình'
    elif score >= 4.0: return 'Yếu'
    else: return 'Kém'

def calculate_average(row):
    """Tính điểm TB (không tính GDTC)"""
    scores = []
    for key, info in SUBJECTS.items():
        if info['counts_gpa'] and pd.notna(row.get(key)) and row.get(key, -1) >= 0:
            scores.append(row[key])
    return round(np.mean(scores), 2) if scores else 0

def can_take_semester_2(conn, mssv):
    """Kiểm tra điều kiện học kỳ 2: TB Tiếng Anh 1 + Tiếng Ấn Độ 1 >= 4"""
    df = load_grades(conn)
    student_sem1 = df[(df['mssv'] == mssv) & (df['semester'] == 1)]
    
    if student_sem1.empty:
        return False, "Chưa có điểm học kỳ 1"
    
    row = student_sem1.iloc[0]
    tieng_anh_1 = row.get('tieng_anh_1', 0) or 0
    tieng_an_do_1 = row.get('tieng_an_do_1', 0) or 0
    avg = (tieng_anh_1 + tieng_an_do_1) / 2
    
    if avg >= 4:
        return True, f"Đủ điều kiện (TB: {avg:.2f})"
    else:
        return False, f"Chưa đủ điều kiện (TB: {avg:.2f} < 4)"

# ======================== CHỨC NĂNG DATABASE ========================
def load_grades(conn):
    return pd.read_sql_query("SELECT * FROM grades", conn)

def save_grade(conn, data):
    c = conn.cursor()
    c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester, 
                 triet_hoc, tieng_anh_1, tieng_anh_2, tieng_an_do_1, tieng_an_do_2,
                 gdtc, tin_hoc_vp, tieng_viet_th, phap_luat, logic,
                 diem_tb, xep_loai, academic_year)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()

def delete_grade(conn, grade_id):
    c = conn.cursor()
    c.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    conn.commit()

def clean_data(conn):
    """Làm sạch dữ liệu: xóa trùng MSSV+semester, sửa điểm âm"""
    df = load_grades(conn)
    c = conn.cursor()
    
    # Đếm trước khi làm sạch
    original_count = len(df)
    
    # Xóa điểm âm
    negative_fixed = 0
    for key in SUBJECTS.keys():
        if key in df.columns:
            negative_count = (df[key] < 0).sum()
            negative_fixed += negative_count
            df.loc[df[key] < 0, key] = None
    
    # Xóa trùng lặp (giữ bản ghi đầu tiên)
    df_clean = df.drop_duplicates(subset=['mssv', 'semester'], keep='first')
    duplicates_removed = original_count - len(df_clean)
    
    # Xóa toàn bộ và insert lại
    c.execute("DELETE FROM grades")
    for _, row in df_clean.iterrows():
        diem_tb = calculate_average(row)
        xep_loai = calculate_grade(diem_tb)
        c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester,
                     triet_hoc, tieng_anh_1, tieng_anh_2, tieng_an_do_1, tieng_an_do_2,
                     gdtc, tin_hoc_vp, tieng_viet_th, phap_luat, logic,
                     diem_tb, xep_loai, academic_year)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (row['mssv'], row['student_name'], row.get('class_name'),
                   row.get('semester', 1),
                   row.get('triet_hoc'), row.get('tieng_anh_1'), row.get('tieng_anh_2'),
                   row.get('tieng_an_do_1'), row.get('tieng_an_do_2'),
                   row.get('gdtc'), row.get('tin_hoc_vp'), row.get('tieng_viet_th'),
                   row.get('phap_luat'), row.get('logic'),
                   diem_tb, xep_loai, ACADEMIC_YEAR))
    conn.commit()
    
    return duplicates_removed, negative_fixed

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

# ======================== GIAO DIỆN ========================
def login_page(conn):
    st.title("Hệ thống Quản lý Điểm Sinh viên")
    st.subheader("Đăng nhập")
    
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
        
        st.info("**Tài khoản mặc định:**\n- Username: admin\n- Password: admin123")

def teacher_dashboard(conn):
    st.sidebar.title(f"{st.session_state['fullname']}")
    st.sidebar.write("Vai trò: **Giáo viên**")
    st.sidebar.write(f"Năm học: **{ACADEMIC_YEAR}**")
    
    if st.sidebar.button("Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", [
        "Dashboard",
        "Quản lý điểm",
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
        manage_grades(conn, df)
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
    
    # Thống kê theo học kỳ
    st.subheader("Thống kê theo học kỳ")
    col1, col2 = st.columns(2)
    with col1:
        sem1_count = len(df[df['semester'] == 1])
        st.metric("Học kỳ 1", f"{sem1_count} bản ghi")
    with col2:
        sem2_count = len(df[df['semester'] == 2])
        st.metric("Học kỳ 2", f"{sem2_count} bản ghi")
    
    # Thống kê theo xếp loại
    st.subheader("Thống kê theo xếp loại")
    xep_loai_counts = df['xep_loai'].value_counts()
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(values=xep_loai_counts.values, names=xep_loai_counts.index, 
                    title='Phân bố xếp loại')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(x=xep_loai_counts.index, y=xep_loai_counts.values,
                    title='Số lượng theo xếp loại', labels={'x': 'Xếp loại', 'y': 'Số lượng'})
        st.plotly_chart(fig, use_container_width=True)

def add_grade_form(conn):
    st.title("Thêm điểm sinh viên")
    
    # Chọn học kỳ trước
    semester = st.radio("Chọn học kỳ", [1, 2], horizontal=True)
    
    col1, col2 = st.columns(2)
    with col1:
        mssv = st.text_input("MSSV *")
        student_name = st.text_input("Họ tên *")
        class_name = st.text_input("Lớp")
    
    # Kiểm tra điều kiện học kỳ 2
    can_sem2 = True
    if semester == 2 and mssv:
        can_sem2, message = can_take_semester_2(conn, mssv)
        if can_sem2:
            st.success(f"{message}")
        else:
            st.error(f"{message}")
    
    # Hiển thị các môn theo học kỳ
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
            subject_scores[key] = st.number_input(label, 0.0, 10.0, 0.0, key=key)
    
    # Hiển thị năm học cố định
    st.info(f"Năm học: **{ACADEMIC_YEAR}** (cố định)")
    
    if st.button("Thêm điểm", type="primary", disabled=(semester == 2 and not can_sem2)):
        if mssv and student_name:
            # Tính điểm TB
            scores_for_avg = {k: v for k, v in subject_scores.items() 
                           if SUBJECTS[k]['counts_gpa'] and v > 0}
            diem_tb = round(np.mean(list(scores_for_avg.values())), 2) if scores_for_avg else 0
            xep_loai = calculate_grade(diem_tb)
            
            # Chuẩn bị data (điền None cho môn không thuộc học kỳ này)
            all_scores = {k: None for k in SUBJECTS.keys()}
            all_scores.update(subject_scores)
            
            save_grade(conn, (
                mssv, student_name, class_name, semester,
                all_scores['triet_hoc'], all_scores['tieng_anh_1'], all_scores['tieng_anh_2'],
                all_scores['tieng_an_do_1'], all_scores['tieng_an_do_2'],
                all_scores['gdtc'], all_scores['tin_hoc_vp'], all_scores['tieng_viet_th'],
                all_scores['phap_luat'], all_scores['logic'],
                diem_tb, xep_loai, ACADEMIC_YEAR
            ))
            st.success(f"Đã thêm điểm cho {student_name} - ĐTB: {diem_tb} - Xếp loại: {xep_loai}")
        else:
            st.error("Vui lòng nhập MSSV và Họ tên!")

def manage_grades(conn, df):
    st.title("Quản lý điểm sinh viên")
    
    # Bộ lọc
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Tìm kiếm (MSSV/Tên)")
    with col2:
        semester_filter = st.selectbox("Học kỳ", ['Tất cả', 1, 2])
    with col3:
        xep_loai_filter = st.selectbox("Xếp loại", ['Tất cả'] + list(df['xep_loai'].dropna().unique()))
    
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df['mssv'].str.contains(search, case=False, na=False) |
                                  filtered_df['student_name'].str.contains(search, case=False, na=False)]
    if semester_filter != 'Tất cả':
        filtered_df = filtered_df[filtered_df['semester'] == semester_filter]
    if xep_loai_filter != 'Tất cả':
        filtered_df = filtered_df[filtered_df['xep_loai'] == xep_loai_filter]
    
    # Hiển thị cột cơ bản
    display_cols = ['id', 'mssv', 'student_name', 'class_name', 'semester', 'diem_tb', 'xep_loai']
    st.dataframe(filtered_df[display_cols], use_container_width=True)
    
    # Xem chi tiết điểm
    if not filtered_df.empty:
        st.subheader("Chi tiết điểm")
        selected_id = st.selectbox("Chọn ID để xem chi tiết", filtered_df['id'].tolist())
        selected_row = df[df['id'] == selected_id].iloc[0]
        
        semester = selected_row.get('semester', 1)
        current_subjects = SEMESTER_1_SUBJECTS if semester == 1 else SEMESTER_2_SUBJECTS
        
        cols = st.columns(5)
        for i, key in enumerate(current_subjects):
            with cols[i % 5]:
                score = selected_row.get(key)
                st.metric(SUBJECTS[key]['name'][:15], score if pd.notna(score) else "-")
        
        if st.button("Xóa bản ghi này", type="secondary"):
            delete_grade(conn, selected_id)
            st.success("Đã xóa!")
            st.rerun()

def clean_data_page(conn, df):
    st.title("Làm sạch dữ liệu")
    
    # Phân tích dữ liệu hiện tại
    st.subheader("Phân tích dữ liệu hiện tại")
    
    # Đếm trùng lặp
    duplicate_count = df.duplicated(subset=['mssv', 'semester'], keep='first').sum()
    
    # Đếm điểm âm
    negative_count = 0
    for key in SUBJECTS.keys():
        if key in df.columns:
            negative_count += (df[key] < 0).sum()
    
    col1, col2 = st.columns(2)
    with col1:
        if duplicate_count > 0:
            st.error(f"Có **{duplicate_count}** bản ghi trùng MSSV + Học kỳ")
        else:
            st.success("Không có bản ghi trùng lặp")
    
    with col2:
        if negative_count > 0:
            st.error(f"Có **{negative_count}** điểm âm (không hợp lệ)")
        else:
            st.success("Không có điểm âm")
    
    st.divider()
    
    st.subheader("🔧 Thực hiện làm sạch")
    st.write("Quá trình này sẽ:")
    st.write("- Xóa các bản ghi trùng MSSV + Học kỳ (giữ bản ghi đầu tiên)")
    st.write("- Xóa các điểm có giá trị âm")
    st.write("- Tính lại điểm TB và xếp loại")
    
    if st.button("Làm sạch dữ liệu", type="primary", 
                disabled=(duplicate_count == 0 and negative_count == 0)):
        duplicates_removed, negatives_fixed = clean_data(conn)
        st.success(f"Hoàn thành! Đã xóa {duplicates_removed} bản ghi trùng và sửa {negatives_fixed} điểm âm.")
        st.rerun()

def import_data(conn):
    st.title("Import dữ liệu")
    
    st.info(f"""
    **Định dạng file CSV cần có các cột:**
    - mssv, student_name, class_name, semester
    - {', '.join(SUBJECTS.keys())}
    
    **Lưu ý:** 
    - Học kỳ (semester) = 1 hoặc 2
    - Năm học cố định = {ACADEMIC_YEAR}
    - Giáo dục thể chất không tính vào GPA
    """)
    
    uploaded_file = st.file_uploader("Chọn file CSV", type=['csv'])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("**Xem trước dữ liệu:**")
            st.dataframe(df.head(10))
            
            if st.button("Import vào database"):
                c = conn.cursor()
                for _, row in df.iterrows():
                    diem_tb = calculate_average(row)
                    xep_loai = calculate_grade(diem_tb)
                    semester = row.get('semester', 1)
                    
                    c.execute('''INSERT INTO grades (mssv, student_name, class_name, semester,
                                 triet_hoc, tieng_anh_1, tieng_anh_2, tieng_an_do_1, tieng_an_do_2,
                                 gdtc, tin_hoc_vp, tieng_viet_th, phap_luat, logic,
                                 diem_tb, xep_loai, academic_year)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                              (row.get('mssv', ''), row.get('student_name', ''), row.get('class_name', ''),
                               semester,
                               row.get('triet_hoc'), row.get('tieng_anh_1'), row.get('tieng_anh_2'),
                               row.get('tieng_an_do_1'), row.get('tieng_an_do_2'),
                               row.get('gdtc'), row.get('tin_hoc_vp'), row.get('tieng_viet_th'),
                               row.get('phap_luat'), row.get('logic'),
                               diem_tb, xep_loai, ACADEMIC_YEAR))
                conn.commit()
                st.success(f"Đã import {len(df)} bản ghi!")
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")

def export_data(df):
    st.title("Export dữ liệu")
    
    if df.empty:
        st.warning("Không có dữ liệu để export.")
        return
    
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Tải file CSV", csv, "student_grades.csv", "text/csv")

def manage_users(conn):
    st.title("Quản lý tài khoản")
    
    tab1, tab2 = st.tabs(["Danh sách", "Thêm mới"])
    
    with tab1:
        users_df = get_all_users(conn)
        st.dataframe(users_df, use_container_width=True)
        
        if len(users_df) > 1:
            user_to_delete = st.selectbox("Chọn user để xóa", 
                                          users_df[users_df['username'] != 'admin']['id'].tolist())
            if st.button("Xóa user"):
                delete_user(conn, user_to_delete)
                st.success("Đã xóa!")
                st.rerun()
    
    with tab2:
        st.subheader("Thêm tài khoản mới")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_fullname = st.text_input("Họ tên")
        new_role = st.selectbox("Vai trò", ["student", "teacher"])
        new_student_id = st.text_input("MSSV (nếu là học sinh)") if new_role == "student" else None
        
        if st.button("Tạo tài khoản"):
            if new_username and new_password and new_fullname:
                if create_user(conn, new_username, new_password, new_fullname, new_role, new_student_id):
                    st.success("Đã tạo tài khoản!")
                    st.rerun()
                else:
                    st.error("Username đã tồn tại!")
            else:
                st.error("Vui lòng điền đầy đủ thông tin!")

def show_charts(df):
    st.title("Biểu đồ phân tích")
    
    if df.empty:
        st.warning("Chưa có dữ liệu để phân tích.")
        return
    
    # 1. Điểm TB theo lớp
    st.subheader("Điểm trung bình theo lớp")
    class_avg = df.groupby('class_name')['diem_tb'].mean().reset_index()
    fig1 = px.bar(class_avg, x='class_name', y='diem_tb', 
                  title='Điểm TB theo lớp', color='diem_tb',
                  labels={'class_name': 'Lớp', 'diem_tb': 'Điểm TB'})
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Phân bố xếp loại
    st.subheader("Phân bố xếp loại")
    fig2 = px.pie(df, names='xep_loai', title='Tỷ lệ xếp loại học lực',
                  color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Điểm TB các môn (chỉ môn tính GPA)
    st.subheader("Điểm trung bình các môn học")
    subject_avg = []
    for key, info in SUBJECTS.items():
        if info['counts_gpa'] and key in df.columns:
            avg = df[key].mean()
            if pd.notna(avg):
                subject_avg.append({'Môn': info['name'], 'Điểm TB': avg})
    
    if subject_avg:
        subject_df = pd.DataFrame(subject_avg)
        fig3 = px.line(subject_df, x='Môn', y='Điểm TB', markers=True, title='Điểm TB các môn')
        st.plotly_chart(fig3, use_container_width=True)
    
    # 4. So sánh học kỳ
    st.subheader("So sánh theo học kỳ")
    semester_avg = df.groupby('semester')['diem_tb'].mean().reset_index()
    semester_avg['semester'] = semester_avg['semester'].map({1: 'Học kỳ 1', 2: 'Học kỳ 2'})
    fig4 = px.bar(semester_avg, x='semester', y='diem_tb', 
                  title='Điểm TB theo học kỳ', color='diem_tb')
    st.plotly_chart(fig4, use_container_width=True)
    
    # 5. Phân bố điểm TB
    st.subheader("Phân bố điểm trung bình")
    fig5 = px.histogram(df, x='diem_tb', nbins=20, title='Phân bố điểm TB')
    st.plotly_chart(fig5, use_container_width=True)

def student_dashboard(conn):
    st.sidebar.title(f"{st.session_state['fullname']}")
    st.sidebar.write("Vai trò: **Học sinh**")
    
    if st.sidebar.button("Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", [
        "Bảng điểm của tôi",
        "Tra cứu điểm",
        "Thống kê chung"
    ])
    
    df = load_grades(conn)
    student_id = st.session_state.get('student_id', '')
    
    if menu == "Bảng điểm của tôi":
        st.title("Bảng điểm của tôi")
        my_grades = df[df['mssv'] == student_id]
        if not my_grades.empty:
            for _, row in my_grades.iterrows():
                semester = row.get('semester', 1)
                st.subheader(f"Học kỳ {semester}")
                
                current_subjects = SEMESTER_1_SUBJECTS if semester == 1 else SEMESTER_2_SUBJECTS
                cols = st.columns(5)
                for i, key in enumerate(current_subjects):
                    with cols[i % 5]:
                        score = row.get(key)
                        st.metric(SUBJECTS[key]['name'][:12], score if pd.notna(score) else "-")
                
                st.metric("Điểm TB", f"{row['diem_tb']:.2f}")
                st.metric("Xếp loại", row['xep_loai'])
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
    
    elif menu == "Thống kê chung":
        st.title("Thống kê chung")
        if not df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Tổng SV", df['mssv'].nunique())
            with col2:
                st.metric("Điểm TB", f"{df['diem_tb'].mean():.2f}")
            with col3:
                excellent_rate = (df['xep_loai'] == 'Giỏi').sum() / len(df) * 100
                st.metric("Tỷ lệ Giỏi", f"{excellent_rate:.1f}%")
            with col4:
                st.metric("Số lớp", df['class_name'].nunique())
            
            fig = px.pie(df, names='xep_loai', title='Phân bố xếp loại')
            st.plotly_chart(fig, use_container_width=True)

# ======================== MAIN ========================
def main():
    st.set_page_config(page_title="Quản lý điểm sinh viên", page_icon="", layout="wide")
    
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
