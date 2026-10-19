"""Dashboard FBP/PCH - pré e pós-teste KoboToolbox (sem CSV e sem escrever no Kobo)."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis import (
    ANSWER_KEY, N_QUESTIONS, TOPICS, build_analysis,
    institution_summary, question_summary,
)
from demo import demo_data
from kobo_client import (
    DEFAULT_BASE_URL, PRE_UID, POS_UID, KoboAPIError, fetch_submissions,
)

ROOT = Path(__file__).resolve().parent
QUESTIONS = json.loads((ROOT / "questionario.json").read_text(encoding="utf-8"))["questions"]
ACCENT = "#12659C"
DARK = "#163E60"
TEAL = "#0B8B83"
AMBER = "#CC7A18"
RED = "#C9565A"

st.set_page_config(page_title="PCH | Formação FBP — Avaliação", page_icon="📘", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
:root { --fbp-blue: #155D91; --fbp-dark: #173D5C; --fbp-light: #EFF6FB; }
.stApp { background: #f8fafc; }
.block-container { padding-top: 1.1rem; padding-bottom: 2.6rem; max-width: 1450px; }
h1 { font-size: 1.50rem !important; color: #173D5C !important; font-weight: 730 !important; }
h2 { font-size: 1.16rem !important; color: #173D5C !important; margin-top: .75rem !important; }
h3 { font-size: 1.02rem !important; color: #173D5C !important; }
[data-testid="stMetric"] { background: white; border: 1px solid #E0EAF2; border-radius: 12px; padding: 13px 14px; box-shadow: 0 1px 6px #1f496010; }
[data-testid="stMetricLabel"] { color: #61788C; }
[data-testid="stMetricValue"] { font-size: 1.66rem; font-weight: 740; color: #193E5C; }
[data-testid="stSidebar"] { background: #F2F6FA; border-right: 1px solid #DFE8F0; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top: 1.25rem; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: .52rem; }
[data-testid="stSidebar"] .stButton button { transition: background .12s ease, border-color .12s ease; }
/* Navegação por botões, sem círculos de radio, com página ativa em destaque. */
[data-testid="stSidebar"] [class*="st-key-nav_"] button {
    width: 100%; min-height: 2.48rem; text-align: left;
    justify-content: flex-start; border-radius: 10px;
    font-size: .88rem; font-weight: 580;
    padding: .48rem .82rem; box-shadow: none;
}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="secondary"] {
    background: transparent; border: 1px solid transparent; color: #334F65;
}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="secondary"]:hover {
    background: #E7F1F8; color: #125A8A; border-color: #DAE8F2;
}
[data-testid="stSidebar"] [class*="st-key-nav_"] button[kind="primary"] {
    background: #155D91; border: 1px solid #155D91; border-left: 4px solid #67C0D3;
    color: white; font-weight: 700;
}
[data-testid="stSidebar"] [class*="st-key-nav_"] button p { font-size: .88rem; }
.fbp-brand-title { color: #173D5C; font-weight: 760; letter-spacing: .01em; font-size: .93rem; line-height: 1.25; }
.fbp-brand-subtitle { color: #728496; font-size: .70rem; line-height: 1.35; margin-top: .2rem; }
.fbp-nav-title { font-size: .70rem; font-weight: 750; letter-spacing: .13em; color: #8293A2; margin-top: .6rem; margin-bottom: -.15rem; }
.fbp-small-separator { border-bottom: 1px solid #DFE8F0; margin: .5rem 0 .35rem; }
hr { border-color: #DFE8F0; }
.fbp-hero { background: linear-gradient(112deg,#173E60,#166C9F); padding: 18px 24px; color: white; border-radius: 13px; margin: 0 0 16px; }
.fbp-hero h1 { color: white !important; font-size: 1.45rem !important; margin: 0 0 5px !important; }
.fbp-hero p { font-size: .86rem; color: #E2F0F7; margin: 0; }
.fbp-section { color: #28658D; font-weight: 750; letter-spacing: .03em; margin: 4px 0 10px; }
.fbp-muted { font-size: .84rem; color: #64788A; }
@media (max-width: 1000px) { .fbp-hero { padding: 14px 17px; } .fbp-hero h1 { font-size: 1.25rem !important; } }
</style>
""", unsafe_allow_html=True)


