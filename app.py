import streamlit as st
import pandas as pd
import plotly.express as px

# ====================== CSS для Material Design и sticky header ======================
st.markdown("""
<style>
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: var(--background-color);
        z-index: 999;
        padding: 1rem 1rem 0.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-radius: 0 0 12px 12px;
    }
    .content-offset {
        margin-top: 120px;
    }
    .card {
        background: var(--background-color);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border: 1px solid var(--text-color-low);
    }
</style>
""", unsafe_allow_html=True)

# ====================== Загрузка и очистка данных ======================
@st.cache_data
def load_data():
    # Marks
    df_marks = pd.read_excel("marks.xlsx")
    percent_cols_marks = ["2", "3", "4", "5"]
    df_marks[percent_cols_marks] = df_marks[percent_cols_marks].replace(",", ".", regex=True).astype(float)
    
    # Scores
    df_scores = pd.read_excel("scores.xlsx")
    ball_cols = [str(i) for i in range(0, 39)]
    existing_ball_cols = [col for col in ball_cols if col in df_scores.columns]
    df_scores[existing_ball_cols] = df_scores[existing_ball_cols].replace(",", ".", regex=True).astype(float)
    df_scores[existing_ball_cols] = df_scores[existing_ball_cols].fillna(0)
    
    # Bias
    df_bias = pd.read_excel("bias.xlsx")
    marker_cols = ["4 РУ", "4 МА", "5 РУ", "5 МА"]
    df_bias[marker_cols] = df_bias[marker_cols].fillna(0).astype(int)
    if "Количество маркеров" not in df_bias.columns:
        df_bias["Количество маркеров"] = df_bias[marker_cols].sum(axis=1)
    
    return df_marks, df_scores, df_bias

df_marks, df_scores, df_bias = load_data()

# ====================== Sticky header с фильтрами ======================
header = st.container()
with header:
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        years = sorted(df_marks["Год"].unique())
        selected_year = st.selectbox("Год", years)
    
    with col2:
        classes = sorted(df_marks[df_marks["Год"] == selected_year]["Класс"].unique())
        selected_class = st.selectbox("Класс", classes)
    
    with col3:
        subjects = sorted(df_marks[(df_marks["Год"] == selected_year) & 
                                  (df_marks["Класс"] == selected_class)]["Предмет"].unique())
        selected_subject = st.selectbox("Предмет", subjects)
    
    # Базовая фильтрация по Marks
    filtered_marks = df_marks[(df_marks["Год"] == selected_year) &
                             (df_marks["Класс"] == selected_class) &
                             (df_marks["Предмет"] == selected_subject)]
    
    with col4:
        muns = ["Все"] + sorted(filtered_marks["Муниципалитет"].unique())
        selected_mun = st.selectbox("Муниципалитет", muns)
    
    # Фильтрация для ОО
    if selected_mun == "Все":
        filtered_oo = filtered_marks
    else:
        filtered_oo = filtered_marks[filtered_marks["Муниципалитет"] == selected_mun]
    
    unique_oo = filtered_oo[["Логин", "ОО"]].drop_duplicates(subset="Логин")
    oo_options = ["Все"] + sorted(unique_oo["ОО"].tolist())
    
    with col5:
        selected_oo = st.selectbox("ОО", oo_options)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Отступ под sticky header
st.markdown('<div class="content-offset"></div>', unsafe_allow_html=True)

# ====================== Определение текущего набора школ (по логину) ======================
if selected_oo == "Все":
    current_marks = filtered_oo
    selected_login = None
else:
    selected_login = unique_oo[unique_oo["ОО"] == selected_oo]["Логин"].iloc[0]
    current_marks = filtered_oo[filtered_oo["Логин"] == selected_login]

logins = current_marks["Логин"].unique()

# ====================== Данные Scores по тем же логинам ======================
current_scores = df_scores[(df_scores["Год"] == selected_year) &
                          (df_scores["Класс"] == selected_class) &
                          (df_scores["Предмет"] == selected_subject) &
                          (df_scores["Логин"].isin(logins))]

# ====================== Сводная информация ======================
total_participants = current_marks["Кол-во участников"].sum()

def get_marks_percentages(df):
    if df.empty:
        return pd.Series([0,0,0,0], index=["2","3","4","5"])
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

# --- Отметки ---
marks_plot_df = pd.DataFrame({
    "Отметка": ["2", "3", "4", "5"],
    "Процент": marks_perc.values
})
fig_marks = px.bar(marks_plot_df, x="Отметка", y="Процент",
                   text="Процент",
                   color="Отметка",
                   color_discrete_map={"2": "#f44336", "3": "#ff9800", "4": "#4caf50", "5": "#2e7d32"},
                   title="Распределение отметок (%)")
fig_marks.update_traces(texttemplate="%{text:.2f}%")
fig_marks.update_layout(showlegend=False, yaxis_title="Процент участников")
col_left.plotly_chart(fig_marks, use_container_width=True)

