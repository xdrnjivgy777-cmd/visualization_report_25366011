import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os

font_path = 'NotoSansJP-Regular.ttf'

if os.path.exists(font_path):
    fe = fm.FontEntry(
        fname=font_path,
        name='NotoSansJP' 
    )
    fm.fontManager.ttflist.insert(0, fe)
    
    plt.rcParams['font.family'] = fe.name
else:
    print(f"警告：未找到字体文件 {font_path}")

plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(layout='wide', page_title='日本物価・消費分析ダッシュボード')

@st.cache_data
def load_data():
    # CPIデータの読み込み
    cpi1 = pd.read_excel('cpi1_1970_2025_pico.xlsx', sheet_name='bm01-1', skiprows=9, usecols='I:CL')
    cpi1.drop([0, 1, 2, 3], axis=0, inplace=True)
    cpi1.drop(cpi1.columns[[1, 2, 3]], axis=1, inplace=True)
    cpi1.columns.values[0] = '年月'
    cpi1['年月'] = pd.to_datetime(cpi1['年月'], format='%Y年%m月')
    cpi1.set_index('年月', inplace=True)
    for col in cpi1.columns:
        cpi1[col] = pd.to_numeric(cpi1[col], errors='coerce')
    
    # 消費データの読み込み
    con1 = pd.read_excel('consumption1_3category_3index_2019_2024_pico.xlsx', sheet_name='RESAS_Life_Category_Data')
    con1['日付'] = pd.to_datetime(con1['日付'])
    con1['年'] = con1['日付'].dt.year
    return cpi1, con1

cpi1, con1 = load_data()

tab1, tab2 = st.tabs(['日本の物価推移', '消費品類分析'])

with tab1:
    st.header('日本の消費者物価指数（CPI）推移')
    
    col1, col2 = st.columns(2)
    with col1:
        selected_metrics = st.multiselect('表示指標を選択', options=cpi1.columns.tolist(), default=['総合'])
    with col2:
        min_year = int(cpi1.index.year.min())
        max_year = int(cpi1.index.year.max())
        year_range = st.slider('期間を選択', min_year, max_year, (min_year, max_year))

    df_cpi_filtered = cpi1[(cpi1.index.year >= year_range[0]) & (cpi1.index.year <= year_range[1])]
    
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    for metric in selected_metrics:
        ax1.plot(df_cpi_filtered.index, df_cpi_filtered[metric], label=metric, marker='o', markersize=2)
    
    ax1.set_title(f'日本の消費者物価指数（{year_range[0]}年～{year_range[1]}年）', fontsize=16)
    ax1.set_ylabel('消費者物価指数（2020年=100）')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.legend()
    st.pyplot(fig1)

with tab2:
    st.header('カテゴリ別：単価と購入点数のバランス分析')
    
    # フィルタリング
    all_large_cats = con1['大分類'].unique().tolist()
    selected_large = st.multiselect('大分類を選択', options=all_large_cats, default=['生鮮・惣菜'])
    
    available_mid_cats = con1[con1['大分類'].isin(selected_large)]['中分類'].dropna().unique().tolist()
    selected_mid = st.multiselect('中分類を選択', options=available_mid_cats, default=available_mid_cats)

    target_metrics = ['レジ通過1000人あたり購入金額', 'レジ通過1000人あたり購入点数']
    
    df_con_filtered = con1[
        (con1['大分類'].isin(selected_large)) &
        (con1['中分類'].isin(selected_mid)) &
        (con1['指標'].isin(target_metrics)) &
        (con1['年'].isin([2020, 2024]))
    ]

    if not df_con_filtered.empty:
        con1_fd_mid = df_con_filtered.pivot_table(
            index=['大分類', '中分類'],
            columns='年',
            values='数値',
            aggfunc='sum'
        )
        
        try:
            val_col = 'レジ通過1000人あたり購入金額'
            qty_col = 'レジ通過1000人あたり購入点数'
            
            df_val = df_con_filtered[df_con_filtered['指標'] == val_col].pivot_table(index=['大分類', '中分類'], columns='年', values='数値', aggfunc='sum')
            df_qty = df_con_filtered[df_con_filtered['指標'] == qty_col].pivot_table(index=['大分類', '中分類'], columns='年', values='数値', aggfunc='sum')
            
            price_2020 = df_val[2020] / df_qty[2020]
            price_2024 = df_val[2024] / df_qty[2024]
            
            plot_df = pd.DataFrame({
                '金額の基準': df_val[2020],
                '金額の変化': df_val[2024] - df_val[2020],
                '単価の変化率(%)': (price_2024 / price_2020 - 1) * 100,
                '点数の変化率(%)': (df_qty[2024] / df_qty[2020] - 1) * 100
            })
            plot_df['金額の寄与率(%)'] = (plot_df['金額の変化'] / plot_df['金額の基準'].sum()) * 100
            plot_df = plot_df.dropna()

            fig2, ax2 = plt.subplots(figsize=(12, 8))
            scatter = ax2.scatter(
                plot_df['単価の変化率(%)'], 
                plot_df['点数の変化率(%)'], 
                s=plot_df['金額の基準'] / 500, 
                c=plot_df['金額の寄与率(%)'], 
                cmap='Blues', 
                alpha=0.6,
                edgecolors='w'
            )
            
            for idx, row in plot_df.iterrows():
                ax2.text(row['単価の変化率(%)'], row['点数の変化率(%)'] + 0.1, idx[1], fontsize=9, ha='center')
            
            ax2.axhline(0, color='gray', linestyle='--', alpha=0.5)
            ax2.axvline(0, color='gray', linestyle='--', alpha=0.5)
            ax2.set_xlabel('単価の変化率 (%)')
            ax2.set_ylabel('点数の変化率 (%)')
            ax2.set_title('食品分類の影響：単価 vs 点数 (バブルの大きさ：金額)', fontsize=16)
            plt.colorbar(scatter, label='金額に対する寄与率 (%)')
            st.pyplot(fig2)
            
        except Exception as e:
            st.error(f'データの計算中にエラーが発生しました。選択範囲に2020年と2024年の両方のデータがあるか確認してください。エラー内容: {e}')
    else:
        st.warning('データが存在しません。フィルター条件を変えてください。')