def setting(name, default=""):
    try:
        val = st.secrets.get(name, None)
        if val is not None:
            return str(val)
    except (FileNotFoundError, RuntimeError, KeyError, AttributeError):
        pass
    return os.environ.get(name, default)


def basic_auth():
    password = setting("DASHBOARD_PASSWORD")
    if not password:
        return
    if st.session_state.get("login_ok", False):
        return
    st.title("🔒 Acesso ao painel FBP")
    with st.form("login"):
        attempted = st.text_input("Palavra-passe de acesso", type="password")
        submitted = st.form_submit_button("Entrar", type="primary")
    if submitted:
        if hmac.compare_digest(attempted, password):
            st.session_state["login_ok"] = True
            st.rerun()
        else:
            st.error("Palavra-passe incorreta.")
    st.stop()


def fmt_pct(value):
    return "—" if pd.isna(value) else f"{value:.1f}%".replace(".", ",")


def fmt_pp(value):
    return "—" if pd.isna(value) else f"{value:+.1f} pp".replace(".", ",")


def csv_bytes(frame):
    return frame.to_csv(index=False, sep=";").encode("utf-8-sig")


@st.cache_data(ttl=180, show_spinner=False)
def load_kobo(base_url: str, pre_uid: str, pos_uid: str, token_hash: str, _token: str):
    pre = fetch_submissions(base_url, pre_uid, _token)
    pos = fetch_submissions(base_url, pos_uid, _token)
    return pre, pos


def filter_dashboard(df, edition, institution, selected_status, text):
    if df.empty:
        return df.copy()
    result = df
    if edition != "Todas":
        result = result[result["Edição"] == edition]
    if institution != "Todas":
        result = result[result["Instituição"] == institution]
    if selected_status:
        result = result[result["Estado"].isin(selected_status)]
    if text.strip():
        result = result[result["Nome"].str.contains(text.strip(), case=False, regex=False, na=False)]
    return result.copy()


def caption_pair():
    st.caption("As médias de pré e pós usam **exatamente os mesmos participantes**, com ambos os testes completos e identidade confirmada. Assim, a evolução não é distorcida por quem ainda não fez o pós-teste.")


def metric_band(frame):
    n_pre = len(frame)
    pairs = frame[frame["Estado"] == "Pré e pós concluídos"] if n_pre else frame
    n_pos = len(pairs)
    coverage = round(100 * n_pos / n_pre, 1) if n_pre else 0
    pre_avg = pairs["Pré (%)"].mean() if n_pos else float("nan")
    pos_avg = pairs["Pós (%)"].mean() if n_pos else float("nan")
    evolution = pos_avg-pre_avg if n_pos else float("nan")
    cols = st.columns(6)
    values = [
        ("Participantes no pré", str(n_pre)),
        ("Pós-testes associados", str(n_pos)),
        ("Cobertura pós", fmt_pct(coverage)),
        ("Média pré (pares)", fmt_pct(pre_avg)),
        ("Média pós (pares)", fmt_pct(pos_avg)),
        ("Evolução média", fmt_pp(evolution)),
    ]
    for col,(name,value) in zip(cols,values):
        col.metric(name,value)
    return pairs


def section_title(text):
    st.markdown(f'<div class="fbp-section">{text}</div>', unsafe_allow_html=True)


def chart_layout(fig, height=350):
    fig.update_layout(
        height=height, margin=dict(l=5,r=5,t=10,b=10),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", size=12, color="#345165"),
        legend=dict(orientation="h",y=1.09,x=0,title_text=""),
    )
    fig.update_yaxes(gridcolor="#e3edf3",zeroline=False)
    return fig


