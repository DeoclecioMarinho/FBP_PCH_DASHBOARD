"""PCH / FBP — painel operacional, analítico e de qualidade dos dados.

Três páginas. Dados lidos diretamente do Kobo. Exclusão apenas com autenticação
administrativa, revalidação dos dados originais e confirmação individual.
"""
import hashlib
import hmac
import html
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis import build_analysis, question_summary, institution_summary, field, score_record
from monitor import pre_per_question, topic_performance, suspected_duplicate_names
from quality import audit_records, can_delete_now, backup_json
from kobo_client import (DEFAULT_BASE_URL, PRE_UID, POS_UID,
                         KoboAPIError, fetch_submissions, delete_submission)

ROOT = Path(__file__).resolve().parent
QUESTIONS = json.loads((ROOT/'questionario.json').read_text(encoding='utf8'))['questions']
NAVY='#172E43'; BLUE='#1E617E'; CYAN='#1587AD'; GREEN='#16836A'; ORANGE='#B67937'; RED='#B94D50'; GREY='#708294'

st.set_page_config(page_title='PCH | Avaliação FBP', page_icon='📘', layout='wide', initial_sidebar_state='expanded')
st.markdown('''
<style>
:root {--navy:#172E43;--blue:#1E617E;--grey:#677E90;}
.stApp {background:#F7F9FC; color:#23394B;}
.block-container {max-width:1260px;padding-top:1.05rem;padding-bottom:2.7rem;}
[data-testid="stSidebar"] {background:#FFFFFF;border-right:1px solid #E3EAF1;}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:1.3rem;}
[data-testid="stSidebar"] .stButton button {width:100%;min-height:45px;text-align:left;justify-content:flex-start;padding-left:14px;border-radius:9px;border:0;font-weight:580;box-shadow:none;}
[data-testid="stSidebar"] button[kind="primary"] {background:#E7F1F7;color:#174D70!important;border-left:3px solid #24769B;border-radius:7px;}
[data-testid="stSidebar"] button[kind="secondary"] {background:transparent;color:#526C7E;}
[data-testid="stSidebar"] button[kind="secondary"]:hover {background:#F0F5F8;color:#24485E;}
h1 {font-weight:735!important;font-size:1.68rem!important;color:#203B52!important;letter-spacing:-.023em;margin-bottom:.12rem!important;}
h2 {font-size:1.16rem!important;font-weight:700!important;color:#203B52!important;padding-top:.3rem!important;}
h3 {font-size:1.00rem!important;font-weight:680!important;color:#284459!important;}
[data-testid="stSelectbox"] label,[data-testid="stTextInput"] label {font-size:.78rem!important;font-weight:590!important;color:#687F90!important;}
[data-testid="stExpander"] {border:1px solid #E1E8EF!important;background:#fff;border-radius:9px;}
[data-testid="stDownloadButton"] button {border-color:#D7E2EB;color:#23536C;border-radius:7px;}
.brand-title {font-size:1.03rem;font-weight:790;color:#1B3B52;line-height:1.25;}
.brand-sub {font-size:.72rem;color:#7890A0;margin-top:3px;}
.sidebar-head {font-size:.64rem;font-weight:790;letter-spacing:.12em;color:#8CA0AF;margin:15px 0 8px;}
.hero-sub {font-size:.85rem;color:#718396;margin:0 0 1.25rem;}
.eyebrow {font-size:.69rem;text-transform:uppercase;letter-spacing:.11em;font-weight:750;color:#7C91A2;}
.kpi-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;margin:.6rem 0 1.1rem;}
.kpi {background:#FFFFFF;border:1px solid #E4EAF0;border-radius:11px;padding:17px 18px 15px;min-width:0;}
.kpi .klabel {font-size:.78rem;color:#708493;font-weight:560;line-height:1.35;}
.kpi .kvalue {font-size:1.8rem;font-weight:780;line-height:1.26;color:#173449;margin-top:7px;letter-spacing:-.02em;}
.kpi .ksub {font-size:.73rem;color:#8A99A4;margin-top:6px;line-height:1.35;}
.section-head {display:flex;align-items:center;justify-content:space-between;margin:.9rem 0 .7rem;gap:15px;}
.section-head .section-title {font-size:1.03rem;font-weight:740;color:#263F52;}
.section-head .section-hint {font-size:.77rem;color:#7D8E9C;}
.fbp-table-wrap {width:100%;border:1px solid #E2E9EF;border-radius:10px;background:#fff;overflow:hidden;margin:6px 0;}
table.fbp-table {width:100%;table-layout:fixed;border-collapse:collapse;font-size:.81rem;}
table.fbp-table th {text-align:left;color:#708391;font-size:.71rem;font-weight:720;background:#F5F8FA;padding:11px 11px;border-bottom:1px solid #E4EBF0;overflow-wrap:anywhere;}
table.fbp-table td {vertical-align:middle;padding:11px;border-bottom:1px solid #ECF1F5;color:#30485A;overflow-wrap:anywhere;word-break:normal;line-height:1.38;}
table.fbp-table tr:last-child td {border-bottom:none;}
table.fbp-table tr:nth-child(2n) {background:#FBFCFD;}
.mini-tag {display:inline-block;border-radius:5px;padding:3px 7px;background:#EAF3F6;color:#285B74;font-weight:630;font-size:.73rem;}
.muted {color:#718495;font-size:.79rem;}
.notice {padding:12px 16px;background:#F0F6F9;border-left:3px solid #4C91B2;color:#315D74;border-radius:6px;font-size:.85rem;line-height:1.52;}
.alert {padding:12px 16px;background:#FEF6EE;border-left:3px solid #D19A51;color:#865927;border-radius:6px;font-size:.85rem;line-height:1.52;}
.foot {font-size:.74rem;color:#8FA0AD;padding-top:1.4rem;border-top:1px solid #E5ECF1;margin-top:2rem;}
@media(max-width:900px) {.kpi-grid {grid-template-columns:repeat(2,minmax(0,1fr));} table.fbp-table {font-size:.73rem;}table.fbp-table td,table.fbp-table th{padding:8px 6px;}}
@media(max-width:560px) {.kpi-grid {grid-template-columns:1fr 1fr;gap:8px;}.kpi{padding:12px}.kpi .kvalue{font-size:1.45rem}.block-container{padding-left:.7rem;padding-right:.7rem}}
</style>
''', unsafe_allow_html=True)


