"""Análise auditável de pré/pós-teste FBP, baseada num UUID e respostas individuais."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
import pandas as pd

ANSWER_KEY = {
    1: "b", 2: "c", 3: "d", 4: "a", 5: "a", 6: "b", 7: "c", 8: "d",
    9: "a", 10: "b", 11: "c", 12: "d", 13: "a", 14: "b", 15: "c",
}
N_QUESTIONS = len(ANSWER_KEY)
INSTITUTIONS = {
    "inde": "INDE — Instituto Nacional para o Desenvolvimento da Educação",
    "dgebs": "DGEBS", "dgepase": "DGEPASE", "ige": "IGE — Inspeção-Geral da Educação",
    "uc_pch": "UC-PCH — Unidade de Coordenação do PCH",
    "uicv": "UICV — Unidade Independente de Contratualização e Verificação",
    "dre": "Direção Regional de Educação", "outra": "Outra instituição / direção",
}
TOPICS = {
    "Conceitos e princípios": range(1, 6),
    "Responsabilidades institucionais": range(6, 10),
    "Implementação e ferramentas": range(10, 15),
    "Gestão de reclamações": range(15, 16),
}


def field(record: dict, key: str, default=None):
    """Procura primeiro campo exato; depois terminal (ex. 'avaliacao/q01')."""
    if key in record and record[key] is not None:
        return record[key]
    paths = [k for k in record if isinstance(k, str) and k.split("/")[-1] == key]
    if paths:
        paths.sort(key=lambda k: (0 if k.startswith("avaliacao/") else 1, len(k)))
        return record.get(paths[0], default)
    return default


def timestamp(record):
    raw = field(record, "_submission_time") or field(record, "fim") or ""
    if not raw:
        return ""
    return str(raw)


def sort_key(record):
    return (timestamp(record), str(field(record, "_id") or field(record, "_uuid") or ""))


def score_record(record: dict):
    responses = {}
    correct = {}
    for n, key in ANSWER_KEY.items():
        name = f"q{n:02d}"
        ans = str(field(record, name) or "").strip().lower()
        responses[name] = ans if ans in {"a", "b", "c", "d"} else ""
        correct[name] = (ans == key) if ans in {"a", "b", "c", "d"} else None
    answered = sum(v != "" for v in responses.values())
    score = sum(v is True for v in correct.values())
    declared = field(record, "total_acertos")
    mismatch = False
    if declared not in (None, ""):
        try:
            mismatch = abs(float(declared) - score) > 0.01
        except (ValueError, TypeError):
            mismatch = True
    return {
        "responses": responses, "correct": correct, "respondidas": answered,
        "acertos": score, "percentagem": round(score * 100 / N_QUESTIONS, 1),
        "nota_20": round(score * 20 / N_QUESTIONS, 1),
        "completo": answered == N_QUESTIONS, "inconsistencia_nota": mismatch,
        "nota_kobo": declared,
    }


def normalize_id(record):
    return str(field(record, "participante_id") or "").strip()


def institution_from(pre):
    code = str(field(pre, "instituicao") or "").strip().lower()
    label = str(field(pre, "instituicao_label") or "").strip()
    if code == "outra":
        return str(field(pre, "instituicao_outra") or label or INSTITUTIONS["outra"]).strip()
    return label or INSTITUTIONS.get(code, code or "Não indicada")


def first_selected(records):
    """Primeira submissão completa: evita inflacionar notas com retentativas."""
    ordered = sorted(records, key=sort_key)
    for rec in ordered:
        if score_record(rec)["completo"]:
            return rec
    return ordered[0]


def build_analysis(pre_raw: list[dict], pos_raw: list[dict]):
    pres = defaultdict(list)
    posts = defaultdict(list)
    no_id_pre, no_id_pos = [], []
    for rec in pre_raw:
        pid = normalize_id(rec)
        (pres[pid] if pid else no_id_pre).append(rec)
    for rec in pos_raw:
        pid = normalize_id(rec)
        (posts[pid] if pid else no_id_pos).append(rec)
    anomalies = []
    if no_id_pre:
        anomalies.append({"Tipo": "Pré-teste sem identificador", "Identificador": "—", "Quantidade": len(no_id_pre), "Observação": "Excluído do cruzamento automático"})
    if no_id_pos:
        anomalies.append({"Tipo": "Pós-teste sem identificador", "Identificador": "—", "Quantidade": len(no_id_pos), "Observação": "Excluído do cruzamento automático"})
    rows, question_rows, paired_rows = [], [], []
    for pid, pre_candidates in pres.items():
        pre = first_selected(pre_candidates)
        pre_score = score_record(pre)
        all_posts = sorted(posts.get(pid, []), key=sort_key)
        valid_posts = [p for p in all_posts if score_record(p)["completo"] and str(field(p, "confirma_identidade") or "").lower() == "sim"]
        pos = valid_posts[0] if valid_posts else (all_posts[0] if all_posts else None)
        pos_score = score_record(pos) if pos else None
        paired = bool(pos and pos in valid_posts and pre_score["completo"])
        if paired:
            state = "Pré e pós concluídos"
        elif pos and pos_score and not pos_score["completo"]:
            state = "Pós-teste incompleto"
        elif pos and str(field(pos, "confirma_identidade") or "").lower() != "sim":
            state = "Identidade não confirmada"
        else:
            state = "Pós-teste pendente"
        if not pre_score["completo"]:
            state = "Pré-teste incompleto"
        institution = institution_from(pre)
        name = str(field(pre, "nome_completo") or "Sem nome").strip()
        edition = str(field(pre, "edicao_id") or "Sem edição").strip()
        row = {
            "participante_id": pid, "Nome": name, "Instituição": institution,
            "Função": str(field(pre, "funcao") or ""), "Edição": edition,
            "Estado": state, "Data pré": timestamp(pre), "Data pós": timestamp(pos) if pos else "",
            "Acertos pré": pre_score["acertos"] if pre_score["completo"] else None,
            "Acertos pós": pos_score["acertos"] if paired else None,
            "Pré (%)": pre_score["percentagem"] if pre_score["completo"] else None,
            "Pós (%)": pos_score["percentagem"] if paired else None,
            "Evolução (pp)": round(pos_score["percentagem"] - pre_score["percentagem"], 1) if paired else None,
            "Nota pré (/20)": pre_score["nota_20"] if pre_score["completo"] else None,
            "Nota pós (/20)": pos_score["nota_20"] if paired else None,
            "Ganho (acertos)": (pos_score["acertos"] - pre_score["acertos"]) if paired else None,
            "N.º pré-testes": len(pre_candidates), "N.º pós-testes": len(all_posts),
            "Inconsistência nota pré": pre_score["inconsistencia_nota"],
            "Inconsistência nota pós": any(score_record(p)["inconsistencia_nota"] for p in all_posts),
            "Respostas pré": pre_score["respondidas"],
            "Respostas pós": pos_score["respondidas"] if pos_score else 0,
        }
        rows.append(row)
        if len(pre_candidates) > 1:
            anomalies.append({"Tipo": "Pré-teste repetido (ID)", "Identificador": pid, "Quantidade": len(pre_candidates), "Observação": name})
        if len(all_posts) > 1:
            anomalies.append({"Tipo": "Pós-teste repetido (ID)", "Identificador": pid, "Quantidade": len(all_posts), "Observação": name})
        if pre_score["inconsistencia_nota"]:
            anomalies.append({"Tipo": "Divergência na nota do pré-teste", "Identificador": pid, "Quantidade": 1, "Observação": name})
        if any(score_record(p)["inconsistencia_nota"] for p in all_posts):
            anomalies.append({"Tipo": "Divergência na nota do pós-teste", "Identificador": pid, "Quantidade": 1, "Observação": name})
        if paired:
            paired_rows.append(row)
            for n in ANSWER_KEY:
                key = f"q{n:02d}"
                question_rows.append({
                    "participante_id": pid, "Edição": edition, "Instituição": institution,
                    "Pergunta": n, "Pré correto": int(pre_score["correct"][key]),
                    "Pós correto": int(pos_score["correct"][key]),
                    "Resposta pré": pre_score["responses"][key],
                    "Resposta pós": pos_score["responses"][key],
                })
    for pid, orphan_posts in posts.items():
        if pid not in pres:
            anomalies.append({"Tipo": "Pós-teste sem pré-teste correspondente", "Identificador": pid, "Quantidade": len(orphan_posts), "Observação": "Rever ligação entre formulários"})
    df = pd.DataFrame(rows)
    qdf = pd.DataFrame(question_rows)
    adf = pd.DataFrame(anomalies, columns=["Tipo", "Identificador", "Quantidade", "Observação"])
    paired_df = pd.DataFrame(paired_rows)
    return {
        "participants": df, "questions": qdf, "anomalies": adf, "paired": paired_df,
        "raw_pre_count": len(pre_raw), "raw_pos_count": len(pos_raw),
        "orphan_post_count": sum(len(v) for k,v in posts.items() if k not in pres),
        "unnamed_pre_count": len(no_id_pre), "unnamed_pos_count": len(no_id_pos),
    }


def institution_summary(df):
    columns = ["Instituição", "Pré-testes", "Pós-testes", "Cobertura (%)", "Pré pares (%)", "Pós pares (%)", "Evolução (pp)"]
    if df.empty:
        return pd.DataFrame(columns=columns)
    out = []
    for inst, g in df.groupby("Instituição", dropna=False):
        paired = g[g["Estado"] == "Pré e pós concluídos"]
        before = paired["Pré (%)"].mean() if not paired.empty else float("nan")
        after = paired["Pós (%)"].mean() if not paired.empty else float("nan")
        out.append({"Instituição": inst, "Pré-testes": len(g), "Pós-testes": len(paired),
                    "Cobertura (%)": round(100 * len(paired) / len(g), 1),
                    "Pré pares (%)": round(before, 1) if not paired.empty else None,
                    "Pós pares (%)": round(after, 1) if not paired.empty else None,
                    "Evolução (pp)": round(after-before, 1) if not paired.empty else None})
    return pd.DataFrame(out, columns=columns).sort_values("Instituição")


def question_summary(qdf, questions):
    if qdf.empty:
        return pd.DataFrame(columns=["Pergunta", "Tema", "Enunciado", "N", "Pré (%)", "Pós (%)", "Evolução (pp)"])
    out=[]
    for n, g in qdf.groupby("Pergunta"):
        x = round(g["Pré correto"].mean()*100,1)
        y = round(g["Pós correto"].mean()*100,1)
        topic = next(k for k,v in TOPICS.items() if n in v)
        out.append({"Pergunta": f"P{n:02d}", "Número": n, "Tema": topic,
                    "Enunciado": questions[n-1]["prompt"], "N": len(g),
                    "Pré (%)": x, "Pós (%)": y, "Evolução (pp)": round(y-x,1)})
    return pd.DataFrame(out).sort_values("Número")