def overview(frame, analyses):
    st.subheader("Visão geral da formação")
    pairs = metric_band(frame)
    caption_pair()
    st.divider()
    left, right = st.columns([1.3, 1], gap="large")
    with left:
        section_title("RESULTADOS POR INSTITUIÇÃO")
        summary = institution_summary(frame)
        usable = summary.dropna(subset=["Pré pares (%)","Pós pares (%)"])
        if usable.empty:
            st.info("Ainda não existem pares completos para comparar médias por instituição.")
        else:
            melted = usable.melt(id_vars="Instituição", value_vars=["Pré pares (%)", "Pós pares (%)"], var_name="Teste",value_name="Média (%)")
            fig = px.bar(melted, x="Instituição", y="Média (%)", color="Teste",barmode="group",
                         color_discrete_map={"Pré pares (%)":ACCENT,"Pós pares (%)":TEAL},text_auto=".1f")
            fig.update_xaxes(tickangle=-15,title_text="")
            fig.update_yaxes(range=[0,105])
            st.plotly_chart(chart_layout(fig), use_container_width=True)
        st.dataframe(summary, use_container_width=True, hide_index=True)
    with right:
        section_title("SITUAÇÃO DOS PARTICIPANTES")
        counts = frame["Estado"].value_counts().reset_index() if not frame.empty else pd.DataFrame(columns=["Estado","count"])
        if not counts.empty:
            counts.columns = ["Estado", "N"]
            fig = px.pie(counts,names="Estado",values="N",hole=.64,
                         color_discrete_sequence=[TEAL,AMBER,ACCENT,RED,"#9aadc0"])
            fig.update_traces(textposition="outside",textinfo="percent+label")
            st.plotly_chart(chart_layout(fig,height=340),use_container_width=True)
        else:
            st.info("Sem registos para os filtros selecionados.")
        pending = frame[frame["Estado"] != "Pré e pós concluídos"] if not frame.empty else frame
        st.caption(f"{len(pending)} participante(s) sem um par válido para a comparação.")
    st.divider()
    section_title("EVOLUÇÃO DOS PARTICIPANTES COM AMBOS OS TESTES")
    if len(pairs):
        dots = pairs[["Nome","Pré (%)","Pós (%)"]].copy()
        fig = go.Figure()
        show_labels = len(dots) <= 10
        fig.add_trace(go.Scatter(x=dots["Pré (%)"],y=dots["Pós (%)"],
                   mode="markers+text" if show_labels else "markers",
                   text=dots["Nome"] if show_labels else None, textposition="top center",
                   customdata=dots["Nome"], name="Participantes",
                   marker=dict(color=ACCENT,size=12,opacity=.84),
                   hovertemplate="%{customdata}<br>Pré: %{x:.1f}%<br>Pós: %{y:.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(x=[0,100],y=[0,100],mode="lines",name="Sem evolução",
                   line=dict(color="#9aadb9",width=1,dash="dot"),showlegend=False))
        fig.update_layout(xaxis=dict(title="Pré-teste (%)",range=[-4,104]),yaxis=dict(title="Pós-teste (%)",range=[-4,104]))
        st.plotly_chart(chart_layout(fig,390),use_container_width=True)
        st.caption("Pontos acima da linha diagonal indicam melhoria; abaixo, diminuição. A escala é de 0 a 100%.")
    else:
        st.info("Quando os participantes concluírem ambos os testes, a comparação individual aparece aqui.")


def participants_page(frame):
    st.subheader("Seguimento individual")
    if frame.empty:
        st.info("Sem registos para os filtros escolhidos.")
        return
    visible=["Nome","Instituição","Função","Edição","Estado","Acertos pré","Acertos pós","Pré (%)","Pós (%)","Evolução (pp)","Data pré","Data pós"]
    st.dataframe(frame[visible],hide_index=True,use_container_width=True,height=400)
    st.download_button("⬇️ Exportar participantes filtrados (CSV)",data=csv_bytes(frame[visible]),
                       file_name="FBP_participantes.csv",mime="text/csv")
    st.divider()
    st.markdown("#### Ficha individual")
    choices = frame.sort_values(["Nome","Instituição"]).apply(lambda r: f"{r['Nome']} · {r['Instituição']} · {r['participante_id'][-8:]}",axis=1).tolist()
    chosen = st.selectbox("Selecionar participante",options=list(range(len(choices))),format_func=lambda x:choices[x])
    row = frame.sort_values(["Nome","Instituição"]).iloc[chosen]
    st.markdown(f"**Nome:** {row['Nome']}  \n**Instituição:** {row['Instituição']}  \n**Função:** {row['Função']}  \n**Edição:** {row['Edição']}  \n**Estado:** {row['Estado']}")
    c1,c2,c3 = st.columns(3)
    c1.metric("Pré-teste",fmt_pct(row["Pré (%)"]))
    c2.metric("Pós-teste",fmt_pct(row["Pós (%)"]))
    c3.metric("Evolução",fmt_pp(row["Evolução (pp)"]))
    if row["N.º pós-testes"] > 1 or row["N.º pré-testes"] > 1:
        st.warning("Foram encontrados registos repetidos com este identificador. A análise usa a primeira submissão completa e mantém os restantes para auditoria.")