def setting(key, fallback=''):
    try:
        val=st.secrets.get(key)
        if val is not None: return str(val)
    except (FileNotFoundError, KeyError, RuntimeError, AttributeError):
        pass
    return os.environ.get(key, fallback)


def secure_access():
    pw=setting('DASHBOARD_PASSWORD')
    if not pw: return False
    if st.session_state.get('access') is True: return True
    st.title('Acesso ao acompanhamento FBP')
    st.caption('Introduza a palavra-passe para consultar os resultados da formação.')
    with st.form('entrar'):
        attempt=st.text_input('Palavra-passe',type='password')
        ok=st.form_submit_button('Entrar',type='primary')
    if ok:
        if hmac.compare_digest(attempt,pw):
            st.session_state['access']=True;st.rerun()
        else:st.error('Palavra-passe incorreta.')
    st.stop()


def h(v): return html.escape(str(v if v is not None and not (isinstance(v,float) and math.isnan(v)) else '—'),quote=True)
def pct(v): return '—' if v is None or pd.isna(v) else f'{v:.1f}%'.replace('.',',')
def diff(v): return '—' if v is None or pd.isna(v) else f'{v:+.1f} pp'.replace('.',',')
def csv(df): return df.to_csv(index=False,sep=';').encode('utf-8-sig')

def cards(items):
    parts=['<div class="kpi-grid">']
    for label, value, sub in items:
        parts.append(f'<div class="kpi"><div class="klabel">{h(label)}</div>'
                     f'<div class="kvalue">{h(value)}</div><div class="ksub">{h(sub)}</div></div>')
    parts.append('</div>')
    st.markdown(''.join(parts),unsafe_allow_html=True)


