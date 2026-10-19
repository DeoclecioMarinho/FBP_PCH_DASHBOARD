"""Indicadores de acompanhamento do pré-teste e alertas de qualidade."""
from collections import defaultdict
import re
import unicodedata

import pandas as pd
from analysis import ANSWER_KEY, TOPICS, first_selected, institution_from, normalize_id, score_record, field


def pre_per_question(raw_pre, allowed_ids, question_catalog):
    """Percentagem de acertos no PRÉ (não exige haver pós-testes)."""
    grouped = defaultdict(list)
    for record in raw_pre:
        pid = normalize_id(record)
        if pid and pid in allowed_ids:
            grouped[pid].append(record)
    scores = []
    for candidates in grouped.values():
        s = score_record(first_selected(candidates))
        if s["completo"]:
            scores.append(s)
    rows = []
    for n in ANSWER_KEY:
        key = f"q{n:02d}"
        n_ok = sum(score["correct"][key] is True for score in scores)
        n_resp = len(scores)
        topic = next(t for t, rng in TOPICS.items() if n in rng)
        rows.append({
            "Pergunta": f"P{n:02d}", "Número": n,
            "Tema": topic, "Enunciado": question_catalog[n - 1]["prompt"],
            "Acertos": n_ok, "N": n_resp,
            "Acerto (%)": round(100 * n_ok / n_resp, 1) if n_resp else None,
        })
    return pd.DataFrame(rows)


def topic_performance(pre_questions):
    """Médias ponderadas pelo número de respostas (cada pergunta tem 1 resposta/participante)."""
    if pre_questions.empty or not pre_questions["N"].sum():
        return pd.DataFrame(columns=["Tema", "Acerto (%)", "Acertos", "Respostas"])
    group = pre_questions.groupby("Tema", sort=False).agg(
        Acertos=("Acertos", "sum"), Respostas=("N", "sum")
    ).reset_index()
    group["Acerto (%)"] = (100 * group["Acertos"] / group["Respostas"]).round(1)
    return group


def normalize_person_name(name):
    text = unicodedata.normalize("NFKD", str(name or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return " ".join(text.split())


def suspected_duplicate_names(pre_raw, allowed_ids):
    """Assinala NOME+INSTITUIÇÃO repetidos em IDs diferentes; não funde registos."""
    by_id = defaultdict(list)
    for rec in pre_raw:
        pid = normalize_id(rec)
        if pid and pid in allowed_ids:
            by_id[pid].append(rec)
    by_person = defaultdict(list)
    for pid, candidates in by_id.items():
        rec = first_selected(candidates)
        nome = str(field(rec, "nome_completo") or "").strip()
        inst = institution_from(rec)
        key = (normalize_person_name(nome), inst.casefold())
        if key[0]:
            by_person[key].append((pid, nome, inst))
    rows = []
    for _, group in by_person.items():
        if len(group) > 1:
            rows.append({
                "Nome": group[0][1], "Instituição": group[0][2],
                "Registos": len(group), "Identificadores": ", ".join(x[0] for x in group),
            })
    return pd.DataFrame(rows, columns=["Nome", "Instituição", "Registos", "Identificadores"])
