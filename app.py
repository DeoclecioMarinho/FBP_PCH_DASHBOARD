"""PCH | FBP — Dashboard operacional da formação (~40 participantes)."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import build_analysis, question_summary
from kobo_client import DEFAULT_BASE_URL, PRE_UID, POS_UID, KoboAPIError, fetch_submissions
from monitor import pre_per_question, topic_performance, suspected_duplicate_names

ROOT = Path(__file__).resolve().parent
QUESTIONS = json.loads((ROOT / "questionario.json").read_text(encoding="utf-8"))["questions"]
NAVY = "#253C4E"
BLUE = "#235D7A"
GREEN = "#18786C"
AMBER = "#A86F29"
RED = "#B85650"
MUTED = "#748596"

st.set_page_config(page_title="PCH · Formação FBP", page_icon="📊", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp { background-color:#F8FAFC; color:#243747; }
.block-container {max-width:1260px; padding-top:1.7rem; padding-bottom:2rem;}
h1 {font-size:1.6rem !important; font-weight:700 !important; color:#22394A !important; margin-bottom:.1rem !important;}
h2 {font-size:1.14rem !important; font-weight:680 !important; color:#243D50 !important; padding-top:.45rem !important;}
h3 {font-size:1rem !important; font-weight:650 !important; color:#243D50 !important;}
[data-testid="stSidebar"] {background:#F0F4F7; border-right:1px solid #E1E8EE;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:1.25rem;}
[data-testid="stMetric"] {background:#fff; padding:14px 16px; border:1px solid #E3EAF0; border-radius:9px;}
[data-testid="stMetricLabel"] {font-size:.81rem; color:#607586;}
[data-testid="stMetricValue"] {font-size:1.58rem; font-weight:720; color:#203C51;}
[data-testid="stMetricDelta"] {font-size:.75rem;}
button[data-baseweb="tab"] {font-size:.9rem; font-weight:620;}
[data-baseweb="tab-list"] {gap:1rem; border-bottom:1px solid #DCE6ED;}
[data-testid="stExpander"] {background:#fff; border:1px solid #E5EBF0; border-radius:8px;}
.fbp-brand {font-size:.98rem; font-weight:730; color:#263E50; margin:0;}
.fbp-sub {font-size:.74rem; color:#758898; margin-top:2px;}
.fbp-eyebrow {color:#718697; font-size:.75rem; letter-spacing:.035em; font-weight:650;}
.fbp-hint {color:#62788A; font-size:.83rem; line-height:1.5; margin:.2rem 0 1rem;}
.fbp-foot {color:#8694A0; font-size:.73rem; margin-top:1rem;}
hr {border-color:#DFE7ED;}
</style>
""", unsafe_allow_html=True)


def setting(key, fallback=""):
    try:
        value = st.secrets.get(key)
        if value is not None:
            return str(value)
    except (FileNotFoundError, AttributeError, KeyError, RuntimeError):
        pass
    return os.environ.get(key, fallback)