def heading(title, sub=''):
    st.markdown(f'<div class="section-head"><span class="section-title">{h(title)}</span>'
                f'<span class="section-hint">{h(sub)}</span></div>',unsafe_allow_html=True)


def clean_table(df, columns, key, size=8, widths=None):
    """HTML table with automatic wrapping and pagination. Never nested scrollbars."""
    if df.empty:
        st.caption('Sem registos para apresentar.');return
    work=df.reset_index(drop=True)
    pages=max(1,math.ceil(len(work)/size))
    old=st.session_state.get(f'{key}_page',1)
    if old>pages:st.session_state[f'{key}_page']=pages
    page=st.session_state.get(f'{key}_page',1)
    visible=work.iloc[(page-1)*size:page*size]
    width_attrs=(widths or [None]*len(columns))
    head=''.join(f'<th style="width:{width_attrs[i]}%">{h(label)}</th>' if width_attrs[i] else f'<th>{h(label)}</th>' for i,(label,_) in enumerate(columns))
    body=''.join('<tr>'+''.join(f'<td>{h(r.get(col, ""))}</td>' for _,col in columns)+'</tr>' for _,r in visible.iterrows())
    st.markdown(f'<div class="fbp-table-wrap"><table class="fbp-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',unsafe_allow_html=True)
    if pages>1:
        a,b,c=st.columns([1,2,1],vertical_alignment='center')
        with a:
            if st.button('← Anterior',key=f'{key}_prev',disabled=page==1):
                st.session_state[f'{key}_page']=page-1;st.rerun()
        with b:st.caption(f'Página {page} de {pages} · {len(work)} registos · {size} por página')
        with c:
            if st.button('Seguinte →',key=f'{key}_next',disabled=page==pages):
                st.session_state[f'{key}_page']=page+1;st.rerun()
    else: st.caption(f'{len(work)} registos')


def bar_chart(df,label_key,value_key,max_rows=5,palette=BLUE):
    data=df.head(max_rows).iloc[::-1]
    values=data[value_key].astype(float).fillna(0)
    color=[RED if n<50 else ORANGE if n<70 else palette for n in values]
    fig=go.Figure(go.Bar(x=values,y=data[label_key],orientation='h',marker_color=color,
          text=[f'{v:.0f}%' for v in values],textposition='outside',cliponaxis=False,
          hovertemplate='%{y}: %{x:.1f}%<extra></extra>'))
    fig.update_layout(height=max(240,58*len(data)+35),margin=dict(t=10,b=18,l=5,r=35),
                      xaxis=dict(range=[0,111],dtick=25,gridcolor='#E7EDF2',title=None,zeroline=False),
                      yaxis=dict(title=None,automargin=True),font=dict(color=NAVY,size=12),
                      showlegend=False,paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})


def side_nav():
    with st.sidebar:
        a,b=st.columns([.46,2],vertical_alignment='center',gap='small')
        with a: st.image(str(ROOT/'assets/logo_pch.png'),width=42)
        with b:
            st.markdown('<div class="brand-title">PCH · Formação FBP</div>'
                        '<div class="brand-sub">Avaliação e acompanhamento</div>',unsafe_allow_html=True)
        st.divider()
        st.markdown('<div class="sidebar-head">NAVEGAÇÃO</div>',unsafe_allow_html=True)
        pages=[('Dashboard','▦  Dashboard'),('Aprendizagem','◫  Aprendizagem'),('Qualidade dos dados','✓  Qualidade dos dados')]
        if 'page' not in st.session_state:st.session_state['page']='Dashboard'
        for page,title in pages:
            if st.button(title,key=f'nav_{page}',type='primary' if st.session_state.page==page else 'secondary',use_container_width=True):
                st.session_state.page=page;st.rerun()
        st.divider()
        if st.button('↻  Atualizar Kobo',use_container_width=True,key='reload'):
            fetch_both.clear();st.rerun()
        st.caption('Atualização automática: a cada 2 minutos.')
    return st.session_state.page


