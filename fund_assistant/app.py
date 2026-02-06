import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import datetime

# Import local modules
import database
import data_api
import logic

# --- Configuration & Setup ---
st.set_page_config(
    page_title="智能理财助手",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Custom CSS for "Pro Stock" Style (Dark/Professional)
st.markdown("""
<style>
    /* Dark Theme Background */
    .stApp {
        background-color: #0E1117;
    }
    .main {
        background-color: #f8f9fa;
    }
    
    /* Metrics / Cards - Professional Dark Box */
    div[data-testid="stMetric"], .stMetric {
        background-color: #1A1C24;
        border: 1px solid #303030;
        padding: 15px;
        border-radius: 4px; /* Sharper corners */
    }
    
    /* Text Colors - High Contrast */
    h1, h2, h3, h4, h5, h6 {
        color: #E0E0E0 !important;
        font-family: 'Arial', sans-serif;
    }
    p, span, div {
        color: #C0C0C0;
    }
    
    /* Buttons - Utilitarian Style */
    .stButton>button {
        background-color: #262730;
        color: #E0E0E0;
        border: 1px solid #404040;
        border-radius: 2px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #363945;
        border-color: #E0E0E0;
        color: #FFFFFF;
    }
    
    /* Tables/Dataframes */
    div[data-testid="stDataFrame"] {
        background-color: #1A1C24;
        border: 1px solid #303030;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1A1C24;
        color: #E0E0E0;
        border: 1px solid #303030;
        border-radius: 2px;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #15171E;
        border-right: 1px solid #303030;
    }
    
    /* Highlights */
    .highlight-card {
        background-color: #1A1C24;
        padding: 20px;
        border-radius: 4px;
        border-left: 4px solid #FFD700; /* Gold accent */
    }
</style>
""", unsafe_allow_html=True)

# --- Data Prefetching (Fast Load) ---
if 'data_prefetched' not in st.session_state:
    with st.spinner('🚀 正在连接交易所数据专线，加载全市场实时行情...'):
        # 1. Get all user holdings
        holdings = database.get_holdings()
        holding_codes = holdings['fund_code'].tolist() if not holdings.empty else []
        
        # 2. Parallel Fetch
        data_api.prefetch_data(holding_codes)
        
        # 3. Mark as done
        st.session_state['data_prefetched'] = True

# --- Sidebar Navigation ---
st.sidebar.title("🚀 基金估值")
page = st.sidebar.radio("导航", ["仪表盘", "股票行情", "基金查询 & 诊断", "持仓管理", "智能定投", "理财科普"])

if page == "股票行情":
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 股票搜索")
    stock_query = st.sidebar.text_input("输入股票代码/名称", placeholder="例如: 600519")
    if stock_query:
        stocks_list = data_api.search_stocks(stock_query)
        if stocks_list:
            stocks = pd.DataFrame(stocks_list)
            stock_options = stocks.apply(lambda x: f"{x['name']} ({x['value']})", axis=1).tolist()
            selected_stock_str = st.sidebar.selectbox("选择股票", options=stock_options)
            if selected_stock_str:
                # Find the record
                selected_stock = stocks[stocks.apply(lambda x: f"{x['name']} ({x['value']})" == selected_stock_str, axis=1)].iloc[0]
                st.session_state['stock_code_to_analyze'] = selected_stock.to_dict()

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 AI 配置 (豆包)")
ai_api_key = st.sidebar.text_input("API Key", type="password", help="从火山引擎申请的 API Key", value=st.session_state.get('ai_api_key', ''))
ai_endpoint_id = st.sidebar.text_input("Endpoint ID", help="部署的推理终端 ID", value=st.session_state.get('ai_endpoint_id', ''))

if ai_api_key: st.session_state['ai_api_key'] = ai_api_key
if ai_endpoint_id: st.session_state['ai_endpoint_id'] = ai_endpoint_id

st.sidebar.markdown("---")
st.sidebar.subheader("⚡ 数据同步")

# Manual Refresh
if st.sidebar.button("🔄 立即刷新数据"):
    st.rerun()

# Auto Refresh Toggle
auto_refresh = st.sidebar.checkbox("开启自动刷新 (每1秒)")

# Last update time
st.sidebar.caption(f"上次更新: {datetime.datetime.now().strftime('%H:%M:%S')}")

st.sidebar.markdown("---")
st.sidebar.success("✅ **数据真实性核验**")
st.sidebar.caption("• 实时估值: 东方财富 (EastMoney)\n• 历史净值: 天天基金 (1234567.com.cn)\n• 财经资讯: 财联社 (CLS)\n• 计算引擎: 本地实时核算")
st.sidebar.info("⚠️ 系统严禁任何模拟、随机或虚假数据。所有指标均基于公开金融网络数据实时获取。")

st.sidebar.markdown("---")
st.sidebar.info("💡 数据来源: AkShare / 公开网络\n🔒 数据存储: 本地 SQLite")

# --- Page: Dashboard ---
@st.fragment
def show_dashboard_metrics():
    # 1. Top Metrics (Holdings Summary)
    holdings = database.get_holdings()
    
    # Check if we should skip API fetching (Auto-refresh ON but NOT trading time)
    skip_api = auto_refresh and not logic.is_trading_time()
    
    # Try to load last state from session_state to prevent "zeroing out"
    if 'last_dashboard_data' not in st.session_state:
        st.session_state['last_dashboard_data'] = {
            'total_market_value': 0.0,
            'total_cost': 0.0,
            'day_profit': 0.0
        }
    
    if not holdings.empty:
        holding_codes = holdings['fund_code'].tolist()
        
        # Only fetch from network if not skipping
        if not skip_api:
            batch_data = data_api.get_batch_realtime_estimates(holding_codes)
            ticks_to_save = []
            
            total_market_value = 0.0
            total_cost = 0.0
            day_profit = 0.0
            
            for index, row in holdings.iterrows():
                fund_code = row['fund_code']
                est = data_api.get_real_time_estimate(fund_code, pre_fetched_data=batch_data.get(fund_code))
                
                current_nav = est['gz']
                market_value = current_nav * row['share']
                cost = row['cost_price'] * row['share']
                
                total_market_value += market_value
                total_cost += cost
                
                pre_close = est.get('pre_close', 0.0)
                if pre_close > 0:
                    day_profit += (current_nav - pre_close) * row['share']
                else:
                    day_profit += market_value - (market_value / (1 + est['zzl'] / 100))

                if est.get('data_date') and est.get('time'):
                    ts = f"{est['data_date']} {est['time']}"
                    if len(est['time']) == 5: ts += ":00"
                    ticks_to_save.append((fund_code, ts, est['zzl'], est['gz']))
            
            # Update session state with new data
            st.session_state['last_dashboard_data'] = {
                'total_market_value': total_market_value,
                'total_cost': total_cost,
                'day_profit': day_profit
            }
            
            if ticks_to_save:
                database.save_tick_batch(ticks_to_save)
        else:
            st.info("🌙 当前非交易时段，自动刷新已暂停。")
            
    # Use data from session state (either fresh or last known)
    data = st.session_state['last_dashboard_data']
    total_market_value = data['total_market_value']
    total_cost = data['total_cost']
    day_profit = data['day_profit']
    
    total_profit = total_market_value - total_cost
    profit_rate = (total_profit / total_cost * 100) if total_cost > 0 else 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总资产 (元)", f"{total_market_value:,.2f}")
    col2.metric("累计收益 (元)", f"{total_profit:+,.2f}", f"{profit_rate:+.2f}%", delta_color="inverse")
    col3.metric("当日预估收益", f"{day_profit:+,.2f}", delta_color="inverse")
    
    # Market Index
    index_data = data_api.get_market_index()
    col4.metric(index_data.get('名称', '沪深300'), f"{index_data.get('最新价', 0)}", f"{index_data.get('涨跌幅', 0)}%", delta_color="inverse")
    
    # Show last update time inside the fragment so user knows it refreshed
    st.caption(f"数据更新时间: {datetime.datetime.now().strftime('%H:%M:%S')}")

    # 2. Charts
    st.markdown("### 📈 资产透视")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        if not holdings.empty:
            # Calculate REAL historical trend of the current portfolio
            holdings_list = holdings[['fund_code', 'share']].to_dict('records')
            history_series = data_api.get_portfolio_history(holdings_list, days=30)
            
            if not history_series.empty:
                # Add current real-time value as the last point if today is not in history (history is usually T-1)
                today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                last_hist_date = history_series.index[-1]
                
                # If the last history date is before today, we append the real-time calculated total_market_value
                if last_hist_date < today:
                    # Append current real-time value
                    history_series[today] = total_market_value
                
                # Determine Color based on Day Profit
                chart_color = '#FF3333' if day_profit >= 0 else '#00CC00' # Red if up, Green if down
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=history_series.index,
                    y=history_series.values,
                    mode='lines+markers',
                    name='总资产',
                    line=dict(color=chart_color, width=2),
                    marker=dict(size=4, color=chart_color),
                    fill='tozeroy',
                    fillcolor=f"rgba({255 if day_profit >= 0 else 0}, {51 if day_profit >= 0 else 204}, {51 if day_profit >= 0 else 0}, 0.1)"
                ))
                
                fig.update_layout(
                    title="近30天资产走势 (基于当前持仓回测)",
                    template='plotly_dark',
                    xaxis_title='日期',
                    yaxis_title='总资产 (元)',
                    margin=dict(l=0, r=0, t=40, b=0),
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("正在获取历史数据或数据不足...")
        else:
            st.info("暂无持仓数据，请前往「持仓管理」添加。")
            
    with c2:
        if not holdings.empty:
            fig_pie = px.pie(holdings, values='cost_price', names='fund_name', title="持仓分布", template='plotly_dark')
            st.plotly_chart(fig_pie, use_container_width=True)
            
    # 3. Market News & Tips
    st.markdown("### � 市场动态 & 智能建议")
    c_news, c_tips = st.columns([2, 1])
    
    with c_news:
        st.subheader("今日财经头条 (财联社)")
        news_list = data_api.get_financial_news()
        if news_list:
            for item in news_list[:5]: # Show top 5 on dashboard
                st.markdown(f"• **[{item['tag']}]** [{item['title']}]({item['url']}) <span style='color: gray; font-size: 0.8em;'>({item['time']})</span>", unsafe_allow_html=True)
        else:
            st.caption("暂无实时新闻。")
            
    with c_tips:
        st.subheader("持仓建议")
        if not holdings.empty:
            tips = logic.optimize_holdings(holdings)
            for tip in tips:
                st.warning(f"⚠️ {tip}")
        else:
            st.success("👋 欢迎！请添加持仓开始分析。")

def render_dashboard():
    st.title("📊 投资仪表盘")
    
    # Check auto_refresh state from sidebar (which is global scope in this file structure)
    # Since st.fragment arguments are evaluated at definition time, 
    # we can't easily change run_every dynamically for a top-level decorated function.
    # However, we can define the fragment wrapper inside here or pass run_every to st.fragment call if using as function.
    # But for cleaner code, we use a trick:
    
    run_interval = 1 if auto_refresh else None
    
    # Use the function as a fragment by calling it? 
    # No, @st.fragment decorator makes the function a fragment.
    # If we want dynamic interval, we have to re-decorate or use st.fragment(func, run_every=...) 
    # BUT st.fragment is a decorator factory.
    
    # Correct way for dynamic interval with st.fragment:
    # We can't change the interval of an already decorated function easily.
    # So we define a wrapper or use the function call syntax if supported.
    # Alternatively, we can just define the fragment inside this function.
    
    @st.fragment(run_every=run_interval)
    def _dynamic_dashboard_metrics():
        show_dashboard_metrics()
        
    _dynamic_dashboard_metrics()

# --- Page: Search & Diagnose ---
def render_search():
    st.title("🔍 基金查询与诊断")
    
    # Show success message if exists in session state
    if 'add_success_msg' in st.session_state:
        st.success(st.session_state['add_success_msg'])
        del st.session_state['add_success_msg']
    
    query_input = st.text_input("输入基金代码或名称", max_chars=20)
    
    if st.button("搜索 / 诊断"):
        st.session_state['search_query'] = query_input
        # Clear previous selection when a new search is performed
        if 'selected_fund_code' in st.session_state:
            del st.session_state['selected_fund_code']
    
    query = st.session_state.get('search_query', '')
    
    if query:
        with st.spinner("正在搜索基金..."):
            search_results = data_api.search_funds(query)
            
            if search_results.empty:
                st.warning("未找到匹配的基金，请检查输入。")
            elif len(search_results) > 1:
                st.subheader(f"找到 {len(search_results)} 个匹配结果")
                
                # Show results in a table with a selection column
                # We'll use a trick with radio or selectbox for better UX in Streamlit
                result_options = search_results.apply(lambda x: f"{x['code']} | {x['name']} ({x['type']})", axis=1).tolist()
                selected_item = st.selectbox("请选择要查看的基金:", options=result_options)
                
                if selected_item:
                    selected_code = selected_item.split(" | ")[0]
                    # Set the selected code to a separate state to render details
                    st.session_state['selected_fund_code'] = selected_code
            else:
                # Only one result
                st.session_state['selected_fund_code'] = search_results.iloc[0]['code']

    selected_fund_code = st.session_state.get('selected_fund_code')
    
    if selected_fund_code:
        with st.spinner("正在获取数据并分析..."):
            fund_code = selected_fund_code
            info = data_api.get_fund_base_info(fund_code)
            
            if info:
                # Layout
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.subheader(f"{info['name']} ({info['code']})")
                    st.write(f"**类型**: {info['type']}")
                    st.write(f"**经理**: {info['manager']}")
                    st.write(f"**成立**: {info['start_date']}")
                    
                    # Realtime
                    est = data_api.get_real_time_estimate(fund_code)
                    st.metric("实时估值", f"{est['gz']}", f"{est['zzl']}%", delta_color="inverse")
                    
                    # Action
                    with st.expander("➕ 添加到持仓"):
                        with st.form("add_holding_form"):
                            share = st.number_input("持有份额", min_value=0.0, step=0.01, format="%.2f", key="add_share")
                            # Use format="%.4f" to enforce 4 decimal places display and input precision
                            cost = st.number_input("持仓成本 (元)", min_value=0.0, step=0.0001, format="%.4f", key="add_cost")
                            submit_holding = st.form_submit_button("确认添加")
                            
                            if submit_holding:
                                if share > 0:
                                    database.add_holding(info['code'], info['name'], share, cost)
                                    # Clear cache to force refresh with new DB values
                                    if 'last_holdings_display' in st.session_state:
                                        del st.session_state['last_holdings_display']
                                    if 'last_dashboard_data' in st.session_state:
                                        del st.session_state['last_dashboard_data']
                                    
                                    # Set success message for next run
                                    st.session_state['add_success_msg'] = f"成功添加 {info['name']} ({share}份) 到持仓！"
                                    st.rerun()
                                else:
                                    st.error("请输入有效的份额")

                with c2:
                    # Diagnosis
                    diag = logic.diagnose_fund(fund_code)
                    st.markdown(f"### 🩺 智能诊断: {diag['stars']} ({diag['score']}分)")
                    st.info(f"💡 **结论**: {diag['conclusion']}")
                    
                    m1, m2, m3 = st.columns(3)
                    m1.metric("近1年收益", diag['metrics']['return_1y'], delta_color="inverse")
                    m2.metric("最大回撤", diag['metrics']['max_drawdown'], delta_color="inverse")
                    m3.metric("夏普比率", diag['metrics']['sharpe'], delta_color="inverse")
                    
                    st.markdown("---")
                    st.subheader("🔍 深度诊断报告")
                    
                    diag_mode = st.radio("选择诊断模式", ["本地专家诊断 (免费)", "AI 深度分析 (豆包)"], horizontal=True)
                    
                    if diag_mode == "本地专家诊断 (免费)":
                        if st.button("🚀 生成本地深度分析", use_container_width=True):
                            with st.spinner("专家引擎正在分析中..."):
                                local_report = logic.analyze_fund_locally(fund_code, fund_name=info['name'])
                                st.markdown(local_report)
                    else:
                        if st.button("🚀 开始 AI 深度分析", use_container_width=True):
                            if not st.session_state.get('ai_api_key') or not st.session_state.get('ai_endpoint_id'):
                                st.error("请先在左侧边栏配置 AI API Key 和 Endpoint ID")
                            else:
                                with st.spinner("豆包正在分析中，请稍候..."):
                                    ai_analysis = logic.analyze_fund_with_ai(
                                        fund_code, 
                                        st.session_state['ai_api_key'], 
                                        st.session_state['ai_endpoint_id'],
                                        fund_name=info['name']
                                    )
                                    st.markdown(ai_analysis)
                    
                    # Charts Section
                    chart_tabs = st.tabs(["当日分时估值", "历史净值走势"])
                    
                    with chart_tabs[0]:
                        # Intraday Trend
                        with st.spinner("加载当日实时估值走势..."):
                            intraday_df = data_api.get_fund_intraday_trend(fund_code)
                            if not intraday_df.empty:
                                # Determine color
                                current_zzl = est.get('zzl', 0)
                                chart_color = '#FF3333' if current_zzl >= 0 else '#00CC00'
                                
                                # Show current change with color
                                color_style = "color: #FF3333;" if current_zzl >= 0 else "color: #00CC00;"
                                st.markdown(f"**当前估算涨幅**: <span style='{color_style} font-size: 1.2em;'>{current_zzl:+.2f}%</span>", unsafe_allow_html=True)
                                
                                fig_intra = go.Figure()
                                fig_intra.add_trace(go.Scatter(
                                    x=intraday_df['时间'],
                                    y=intraday_df['估算值'],
                                    mode='lines+markers',
                                    name='估算净值',
                                    line=dict(color=chart_color, width=2),
                                    marker=dict(size=3, color=chart_color),
                                    fill='tozeroy',
                                    fillcolor=f"rgba({255 if current_zzl >= 0 else 0}, {51 if current_zzl >= 0 else 204}, {51 if current_zzl >= 0 else 0}, 0.1)"
                                ))
                                
                                fig_intra.update_layout(
                                    title=f"{info['name']} 当日实时估值走势",
                                    template='plotly_dark',
                                    xaxis=dict(tickformat="%H:%M", showgrid=False),
                                    yaxis=dict(showgrid=True, gridcolor='#333'),
                                    margin=dict(l=0, r=0, t=40, b=0),
                                    hovermode='x unified'
                                )
                                st.plotly_chart(fig_intra, use_container_width=True)
                            else:
                                st.info("该基金暂不支持分时估值或当前非交易时段。")
                                # Show a metric instead
                                st.metric("当前估值", f"{est['gz']}", f"{est['zzl']}%", delta_color="inverse")

                    with chart_tabs[1]:
                        # History Chart
                        hist_df = data_api.get_fund_nav_history(fund_code)
                        if not hist_df.empty:
                            # Add Real-time point
                            try:
                                est_date_str = est.get('data_date') if est else None
                                if est_date_str and est and est.get('gz'):
                                    est_date = pd.to_datetime(est_date_str)
                                    if hist_df['净值日期'].max() < est_date:
                                        new_row = pd.DataFrame({'净值日期': [est_date], '单位净值': [float(est['gz'])]})
                                        hist_df = pd.concat([hist_df, new_row], ignore_index=True)
                            except Exception as e:
                                print(f"Error appending real-time point: {e}")

                            chart_color = '#FF3333' if est and est.get('zzl', 0) >= 0 else '#00CC00'
                            
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=hist_df['净值日期'],
                                y=hist_df['单位净值'],
                                mode='lines+markers',
                                name='单位净值',
                                line=dict(color=chart_color, width=2),
                                marker=dict(size=4, color=chart_color),
                                fill='tozeroy',
                                fillcolor=f"rgba({255 if est and est.get('zzl', 0) >= 0 else 0}, {51 if est and est.get('zzl', 0) >= 0 else 204}, {51 if est and est.get('zzl', 0) >= 0 else 0}, 0.1)"
                            ))
                            
                            fig.update_layout(
                                title="历史净值走势",
                                template='plotly_dark',
                                xaxis_title='日期',
                                yaxis_title='单位净值',
                                margin=dict(l=0, r=0, t=40, b=0),
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig, use_container_width=True)
            else:
                st.error("无法获取该基金详情。")

