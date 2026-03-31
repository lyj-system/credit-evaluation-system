# 系统2_custom_login.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import hashlib
from datetime import datetime

# ==================== 页面配置 ====================
st.set_page_config(page_title="供应链金融信用评估系统", layout="wide")

# ==================== 用户数据存储路径 ====================
USERS_DB_FILE = "users_db.json"  # 存储用户名和密码哈希
USER_DATA_DIR = "user_data"  # 存储每个用户的历史记录文件

# 确保用户数据目录存在
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)


# ==================== 密码加密 ====================
def hash_password(password):
    """简单的密码哈希（实际应用可使用更安全的bcrypt，这里用sha256足够演示）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, hashed):
    return hash_password(password) == hashed


# ==================== 用户数据库操作 ====================
def load_users_db():
    if os.path.exists(USERS_DB_FILE):
        with open(USERS_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users_db(users):
    with open(USERS_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register_user(username, password):
    users = load_users_db()
    if username in users:
        return False  # 用户名已存在
    users[username] = hash_password(password)
    save_users_db(users)
    # 为用户创建空历史文件
    user_history_file = os.path.join(USER_DATA_DIR, f"{username}_history.json")
    if not os.path.exists(user_history_file):
        with open(user_history_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
    return True


def login_user(username, password):
    users = load_users_db()
    if username not in users:
        return False
    return verify_password(password, users[username])


def get_user_history_file(username):
    return os.path.join(USER_DATA_DIR, f"{username}_history.json")


def load_history(username):
    file_path = get_user_history_file(username)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(username, record):
    history = load_history(username)
    history.append(record)
    file_path = get_user_history_file(username)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def clear_all_history(username):
    file_path = get_user_history_file(username)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)


# ==================== 登录状态管理 ====================
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = None


# ==================== 登录/注册界面 ====================
def login_page():
    st.title("🔐 中小企业供应链金融信用智能评估系统")
    st.markdown("---")
    st.subheader("登录或注册")

    with st.form("login_form"):
        username = st.text_input("用户名", placeholder="自定义用户名（首次使用将自动注册）")
        password = st.text_input("密码", type="password", placeholder="密码")
        col1, col2 = st.columns([1, 3])
        with col1:
            submitted = st.form_submit_button("登录 / 注册", use_container_width=True)

        if submitted:
            if not username or not password:
                st.warning("请输入用户名和密码")
            else:
                # 先尝试登录
                if login_user(username, password):
                    st.session_state.username = username
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    # 登录失败，尝试注册（如果用户名不存在）
                    if username not in load_users_db():
                        if register_user(username, password):
                            st.success(f"注册成功！欢迎 {username}")
                            st.session_state.username = username
                            st.session_state.logged_in = True
                            st.rerun()
                        else:
                            st.error("注册失败，请稍后重试")
                    else:
                        st.error("用户名或密码错误")

    st.markdown("---")
    st.caption("提示：首次使用请输入自定义用户名和密码，系统将自动创建账户。后续使用相同凭据登录即可。")


# ==================== 主应用（登录后） ====================
def main_app():
    username = st.session_state.username
    st.title(f"🏭 中小企业供应链金融信用智能评估系统")
    st.markdown("---")

    # ==================== 权重配置 ====================
    WEIGHTS = {
        '经营年限': 0.023,
        '不良记录': 0.059,
        '员工规模': 0.013,
        '资产负债率': 0.034,
        '流动比率': 0.063,
        '营业收入': 0.118,
        '净利润': 0.063,
        '合作年限': 0.082,
        '订单履约率': 0.151,
        '回款率': 0.082,
        '合同完成率': 0.152,
        '存货周转率': 0.020,
        '逾期记录': 0.089,
        '纳税等级': 0.051
    }

    DIMENSIONS = {
        '企业基本资质': ['经营年限', '不良记录', '员工规模'],
        '财务状况': ['资产负债率', '流动比率', '营业收入', '净利润'],
        '供应链交易': ['合作年限', '订单履约率', '回款率', '合同完成率'],
        '运营风险': ['存货周转率', '逾期记录', '纳税等级']
    }

    # ==================== 评分函数 ====================
    def standardize_data(data):
        std = data.copy()
        std['经营年限'] = min(data['经营年限'] / 20, 1.0)
        std['员工规模'] = min(data['员工规模'] / 500, 1.0)
        std['流动比率'] = min(data['流动比率'] / 3, 1.0)
        std['营业收入'] = min(data['营业收入'] / 30000, 1.0)
        std['净利润'] = min(max(data['净利润'] / 2000, 0), 1.0)
        std['合作年限'] = min(data['合作年限'] / 15, 1.0)
        std['订单履约率'] = data['订单履约率'] / 100
        std['回款率'] = data['回款率'] / 100
        std['合同完成率'] = data['合同完成率'] / 100
        std['存货周转率'] = min(data['存货周转率'] / 12, 1.0)
        std['纳税等级'] = data['纳税等级'] / 4
        std['不良记录'] = 1 - data['不良记录']
        std['资产负债率'] = 1 - min(data['资产负债率'] / 100, 1.0)
        std['逾期记录'] = 1 - data['逾期记录']
        return std

    def calculate_score(std_data):
        return sum(std_data[key] * WEIGHTS[key] for key in WEIGHTS.keys())

    def get_rating(score):
        if score >= 0.85:
            return "AAA", "信用极好", "#1a7f37"
        elif score >= 0.70:
            return "AA", "信用优良", "#2c6e49"
        elif score >= 0.55:
            return "A", "信用良好", "#f39c12"
        elif score >= 0.35:
            return "B", "信用一般", "#e67e22"
        else:
            return "C", "信用较差", "#c0392b"

    def calculate_dimension_scores(std_data):
        dim_scores = {}
        for dim, indicators in DIMENSIONS.items():
            dim_weight_sum = sum(WEIGHTS[i] for i in indicators)
            dim_score = sum(std_data[i] * WEIGHTS[i] for i in indicators) / dim_weight_sum
            dim_scores[dim] = dim_score
        return dim_scores

    def draw_radar_chart(dim_scores, title="企业各维度得分"):
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[dim_scores['企业基本资质'], dim_scores['财务状况'],
               dim_scores['供应链交易'], dim_scores['运营风险'],
               dim_scores['企业基本资质']],
            theta=['企业基本资质', '财务状况', '供应链交易', '运营风险', '企业基本资质'],
            fill='toself',
            name='当前企业',
            line_color='#1f77b4'
        ))
        fig.add_trace(go.Scatterpolar(
            r=[1, 1, 1, 1, 1],
            theta=['企业基本资质', '财务状况', '供应链交易', '运营风险', '企业基本资质'],
            fill='none',
            line=dict(color='rgba(0,0,0,0.2)', dash='dot'),
            name='基准线'
        ))
        fig.update_layout(
            title=title,
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            showlegend=False,
            height=400
        )
        return fig

    # ==================== 侧边栏 ====================
    with st.sidebar:
        st.header("📋 信用等级说明")
        with st.expander("🔵 AAA级 (≥0.85) - 信用极好", expanded=False):
            st.markdown("""
            **企业特征：** 经营年限长（>10年），无不良记录，资产负债率<50%，履约率接近100%
            **信用状况：** 违约可能性极低，可给予优惠利率，简化审批流程。
            """)
        with st.expander("🟢 AA级 (0.70-0.85) - 信用优良", expanded=False):
            st.markdown("""
            **企业特征：** 经营状况良好，资产负债率50%-65%，履约率>95%
            **信用状况：** 违约可能性较低，可按正常条件提供融资。
            """)
        with st.expander("🟡 A级 (0.55-0.70) - 信用良好", expanded=False):
            st.markdown("""
            **企业特征：** 处于成长期，负债率65%-75%，履约率90%-95%
            **信用状况：** 存在一定风险点，需适度控制额度，加强监控。
            """)
        with st.expander("🟠 B级 (0.35-0.55) - 信用一般", expanded=False):
            st.markdown("""
            **企业特征：** 经营下滑，负债率>75%，履约率85%-90%，有不良记录
            **信用状况：** 风险较高，需谨慎授信，要求担保。
            """)
        with st.expander("🔴 C级 (<0.35) - 信用较差", expanded=False):
            st.markdown("""
            **企业特征：** 经营不稳定，履约率<85%，有多次逾期记录
            **信用状况：** 风险极高，不建议授信。
            """)
        st.markdown("---")
        # 显示当前用户名
        st.markdown(f"**当前用户：** `{st.session_state.username}`")
        st.markdown("---")
        st.caption("系统支持权重参数后台调整")
        if st.button("🚪 切换用户 / 登出", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    # ==================== 主界面 Tab 布局 ====================
    tab1, tab2, tab3 = st.tabs(["📝 单企评估", "📂 批量导入", "📜 历史记录"])

    # ==================== Tab1: 单企评估 ====================
    with tab1:
        col1, col2 = st.columns([1, 1.5])

        with col1:
            st.header("企业信息")
            company_name = st.text_input("🏢 公司名称", placeholder="请输入企业全称", value="")

            st.subheader("企业基本资质")
            c1 = st.number_input("经营年限(年)", min_value=0, max_value=50, value=8)
            c2 = st.selectbox("有无不良信用记录", ["无", "有"])
            c3 = st.number_input("员工人数(人)", min_value=1, max_value=1000, value=120)

            st.subheader("财务状况")
            col_a, col_b = st.columns(2)
            with col_a:
                c4 = st.number_input("资产负债率(%)", min_value=0.0, max_value=100.0, value=55.0)
                c5 = st.number_input("流动比率", min_value=0.0, max_value=5.0, value=1.5)
                c6 = st.number_input("营业收入(万元)", min_value=0.0, max_value=50000.0, value=8000.0)
            with col_b:
                c7 = st.number_input("净利润(万元)", min_value=-1000.0, max_value=10000.0, value=350.0)

            st.subheader("供应链交易与履约")
            col_c, col_d = st.columns(2)
            with col_c:
                c8 = st.number_input("与核心企业合作年限", min_value=0, max_value=30, value=5)
                c9 = st.number_input("订单履约率(%)", min_value=0.0, max_value=100.0, value=96.0)
            with col_d:
                c10 = st.number_input("应收账款回款率(%)", min_value=0.0, max_value=100.0, value=85.0)
                c11 = st.number_input("合同完成率(%)", min_value=0.0, max_value=100.0, value=97.0)

            st.subheader("运营与风险能力")
            col_e, col_f = st.columns(2)
            with col_e:
                c12 = st.number_input("存货周转率(次)", min_value=0.0, max_value=20.0, value=5.5)
                c13 = st.selectbox("有无逾期还款记录", ["无", "有"])
            with col_f:
                c14 = st.selectbox("纳税信用等级", ["A级", "B级", "C级", "D级"])

            evaluate_btn = st.button("🚀 开始评估", use_container_width=True)

        with col2:
            st.header("评估结果")

            if evaluate_btn:
                if not company_name:
                    st.warning("⚠️ 请输入公司名称")
                else:
                    data = {
                        '经营年限': c1,
                        '不良记录': 0 if c2 == "无" else 1,
                        '员工规模': c3,
                        '资产负债率': c4,
                        '流动比率': c5,
                        '营业收入': c6,
                        '净利润': c7,
                        '合作年限': c8,
                        '订单履约率': c9,
                        '回款率': c10,
                        '合同完成率': c11,
                        '存货周转率': c12,
                        '逾期记录': 0 if c13 == "无" else 1,
                        '纳税等级': {'A级': 4, 'B级': 3, 'C级': 2, 'D级': 1}[c14]
                    }

                    std_data = standardize_data(data)
                    total_score = calculate_score(std_data)
                    rating, rating_desc, _ = get_rating(total_score)
                    dim_scores = calculate_dimension_scores(std_data)

                    record = {
                        '公司名称': company_name,
                        '评估时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        '综合得分': round(total_score, 4),
                        '信用等级': rating,
                        '等级含义': rating_desc,
                        '数据': data,
                        '维度得分': dim_scores
                    }
                    save_history(username, record)

                    col_g, col_h, col_i = st.columns(3)
                    col_g.metric("综合信用得分", f"{total_score:.4f}")
                    col_h.metric("信用等级", rating)
                    col_i.metric("等级含义", rating_desc)

                    fig = draw_radar_chart(dim_scores)
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("指标得分明细")
                    df_results = pd.DataFrame({
                        '指标': list(WEIGHTS.keys()),
                        '权重': list(WEIGHTS.values()),
                        '标准化值': [std_data[k] for k in WEIGHTS.keys()],
                        '加权得分': [std_data[k] * WEIGHTS[k] for k in WEIGHTS.keys()]
                    }).sort_values('加权得分', ascending=False)
                    st.dataframe(df_results, use_container_width=True)
            else:
                st.info("👈 请填写企业信息后点击「开始评估」")

    # ==================== Tab2: 批量导入 ====================
    with tab2:
        st.header("📂 批量导入企业数据")
        st.markdown("支持Excel文件（.xlsx或.xls）批量导入，系统将自动评估并保存结果")

        uploaded_file = st.file_uploader("选择Excel文件", type=['xlsx', 'xls'])

        if uploaded_file is not None:
            try:
                df = pd.read_excel(uploaded_file)
                st.write("数据预览：")
                st.dataframe(df.head())

                required_cols = ['公司名称', '经营年限', '不良记录', '员工规模', '资产负债率',
                                 '流动比率', '营业收入', '净利润', '合作年限', '订单履约率',
                                 '回款率', '合同完成率', '存货周转率', '逾期记录', '纳税等级']

                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    st.error(f"缺少必需列：{missing_cols}")
                    st.markdown("""
                    **Excel模板格式要求：**
                    列名必须包含：公司名称、经营年限、不良记录（0=无/1=有）、员工规模、资产负债率、
                    流动比率、营业收入、净利润、合作年限、订单履约率、回款率、合同完成率、
                    存货周转率、逾期记录（0=无/1=有）、纳税等级（A级/B级/C级/D级）
                    """)
                else:
                    if st.button("开始批量评估", use_container_width=True):
                        results = []
                        with st.spinner("正在评估中..."):
                            for idx, row in df.iterrows():
                                try:
                                    tax_map = {'A级': 4, 'B级': 3, 'C级': 2, 'D级': 1}
                                    tax_value = tax_map.get(str(row['纳税等级']).strip(), 2)

                                    data = {
                                        '经营年限': row['经营年限'],
                                        '不良记录': row['不良记录'],
                                        '员工规模': row['员工规模'],
                                        '资产负债率': row['资产负债率'],
                                        '流动比率': row['流动比率'],
                                        '营业收入': row['营业收入'],
                                        '净利润': row['净利润'],
                                        '合作年限': row['合作年限'],
                                        '订单履约率': row['订单履约率'],
                                        '回款率': row['回款率'],
                                        '合同完成率': row['合同完成率'],
                                        '存货周转率': row['存货周转率'],
                                        '逾期记录': row['逾期记录'],
                                        '纳税等级': tax_value
                                    }
                                    std_data = standardize_data(data)
                                    total_score = calculate_score(std_data)
                                    rating, rating_desc, _ = get_rating(total_score)
                                    dim_scores = calculate_dimension_scores(std_data)

                                    company_name = str(row['公司名称'])
                                    result_item = {
                                        '公司名称': company_name,
                                        '综合得分': round(total_score, 4),
                                        '信用等级': rating,
                                        '等级含义': rating_desc,
                                        '评估时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    results.append(result_item)

                                    record = {
                                        '公司名称': company_name,
                                        '评估时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        '综合得分': round(total_score, 4),
                                        '信用等级': rating,
                                        '等级含义': rating_desc,
                                        '数据': data,
                                        '维度得分': dim_scores
                                    }
                                    save_history(username, record)

                                except Exception as e:
                                    results.append({
                                        '公司名称': row.get('公司名称', f'第{idx + 2}行'),
                                        '综合得分': None,
                                        '信用等级': '评估失败',
                                        '等级含义': str(e)[:50],
                                        '评估时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    })

                        st.success(f"✅ 评估完成！共处理 {len(results)} 家企业")
                        df_results = pd.DataFrame(results)
                        st.dataframe(df_results, use_container_width=True)

                        csv = df_results.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 下载评估结果", csv, "batch_results.csv", "text/csv")

            except Exception as e:
                st.error(f"文件读取失败：{e}")

    # ==================== Tab3: 历史记录 ====================
    with tab3:
        st.header("📜 历史评估记录")

        history = load_history(username)

        if not history:
            st.info("暂无历史记录，请先进行单企评估或批量导入")
        else:
            st.subheader("📊 历史统计")
            df_history = pd.DataFrame(history)
            if '综合得分' in df_history.columns:
                col1, col2, col3 = st.columns(3)
                col1.metric("总评估次数", len(history))
                col2.metric("平均得分", f"{df_history['综合得分'].mean():.3f}")
                col3.metric("最高得分", f"{df_history['综合得分'].max():.3f}")

            st.subheader("📋 记录列表")

            for i, record in enumerate(history):
                with st.container():
                    col_a, col_b, col_c, col_d, col_e, col_f = st.columns([2, 1.5, 1.5, 1.5, 1.5, 1])
                    with col_a:
                        st.write(f"**{record.get('公司名称', '未知')}**")
                    with col_b:
                        st.write(f"时间：{record.get('评估时间', '')[:16]}")
                    with col_c:
                        st.write(f"得分：{record.get('综合得分', 'N/A')}")
                    with col_d:
                        st.write(f"等级：{record.get('信用等级', 'N/A')}")
                    with col_e:
                        st.write(f"含义：{record.get('等级含义', 'N/A')}")
                    with col_f:
                        if '维度得分' in record and record.get('综合得分') is not None:
                            if st.button(f"📊 雷达图", key=f"history_radar_{i}"):
                                dim_scores = record['维度得分']
                                fig = draw_radar_chart(dim_scores, f"{record.get('公司名称', '未知')} 各维度得分")
                                st.plotly_chart(fig, use_container_width=True)
                        else:
                            if '数据' in record:
                                std_data = standardize_data(record['数据'])
                                dim_scores = calculate_dimension_scores(std_data)
                                if st.button(f"📊 雷达图", key=f"history_radar_recalc_{i}"):
                                    fig = draw_radar_chart(dim_scores, f"{record.get('公司名称', '未知')} 各维度得分")
                                    st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.write("无数据")
                    st.divider()

            col_del1, col_del2 = st.columns(2)
            with col_del1:
                if st.button("🗑️ 清空所有历史记录", use_container_width=True):
                    clear_all_history(username)
                    st.rerun()
            with col_del2:
                display_df = df_history.copy()
                if '数据' in display_df.columns:
                    display_df = display_df.drop(columns=['数据'])
                if '维度得分' in display_df.columns:
                    display_df = display_df.drop(columns=['维度得分'])
                csv = display_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 导出历史记录", csv, "credit_history.csv", "text/csv")

    st.markdown("---")
    st.caption("© 面向供应链金融的企业智能信用评估系统")


# ==================== 主入口 ====================
init_session_state()
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