@st.cache_data(ttl=120,show_spinner=False)
def fetch_both(base,pre_uid,pos_uid,digest,_token):
    return (fetch_submissions(base,pre_uid,_token),fetch_submissions(base,pos_uid,_token),
            datetime.now(timezone.utc).strftime('%d/%m/%Y · %H:%M UTC'))


def selection_panel(df):
    with st.sidebar:
        st.markdown('<div class="sidebar-head">FILTROS</div>',unsafe_allow_html=True)
        if df.empty:
            st.caption('Sem participantes.');return 'Todas','Todas'
        editions=sorted(df['Edição'].dropna().unique())
        serial=st.session_state.get('reset_serial',0)
        edition=st.selectbox('Edição da formação',['Todas',*editions],key=f'edition_filter_{serial}')
        inst=sorted(df['Instituição'].dropna().unique())
        institution=st.selectbox('Instituição',['Todas',*inst],key=f'inst_filter_{serial}')
        if st.button('Limpar filtros',key='reset_filters',use_container_width=True):
            st.session_state['reset_serial']=serial+1
            st.rerun()
        return edition,institution


def view_dashboard(df, pre_raw, raw_pre_count, raw_pos_count, qpre, access):
    st.title('Dashboard')
    st.markdown('<div class="hero-sub">Visão operacional da formação · dados atualizados a partir do Kobo</div>',unsafe_allow_html=True)
    valid=df[df['Pré (%)'].notna()] if not df.empty else df
    paired=df[df['Estado']=='Pré e pós concluídos'] if not df.empty else df
    npre=len(valid);npost=len(paired);pending=npre-npost
    pre_mean=valid['Pré (%)'].mean() if npre else None
    gain=paired['Evolução (pp)'].mean() if npost else None
    cards([('Participantes com pré-teste',npre,'Registos únicos e completos'),
           ('Pós-testes associados',npost,f'{pending} ainda sem pós-teste válido'),
           ('Média do pré-teste',pct(pre_mean),'Conhecimentos iniciais'),
           ('Evolução média',diff(gain) if npost else '—','Apenas participantes com ambos os testes')])
    left,right=st.columns([1.18,.9],gap='large')
    with left:
        heading('Conteúdos que precisam de reforço','Pré-teste · 5 perguntas')
        if npre and not qpre.empty:
            weakest=qpre.sort_values(['Acerto (%)','Número']).head(5)
            bar_chart(weakest,'Pergunta','Acerto (%)')
            with st.expander('Ver os enunciados destas perguntas'):
                for _,r in weakest.iterrows():
                    st.markdown(f"**{r['Pergunta']} · {pct(r['Acerto (%)'])}** — {r['Enunciado']}")
        else: st.info('Os resultados aparecerão à medida que os pré-testes forem submetidos.')
    with right:
        heading('Situação da formação','Baseada nos testes submetidos')
        if npre:
            rate=100*npost/npre
            st.markdown(f'<div class="notice"><b>{npost} de {npre}</b> participantes com pré-teste válido '
                        f'já têm pós-teste associado (<b>{rate:.0f}%</b>).</div>',unsafe_allow_html=True)
            st.progress(min(1,npost/npre))
            if npre<5:
                st.warning('Amostra inicial reduzida. Interprete as dificuldades com prudência.')
            elif not qpre.empty:
                weak=qpre[qpre['Acerto (%)']<50]
                if len(weak):
                    st.warning(f'{len(weak)} pergunta(s) com menos de 50% de acertos no pré-teste. Ver Aprendizagem.')
                else: st.success('Nenhuma pergunta abaixo de 50% de acertos no pré-teste.')
        else:st.info('A aguardar os primeiros pré-testes.')
        st.caption(f'Submissões recebidas: {raw_pre_count} pré e {raw_pos_count} pós (inclui eventuais repetições).')
        if npost:
            st.markdown('**Comparação entre os mesmos participantes**')
            pre_p=paired['Pré (%)'].mean();pos_p=paired['Pós (%)'].mean()
            st.write(f'Pré-teste: **{pct(pre_p)}** → Pós-teste: **{pct(pos_p)}**')
        st.caption('O sistema não assume uma meta fixa de participantes.')
    heading('Acompanhamento dos participantes','Até 8 linhas por página')
    if access and not df.empty:
        query=st.text_input('Pesquisar por nome',placeholder='Pesquisar participante…',label_visibility='collapsed',key='dash_q')
        part=df[df['Nome'].str.contains(query,case=False,regex=False,na=False)] if query else df
        display=part[['Nome','Instituição','Pré (%)','Pós (%)','Evolução (pp)','Estado']].copy()
        for column in ['Pré (%)','Pós (%)']:display[column]=display[column].map(pct)
        display['Evolução (pp)']=display['Evolução (pp)'].map(diff)
        clean_table(display.sort_values('Nome'),[('Participante','Nome'),('Instituição','Instituição'),('Pré','Pré (%)'),('Pós','Pós (%)'),('Evolução','Evolução (pp)'),('Estado','Estado')],key='main_part',widths=[23,22,10,10,12,23])
        st.download_button('Exportar participantes (CSV)',data=csv(part.drop(columns=['participante_id'],errors='ignore')),
                           file_name='FBP_participantes.csv',mime='text/csv')
    elif not access: st.info('Para consultar nomes e exportar resultados, configura DASHBOARD_PASSWORD nas Secrets.')
    else:st.caption('Ainda não existem participantes.')