# --- Page: Stock Analysis ---
def render_stock_analysis():
    st.title("📈 股票行情分析")
    
    # Get selected stock from session state
    stock_code_to_analyze = st.session_state.get('stock_code_to_analyze')
    
    # If no stock selected via sidebar, show some defaults or instructions
    if not stock_code_to_analyze:
        st.info("请在左侧侧边栏搜索并选择股票查看详情。")
        
        # Quick access buttons for popular stocks
        st.markdown("### 🚀 快速查看热门股票")
        popular_stocks = [
            {"name": "贵州茅台", "value": "sh600519", "symbol": "600519", "market": "sh"},
            {"name": "宁德时代", "value": "sz300750", "symbol": "300750", "market": "sz"},
            {"name": "东方财富", "value": "sz300059", "symbol": "300059", "market": "sz"},
            {"name": "招商银行", "value": "sh600036", "symbol": "600036", "market": "sh"}
        ]
        
        cols = st.columns(4)
        for i, s in enumerate(popular_stocks):
            if cols[i].button(f"{s['name']}\n({s['value']})", use_container_width=True):
                st.session_state['stock_code_to_analyze'] = s
                st.rerun()
        
        st.markdown("""
        ---
        ### 💡 功能提示
        1. 在左侧边栏输入股票代码或名称进行搜索。
        2. 支持 A 股市场（沪深）实时行情。
        3. 包含分时图、K 线图（日/周/月）及五档盘口。
        4. 开盘期间支持 3 秒自动刷新。
        """)
        return

    # Fetch Data
    full_code = stock_code_to_analyze['value']
    symbol = stock_code_to_analyze['symbol']
    market = stock_code_to_analyze['market']
    name = stock_code_to_analyze['name']
    
    run_interval = 3 if auto_refresh and logic.is_trading_time() else None
    
    @st.fragment(run_every=run_interval)
    def _stock_fragment():
        with st.spinner(f"正在获取 {name} 实时行情..."):
            detail = data_api.get_stock_realtime_detail(full_code)
            
        if not detail:
            st.error("获取实时行情失败，请稍后重试。")
            return
            
        # --- Header Section (Price & Change) ---
        h_col1, h_col2, h_col3 = st.columns([2, 3, 2])
        
        color = '#FF3333' if detail['change'] >= 0 else '#00CC00'
        arrow = '↑' if detail['change'] >= 0 else '↓'
        
        with h_col1:
            st.markdown(f"## {detail['name']}")
            st.caption(f"{full_code.upper()}")
            
        with h_col2:
            st.markdown(f"""
            <div style="display: flex; align-items: baseline;">
                <span style="font-size: 3em; font-weight: bold; color: {color};">{detail['price']:.2f}</span>
                <span style="font-size: 1.5em; margin-left: 15px; color: {color};">{arrow} {detail['change']:.2f} ({detail['pct_change']:.2f}%)</span>
            </div>
            """, unsafe_allow_html=True)
            
        with h_col3:
            st.caption(f"交易时间: {detail['date']} {detail['time']}")
            
        st.divider()
        
        # --- Metrics Grid ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("今开", f"{detail['open']:.2f}", delta=f"{detail['open']-detail['pre_close']:.2f}", delta_color="normal")
        m2.metric("最高", f"{detail['high']:.2f}", delta=f"{detail['high']-detail['pre_close']:.2f}", delta_color="normal")
        m3.metric("最低", f"{detail['low']:.2f}", delta=f"{detail['low']-detail['pre_close']:.2f}", delta_color="normal")
        m4.metric("昨收", f"{detail['pre_close']:.2f}")
        
        m5, m6, m7, m8 = st.columns(4)
        vol_wan = detail['volume'] / 10000
        amt_yi = detail['amount'] / 100000000
        m5.metric("成交量", f"{vol_wan:.2f} 万手")
        m6.metric("成交额", f"{amt_yi:.2f} 亿")
        # Placeholder for Amplitude/Turnover if available later
        m7.metric("振幅", "--%") 
        m8.metric("换手率", "--%")

        # --- Main Layout: Charts (Left) + Order Book (Right) ---
        c_col, o_col = st.columns([3, 1])
        
        with c_col:
            st.subheader("📊 走势图")
            tab_intra, tab_day, tab_week, tab_month = st.tabs(["分时走势", "日K线", "周K线", "月K线"])
            
            with tab_intra:
                trends_data = data_api.get_stock_trends(symbol, market)
                if trends_data and trends_data['trends']:
                    df_trends = pd.DataFrame(trends_data['trends'])
                    # Pre-close line
                    pre_close = trends_data['pre_close']
                    
                    fig = go.Figure()
                    
                    # Main Line
                    fig.add_trace(go.Scatter(
                        x=df_trends['time'], 
                        y=df_trends['price'],
                        mode='lines',
                        name='价格',
                        line=dict(color='#FFFFFF', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(255, 255, 255, 0.1)' # Light fill
                    ))
                    
                    # Pre-close dashed line
                    fig.add_hline(y=pre_close, line_dash="dash", line_color="gray", annotation_text="昨收")
                    
                    # Update Layout
                    max_p = df_trends['price'].max()
                    min_p = df_trends['price'].min()
                    # Ensure symmetric range around pre_close for visual balance (like trading software)
                    limit = max(abs(max_p - pre_close), abs(min_p - pre_close))
                    if limit == 0: limit = pre_close * 0.01
                    
                    fig.update_layout(
                        template='plotly_dark',
                        height=450,
                        margin=dict(l=0, r=0, t=30, b=0),
                        xaxis=dict(
                            type='category', 
                            nticks=8,
                            tickangle=0
                        ),
                        yaxis=dict(
                            range=[pre_close - limit * 1.1, pre_close + limit * 1.1],
                            showgrid=True,
                            gridcolor='#333'
                        ),
                        hovermode='x unified'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无分时数据")

            def plot_kline(period_code):
                k_data = data_api.get_stock_kline(symbol, market, period_code)
                if k_data:
                    df_k = pd.DataFrame(k_data)
                    
                    fig = go.Figure(data=[go.Candlestick(
                        x=df_k['date'],
                        open=df_k['open'],
                        high=df_k['high'],
                        low=df_k['low'],
                        close=df_k['close'],
                        increasing_line_color='#FF3333', 
                        decreasing_line_color='#00CC00',
                        name='K线'
                    )])
                    
                    # Add MA (Moving Averages)
                    df_k['MA5'] = df_k['close'].rolling(window=5).mean()
                    df_k['MA10'] = df_k['close'].rolling(window=10).mean()
                    df_k['MA20'] = df_k['close'].rolling(window=20).mean()
                    
                    fig.add_trace(go.Scatter(x=df_k['date'], y=df_k['MA5'], mode='lines', name='MA5', line=dict(color='white', width=1)))
                    fig.add_trace(go.Scatter(x=df_k['date'], y=df_k['MA10'], mode='lines', name='MA10', line=dict(color='yellow', width=1)))
                    fig.add_trace(go.Scatter(x=df_k['date'], y=df_k['MA20'], mode='lines', name='MA20', line=dict(color='magenta', width=1)))
                    
                    fig.update_layout(
                        template='plotly_dark',
                        xaxis_rangeslider_visible=False,
                        height=450,
                        margin=dict(l=0, r=0, t=30, b=0),
                        hovermode='x unified',
                        yaxis=dict(
                            autorange=True,
                            fixedrange=False
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("暂无K线数据")

            with tab_day:
                plot_kline('101') # Day
            with tab_week:
                plot_kline('102') # Week
            with tab_month:
                plot_kline('103') # Month

        with o_col:
            st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True) # Spacer
            st.markdown("##### 🖐 五档盘口")
            
            ba = detail.get('bid_ask', {})
            
            # Helper to display a row
            def order_row(label, price, vol, color):
                if price == 0: price_str = "--"
                else: price_str = f"{price:.2f}"
                
                if vol == 0: vol_str = "--"
                else: vol_str = f"{int(vol/100)}" # Lots
                
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 4px;">
                    <span style="color: gray;">{label}</span>
                    <span style="color: {color}; font-weight: bold;">{price_str}</span>
                    <span style="color: #E0E0E0;">{vol_str}</span>
                </div>
                """, unsafe_allow_html=True)

            # Asks (Sell 5 -> Sell 1)
            for i in range(5, 0, -1):
                p = ba.get(f'a{i}_p', 0)
                v = ba.get(f'a{i}_v', 0)
                c = '#00CC00' # Green for Sell
                order_row(f"卖{i}", p, v, c)
            
            st.divider()
            
            # Bids (Buy 1 -> Buy 5)
            for i in range(1, 6):
                p = ba.get(f'b{i}_p', 0)
                v = ba.get(f'b{i}_v', 0)
                c = '#FF3333' # Red for Buy
                order_row(f"买{i}", p, v, c)

    _stock_fragment()

# --- Page: Holdings ---
def render_holdings():
    st.title("💼 持仓管理")
    
    run_interval = 1 if auto_refresh else None
    
    @st.fragment(run_every=run_interval)
    def _holdings_fragment():
        holdings = database.get_holdings()
        
        # Check if we should skip API fetching (Auto-refresh ON but NOT trading time)
        skip_api = auto_refresh and not logic.is_trading_time()
        
        # Initialize session state for holdings if not present
        if 'last_holdings_display' not in st.session_state:
            st.session_state['last_holdings_display'] = None
            st.session_state['last_batch_trends'] = {}
        
        if not holdings.empty:
            holding_codes = holdings['fund_code'].tolist()
            batch_data = {} # Initialize to avoid UnboundLocalError
            
            if not skip_api:
                # Initial state for display columns
                current_navs = [0.0] * len(holdings)
                market_values = [0.0] * len(holdings)
                profits = [0.0] * len(holdings)
                day_profits = [0.0] * len(holdings)
                day_changes = [0.0] * len(holdings)
                data_dates = ["--"] * len(holdings)
                
                # Batch fetch real-time data
                batch_data = data_api.get_batch_realtime_estimates(holding_codes)
                batch_trends = data_api.get_batch_intraday_trends(holding_codes)

                if not auto_refresh:
                    progress_bar = st.progress(0)
                
                ticks_to_save = []
                
                for i, row in holdings.iterrows():
                    fund_code = row['fund_code']
                    est = data_api.get_real_time_estimate(fund_code, pre_fetched_data=batch_data.get(fund_code))
                    
                    nav = est['gz']
                    mv = nav * row['share']
                    prof = mv - (row['cost_price'] * row['share'])
                    
                    pre_close = est.get('pre_close', 0.0)
                    if pre_close > 0:
                        d_prof = (nav - pre_close) * row['share']
                    else:
                        d_prof = mv - (mv / (1 + est['zzl'] / 100))
                    
                    current_navs[i] = nav
                    market_values[i] = round(mv, 2)
                    profits[i] = round(prof, 2)
                    day_profits[i] = round(d_prof, 2)
                    day_changes[i] = est['zzl']
                    data_dates[i] = est.get('data_date', '--')
                    
                    if est.get('data_date') and est.get('time'):
                        ts = f"{est['data_date']} {est['time']}"
                        if len(est['time']) == 5: ts += ":00"
                        ticks_to_save.append((fund_code, ts, est['zzl'], est['gz']))
                    
                    if not auto_refresh:
                        progress_bar.progress((i + 1) / len(holdings))
                
                # Update display DF
                display_df = holdings.copy()
                display_df['最新净值'] = current_navs
                display_df['数据日期'] = data_dates
                display_df['当前市值'] = market_values
                display_df['当日收益'] = day_profits
                display_df['当日涨幅%'] = day_changes
                display_df['累计盈亏'] = profits
                
                # Save to session state
                st.session_state['last_holdings_display'] = display_df
                st.session_state['last_batch_trends'] = batch_trends
                
                if ticks_to_save:
                    database.save_tick_batch(ticks_to_save)
            else:
                st.info("🌙 当前非交易时段，自动刷新已暂停。")
                # Use last known data if available
                display_df = st.session_state['last_holdings_display']
                batch_trends = st.session_state['last_batch_trends']
                
            # If we have data (either fresh or from session state), render it
            if display_df is not None:
                # Ensure cost_price is displayed with 4 decimals in the dataframe
                st.dataframe(
                    display_df[['fund_code', 'fund_name', 'share', 'cost_price', '最新净值', '当日涨幅%', '当日收益', '累计盈亏', '当前市值', '数据日期']].style.format({
                        'cost_price': '{:.4f}',
                        '最新净值': '{:.4f}',
                        '当前市值': '{:.2f}',
                        '累计盈亏': '{:.2f}',
                        '当日收益': '{:.2f}',
                        '当日涨幅%': '{:.2f}%'
                    }),
                    use_container_width=True
                )
                
                st.caption(f"🕒 实时数据更新于: {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                # --- Individual Detailed Charts (Intraday Percentage) ---
                st.markdown("### 📊 持仓基金当日涨幅走势详情")
                
                chart_cols = st.columns(3) # Grid layout
                
                for idx, row in holdings.iterrows():
                    fund_code = row['fund_code']
                    
                    # 1. Try to get Local DB Data (Continuous Accumulation)
                    db_df = database.get_today_ticks(fund_code)
                    
                    # 2. Get API Trend for basic coverage
                    trend_data = batch_trends.get(fund_code, {})
                    
                    times = []
                    pcts = []
                    is_history = False
                    
                    if not db_df.empty:
                        # Use Local DB Data as the primary source for the chart
                        times = pd.to_datetime(db_df['record_time']).dt.strftime('%H:%M:%S').tolist()
                        pcts = db_df['pct'].tolist()
                        
                        # Merge with API data if API has more points (e.g., historical morning data)
                        if trend_data and trend_data.get('pct'):
                            api_times = trend_data['times']
                            api_pcts = trend_data['pct']
                            
                            # Find the first DB time in API times to avoid overlap
                            if times:
                                first_db_time = times[0]
                                # Only keep API points that are BEFORE our first DB point
                                filtered_api = [(t, p) for t, p in zip(api_times, api_pcts) if t < first_db_time]
                                
                                # Prepend them
                                if filtered_api:
                                    times = [t for t, p in filtered_api] + times
                                    pcts = [p for t, p in filtered_api] + pcts
                        
                    elif trend_data and trend_data.get('pct'):
                        # Fallback to API Data if DB is totally empty
                        times = trend_data['times']
                        pcts = trend_data['pct']
                        is_history = trend_data.get('is_history', False)
                    
                    with chart_cols[idx % 3]:
                        # Container styling for the card
                        with st.container(border=True):
                            st.markdown(f"**{row['fund_name']}** ({fund_code})")
                            
                            if pcts:
                                current_pct = pcts[-1]
                                
                                status_suffix = " (最近交易日)" if is_history else ""
                                # If using DB data, maybe add a small indicator?
                                if not db_df.empty:
                                    status_suffix = " (实时追踪)"
                                
                                # Determine Color based on current value
                                color = '#FF3333' if current_pct >= 0 else '#00CC00'
                                
                                st.markdown(f"<span style='color:{color}; font-size: 1.2em; font-weight: bold;'>{current_pct:+.2f}%</span> <span style='font-size: 0.8em; color: gray;'>{status_suffix}</span>", unsafe_allow_html=True)
                                
                                # Create Area Line Chart (Matching Stock Style)
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(
                                    x=times, 
                                    y=pcts, 
                                    mode='lines', 
                                    name='涨幅%',
                                    line=dict(color=color, width=2),
                                    fill='tozeroy',
                                    fillcolor=f"rgba({255 if current_pct >= 0 else 0}, {51 if current_pct >= 0 else 204}, {51 if current_pct >= 0 else 0}, 0.1)"
                                ))
                                
                                fig.update_layout(
                                    template='plotly_dark',
                                    margin=dict(l=0, r=0, t=10, b=0),
                                    height=200,
                                    showlegend=False,
                                    xaxis=dict(
                                        showgrid=False, 
                                        tickmode='auto',
                                        nticks=5
                                    ),
                                    yaxis=dict(
                                        showgrid=True, 
                                        gridcolor='#333',
                                        zeroline=True,
                                        zerolinecolor='#666'
                                    ),
                                    hovermode='x unified'
                                )
                                
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{fund_code}")
                            else:
                                st.caption("暂无分时涨幅数据")
                                # Placeholder height
                                st.markdown("<div style='height: 200px; display: flex; align-items: center; justify-content: center; color: gray;'>市场未开盘或暂无实时数据</div>", unsafe_allow_html=True)
            else:
                st.info("暂无持仓数据可显示。")

            st.subheader("🛠️ 管理操作")
            
            # --- Management Operations (Edit/Delete/Trade) ---
            m_col1, m_col2, m_col3 = st.columns(3)
            
            # Create a list of options for the selectbox: "ID: FundName (Code)"
            mgmt_options = holdings.apply(lambda x: f"{x['id']} : {x['fund_name']} ({x['fund_code']})", axis=1).tolist()
            
            with m_col1:
                with st.expander("🔄 加仓 / 减仓 (交易录入)", expanded=True):
                    if mgmt_options:
                        selected_to_trade = st.selectbox("选择交易基金", options=mgmt_options, key="trade_select")
                        trade_id = int(selected_to_trade.split(' : ')[0])
                        trade_row = holdings[holdings['id'] == trade_id].iloc[0]
                        trade_fund_code = trade_row['fund_code']
                        
                        # Fetch Real-time Estimate for Default Price
                        est_price = 0.0
                        if batch_data and trade_fund_code in batch_data:
                            est_price = batch_data[trade_fund_code]['gz']
                        elif display_df is not None:
                            # Fallback to display_df (which might be from session state)
                            match = display_df[display_df['fund_code'] == trade_fund_code]
                            if not match.empty:
                                est_price = match.iloc[0]['最新净值']
                        
                        trade_type = st.radio("交易方向", ["加仓 (买入)", "减仓 (卖出)"], horizontal=True)
                        
                        # Effective Date Logic
                        eff_date = logic.get_effective_trading_date()
                        st.caption(f"📅 有效净值日期: **{eff_date}** (根据 15:00 规则判定)")
                        
                        with st.form("trade_form"):
                            # Ensure value is at least min_value to avoid StreamlitValueBelowMinError
                            default_t_price = max(0.0001, float(est_price))
                            t_price = st.number_input("成交净值 (元)", value=default_t_price, min_value=0.0001, step=0.0001, format="%.4f", help="默认为当前实时估值，可手动修正为确认净值")
                            
                            if "加仓" in trade_type:
                                t_amount = st.number_input("买入金额 (元)", min_value=0.0, step=100.0, format="%.2f")
                                # Calculate estimated shares for display
                                est_share = t_amount / t_price if t_price > 0 else 0
                                st.markdown(f"📏 预估增加份额: **{est_share:.2f}**")
                            else:
                                t_share = st.number_input("卖出份额", min_value=0.0, max_value=float(trade_row['share']), step=10.0, format="%.2f")
                                # Calculate estimated return amount
                                est_return = t_share * t_price
                                st.markdown(f"💰 预估回款金额: **{est_return:.2f}** 元")
                            
                            if st.form_submit_button("🚀 确认交易"):
                                old_share = trade_row['share']
                                old_cost = trade_row['cost_price']
                                
                                if "加仓" in trade_type:
                                    # Buy: Input is Amount
                                    # Calculate share delta
                                    share_delta = t_amount / t_price if t_price > 0 else 0
                                    new_share, new_cost = logic.calculate_new_cost(old_share, old_cost, share_delta, t_price, "buy")
                                    
                                    database.update_holding(trade_id, new_share, new_cost)
                                    msg = f"已加仓 {t_amount}元 (约 {share_delta:.2f}份)。\n最新持仓: {new_share:.2f}份, 成本: {new_cost:.4f}"
                                else:
                                    # Sell: Input is Share
                                    new_share, new_cost = logic.calculate_new_cost(old_share, old_cost, t_share, t_price, "sell")
                                    
                                    database.update_holding(trade_id, new_share, new_cost)
                                    msg = f"已减仓 {t_share}份。\n最新持仓: {new_share:.2f}份, 成本: {new_cost:.4f}"
                                
                                # Clear cache
                                if 'last_holdings_display' in st.session_state: del st.session_state['last_holdings_display']
                                if 'last_dashboard_data' in st.session_state: del st.session_state['last_dashboard_data']
                                
                                st.success(msg)
                                time.sleep(1.5)
                                st.rerun()
                    else:
                        st.caption("暂无持仓可交易")

            with m_col2:
                with st.expander("📝 修正持仓 (手动)", expanded=True):
                    if mgmt_options:
                        selected_to_edit = st.selectbox("选择要修正的持仓", options=mgmt_options, key="edit_select")
                        # Get current values for pre-filling
                        edit_id = int(selected_to_edit.split(' : ')[0])
                        current_row = holdings[holdings['id'] == edit_id].iloc[0]
                        
                        with st.form("edit_holding_form"):
                            new_share = st.number_input("调整后份额", value=float(current_row['share']), step=0.01, format="%.2f")
                            new_cost = st.number_input("调整后持仓成本 (元)", value=float(current_row['cost_price']), step=0.0001, format="%.4f")
                            
                            if st.form_submit_button("✅ 确认修正", use_container_width=True):
                                database.update_holding(edit_id, new_share, new_cost)
                                # Clear cache to force refresh with new DB values
                                if 'last_holdings_display' in st.session_state:
                                    del st.session_state['last_holdings_display']
                                if 'last_dashboard_data' in st.session_state:
                                    del st.session_state['last_dashboard_data']
                                
                                st.success(f"已更新 {current_row['fund_name']} 的持仓数据")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.caption("暂无持仓可修改")

            with m_col3:
                with st.expander("🗑️ 删除持仓", expanded=True):
                    if mgmt_options:
                        selected_to_delete = st.selectbox("选择要删除的持仓", options=mgmt_options, key="delete_select")
                        
                        if st.button("🗑️ 确认删除", use_container_width=True):
                            # Extract ID from the selection string
                            del_id = int(selected_to_delete.split(' : ')[0])
                            database.delete_holding(del_id)
                            # Clear cache to force refresh with new DB values
                            if 'last_holdings_display' in st.session_state:
                                del st.session_state['last_holdings_display']
                            if 'last_dashboard_data' in st.session_state:
                                del st.session_state['last_dashboard_data']
                                
                            st.success(f"已删除持仓: {selected_to_delete}")
                            time.sleep(1) # Give user a moment to see the success message
                            st.rerun()
                    else:
                        st.caption("暂无持仓可删除")
            
        else:
            st.info("暂无持仓。")
            
        with st.expander("📥 批量导入/导出"):
            st.write("支持 Excel/CSV 格式导入 (开发中...)")
            if not holdings.empty:
                st.download_button("导出持仓 CSV", holdings.to_csv(), "holdings.csv")

    # Execute the fragment
    _holdings_fragment()

# --- Page: Investment Plan ---
def render_plan():
    st.title("📅 智能定投规划")
    
    tab1, tab2 = st.tabs(["🎯 创建计划 & 测算", "📋 我的定投"])
    
    with tab1:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("1. 设定参数")
            fund_code = st.text_input("定投基金代码", "110011")
            amount = st.number_input("每期定投金额", value=1000)
            freq = st.selectbox("定投频率", ["每周", "每两周", "每月"])
            duration = st.slider("预计定投时长 (年)", 1, 10, 3)
            
            if st.button("开始测算"):
                with st.spinner("正在回测历史数据..."):
                    res = logic.project_investment_plan(fund_code, amount, 30, duration) # approx freq
                    st.session_state['plan_result'] = res
        
        with c2:
            st.subheader("2. 收益测算 (基于历史真实波动)")
            st.caption("⚠️ 测算逻辑说明：系统提取该基金近3年历史净值，通过蒙特卡洛模型计算年化收益均值及标准差。乐观/悲观场景分别代表概率分布的 ±1 标准差。测算仅供参考，不代表未来表现。")
            if 'plan_result' in st.session_state and st.session_state['plan_result']:
                res = st.session_state['plan_result']
                
                # Plot
                fig = go.Figure()
                
                # Optimistic
                fig.add_trace(go.Scatter(y=res['optimistic']['trend'], mode='lines', name='乐观 (前20%)', line=dict(color='#FF3333', dash='dash')))
                # Neutral
                fig.add_trace(go.Scatter(y=res['neutral']['trend'], mode='lines', name='中性 (平均)', line=dict(color='#FFD700')))
                # Pessimistic
                fig.add_trace(go.Scatter(y=res['pessimistic']['trend'], mode='lines', name='悲观 (后20%)', line=dict(color='#00CC00', dash='dot')))
                # Invested Base
                fig.add_trace(go.Scatter(y=[amount * (i+1) for i in range(len(res['neutral']['trend']))], mode='lines', name='本金投入', line=dict(color='#666666')))
                
                fig.update_layout(title="定投收益模拟曲线", xaxis_title="期数 (月)", yaxis_title="资产总值", template='plotly_dark')
                st.plotly_chart(fig, width='stretch')
                
                st.info(f"📊 **中性预期**: 坚持定投 {duration} 年，累计投入 {res['neutral']['total_invested']} 元，期末预计市值 **{res['neutral']['final_value']:.2f}** 元 (收益率 {res['neutral']['yield_rate']*100:.2f}%)")
                
                if st.button("保存该计划"):
                    database.add_plan(fund_code, "未命名基金", amount, freq, datetime.datetime.now().strftime("%Y-%m-%d"))
                    st.success("计划已保存！")
    
    with tab2:
        plans = database.get_plans()
        if not plans.empty:
            st.dataframe(plans)
            # Action buttons would go here
        else:
            st.info("暂无定投计划。")

# --- Page: Knowledge ---
def render_knowledge():
    st.title("📚 理财科普")
    
    st.markdown("""
    ### 🎓 新手必读
    - **什么是基金定投？**  
      定期定额投资，通过拉长投资周期，平摊持仓成本，降低择时风险。微笑曲线是定投的核心信仰。
    
    - **如何挑选好基金？**  
      "4433法则": 近1年排名前1/4，近2年、3年、5年排名前1/3，加上基金经理从业年限>3年。
      
    ### 📰 今日资讯 (财联社 7x24)
    """)
    
    with st.spinner("正在获取实时财经快讯..."):
        news_list = data_api.get_financial_news()
        
    if news_list:
        for item in news_list:
            with st.container():
                # Make title a clickable link if URL exists
                if item.get('url'):
                    st.markdown(f"**[{item['tag']}] [{item['title']}]({item['url']})**")
                else:
                    st.markdown(f"**[{item['tag']}] {item['title']}**")
                    
                st.caption(f"发布时间: {item['time']}")
                st.divider()
    else:
        st.warning("暂无新闻数据或获取失败。")

# --- Main Routing ---
if page == "仪表盘":
    render_dashboard()
elif page == "股票行情":
    render_stock_analysis()
elif page == "基金查询 & 诊断":
    render_search()
elif page == "持仓管理":
    render_holdings()
elif page == "智能定投":
    render_plan()
elif page == "理财科普":
    render_knowledge()