def learning_page(frame, qdf):
    st.subheader("Aprendizagem por pergunta e competência")
    if qdf.empty:
        st.info("São necessários participantes com os dois testes concluídos para comparar as respostas por pergunta.")
        return
    summary = question_summary(qdf, QUESTIONS)
    box1, box2 = st.columns([1.5,1],gap="large")
    with box1:
        section_title("PERCENTAGEM DE RESPOSTAS CORRETAS — 15 PERGUNTAS")
        m = summary.melt(id_vars="Pergunta",value_vars=["Pré (%)","Pós (%)"],var_name="Avaliação",value_name="Corretas (%)")
        fig=px.bar(m,x="Pergunta",y="Corretas (%)",color="Avaliação",barmode="group",
                   color_discrete_map={"Pré (%)":ACCENT,"Pós (%)":TEAL})
        fig.update_yaxes(range=[0,100]);fig.update_xaxes(title_text="")
        st.plotly_chart(chart_layout(fig,360),use_container_width=True)
    with box2:
        section_title("EVOLUÇÃO POR COMPETÊNCIA")
        topics=[]
        for topic,ns in TOPICS.items():
            k=qdf[qdf["Pergunta"].isin(ns)]
            if k.empty:continue
            b=round(k["Pré correto"].mean()*100,1);a=round(k["Pós correto"].mean()*100,1)
            topics.append({"Competência":topic,"Pré (%)":b,"Pós (%)":a,"Evolução (pp)":round(a-b,1)})
        tdf=pd.DataFrame(topics)
        st.dataframe(tdf,hide_index=True,use_container_width=True,height=350)
    section_title("DETALHE POR PERGUNTA")
    st.dataframe(summary[["Pergunta","Tema","Enunciado","N","Pré (%)","Pós (%)","Evolução (pp)"]],
                 hide_index=True,use_container_width=True,height=400)
    st.download_button("⬇️ Exportar resultados por pergunta (CSV)",data=csv_bytes(summary),file_name="FBP_perguntas.csv",mime="text/csv")
    index=st.selectbox("Analisar uma pergunta",options=list(range(1,16)),format_func=lambda n:f"Pergunta {n:02d} — {QUESTIONS[n-1]['prompt'][:90]}")
    q=QUESTIONS[index-1]
    st.markdown(f"**{q['prompt']}**")
    ans_letters={"a":"A", "b":"B","c":"C","d":"D"}
    for code,txt in q["options"].items():
        mark="✅" if code==ANSWER_KEY[index] else ""
        st.write(f"{mark} **{ans_letters[code]}.** {txt}")
    small=qdf[qdf["Pergunta"]==index]
    c1,c2,c3=st.columns(3)
    c1.metric("Corretas no pré",fmt_pct(small["Pré correto"].mean()*100))
    c2.metric("Corretas no pós",fmt_pct(small["Pós correto"].mean()*100))
    c3.metric("Evolução",fmt_pp((small["Pós correto"].mean()-small["Pré correto"].mean())*100))
    st.caption("A chave de respostas provém da grelha de correção do documento original. O acesso ao painel deve ser reservado à equipa técnica enquanto decorrerem avaliações.")