def view_aprendizagem(df,qpre,paired_questions,access):
    st.title('Aprendizagem')
    st.markdown('<div class="hero-sub">Diagnóstico inicial, evolução das competências e resultados por instituição</div>',unsafe_allow_html=True)
    valid=df[df['Pré (%)'].notna()] if not df.empty else df
    paired=df[df['Estado']=='Pré e pós concluídos'] if not df.empty else df
    npre=len(valid);npair=len(paired)
    cards([('Pré-testes válidos',npre,'Base do diagnóstico inicial'),
           ('Média inicial',pct(valid['Pré (%)'].mean()) if npre else '—','Todos os pré-testes válidos'),
           ('Pares pré/pós',npair,'Participantes comparáveis'),
           ('Ganho médio',diff(paired['Evolução (pp)'].mean()) if npair else '—','Diferença em pontos percentuais')])
    if npre and not qpre.empty:
        heading('Domínio por competência','Percentagem de respostas corretas · pré-teste')
        topics=topic_performance(qpre)
        if not topics.empty:
            bar_chart(topics.sort_values('Acerto (%)'),'Tema','Acerto (%)',max_rows=4,palette=GREEN)
        heading('Análise por pergunta','15 perguntas · prioridade às dificuldades')
        qs=qpre.sort_values(['Acerto (%)','Número']).copy()
        compact=qs[['Pergunta','Tema','Acertos','N','Acerto (%)']].copy()
        compact['Acerto (%)']=compact['Acerto (%)'].map(pct)
        clean_table(compact,[('Pergunta','Pergunta'),('Tema','Tema'),('Certas','Acertos'),('Respostas','N'),('Taxa de acerto','Acerto (%)')],key='pre_questions',size=8,widths=[12,41,13,14,20])
        selected=st.selectbox('Ler o enunciado completo',qs['Pergunta'].tolist(),key='question_detail')
        qrow=qs[qs['Pergunta']==selected].iloc[0]
        st.markdown(f'<div class="notice"><b>{h(selected)}</b> — {h(qrow["Enunciado"])}<br>'
                    f'Taxa de acerto no pré-teste: <b>{h(pct(qrow["Acerto (%)"]))}</b>.</div>',unsafe_allow_html=True)
        st.download_button('Exportar análise por pergunta',csv(qpre),'FBP_aprendizagem_perguntas.csv',mime='text/csv')
    if npair:
        heading('Evolução após a formação','Comparação apenas entre os mesmos participantes')
        pre_pct=paired['Pré (%)'].mean();pos_pct=paired['Pós (%)'].mean()
        a,b=st.columns([.75,1.25],gap='large')
        with a:
            fig=go.Figure(go.Bar(x=['Pré-teste','Pós-teste'],y=[pre_pct,pos_pct],marker_color=[BLUE,GREEN],
                text=[pct(pre_pct),pct(pos_pct)],textposition='outside'))
            fig.update_layout(height=280,margin=dict(t=25,b=10,l=8,r=8),showlegend=False,
                              yaxis=dict(range=[0,110],gridcolor='#E8EDF2',title='% de acertos'),
                              paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with b:
            if not paired_questions.empty:
                ques=question_summary(paired_questions,QUESTIONS)
                comp=ques[['Pergunta','N','Pré (%)','Pós (%)','Evolução (pp)']].copy()
                comp['Pré (%)']=comp['Pré (%)'].map(pct);comp['Pós (%)']=comp['Pós (%)'].map(pct)
                comp['Evolução (pp)']=comp['Evolução (pp)'].map(diff)
                clean_table(comp,[('Pergunta','Pergunta'),('N pares','N'),('Pré','Pré (%)'),('Pós','Pós (%)'),('Ganho','Evolução (pp)')],key='post_ques',size=6,widths=[20,17,20,20,23])
                st.download_button('Exportar evolução por pergunta',csv(ques),'FBP_evolucao_por_pergunta.csv',mime='text/csv')
    else:
        st.info('A comparação pré/pós será apresentada quando existirem participantes com ambas as avaliações válidas.')
    if not df.empty:
        heading('Resultados por instituição','Médias dos pares válidos, sem misturar amostras')
        inst=institution_summary(df)
        short=inst[['Instituição','Pré-testes','Pós-testes','Pré pares (%)','Pós pares (%)','Evolução (pp)']].copy()
        for col in ['Pré pares (%)','Pós pares (%)']:short[col]=short[col].map(pct)
        short['Evolução (pp)']=short['Evolução (pp)'].map(diff)
        clean_table(short,[('Instituição','Instituição'),('Pré','Pré-testes'),('Pós','Pós-testes'),('Pré pares','Pré pares (%)'),('Pós pares','Pós pares (%)'),('Ganho','Evolução (pp)')],key='inst',size=7,widths=[32,11,11,16,16,14])


def view_qualidade(df,report,pre_raw,pos_raw,access,base,pre_uid,pos_uid,token):
    st.title('Qualidade dos dados')
    st.markdown('<div class="hero-sub">Deteção de duplicados, inconsistências e resolução segura de registos</div>',unsafe_allow_html=True)
    if st.session_state.get('last_delete'):
        st.success(st.session_state.pop('last_delete'))
    audit=audit_records(pre_raw,pos_raw)
    ids=set(df['participante_id']) if not df.empty else set()
    group_view=[g for g in audit['groups'] if any(x['pid'] in ids for x in g['rows'])] if ids else audit['groups']
    anomalies=report['anomalies']
    if not anomalies.empty and ids:
        anomalies=anomalies[anomalies['Identificador'].isin(ids)|anomalies['Identificador'].eq('—')]
    score_diffs=0 if df.empty else int(df['Inconsistência nota pré'].sum()+df['Inconsistência nota pós'].sum())
    incomplete=0 if df.empty else int(df['Respostas pré'].lt(15).sum())
    orphan=report['orphan_post_count']
    cards([('Grupos de duplicados',len(group_view),'Requerem verificação individual'),
           ('Notas divergentes',score_diffs,'Cálculo Kobo × dashboard'),
           ('Pré-testes incompletos',incomplete,'Respostas em falta'),
           ('Pós-testes sem pré',orphan,'Identificadores não associados')])
    if not access:
        st.info('Para ver nomes, grupos de duplicados, auditorias e opções de eliminação, configura DASHBOARD_PASSWORD nas Secrets.')
        return
    heading('Duplicados detetados','Nenhum registo é apagado automaticamente')
    if not group_view:
        st.success('Não foram encontrados duplicados por identificador ou por nome/instituição.')
    else:
        st.markdown('<div class="notice">Os registos com o mesmo ID são repetidos. Nomes iguais com IDs diferentes são '
                    '<b>apenas suspeitas</b>: podem representar pessoas diferentes.</div>',unsafe_allow_html=True)
        slim=[]
        for g in group_view:
            slim.append({'Tipo':g['type'],'Grupo':g['label'],'Submissões':len(g['rows']),
                         'Ação':'Rever antes de eliminar'})
        clean_table(pd.DataFrame(slim),[('Tipo','Tipo'),('Participante / referência','Grupo'),('Registos','Submissões'),('Tratamento','Ação')],key='groups',size=6,widths=[19,49,12,20])
    heading('Outras verificações','Sinalizações da API e dos cálculos')
    if not anomalies.empty:
        clean_table(anomalies,[('Anomalia','Tipo'),('Referência','Identificador'),('N.º','Quantidade'),('Observação','Observação')],key='anomalies',size=7,widths=[32,19,8,41])
        if access:st.download_button('Exportar alertas',csv(anomalies),'FBP_alertas_qualidade.csv',mime='text/csv')
    else:st.caption('Nenhuma inconsistência adicional identificada.')
    if not access:
        st.info('A revisão individual e eventual eliminação exigem acesso com palavra-passe do dashboard.')
        return
    with st.expander('Rever os registos originais e corrigir duplicados',expanded=False):
        if not group_view:
            st.caption('Sem candidatos a eliminar.');return
        options={g['key']:g for g in group_view}
        chosen=st.selectbox('Grupo a analisar',list(options),format_func=lambda k:f"{options[k]['type']} — {options[k]['label']}",key='qc_group')
        group=options[chosen]
        records=[]
        for r in sorted(group['rows'],key=lambda x:(x['time'],x['id'] or 0)):
            c=audit['candidates'].get((r['phase'],r['id']))
            records.append({'Kobo ID':r['id'],'Formulário':'Pré-teste' if r['phase']=='pre' else 'Pós-teste',
                            'ID participante':r['pid'],'Data':r['time'][:16].replace('T',' '),
                            'Acertos':f"{r['score']['acertos']}/15",'Situação':('Pode eliminar após revisão' if c and c['eligible'] else 'Conservar / protegido')})
        clean_table(pd.DataFrame(records),[('Kobo ID','Kobo ID'),('Fase','Formulário'),('ID participante','ID participante'),('Data','Data'),('Nota','Acertos'),('Proteção','Situação')],key='candidate_recs',size=6,widths=[11,15,22,18,10,24])
        st.caption(group['reason'])
        eligible=[r for r in group['rows'] if (r['phase'],r['id']) in audit['candidates'] and audit['candidates'][(r['phase'],r['id'])]['eligible']]
        if not eligible:
            st.warning('Não há submissões elegíveis para eliminação segura neste grupo. Requer revisão no Kobo.')
            return
        candidate_map={f"{r['phase']}:{r['id']}":audit['candidates'][(r['phase'],r['id'])] for r in eligible}
        selected=st.selectbox('Registo candidato a eliminar',list(candidate_map),
                              format_func=lambda k:f"{candidate_map[k]['id']} · {'PRÉ' if candidate_map[k]['phase']=='pre' else 'PÓS'} · {candidate_map[k]['pid']}",key='qc_delete_select')
        item=candidate_map[selected]
        st.info(item['reason'])
        st.download_button('Descarregar cópia de segurança deste registo (JSON)',
            data=backup_json(item),file_name=f"FBP_backup_{item['phase']}_{item['id']}.json",mime='application/json')
        if setting('ENABLE_KOBO_DELETE').strip().lower() not in ('true','1','yes') or not setting('ADMIN_DELETE_PASSWORD'):
            st.warning('A eliminação está desativada. Um administrador deve configurar ENABLE_KOBO_DELETE = true e ADMIN_DELETE_PASSWORD nas Secrets.')
            return
        st.markdown('**Eliminação definitiva no Kobo** — afeta os dados originais e pode afetar as ligações do pós-teste.')
        with st.form('delete_one_submission',clear_on_submit=True):
            admin_pw=st.text_input('Palavra-passe de administrador',type='password')
            confirm=st.text_input(f"Para confirmar, escreve exatamente ELIMINAR {item['id']}")
            understand=st.checkbox('Verifiquei a submissão, descarreguei a cópia de segurança e confirmo a eliminação definitiva.')
            delete_now=st.form_submit_button('Eliminar esta submissão no Kobo',type='secondary')
        if delete_now:
            if not hmac.compare_digest(admin_pw,setting('ADMIN_DELETE_PASSWORD')):
                st.error('Autenticação do administrador falhou.');return
            if confirm!=f"ELIMINAR {item['id']}" or not understand:
                st.error('A confirmação está incompleta. Não foram apagados registos.');return
            try:
                # Nova leitura SEM CACHE antes de um pedido irreversível.
                fresh_pre=fetch_submissions(base,pre_uid,token)
                fresh_pos=fetch_submissions(base,pos_uid,token)
                fresh=can_delete_now(item['phase'],item['id'],fresh_pre,fresh_pos)
                if not fresh or fresh['pid']!=item['pid']:
                    st.error('A situação do registo mudou ou deixou de ser seguro eliminá-lo. Atualiza o painel.');return
                uid=pre_uid if item['phase']=='pre' else pos_uid
                delete_submission(base,uid,item['id'],token)
                st.session_state['last_delete']=f"Submissão {item['id']} eliminada no Kobo. Guarda a cópia de segurança."
                fetch_both.clear();st.rerun()
            except KoboAPIError as exc: st.error(str(exc))


def main():
    access=secure_access()
    page=side_nav()
    token=setting('KOBO_TOKEN')
    base=setting('KOBO_BASE_URL',DEFAULT_BASE_URL)
    pre_uid=setting('KOBO_PRE_UID',PRE_UID)
    pos_uid=setting('KOBO_POS_UID',POS_UID)
    if not token:
        st.error('Falta configurar KOBO_TOKEN nas Secrets do Streamlit.')
        st.code('KOBO_BASE_URL = "https://kf.kobo.ucp-pch.org"\n'
                'KOBO_PRE_UID = "a9UStPiv4QDyzfZeHiBzwu"\n'
                'KOBO_POS_UID = "a2JXAwUZP7h3z3nUmpfchj"\n'
                'KOBO_TOKEN = "INSERIR_TOKEN_AQUI"',language='toml')
        st.stop()
    try:
        with st.spinner('A consultar os dois formulários Kobo…'):
            pre_raw,pos_raw,updated=fetch_both(base,pre_uid,pos_uid,hashlib.sha256(token.encode()).hexdigest(),token)
    except KoboAPIError as exc: st.error(str(exc));st.stop()
    except Exception: st.error('Erro inesperado na consulta. Consulte os logs do Streamlit.');st.stop()
    report=build_analysis(pre_raw,pos_raw)
    full=report['participants']
    edition,institution=selection_panel(full)
    data=full.copy()
    if not data.empty:
        if edition!='Todas':data=data[data['Edição']==edition]
        if institution!='Todas':data=data[data['Instituição']==institution]
    ids=set(data['participante_id']) if not data.empty else set()
    qpre=pre_per_question(pre_raw,ids,QUESTIONS)
    paired_questions=report['questions']
    if not paired_questions.empty:paired_questions=paired_questions[paired_questions['participante_id'].isin(ids)]
    with st.sidebar:
        st.divider()
        st.caption(f'Kobo PCH · {updated}')
        st.caption('15 perguntas · Edição '+(edition if edition!='Todas' else 'todas'))
    if page=='Dashboard':
        view_dashboard(data,pre_raw,report['raw_pre_count'],report['raw_pos_count'],qpre,access)
    elif page=='Aprendizagem':
        view_aprendizagem(data,qpre,paired_questions,access)
    else:
        view_qualidade(data,report,pre_raw,pos_raw,access,base,pre_uid,pos_uid,token)
    st.markdown('<div class="foot">Projeto de Capital Humano · FBP | Resultados recalculados a partir das respostas Kobo · '+
                'As notas não são alteradas no servidor.</div>',unsafe_allow_html=True)

if __name__=='__main__':main()