# --- Первичные баллы ---
def get_scores_percentages(df):
    if df.empty:
        return pd.DataFrame(columns=["Балл", "Процент"])
    total = df["Кол-во участников"].sum()
    ball_cols = [col for col in df.columns if col.isdigit()]
    weighted = pd.DataFrame(0.0, index=ball_cols, columns=["count"])
    for _, row in df.iterrows():
        weighted["count"] += row[ball_cols] / 100 * row["Кол-во участников"]
    percents = weighted["count"] / total * 100
    percents = percents.round(2)
    positive_balls = [int(col) for col in percents.index if percents[col] > 0]
    if not positive_balls:
        return pd.DataFrame(columns=["Балл", "Процент"])
    max_ball = max(positive_balls)
    balls = list(range(0, max_ball + 1))
    perc_values = [percents.get(str(b), 0.0) for b in balls]
    return pd.DataFrame({"Балл": balls, "Процент": perc_values})

scores_plot_df = get_scores_percentages(current_scores)
if not scores_plot_df.empty:
    max_ball = scores_plot_df["Балл"].max()
    fig_scores = px.bar(scores_plot_df, x="Балл", y="Процент",
                        text="Процент",
                        color_discrete_sequence=["#2196f3"],
                        title="Распределение первичных баллов (%)")
    fig_scores.update_traces(texttemplate="%{text:.2f}%")
    fig_scores.update_xaxes(range=[-0.5, max_ball + 0.5], dtick=1)
    fig_scores.update_layout(yaxis_title="Процент участников")
    col_right.plotly_chart(fig_scores, use_container_width=True)
else:
    col_right.warning("Нет данных по первичным баллам для выбранных фильтров.")

# ====================== Признаки необъективности ======================
st.markdown("### Признаки необъективности")

bias_year = df_bias[df_bias["Год"] == selected_year]
marker_cols = ["4 РУ", "4 МА", "5 РУ", "5 МА"]

bias_cols = st.columns([2, 3, 2])

# Левая карточка — только для конкретной школы
if selected_oo != "Все":
    with bias_cols[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader(f"Анализ выбранной школы ({selected_year})")
        school_bias = bias_year[bias_year["Логин"] == selected_login]
        if not school_bias.empty and school_bias["Количество маркеров"].iloc[0] > 0:
            total_mark = school_bias["Количество маркеров"].iloc[0]
            markers_list = []
            for col in marker_cols:
                if school_bias[col].iloc[0] > 0:
                    class_num, subj = col.split()
                    markers_list.append(f"{subj} {class_num}")
            markers_str = ", ".join(markers_list)
            st.write(f"**Количество маркеров:** {total_mark}")
            st.write(markers_str)
            st.warning("В школе выявлены признаки необъективности.")
        else:
            st.success("Маркеры отсутствуют")
        st.markdown('</div>', unsafe_allow_html=True)

# Средняя карточка — доля ОО с маркерами (по всему региону)
with bias_cols[1]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Доля ОО с признаками необъективности")
    
    def base_schools_count(year):
        base = df_marks[(df_marks["Год"] == year) &
                        (df_marks["Класс"] == 4) &
                        (df_marks["Предмет"] == "Русский язык")]
        return base["Логин"].nunique()
    
    years_to_show = [selected_year - 2, selected_year - 1, selected_year]
    dolya_cols = st.columns(3)
    for i, y in enumerate(years_to_show):
        if y in df_bias["Год"].unique():
            base = base_schools_count(y)
            marked_df = df_bias[df_bias["Год"] == y]
            marked = len(marked_df[marked_df["Количество маркеров"] > 0]["Логин"].unique())
            dolya = marked / base * 100 if base > 0 else 0
            dolya_cols[i].metric(str(y), f"{dolya:.1f}%")
    
    # Попадание выбранной школы в маркеры за 3 года
    if selected_oo != "Все":
        years_with_marker = []
        for y in years_to_show:
            if y in df_bias["Год"].unique():
                past_bias = df_bias[(df_bias["Год"] == y) & (df_bias["Логин"] == selected_login)]
                if not past_bias.empty and past_bias["Количество маркеров"].iloc[0] > 0:
                    years_with_marker.append(str(y))
        if years_with_marker:
            st.write(f"Школа попадала в списки необъективности в годы: {', '.join(years_with_marker)}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Правая карточка — список школ муниципалитета с маркерами
with bias_cols[2]:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Список ОО муниципалитета с маркерами")
    if selected_mun != "Все":
        mun_logins = filtered_oo["Логин"].unique()
        mun_marked = bias_year[(bias_year["Логин"].isin(mun_logins)) &
                               (bias_year["Количество маркеров"] > 0)]
        marked_schools = sorted(mun_marked["ОО"].unique())
        if marked_schools:
            for school in marked_schools:
                st.write(f"• {school}")
        else:
            st.success("В этом году в выбранном районе школы с признаками необъективности отсутствуют. 👍")
    else:
        st.info("Выберите конкретный муниципалитет для просмотра списка.")
    st.markdown('</div>', unsafe_allow_html=True)