def quality_page(analysis, frame):
    st.subheader("Qualidade e consistência dos dados")
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Submissões pré (bruto)",str(analysis["raw_pre_count"]))
    c2.metric("Submissões pós (bruto)",str(analysis["raw_pos_count"]))
    c3.metric("Pós sem pré correspondente",str(analysis["orphan_post_count"]))
    c4.metric("Ocorrências de auditoria",str(len(analysis["anomalies"])))
    st.caption("Participantes = identificadores únicos no pré-teste. Submissões = formulários recebidos. Podem divergir por duplicados, dados incompletos ou registos órfãos.")
    st.markdown("#### Problemas detetados")
    anomalies = analysis["anomalies"]
    if anomalies.empty:
        st.success("Não foram encontrados os problemas abrangidos pelas verificações automáticas.")
    else:
        st.dataframe(anomalies,hide_index=True,use_container_width=True)
        st.download_button("⬇️ Exportar auditoria (CSV)",csv_bytes(anomalies),"FBP_auditoria.csv","text/csv")
    st.markdown("#### Participantes a verificar")
    if not frame.empty:
        subset=frame[(frame["Estado"]!="Pré e pós concluídos") | (frame["N.º pré-testes"]>1) | (frame["N.º pós-testes"]>1) | frame["Inconsistência nota pré"] | frame["Inconsistência nota pós"]]
        if subset.empty:
            st.success("Sem casos individuais pendentes nos filtros atuais.")
        else:
            st.dataframe(subset[["Nome","Instituição","Estado","N.º pré-testes","N.º pós-testes","Inconsistência nota pré","Inconsistência nota pós"]],use_container_width=True,hide_index=True)
            st.download_button("⬇️ Exportar pendências (CSV)",csv_bytes(subset),"FBP_pendentes.csv","text/csv")
    with st.expander("Como são calculadas e ligadas as avaliações?"):
        st.markdown("""
- A ligação utiliza **`participante_id`**, criado no pré-teste e recuperado no pós-teste. Não é feita correspondência pelo nome.
- São consideradas **15 respostas obrigatórias**. Uma submissão com menos respostas não entra nas médias de aprendizagem.
- Para um mesmo identificador, mantém-se a **primeira submissão completa**; repetição é assinalada para auditoria.
- Só conta como pós-teste válido uma submissão completa com **`confirma_identidade = sim`**.
- O sistema recalcula os acertos diretamente a partir de **`q01`…`q15`**, comparando-os com a grelha do formador. Diferenças com `total_acertos` guardado no Kobo ficam sinalizadas.
- Evolução em pontos percentuais = percentagem do pós-teste menos a do pré-teste. Não confundir com crescimento percentual relativo.
- Os dados são consultados apenas para leitura; **o dashboard nunca altera os registos no Kobo**.
""")


def change_page(name):
    st.session_state["fbp_page"] = name


