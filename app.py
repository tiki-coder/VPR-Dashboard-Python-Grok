import streamlit as st
import pandas as pd
import plotly.express as px

# ====================== Wide layout и Material Design стиль ======================
st.set_page_config(page_title="VPR Dashboard", layout="wide")

st.markdown("""
<style>
    /* Основные Material Design элементы */
    .main {
        background: var(--background-color);
    }
    h1, h2, h3 {
        font-family: 'Google Sans', sans-serif;
        color: var(--text-color);
    }
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: var(--background-color);
        z-index: 999;
        padding: 1rem 1rem 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border-radius: 0 0 16px 16px;
        backdrop-filter: blur(10px);
    }
    .content-offset {
        margin-top: 140px;
    }
    .material-card {
        background: var(--background-color);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        border: 1px solid var(--text-color-low-opacity);
        min-height: 420px; /* Выравнивание высоты карточек */
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
    }
    .material-card h3 {
        margin-top: 0;
        color: var(--primary-color, #6200EE);
        border-bottom: 2px solid var(--primary-color, #6200EE);
        padding-bottom: 0.5rem;
    }
    .divider {
        height: 1px;
        background: var(--text-color-low-opacity);
        margin: 2rem 0;
    }
    /* Метрики в Material стиле */
    .stMetric {
        background: var(--background-color);
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ====================== Загрузка данных ======================
@st.cache_data
def load_data():
    df_marks = pd.read_excel("marks.xlsx")
    percent_cols_marks = ["2", "3", "4", "5"]
    df_marks[percent_cols_marks] = df_marks[percent_cols_marks].replace(",", ".", regex=True).astype(float)
    df_marks["Кол-во участников"] = pd.to_numeric(
        df_marks["Кол-во участников"].astype(str).str.replace(",", "").str.strip(),
        errors='coerce'
    ).fillna(0).astype(int)
    
    df_scores = pd.read_excel("scores.xlsx")
    ball_cols = [str(i) for i in range(0, 39)]
    existing_ball_cols = [col for col in ball_cols if col in df_scores.columns]
    df_scores[existing_ball_cols] = df_scores[existing_ball_cols].replace(",", ".", regex=True)
    df_scores[existing_ball_cols] = pd.to_numeric(df_scores[existing_ball_cols].stack(), errors='coerce').unstack().fillna(0).astype(float)
    df_scores["Кол-во участников"] = pd.to_numeric(
        df_scores["Кол-во участников"].astype(str).str.replace(",", "").str.strip(),
        errors='coerce'
    ).fillna(0).astype(int)
    
    df_bias = pd.read_excel("bias.xlsx")
    marker_cols = ["4 РУ", "4 МА", "5 РУ", "5 МА"]
    df_bias[marker_cols] = df_bias[marker_cols].fillna(0).astype(int)
    if "Количество маркеров" not in df_bias.columns:
        df_bias["Количество маркеров"] = df_bias[marker_cols].sum(axis=1)
    
    return df_marks, df_scores, df_bias

df_marks, df_scores, df_bias = load_data()

# ====================== Фильтры (sticky) ======================
header = st.container()
with header:
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        years = sorted(df_marks["Год"].unique())
        selected_year = st.selectbox("Год", years, key="year")
    
    with col2:
        classes = sorted(df_marks[df_marks["Год"] == selected_year]["Класс"].unique())
        selected_class = st.selectbox("Класс", classes, key="class")
    
    with col3:
        subjects = sorted(df_marks[(df_marks["Год"] == selected_year) & 
                                  (df_marks["Класс"] == selected_class)]["Предмет"].unique())
        selected_subject = st.selectbox("Предмет", subjects, key="subject")
    
    filtered_marks = df_marks[(df_marks["Год"] == selected_year) &
                             (df_marks["Класс"] == selected_class) &
                             (df_marks["Предмет"] == selected_subject)]
    
    with col4:
        muns = ["Все"] + sorted(filtered_marks["Муниципалитет"].unique())
        selected_mun = st.selectbox("Муниципалитет", muns, key="mun")
    
    if selected_mun == "Все":
        filtered_oo = filtered_marks
    else:
        filtered_oo = filtered_marks[filtered_marks["Муниципалитет"] == selected_mun]
    
    unique_oo = filtered_oo[["Логин", "ОО"]].drop_duplicates(subset="Логин")
    oo_options = ["Все"] + sorted(unique_oo["ОО"].tolist())
    
    with col5:
        selected_oo = st.selectbox("ОО", oo_options, key="oo")
    
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="content-offset"></div>', unsafe_allow_html=True)

# ====================== Логины для текущего контекста (графики отметок и баллов) ======================
if selected_oo == "Все":
    current_marks = filtered_oo
    selected_login = None
else:
    selected_login = unique_oo[unique_oo["ОО"] == selected_oo]["Логин"].iloc[0]
    current_marks = filtered_oo[filtered_oo["Логин"] == selected_login]

logins = current_marks["Логин"].unique()

current_scores = df_scores[(df_scores["Год"] == selected_year) &
                          (df_scores["Класс"] == selected_class) &
                          (df_scores["Предмет"] == selected_subject) &
                          (df_scores["Логин"].isin(logins))]

# ====================== Сводная информация ======================
total_participants = current_marks["Кол-во участников"].sum()

def get_marks_percentages(df):
    if df.empty or total_participants == 0:
        return pd.Series([0.0]*4, index=["2","3","4","5"])
    total = df["Кол-во участников"].sum()
    weighted = (df[["2","3","4","5"]] / 100 * df["Кол-во участников"].values[:, None]).sum()
    return (weighted / total * 100).round(2)

marks_perc = get_marks_percentages(current_marks)
uspevaemost = 100 - marks_perc["2"]
kachestvo = marks_perc["4"] + marks_perc["5"]

st.markdown("### Сводная информация")
summary_cols = st.columns(4)
summary_cols[0].metric("Выбранная ОО", selected_oo if selected_oo != "Все" else "Все школы")
summary_cols[1].metric("Участников", int(total_participants))
summary_cols[2].metric("Успеваемость", f"{uspevaemost:.2f}%")
summary_cols[3].metric("Качество", f"{kachestvo:.2f}%")

# ====================== Графики ======================
col_left, col_right = st.columns(2)

marks_plot_df = pd.DataFrame({"Отметка": ["2", "3", "4", "5"], "Процент": marks_perc.values})
fig_marks = px.bar(marks_plot_df, x="Отметка", y="Процент", text="Процент",
                   color="Отметка",
                   color_discrete_map={"2": "#f44336", "3": "#ff9800", "4": "#4caf50", "5": "#2e7d32"},
                   title="Распределение отметок (%)")
fig_marks.update_traces(texttemplate="%{text:.2f}%")
fig_marks.update_layout(showlegend=False, yaxis_title="Процент участников")
col_left.plotly_chart(fig_marks, use_container_width=True)

def get_scores_percentages(df):
    if df.empty or df["Кол-во участников"].sum() == 0:
        return pd.DataFrame(columns=["Балл", "Процент"])
    total = df["Кол-во участников"].sum()
    ball_cols = [col for col in df.columns if col.isdigit()]
    weighted = pd.Series(0.0, index=ball_cols)
    for _, row in df.iterrows():
        weighted += row[ball_cols] / 100 * row["Кол-во участников"]
    percents = weighted / total * 100
    percents = pd.to_numeric(percents, errors='coerce').fillna(0).round(2)
    positive_balls = [int(col) for col in percents.index if percents[col] > 0]
    if not positive_balls:
        return pd.DataFrame(columns=["Балл", "Процент"])
    max_ball = max(positive_balls)
    balls = list(range(0, max_ball + 1))
    return pd.DataFrame({"Балл": balls, "Процент": [percents.get(str(b), 0.0) for b in balls]})

scores_plot_df = get_scores_percentages(current_scores)
if not scores_plot_df.empty:
    max_ball = scores_plot_df["Балл"].max()
    fig_scores = px.bar(scores_plot_df, x="Балл", y="Процент",
                        color_discrete_sequence=["#2196f3"],
                        title="Распределение первичных баллов (%)")
    fig_scores.update_xaxes(range=[-0.5, max_ball + 0.5], dtick=1)
    fig_scores.update_layout(yaxis_title="Процент участников")
    col_right.plotly_chart(fig_scores, use_container_width=True)
else:
    col_right.warning("Нет данных по первичным баллам для выбранных фильтров.")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ====================== Признаки необъективности (независимо от класса/предмета) ======================
st.markdown("### Признаки необъективности")

# Логины муниципалитета по году (независимо от класса/предмета)
if selected_mun == "Все":
    mun_marks_all = df_marks[df_marks["Год"] == selected_year]
else:
    mun_marks_all = df_marks[(df_marks["Год"] == selected_year) & (df_marks["Муниципалитет"] == selected_mun)]

mun_logins = mun_marks_all["Логин"].unique()

bias_year = df_bias[df_bias["Год"] == selected_year]
marker_cols = ["4 РУ", "4 МА", "5 РУ", "5 МА"]

bias_cols = st.columns(3)

# Левая карточка
with bias_cols[0]:
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    st.markdown("#### Анализ выбранной школы")
    if selected_oo != "Все" and selected_login is not None:
        school_bias = bias_year[bias_year["Логин"] == selected_login]
        if not school_bias.empty and school_bias["Количество маркеров"].iloc[0] > 0:
            total_mark = school_bias["Количество маркеров"].iloc[0]
            markers_list = [f"{col.split()[1]} {col.split()[0]}" for col in marker_cols if school_bias[col].iloc[0] > 0]
            st.markdown(f"**Количество маркеров:** {total_mark}")
            st.markdown("**Предметы:** " + ", ".join(markers_list))
            st.warning("Выявлены признаки необъективности")
        else:
            st.success("Маркеры отсутствуют ✔️")
    else:
        st.info("Выберите конкретную школу для анализа")
    st.markdown('</div>', unsafe_allow_html=True)

# Средняя карточка
with bias_cols[1]:
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    st.markdown("#### Доля ОО с признаками необъективности (по республике)")
    
    def base_schools_count(year):
        base = df_marks[(df_marks["Год"] == year) & (df_marks["Класс"] == 4) & (df_marks["Предмет"] == "Русский язык")]
        return base["Логин"].nunique() if not base.empty else 0
    
    years_to_show = [selected_year - 2, selected_year - 1, selected_year]
    dolya_subcols = st.columns(3)
    for i, y in enumerate(years_to_show):
        if y in df_bias["Год"].unique():
            base = base_schools_count(y)
            marked_df = df_bias[df_bias["Год"] == y]
            marked = len(marked_df[marked_df["Количество маркеров"] > 0]["Логин"].unique())
            dolya = marked / base * 100 if base > 0 else 0
            dolya_subcols[i].metric(str(y), f"{dolya:.1f}%")
    
    if selected_oo != "Все" and selected_login is not None:
        years_with_marker = [str(y) for y in years_to_show if y in df_bias["Год"].unique() and 
                             not df_bias[(df_bias["Год"] == y) & (df_bias["Логин"] == selected_login)].empty and
                             df_bias[(df_bias["Год"] == y) & (df_bias["Логин"] == selected_login)]["Количество маркеров"].iloc[0] > 0]
        if years_with_marker:
            st.markdown(f"**Школа попадала в списки:** {', '.join(years_with_marker)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Правая карточка
with bias_cols[2]:
    st.markdown('<div class="material-card">', unsafe_allow_html=True)
    st.markdown("#### Список ОО с маркерами в муниципалитете")
    if selected_mun != "Все":
        mun_marked = bias_year[(bias_year["Логин"].isin(mun_logins)) & (bias_year["Количество маркеров"] > 0)]
        marked_schools = sorted(mun_marked["ОО"].unique())
        if marked_schools:
            for school in marked_schools:
                st.markdown(f"• {school}")
        else:
            st.success("Школы с признаками необъективности отсутствуют ✔️")
    else:
        st.info("Выберите муниципалитет для просмотра списка")
    st.markdown('</div>', unsafe_allow_html=True)
