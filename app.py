import streamlit as st
import sqlite3
import pandas as pd
import os
import re
from groq import Groq

# --- 1. إعدادات الواجهة والتصميم (UI & CSS) ---
st.set_page_config(page_title="Ar-Spider Smart Engine", page_icon="", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');

    .stApp {
        font-family: 'Tajawal', sans-serif;
        direction: RTL;
        text-align: right;
    }

    input {
        direction: RTL !important;
        text-align: right !important;
    }

    div.stButton > button {
        width: 100%;
        border-radius: 12px;
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        color: white;
        font-weight: bold;
        height: 3.5em;
        border: none;
    }

    .sql-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 12px;
        border-right: 6px solid #10b981;
        color: #34d399;
        font-family: 'Courier New', monospace;
        direction: LTR !important;
        text-align: left !important;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)


# --- 2. إدارة قاعدة البيانات (20 طالباً - أسماء رجال) ---
def init_db():
    conn = sqlite3.connect('university.db')
    cursor = conn.cursor()

    cursor.execute('DROP TABLE IF EXISTS students')
    cursor.execute('DROP TABLE IF EXISTS departments')

    cursor.execute('CREATE TABLE departments (dept_id INTEGER PRIMARY KEY, dept_name TEXT)')
    cursor.execute('''CREATE TABLE students (
                        student_id INTEGER PRIMARY KEY, name TEXT, 
                        dept_id INTEGER, age INTEGER, gpa REAL, city TEXT,
                        FOREIGN KEY (dept_id) REFERENCES departments (dept_id))''')

    depts = [(1, 'علوم الحاسب'), (2, 'الهندسة'), (3, 'إدارة الأعمال'), (4, 'الطب'), (5, 'القانون')]
    cursor.executemany('INSERT INTO departments VALUES (?,?)', depts)

    # 20 طالباً - 5 منهم اسمهم الأول "عبدالله"
    students_data = [
        (1, 'عبدالله الفيفي', 1, 22, 3.9, 'جازان'), (2, 'عبدالله القحطاني', 1, 23, 3.7, 'الرياض'),
        (3, 'عبدالله الزهراني', 2, 21, 3.8, 'جدة'), (4, 'عبدالله الشمري', 3, 24, 3.5, 'حائل'),
        (5, 'عبدالله العتيبي', 1, 20, 4.0, 'مكة'), (6, 'محمد الدوسري', 5, 22, 3.5, 'الدمام'),
        (7, 'خالد الغامدي', 2, 23, 3.9, 'الباحة'), (8, 'فيصل الحربي', 1, 21, 3.4, 'المدينة'),
        (9, 'سلطان المطيري', 2, 22, 3.6, 'القصيم'), (10, 'تركي التميمي', 3, 25, 2.9, 'الرياض'),
        (11, 'فهد السبيعي', 4, 21, 3.8, 'الخبر'), (12, 'صالح الشهري', 1, 23, 3.1, 'أبها'),
        (13, 'عمر الرويلي', 5, 20, 3.7, 'سكاكا'), (14, 'ابراهيم العنزي', 2, 24, 3.3, 'تبوك'),
        (15, 'ياسر العلي', 3, 22, 3.5, 'نجران'), (16, 'ناصر باوزير', 1, 21, 3.6, 'جدة'),
        (17, 'أحمد الفيفي', 2, 23, 4.0, 'فيفاء'), (18, 'سعد المالكي', 4, 22, 3.4, 'الطائف'),
        (19, 'سامي الرشيدي', 5, 21, 3.2, 'حفر الباطن'), (20, 'ماجد الشريف', 1, 24, 3.9, 'مكة')
    ]
    cursor.executemany('INSERT INTO students VALUES (?,?,?,?,?,?)', students_data)
    conn.commit()
    conn.close()


# --- 3. الدوال البرمجية والربط بالذكاء الاصطناعي ---

def get_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema = ""
    for table in tables:
        t_name = table[0]
        cursor.execute(f"PRAGMA table_info('{t_name}')")
        cols = [col[1] for col in cursor.fetchall()]
        schema += f"Table {t_name}: Columns({', '.join(cols)})\n"
    conn.close()
    return schema


def text_to_sql(query, schema, model, api_key):
    client = Groq(api_key=api_key)
    # تحسين البرومبت لإجبار الموديل على الـ JOIN عند الحاجة
    prompt = f"""
    Schema:
    {schema}

    Instructions:
    1. Convert the Arabic query to valid SQL.
    2. If the query involves department names (e.g., 'علوم الحاسب'), you MUST JOIN 'students' and 'departments' on 'dept_id'.
    3. Use 'LIKE' with wildcards for name searches (e.g., name LIKE 'عبدالله%').
    4. Return ONLY the SQL code inside a sql  block.

    Query: {query}
    """
    try:
        response = client.chat.completions.create(
            messages=[{"role": "system", "content": "You are a professional Text-to-SQL expert."},
                      {"role": "user", "content": prompt}],
            model=model, temperature=0
        )
        content = response.choices[0].message.content
        sql = re.search(r'sql\s*(.*?)\s*', content, re.DOTALL)
        return sql.group(1).strip() if sql else content.strip()
    except Exception as e:
        return f"Error: {e}"


# --- 4. واجهة المستخدم الرئيسية ---

init_db()
current_schema = get_schema('university.db')

with st.sidebar:
    st.markdown("<h2 style='text-align: center;'> الإعدادات</h2>", unsafe_allow_html=True)
    api_key = st.text_input(" Groq API Key:", type="password")
    model_name = st.selectbox(" النموذج:", ["llama-3.3-70b-versatile", "deepseek-r1-distill-llama-70b"])
    st.divider()
    st.info(" حالة القاعدة: متصلة (20 سجل)")

st.markdown("<h1 style='text-align: center;'> المحرك الذكي</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>مشروع تخرج  | جامعة جازان</p>", unsafe_allow_html=True)

query_input = st.text_input(" أدخل سؤالك بالعربية:", placeholder="مثلاً: كم طالب اسمه عبدالله في قسم علوم الحاسب؟")

if st.button("توليد وتنفيذ الاستعلام "):
    if not api_key:
        st.error(" يرجى إدخال مفتاح API في القائمة الجانبية.")
    elif query_input:
        with st.spinner(' جاري معالجة السؤال برمجياً...'):
            sql_code = text_to_sql(query_input, current_schema, model_name, api_key)

            if "Error" in sql_code:
                st.error(sql_code)
            else:
                st.markdown("###  SQL المولد")
                st.markdown(f'<div class="sql-card"><code>{sql_code}</code></div>', unsafe_allow_html=True)

                try:
                    conn = sqlite3.connect('university.db')
                    df = pd.read_sql_query(sql_code, conn)
                    conn.close()

                    st.markdown("###  النتائج")
                    if not df.empty:
                        st.success(f"تم إيجاد {len(df)} سجل")
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.warning("لا توجد بيانات مطابقة.")
                except Exception as e:
                    st.error(f"خطأ في التنفيذ: {e}")
    else:
        st.warning("يرجى كتابة سؤال.")

st.divider()
st.caption("Graduate Project © 2026 | Ar-Spider Engine")