def main():
    basic_auth()
    base=setting("KOBO_BASE_URL",DEFAULT_BASE_URL)
    pre_uid=setting("KOBO_PRE_UID",PRE_UID)
    pos_uid=setting("KOBO_POS_UID",POS_UID)
    token=setting("KOBO_TOKEN")
    if "fbp_page" not in st.session_state:
        st.session_state["fbp_page"] = "Visão geral"

    with st.sidebar:
        logo=ROOT/"assets"/"logo_pch.png"
        brand_logo, brand_text = st.columns([.85, 2.35], gap="small", vertical_alignment="center")
        with brand_logo:
            if logo.exists():
                st.image(str(logo), width=68)
        with brand_text:
            st.markdown('<div class="fbp-brand-title">PCH · Formação FBP</div>'
                        '<div class="fbp-brand-subtitle">Monitorização da aprendizagem</div>', unsafe_allow_html=True)
        st.markdown('<div class="fbp-small-separator"></div><div class="fbp-nav-title">NAVEGAÇÃO</div>', unsafe_allow_html=True)
        nav_items = [
            ("Visão geral", "📊  Visão geral", "nav_visao"),
            ("Participantes", "👥  Participantes", "nav_participantes"),
            ("Aprendizagem", "📈  Aprendizagem", "nav_aprendizagem"),
            ("Qualidade dos dados", "🛡️  Qualidade dos dados", "nav_qualidade"),
        ]
        for page_name, label, key in nav_items:
            st.button(label, key=key,
                      type="primary" if st.session_state["fbp_page"] == page_name else "secondary",
                      on_click=change_page, args=(page_name,), use_container_width=True)
        page=st.session_state["fbp_page"]
        st.markdown('<div class="fbp-small-separator"></div><div class="fbp-nav-title">DADOS</div>', unsafe_allow_html=True)
        if st.button("↻  Atualizar Kobo", key="refresh_kobo", use_container_width=True):
            load_kobo.clear()
            st.rerun()
        st.caption("Atualização automática a cada 3 minutos.")
        with st.expander("⚙️ Ferramentas", expanded=False):
            demo=st.toggle("Modo demonstração", value=False, help="Mostra dados fictícios para experimentar o painel.")
            if demo:
                st.caption("Os valores apresentados não são dados reais.")
        if not token and not demo:
            st.caption("⚠️ Falta configurar KOBO_TOKEN em Secrets.")

    st.markdown('<div class="fbp-hero"><h1>Financiamento Baseado em Performance</h1>'
                '<p>Projeto de Capital Humano · Avaliação da Formação · Pré-teste e Pós-teste</p></div>',
                unsafe_allow_html=True)

    if demo:
        raw_pre,raw_pos=demo_data()
        st.warning("MODO DEMONSTRAÇÃO — Todos os dados apresentados são fictícios e não provêm do teu servidor Kobo.")
    else:
        if not token:
            st.warning("É necessário configurar a credencial Kobo para apresentar os resultados reais.")
            st.markdown("**Ativar a ligação**: no Streamlit Cloud, abre **Manage app → Settings → Secrets**, insere a configuração abaixo e guarda.")
            st.code('KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"\n'
                    'KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"\n'
                    'KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"\n'
                    'KOBO_TOKEN = "INSERIR_TOKEN_PRIVADO"', language="toml")
            st.info("O token não deve ser introduzido no app.py nem publicado no GitHub. Podes usar Ferramentas → Modo demonstração para visualizar o painel sem credenciais.")
            st.stop()
        digest=hashlib.sha256(token.encode("utf8")).hexdigest()
        try:
            with st.spinner("A consultar os pré e pós-testes na API Kobo…"):
                raw_pre,raw_pos=load_kobo(base,pre_uid,pos_uid,digest,token)
        except KoboAPIError as exc:
            st.error(f"Não foi possível carregar os dados: {exc}")
            st.info("Confirma domínio, permissões de leitura dos dois formulários e conectividade. Não é necessário qualquer ficheiro CSV.")
            st.stop()
    analysis=build_analysis(raw_pre,raw_pos)
    full=analysis["participants"]

    if not full.empty:
        with st.sidebar:
            st.markdown("#### Filtros")
            editions=["Todas"]+sorted(full["Edição"].dropna().unique().tolist())
            edition=st.selectbox("Edição",editions)
            institution=st.selectbox("Instituição",["Todas"]+sorted(full["Instituição"].dropna().unique().tolist()))
            status=st.multiselect("Estado",sorted(full["Estado"].dropna().unique().tolist()),default=[])
            lookup=st.text_input("Pesquisar nome",placeholder="Nome do participante")
        filtered=filter_dashboard(full,edition,institution,status,lookup)
    else:
        filtered=full.copy()
        st.info("Ainda não há participantes com identificador único no pré-teste.")

    allowed=set(filtered["participante_id"].tolist()) if not filtered.empty else set()
    qdf=analysis["questions"]
    qdf=qdf[qdf["participante_id"].isin(allowed)] if not qdf.empty else qdf
    if page=="Visão geral":overview(filtered,analysis)
    elif page=="Participantes":participants_page(filtered)
    elif page=="Aprendizagem":learning_page(filtered,qdf)
    else:quality_page(analysis,filtered)

    st.divider()
    source_label="Dados demonstrativos" if demo else "Fonte: KoboToolbox PCH (API v2)"
    st.caption(f"{source_label} · Edição 0001 ou outras edições, conforme os registos · 15 perguntas · Consulta às {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC · Desenvolvido para o acompanhamento da formação FBP")

if __name__=="__main__":
    main()
