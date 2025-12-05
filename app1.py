# app.py - Ứng dụng phân tích kết quả học tập sinh viên
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
from datetime import datetime

# ======================== CẤU HÌNH DATABASE ========================
def init_db():
    conn = sqlite3.connect('student_grades.db', check_same_thread=False)
    c = conn.cursor()
    
    # Bảng users (giáo viên/học sinh)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        fullname TEXT NOT NULL,
        role TEXT NOT NULL,
        student_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Bảng điểm sinh viên
    c.execute('''CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mssv TEXT NOT NULL,
        student_name TEXT NOT NULL,
        class_name TEXT,
        toan REAL,
        ly REAL,
        hoa REAL,
        van REAL,
        anh REAL,
        tin_hoc REAL,
        lap_trinh REAL,
        diem_tb REAL,
        xep_loai TEXT,
        semester TEXT,
        academic_year TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Tạo tài khoản admin mặc định nếu chưa có
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

def get_user_info(conn, username):
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    return c.fetchone()

def calculate_grade(score):
    if score >= 8.5: return 'Giỏi'
    elif score >= 7.0: return 'Khá'
    elif score >= 5.5: return 'Trung bình'
    elif score >= 4.0: return 'Yếu'
    else: return 'Kém'

def calculate_average(row):
    subjects = ['toan', 'ly', 'hoa', 'van', 'anh', 'tin_hoc', 'lap_trinh']
    scores = [row[s] for s in subjects if pd.notna(row.get(s))]
    return round(np.mean(scores), 2) if scores else 0

# ======================== CHỨC NĂNG DATABASE ========================
def load_grades(conn):
    return pd.read_sql_query("SELECT * FROM grades", conn)

def save_grade(conn, data):
    c = conn.cursor()
    c.execute('''INSERT INTO grades (mssv, student_name, class_name, toan, ly, hoa, van, anh, tin_hoc, lap_trinh, diem_tb, xep_loai, semester, academic_year)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()

def update_grade(conn, grade_id, data):
    c = conn.cursor()
    c.execute('''UPDATE grades SET mssv=?, student_name=?, class_name=?, toan=?, ly=?, hoa=?, van=?, anh=?, tin_hoc=?, lap_trinh=?, diem_tb=?, xep_loai=?, semester=?, academic_year=?, updated_at=?
                 WHERE id=?''', (*data, datetime.now(), grade_id))
    conn.commit()

def delete_grade(conn, grade_id):
    c = conn.cursor()
    c.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    conn.commit()

def import_grades_from_df(conn, df):
    c = conn.cursor()
    for _, row in df.iterrows():
        diem_tb = calculate_average(row)
        xep_loai = calculate_grade(diem_tb)
        c.execute('''INSERT INTO grades (mssv, student_name, class_name, toan, ly, hoa, van, anh, tin_hoc, lap_trinh, diem_tb, xep_loai, semester, academic_year)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (row.get('mssv', ''), row.get('student_name', ''), row.get('class_name', ''),
                   row.get('toan'), row.get('ly'), row.get('hoa'), row.get('van'),
                   row.get('anh'), row.get('tin_hoc'), row.get('lap_trinh'),
                   diem_tb, xep_loai, row.get('semester', ''), row.get('academic_year', '')))
    conn.commit()

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
    st.title("🎓 Hệ thống Quản lý Điểm Sinh viên")
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
    st.sidebar.title(f"👨‍🏫 {st.session_state['fullname']}")
    st.sidebar.write("Vai trò: **Giáo viên**")
    
    if st.sidebar.button("🚪 Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", [
        "📊 Dashboard",
        "📋 Quản lý điểm",
        "➕ Thêm điểm",
        "📥 Import dữ liệu",
        "📤 Export dữ liệu",
        "👥 Quản lý tài khoản",
        "📈 Biểu đồ phân tích"
    ])
    
    df = load_grades(conn)
    
    if menu == "📊 Dashboard":
        show_dashboard(df)
    elif menu == "📋 Quản lý điểm":
        manage_grades(conn, df)
    elif menu == "➕ Thêm điểm":
        add_grade_form(conn)
    elif menu == "📥 Import dữ liệu":
        import_data(conn)
    elif menu == "📤 Export dữ liệu":
        export_data(df)
    elif menu == "👥 Quản lý tài khoản":
        manage_users(conn)
    elif menu == "📈 Biểu đồ phân tích":
        show_charts(df)

def student_dashboard(conn):
    st.sidebar.title(f"👨‍🎓 {st.session_state['fullname']}")
    st.sidebar.write("Vai trò: **Học sinh**")
    
    if st.sidebar.button("🚪 Đăng xuất"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    menu = st.sidebar.radio("Menu", [
        "📋 Bảng điểm của tôi",
        "🔍 Tra cứu điểm",
        "📊 Thống kê chung"
    ])
    
    df = load_grades(conn)
    student_id = st.session_state.get('student_id', '')
    
    if menu == "📋 Bảng điểm của tôi":
        st.title("📋 Bảng điểm của tôi")
        my_grades = df[df['mssv'] == student_id]
        if not my_grades.empty:
            st.dataframe(my_grades, use_container_width=True)
            
            # Thống kê cá nhân
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Điểm TB", f"{my_grades['diem_tb'].mean():.2f}")
            with col2:
                st.metric("Xếp loại", my_grades['xep_loai'].mode()[0] if not my_grades['xep_loai'].mode().empty else "N/A")
            with col3:
                st.metric("Số học phần", len(my_grades))
        else:
            st.warning("Chưa có dữ liệu điểm của bạn.")
    
    elif menu == "🔍 Tra cứu điểm":
        st.title("🔍 Tra cứu điểm sinh viên")
        search_term = st.text_input("Nhập MSSV hoặc tên sinh viên")
        if search_term:
            results = df[df['mssv'].str.contains(search_term, case=False, na=False) | 
                        df['student_name'].str.contains(search_term, case=False, na=False)]
            if not results.empty:
                # Chỉ hiển thị thông tin cơ bản
                st.dataframe(results[['mssv', 'student_name', 'class_name', 'diem_tb', 'xep_loai']], 
                           use_container_width=True)
            else:
                st.info("Không tìm thấy kết quả.")
    
    elif menu == "📊 Thống kê chung":
        st.title("📊 Thống kê chung")
        if not df.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Tổng sinh viên", df['mssv'].nunique())
            with col2:
                st.metric("Điểm TB toàn trường", f"{df['diem_tb'].mean():.2f}")
            with col3:
                st.metric("Tỷ lệ Giỏi", f"{(df['xep_loai'] == 'Giỏi').sum() / len(df) * 100:.1f}%")
            with col4:
                st.metric("Số lớp", df['class_name'].nunique())
            
            # Biểu đồ phân bố xếp loại
            fig = px.pie(df, names='xep_loai', title='Phân bố xếp loại')
            st.plotly_chart(fig, use_container_width=True)

def show_dashboard(df):
    st.title("📊 Dashboard Tổng quan")
    
    if df.empty:
        st.warning("Chưa có dữ liệu. Vui lòng import hoặc thêm dữ liệu.")
        return
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tổng sinh viên", df['mssv'].nunique())
    with col2:
        st.metric("Điểm TB", f"{df['diem_tb'].mean():.2f}")
    with col3:
        st.metric("Cao nhất", f"{df['diem_tb'].max():.2f}")
    with col4:
        st.metric("Thấp nhất", f"{df['diem_tb'].min():.2f}")
    
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

def manage_grades(conn, df):
    st.title("📋 Quản lý điểm sinh viên")
    
    # Bộ lọc
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("🔍 Tìm kiếm (MSSV/Tên)")
    with col2:
        class_filter = st.selectbox("Lớp", ['Tất cả'] + list(df['class_name'].dropna().unique()))
    with col3:
        xep_loai_filter = st.selectbox("Xếp loại", ['Tất cả'] + list(df['xep_loai'].dropna().unique()))
    
    filtered_df = df.copy()
    if search:
        filtered_df = filtered_df[filtered_df['mssv'].str.contains(search, case=False, na=False) |
                                  filtered_df['student_name'].str.contains(search, case=False, na=False)]
    if class_filter != 'Tất cả':
        filtered_df = filtered_df[filtered_df['class_name'] == class_filter]
    if xep_loai_filter != 'Tất cả':
        filtered_df = filtered_df[filtered_df['xep_loai'] == xep_loai_filter]
    
    st.dataframe(filtered_df, use_container_width=True)
    
    # Sửa/Xóa
    st.subheader("Sửa/Xóa điểm")
    if not filtered_df.empty:
        selected_id = st.selectbox("Chọn ID để sửa/xóa", filtered_df['id'].tolist())
        selected_row = df[df['id'] == selected_id].iloc[0]
        
        with st.expander("Sửa thông tin"):
            col1, col2 = st.columns(2)
            with col1:
                new_mssv = st.text_input("MSSV", selected_row['mssv'])
                new_name = st.text_input("Họ tên", selected_row['student_name'])
                new_class = st.text_input("Lớp", selected_row['class_name'] or '')
                new_toan = st.number_input("Toán", 0.0, 10.0, float(selected_row['toan'] or 0))
                new_ly = st.number_input("Lý", 0.0, 10.0, float(selected_row['ly'] or 0))
                new_hoa = st.number_input("Hóa", 0.0, 10.0, float(selected_row['hoa'] or 0))
            with col2:
                new_van = st.number_input("Văn", 0.0, 10.0, float(selected_row['van'] or 0))
                new_anh = st.number_input("Anh", 0.0, 10.0, float(selected_row['anh'] or 0))
                new_tin = st.number_input("Tin học", 0.0, 10.0, float(selected_row['tin_hoc'] or 0))
                new_lap_trinh = st.number_input("Lập trình", 0.0, 10.0, float(selected_row['lap_trinh'] or 0))
                new_semester = st.text_input("Học kỳ", selected_row['semester'] or '')
                new_year = st.text_input("Năm học", selected_row['academic_year'] or '')
            
            if st.button("💾 Lưu thay đổi"):
                scores = [new_toan, new_ly, new_hoa, new_van, new_anh, new_tin, new_lap_trinh]
                diem_tb = round(np.mean([s for s in scores if s > 0]), 2)
                xep_loai = calculate_grade(diem_tb)
                update_grade(conn, selected_id, (new_mssv, new_name, new_class, new_toan, new_ly, new_hoa, new_van, new_anh, new_tin, new_lap_trinh, diem_tb, xep_loai, new_semester, new_year))
                st.success("Đã cập nhật!")
                st.rerun()
        
        if st.button("🗑️ Xóa bản ghi này", type="secondary"):
            delete_grade(conn, selected_id)
            st.success("Đã xóa!")
            st.rerun()

def add_grade_form(conn):
    st.title("➕ Thêm điểm sinh viên")
    
    col1, col2 = st.columns(2)
    with col1:
        mssv = st.text_input("MSSV *")
        student_name = st.text_input("Họ tên *")
        class_name = st.text_input("Lớp")
        toan = st.number_input("Toán", 0.0, 10.0, 0.0)
        ly = st.number_input("Lý", 0.0, 10.0, 0.0)
        hoa = st.number_input("Hóa", 0.0, 10.0, 0.0)
    with col2:
        van = st.number_input("Văn", 0.0, 10.0, 0.0)
        anh = st.number_input("Anh", 0.0, 10.0, 0.0)
        tin_hoc = st.number_input("Tin học", 0.0, 10.0, 0.0)
        lap_trinh = st.number_input("Lập trình", 0.0, 10.0, 0.0)
        semester = st.text_input("Học kỳ")
        academic_year = st.text_input("Năm học")
    
    if st.button("➕ Thêm điểm", type="primary"):
        if mssv and student_name:
            scores = [toan, ly, hoa, van, anh, tin_hoc, lap_trinh]
            diem_tb = round(np.mean([s for s in scores if s > 0]), 2)
            xep_loai = calculate_grade(diem_tb)
            save_grade(conn, (mssv, student_name, class_name, toan, ly, hoa, van, anh, tin_hoc, lap_trinh, diem_tb, xep_loai, semester, academic_year))
            st.success(f"Đã thêm điểm cho {student_name} - ĐTB: {diem_tb} - Xếp loại: {xep_loai}")
        else:
            st.error("Vui lòng nhập MSSV và Họ tên!")

def import_data(conn):
    st.title("📥 Import dữ liệu")
    
    st.info("""
    **Định dạng file CSV/Excel cần có các cột:**
    - mssv, student_name, class_name
    - toan, ly, hoa, van, anh, tin_hoc, lap_trinh
    - semester, academic_year (tùy chọn)
    """)
    
    uploaded_file = st.file_uploader("Chọn file CSV hoặc Excel", type=['csv', 'xlsx', 'xls'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("**Xem trước dữ liệu:**")
            st.dataframe(df.head(10))
            
            if st.button("📥 Import vào database"):
                import_grades_from_df(conn, df)
                st.success(f"Đã import {len(df)} bản ghi!")
                st.rerun()
        except Exception as e:
            st.error(f"Lỗi: {e}")

def export_data(df):
    st.title("📤 Export dữ liệu")
    
    if df.empty:
        st.warning("Không có dữ liệu để export.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Tải CSV", csv, "student_grades.csv", "text/csv")
    with col2:
        # Export Excel
        from io import BytesIO
        buffer = BytesIO()
        df.to_excel(buffer, index=False)
        st.download_button("📥 Tải Excel", buffer.getvalue(), "student_grades.xlsx")

def manage_users(conn):
    st.title("👥 Quản lý tài khoản")
    
    tab1, tab2 = st.tabs(["Danh sách", "Thêm mới"])
    
    with tab1:
        users_df = get_all_users(conn)
        st.dataframe(users_df, use_container_width=True)
        
        # Xóa user
        if len(users_df) > 1:
            user_to_delete = st.selectbox("Chọn user để xóa", 
                                          users_df[users_df['username'] != 'admin']['id'].tolist())
            if st.button("🗑️ Xóa user"):
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
        
        if st.button("➕ Tạo tài khoản"):
            if new_username and new_password and new_fullname:
                if create_user(conn, new_username, new_password, new_fullname, new_role, new_student_id):
                    st.success("Đã tạo tài khoản!")
                    st.rerun()
                else:
                    st.error("Username đã tồn tại!")
            else:
                st.error("Vui lòng điền đầy đủ thông tin!")

def show_charts(df):
    st.title("📈 Biểu đồ phân tích")
    
    if df.empty:
        st.warning("Chưa có dữ liệu để phân tích.")
        return
    
    # 1. Biểu đồ cột - Điểm TB theo lớp
    st.subheader("1️⃣ Điểm trung bình theo lớp")
    class_avg = df.groupby('class_name')['diem_tb'].mean().reset_index()
    fig1 = px.bar(class_avg, x='class_name', y='diem_tb', 
                  title='Điểm TB theo lớp', color='diem_tb',
                  labels={'class_name': 'Lớp', 'diem_tb': 'Điểm TB'})
    st.plotly_chart(fig1, use_container_width=True)
    
    # 2. Biểu đồ tròn - Phân bố xếp loại
    st.subheader("2️⃣ Phân bố xếp loại")
    fig2 = px.pie(df, names='xep_loai', title='Tỷ lệ xếp loại học lực',
                  color_discrete_sequence=px.colors.qualitative.Set3)
    st.plotly_chart(fig2, use_container_width=True)
    
    # 3. Biểu đồ đường - Điểm TB các môn
    st.subheader("3️⃣ Điểm trung bình các môn học")
    subjects = ['toan', 'ly', 'hoa', 'van', 'anh', 'tin_hoc', 'lap_trinh']
    subject_names = ['Toán', 'Lý', 'Hóa', 'Văn', 'Anh', 'Tin học', 'Lập trình']
    subject_avg = [df[s].mean() for s in subjects]
    fig3 = px.line(x=subject_names, y=subject_avg, markers=True,
                   title='Điểm TB các môn', labels={'x': 'Môn học', 'y': 'Điểm TB'})
    st.plotly_chart(fig3, use_container_width=True)
    
    # 4. Histogram - Phân bố điểm TB
    st.subheader("4️⃣ Phân bố điểm trung bình")
    fig4 = px.histogram(df, x='diem_tb', nbins=20, 
                        title='Phân bố điểm TB', labels={'diem_tb': 'Điểm TB'})
    st.plotly_chart(fig4, use_container_width=True)
    
    # 5. Box plot - Điểm theo lớp
    st.subheader("5️⃣ Phân bố điểm theo lớp")
    fig5 = px.box(df, x='class_name', y='diem_tb', color='class_name',
                  title='Box plot điểm TB theo lớp')
    st.plotly_chart(fig5, use_container_width=True)
    
    # 6. Scatter plot
    st.subheader("6️⃣ Tương quan Toán - Lập trình")
    fig6 = px.scatter(df, x='toan', y='lap_trinh', color='xep_loai',
                      title='Tương quan điểm Toán và Lập trình',
                      labels={'toan': 'Điểm Toán', 'lap_trinh': 'Điểm Lập trình'})
    st.plotly_chart(fig6, use_container_width=True)
    
    # 7. Heatmap - Ma trận tương quan
    st.subheader("7️⃣ Ma trận tương quan các môn")
    numeric_cols = df[subjects].dropna()
    if not numeric_cols.empty:
        corr_matrix = numeric_cols.corr()
        fig7 = px.imshow(corr_matrix, text_auto=True, aspect="auto",
                         title='Ma trận tương quan', x=subject_names, y=subject_names)
        st.plotly_chart(fig7, use_container_width=True)

# ======================== MAIN ========================
def main():
    st.set_page_config(page_title="Quản lý điểm sinh viên", page_icon="🎓", layout="wide")
    
    # Khởi tạo database
    conn = init_db()
    
    # Kiểm tra đăng nhập
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