def secure_auth():
    password = setting("DASHBOARD_PASSWORD")
    if not password:
        return False  # Exibe apenas agregados, sem dados pessoais.
    if st.session_state.get("authenticated"):
        return True
    st.title("Acesso ao acompanhamento FBP")
    st.caption("Insere a palavra-passe para consultar os resultados da formação.")
    with st.form("login"):
        attempt = st.text_input("Palavra-passe", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        if hmac.compare_digest(attempt, password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Palavra-passe incorreta.")
    st.stop()


def fmt_pct(x):
    return "—" if x is None or pd.isna(x) else f"{float(x):.1f}%".replace(".", ",")


def fmt_pp(x):
    return "—" if x is None or pd.isna(x) else f"{float(x):+.1f} pp".replace(".", ",")


def csv_content(df):
    return df.to_csv(index=False, sep=";").encode("utf-8-sig")


@st.cache_data(ttl=120, show_spinner=False)
def fetch_both(base, pre_uid, pos_uid, token_hash, _token):
    return (fetch_submissions(base, pre_uid, _token),
            fetch_submissions(base, pos_uid, _token),
            datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"))


def question_chart(data):
    """Gráfico sóbrio de perguntas com baixos acertos — não mostra a chave de correção."""
    ordered = data.sort_values(["Acerto (%)", "Número"], ascending=[True, True]).copy()
    colors = [RED if v < 50 else AMBER if v < 70 else GREEN for v in ordered["Acerto (%)"]]
    fig = go.Figure(go.Bar(
        y=ordered["Pergunta"], x=ordered["Acerto (%)"], orientation="h",
        marker_color=colors, text=ordered["Acerto (%)"].map(lambda v: f"{v:.0f}%"),
        textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}% de respostas corretas<extra></extra>",
    ))
    fig.update_layout(height=max(270, 40*len(data)+40),
        xaxis=dict(title="% de respostas corretas", range=[0, 111],
                   tickvals=[0,25,50,75,100], gridcolor="#E7EEF3", zeroline=False),
        yaxis=dict(title="", autorange="reversed"),
        margin=dict(l=12, r=35, t=10, b=25),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=NAVY, size=12), showlegend=False)
    return fig


def avg_comparison(pre_value, pos_value):
    fig = go.Figure(go.Bar(
        x=["Pré-teste", "Pós-teste"], y=[pre_value, pos_value],
        marker_color=[BLUE, GREEN], text=[f"{pre_value:.1f}%", f"{pos_value:.1f}%"],
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(height=270, showlegend=False, margin=dict(l=10,r=10,t=20,b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color=NAVY, size=12),
                      yaxis=dict(range=[0,110], gridcolor="#E6EDF2", title="% de acertos"),
                      xaxis=dict(title=""))
    return fig


def pre_view(frame, raw_pre, goal, access, anomalies):
    complete = frame[frame["Pré (%)"].notna()].copy() if not frame.empty else frame.copy()
    n_pre = len(complete)
    mean = complete["Pré (%)"].mean() if n_pre else None
    ids = set(frame["participante_id"]) if not frame.empty else set()
    qdf = pre_per_question(raw_pre, ids, QUESTIONS)
    suspects = suspected_duplicate_names(raw_pre, ids)
    bad_pre = (frame["Inconsistência nota pré"].sum() if not frame.empty else 0)
    gaps = max(0, goal - n_pre) if goal is not None else None
    qlow = qdf[qdf["Acerto (%)"] < 50].copy() if n_pre else qdf.head(0)

    st.markdown("#### Como está a decorrer o pré-teste?")
    a,b,c,d = st.columns(4)
    a.metric("Pré-testes completos", f"{n_pre} / {goal}" if goal is not None else n_pre)
    b.metric("Por completar (estimativa)", gaps if gaps is not None else "—")
    c.metric("Média do pré-teste", fmt_pct(mean))
    d.metric("Perguntas abaixo de 50%", str(len(qlow)) if n_pre >= 5 else "—")
    if goal is not None:
        st.progress(min(n_pre / goal, 1.0))
        st.caption(f"{n_pre} formulários completos de uma meta de {goal} participantes. A meta é indicativa, não uma lista nominal de presenças.")
    else:
        st.caption("A meta de 40 participantes aplica-se à formação completa. O filtro institucional mostra apenas os registos selecionados.")

    if not n_pre:
        st.info("Ainda não existem pré-testes completos nos filtros selecionados. O painel irá mostrar as dificuldades assim que chegarem respostas.")
    elif n_pre < 5:
        st.info(f"Há apenas {n_pre} pré-teste(s) completo(s). Aguarda pelo menos 5 respostas para interpretar tendências; as percentagens ainda são muito instáveis.")
    elif len(qlow):
        names = ", ".join(qlow.sort_values("Acerto (%)")["Pergunta"].head(5))
        st.warning(f"**Atenção para a formação:** {len(qlow)} pergunta(s) tiveram menos de metade de respostas certas. Prioriza {names} na explicação dos conteúdos.")
    else:
        st.success("Até ao momento, nenhuma pergunta ficou abaixo de 50% de acertos.")
    if bad_pre or not suspects.empty:
        st.caption(f"⚠️ Há {len(suspects)} possível(is) duplicado(s) de nome/instituição e {int(bad_pre)} diferença(s) no cálculo das notas. Consulta «Registos a verificar» abaixo.")

    if n_pre:
        st.divider()
        st.markdown("#### Onde estão as maiores dificuldades?")
        st.caption("Percentagem de respostas corretas no pré-teste. As perguntas aparecem da mais difícil para a mais fácil. Não são apresentadas as respostas certas.")
        hardest = qdf.sort_values(["Acerto (%)", "Número"], ascending=[True, True]).head(5)
        a,b = st.columns([.72, 1.28], gap="large")
        with a:
            st.plotly_chart(question_chart(hardest), use_container_width=True,
                            config={"displayModeBar": False})
        with b:
            for _, row in hardest.iterrows():
                st.markdown(f"**{row['Pergunta']} · {fmt_pct(row['Acerto (%)'])} de acertos**  ")
                st.write(row["Enunciado"])
        with st.expander("Ver análise de todas as 15 perguntas"):
            all_questions = qdf.sort_values("Número")[
                ["Pergunta","Tema","Enunciado","Acertos","N","Acerto (%)"]].copy()
            st.dataframe(all_questions, use_container_width=True, hide_index=True, height=435,
                         column_config={"Acerto (%)": st.column_config.ProgressColumn(
                             "Acerto (%)", min_value=0, max_value=100, format="%.0f%%")})
            st.download_button("Exportar análise por pergunta", csv_content(all_questions),
                               "FBP_pre_perguntas.csv", "text/csv")
        with st.expander("Ver resultados por tema"):
            topics = topic_performance(qdf)
            st.dataframe(topics[["Tema","Acerto (%)"]], use_container_width=True,
                         hide_index=True, column_config={"Acerto (%)":st.column_config.ProgressColumn(
                             "Acerto (%)", min_value=0, max_value=100, format="%.0f%%")})

    st.divider()
    st.markdown("#### Participação e qualidade dos registos")
    if access and not frame.empty:
        search = st.text_input("Pesquisar participante", placeholder="Escreve um nome", key="pre_search")
        display = frame[frame["Nome"].str.contains(search, case=False, regex=False, na=False)] if search else frame
        cols = ["Nome", "Instituição", "Acertos pré", "Pré (%)", "Data pré"]
        st.dataframe(display[cols].sort_values("Nome"), use_container_width=True,
                     hide_index=True, height=min(420, 42*(len(display)+1)+15))
        st.download_button("Exportar participantes", csv_content(frame[cols]),
                           "FBP_pre_participantes.csv", mime="text/csv")
    elif not access:
        st.caption("Os nomes dos participantes ficam disponíveis quando configurares `DASHBOARD_PASSWORD` nas Secrets.")
    else:
        st.caption("Sem participantes registados.")

    count_anomalies = len(anomalies)
    if count_anomalies or not suspects.empty or (not frame.empty and frame["Respostas pré"].lt(15).any()):
        with st.expander(f"Registos a verificar ({count_anomalies} alertas técnicos; {len(suspects)} possíveis nomes repetidos)"):
            if not access:
                st.caption("Configura a palavra-passe do dashboard para consultar os detalhes individuais.")
            else:
                if not suspects.empty:
                    st.markdown("**Possíveis inscrições duplicadas** — mesmo nome e instituição, mas identificadores diferentes. Confirmar antes de eliminar qualquer registo.")
                    st.dataframe(suspects, hide_index=True, use_container_width=True)
                if not anomalies.empty:
                    st.markdown("**Alertas automáticos**")
                    st.dataframe(anomalies, hide_index=True, use_container_width=True)
                incomplete = frame[frame["Pré (%)"].isna()]
                if not incomplete.empty:
                    st.markdown("**Pré-testes incompletos**")
                    st.dataframe(incomplete[["Nome", "Instituição", "Respostas pré"]],
                                 hide_index=True, use_container_width=True)
    else:
        st.caption("Não foram detetadas anomalias de duplicados por identificador nem discrepâncias de notas.")


def post_view(frame, raw_pre, access, question_records):
    st.markdown("#### Resultados após a formação")
    pairs = frame[frame["Estado"] == "Pré e pós concluídos"].copy() if not frame.empty else frame.copy()
    n_all = len(frame[frame["Pré (%)"].notna()]) if not frame.empty else 0
    n_pos = len(pairs)
    a,b,c,d = st.columns(4)
    a.metric("Pré-testes completos", n_all)
    b.metric("Pós-testes associados", f"{n_pos} / {n_all}")
    if not n_pos:
        c.metric("Média pós-teste", "—")
        d.metric("Evolução da aprendizagem", "—")
        st.info("Assim que forem submetidos pós-testes, vais ver aqui a comparação das notas e quem ainda falta concluir.")
        return
    pre_mean = pairs["Pré (%)"].mean()
    pos_mean = pairs["Pós (%)"].mean()
    delta = pos_mean - pre_mean
    c.metric("Média pós-teste", fmt_pct(pos_mean))
    d.metric("Evolução média", fmt_pp(delta))
    st.caption("As médias são calculadas apenas para participantes com os dois testes completos e a identidade confirmada.")

    st.divider()
    l,r = st.columns([.85, 1.15], gap="large")
    with l:
        st.markdown("#### Evolução das classificações")
        st.plotly_chart(avg_comparison(pre_mean, pos_mean), use_container_width=True,
                        config={"displayModeBar": False})
    with r:
        st.markdown("#### Quem falta concluir o pós-teste?")
        pending = frame[(frame["Estado"] != "Pré e pós concluídos") & frame["Pré (%)"].notna()].copy()
        if not len(pending):
            st.success("Todos os participantes do pré-teste têm um pós-teste válido associado.")
        elif access:
            st.dataframe(pending[["Nome","Instituição","Estado"]],
                         use_container_width=True, hide_index=True,
                         height=min(285,42*(len(pending)+1)+12))
        else:
            st.info(f"Existem {len(pending)} participante(s) sem pós-teste válido. Consulta de nomes disponível com palavra-passe.")

    st.divider()
    st.markdown("#### Resultados individuais")
    if access:
        cols = ["Nome","Instituição","Pré (%)","Pós (%)","Evolução (pp)","Estado"]
        st.dataframe(frame[cols].sort_values("Nome"), use_container_width=True,
                     hide_index=True, height=min(470,42*(len(frame)+1)+12),
                     column_config={"Pré (%)":st.column_config.NumberColumn(format="%.1f%%"),
                                    "Pós (%)":st.column_config.NumberColumn(format="%.1f%%"),
                                    "Evolução (pp)":st.column_config.NumberColumn(format="%+.1f pp")})
        st.download_button("Exportar comparação individual", csv_content(frame[cols]),
                           "FBP_pre_pos_individual.csv", mime="text/csv")
    else:
        st.caption("Resultados individuais protegidos. Configura `DASHBOARD_PASSWORD` nas Secrets.")
    if not question_records.empty:
        with st.expander("Análise pré/pós por pergunta (mesmos participantes)"):
            qs = question_summary(question_records, QUESTIONS)
            cols = ["Pergunta","Tema","N","Pré (%)","Pós (%)","Evolução (pp)"]
            st.dataframe(qs[cols], use_container_width=True, hide_index=True)
            st.download_button("Exportar evolução por pergunta", csv_content(qs),
                               "FBP_pre_pos_perguntas.csv", mime="text/csv")


def main():
    access = secure_auth()
    token = setting("KOBO_TOKEN")
    base = setting("KOBO_BASE_URL", DEFAULT_BASE_URL)
    pre_uid = setting("KOBO_PRE_UID", PRE_UID)
    pos_uid = setting("KOBO_POS_UID", POS_UID)

    with st.sidebar:
        col_icon,col_title = st.columns([.65, 2.5], gap="small", vertical_alignment="center")
        with col_icon:
            logo = ROOT / "assets" / "logo_pch.png"
            if logo.exists():
                st.image(str(logo), width=48)
        with col_title:
            st.markdown('<div class="fbp-brand">PCH · FBP</div><div class="fbp-sub">Avaliação da formação</div>', unsafe_allow_html=True)
        st.divider()
        st.caption("ACOMPANHAMENTO")
        goal = st.number_input("Meta de participantes", min_value=1, max_value=1000, value=40, step=1)
        if st.button("↻ Atualizar dados Kobo", use_container_width=True):
            fetch_both.clear()
            st.rerun()
        st.caption("Atualização automática: até 2 minutos")

    st.title("Formação FBP")
    st.markdown('<div class="fbp-hint">Acompanhamento do pré-teste e evolução da aprendizagem · Projeto de Capital Humano</div>',
                unsafe_allow_html=True)
    if not token:
        st.warning("Falta configurar `KOBO_TOKEN` nas Secrets do Streamlit Cloud.")
        with st.expander("Mostrar configuração", expanded=True):
            st.code('KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"\n'
                    'KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"\n'
                    'KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"\n'
                    'KOBO_TOKEN = "INSERIR_TOKEN_PRIVADO"\n'
                    'DASHBOARD_PASSWORD = "ESCOLHER_PALAVRA_PASSE"',language="toml")
        st.stop()
    try:
        digest = hashlib.sha256(token.encode("utf8")).hexdigest()
        with st.spinner("A carregar respostas do Kobo…"):
            pre_raw, pos_raw, updated = fetch_both(base, pre_uid, pos_uid, digest, token)
    except KoboAPIError as e:
        st.error(f"Não foi possível obter os dados: {e}")
        st.stop()
    except Exception:
        st.error("Falha inesperada ao ler os dados. Consulta os logs do Streamlit (sem divulgar as credenciais).")
        st.stop()

    report = build_analysis(pre_raw, pos_raw)
    full = report["participants"]
    with st.sidebar:
        if not full.empty:
            st.caption("FILTROS")
            editions = sorted(full["Edição"].dropna().unique())
            if len(editions) > 1:
                selected_edition = st.selectbox("Edição", ["Todas",*editions])
            else:
                selected_edition = editions[0] if editions else "Todas"
                st.caption(f"Edição: {selected_edition}")
            inst = sorted(full["Instituição"].dropna().unique())
            selected_inst = st.selectbox("Instituição", ["Todas",*inst]) if len(inst)>1 else "Todas"
        else:
            selected_edition,selected_inst = "Todas","Todas"
        st.divider()
        st.caption(f"Fonte: Kobo PCH · {updated}")

    filtered = full.copy()
    if not filtered.empty:
        if selected_edition != "Todas":
            filtered = filtered[filtered["Edição"] == selected_edition]
        if selected_inst != "Todas":
            filtered = filtered[filtered["Instituição"] == selected_inst]
    ids = set(filtered["participante_id"]) if not filtered.empty else set()
    qrecords = report["questions"]
    if not qrecords.empty:
        qrecords = qrecords[qrecords["participante_id"].isin(ids)]
    st.caption(f"Edição: {selected_edition}" + (f"  ·  {selected_inst}" if selected_inst != "Todas" else ""))

    pre_anomalies = report["anomalies"]
    if not pre_anomalies.empty:
        pre_anomalies = pre_anomalies[pre_anomalies["Tipo"].str.contains("pré", case=False, na=False)]
    tab_pre, tab_pos = st.tabs(["Durante o pré-teste", "Resultados finais"])
    with tab_pre:
        pre_view(filtered, pre_raw, goal if selected_inst == "Todas" else None, access, pre_anomalies)
    with tab_pos:
        post_view(filtered, pre_raw, access, qrecords)
    st.markdown('<div class="fbp-foot">PCH · FBP | 15 perguntas | Resultados recalculados a partir das respostas do Kobo. Não altera os dados originais.</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
