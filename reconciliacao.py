"""Reconciliação conservadora das duas fontes Kobo, sem alterar os originais.

Uma segunda submissão ao formulário PRÉ não é automaticamente um PÓS:
exige identidade, ordem cronológica e aprovação explícita registada em CSV.
Duplicados *óbvios* (mesma pessoa, mesmas 15 respostas, em 15 min) são
excluídos dos indicadores, mas só se apagam fisicamente com confirmação.
"""
from collections import defaultdict
from datetime import datetime, timezone
import csv
import io
import pandas as pd
from analysis import field, institution_from, normalize_id, score_record
from monitor import normalize_person_name

MAX_REPEAT_MINUTES = 15
MIN_AS_POST_MINUTES = 30
DECISION_COLUMNS = ["pre_id_original", "pre_id_segundo", "decisao", "responsavel", "nota", "data_decisao"]


def kobo_id(rec):
    try:
        return int(field(rec, "_id"))
    except (ValueError, TypeError):
        return None


def date_of(rec):
    text = str(field(rec, "_submission_time") or field(rec, "fim") or "").strip()
    if not text:
        return None
    try:
        dt = pd.to_datetime(text, utc=True, errors="coerce")
        return dt.to_pydatetime() if not pd.isna(dt) else None
    except (ValueError, TypeError, OverflowError):
        return None


def identity(rec):
    return (
        normalize_person_name(field(rec, "nome_completo")),
        normalize_person_name(institution_from(rec)),
        str(field(rec, "edicao_id") or "").strip(),
    )


def response_signature(rec):
    s = score_record(rec)
    return tuple(s["responses"][f"q{i:02d}"] for i in range(1, 16))


def _ordered(rows):
    return sorted(rows, key=lambda rec: (date_of(rec) or datetime.max.replace(tzinfo=timezone.utc), kobo_id(rec) or 0))


def _has_valid_post(records):
    return any(score_record(r)["completo"] and str(field(r, "confirma_identidade") or "").strip().lower() == "sim" for r in records)


def read_decisions(data):
    """Aceita CSV (bytes, texto, DataFrame ou lista de dicionários)."""
    if isinstance(data, list):
        return [dict(item) for item in data]
    if isinstance(data, pd.DataFrame):
        return data.fillna("").to_dict("records")
    if data is None:
        return []
    if isinstance(data, bytes):
        data = data.decode("utf-8-sig")
    if not str(data).strip():
        return []
    return list(csv.DictReader(io.StringIO(str(data)), delimiter=";"))


def decisions_csv(rows):
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=DECISION_COLUMNS, delimiter=";", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buff.getvalue().encode("utf-8-sig")


def _candidate(first, second, real_posts):
    a, b = score_record(first), score_record(second)
    first_id, second_id = kobo_id(first), kobo_id(second)
    if first_id is None or second_id is None or first_id == second_id:
        return None
    pida, pidb = normalize_id(first), normalize_id(second)
    if not pida or not pidb or not identity(first)[0]:
        return None
    if identity(first) != identity(second):
        return None
    if not (a["completo"] and b["completo"]):
        return None
    if real_posts.get(pida) or real_posts.get(pidb):
        return None
    t1, t2 = date_of(first), date_of(second)
    if not t1 or not t2 or t2 <= t1:
        return None
    mins = round((t2-t1).total_seconds()/60, 1)
    if mins < MIN_AS_POST_MINUTES:
        return None
    return {
        "pre_id_original": first_id,
        "pre_id_segundo": second_id,
        "participante_id_original": pida,
        "participante_id_segundo": pidb,
        "nome": str(field(first,"nome_completo") or ""),
        "instituicao": institution_from(first),
        "edicao": identity(first)[2],
        "data_primeiro": t1.isoformat(timespec='minutes'),
        "data_segundo": t2.isoformat(timespec='minutes'),
        "intervalo_min": mins,
        "acertos_primeiro": a["acertos"],
        "acertos_segundo": b["acertos"],
        "mudou_respostas": response_signature(first)!=response_signature(second),
        "q_diferentes": sum(x!=y for x,y in zip(response_signature(first),response_signature(second))),
    }


def reconcile(pre_raw, pos_raw, decisions=None):
    """Devolve dados reconciliados e auditoria. NÃO envia pedidos DELETE ao Kobo."""
    decisions = read_decisions(decisions)
    post_by_pid = defaultdict(list)
    for p in pos_raw:
        post_by_pid[normalize_id(p)].append(p)
    by_identity = defaultdict(list)
    for p in pre_raw:
        key=identity(p)
        if key[0]:
            by_identity[key].append(p)
    # Nunca fundir participantes apenas por terem o mesmo nome. Só excluir
    # repetição com 15 respostas idênticas, minutos próximos e nenhum pós válido.
    excluded_ids = set()
    obvious = []
    for same_person in by_identity.values():
        valid = [r for r in _ordered(same_person) if score_record(r)["completo"]]
        keepers = []
        for cur in valid:
            cur_id = kobo_id(cur)
            if cur_id is None:
                keepers.append(cur)
                continue
            found = None
            for prev in keepers:
                prev_t, cur_t = date_of(prev), date_of(cur)
                if not prev_t or not cur_t:
                    continue
                delta = (cur_t-prev_t).total_seconds()/60
                if delta < 0 or delta > MAX_REPEAT_MINUTES:
                    continue
                if response_signature(prev)!=response_signature(cur):
                    continue
                # Não apagar a identidade de uma submissão com pós já associado.
                if _has_valid_post(post_by_pid.get(normalize_id(cur), [])):
                    continue
                found=prev
                break
            if found:
                excluded_ids.add(cur_id)
                obvious.append({
                    "id_conservar": kobo_id(found), "id_repetido": cur_id,
                    "participante_id": normalize_id(cur),
                    "nome": str(field(cur,"nome_completo") or ""),
                    "instituicao": institution_from(cur),
                    "motivo": f"15 respostas iguais e submissões num intervalo até {MAX_REPEAT_MINUTES} minutos",
                })
            else:
                keepers.append(cur)
    raw_clean = [r for r in pre_raw if kobo_id(r) not in excluded_ids]
    clean_grouped = defaultdict(list)
    for r in raw_clean:
        k=identity(r)
        if k[0]:
            clean_grouped[k].append(r)
    all_candidates = []
    for same_person in clean_grouped.values():
        # Só tratar automaticamente agrupamentos com exatamente dois pré-testes.
        # Três ou mais implicam seleção humana dos dois registos pertinentes.
        ordered = _ordered(same_person)
        if len(ordered) == 2:
            candidate = _candidate(ordered[0], ordered[1], post_by_pid)
            if candidate:
                all_candidates.append(candidate)
    by_pair = {(c['pre_id_original'],c['pre_id_segundo']):c for c in all_candidates}
    # Decisões declaradas não são aplicadas cegamente: devem continuar válidas
    # perante a fonte viva Kobo e nunca reclassificar com pós verdadeiro presente.
    approved=[]
    blocked=[]
    by_kobo_id = {kobo_id(r): r for r in raw_clean if kobo_id(r) is not None}
    for decision in decisions:
        try:
            orig, second = int(decision.get('pre_id_original')), int(decision.get('pre_id_segundo'))
        except (ValueError,TypeError):
            continue
        if str(decision.get('decisao') or '').strip().lower() != 'usar_como_pos':
            continue
        pair=(orig,second)
        candidate=by_pair.get(pair)
        if not candidate:
            blocked.append({'par':pair,'motivo':'A decisão já não cumpre as regras de segurança ou o pós verdadeiro apareceu'})
            continue
        if any(r['pre_id_original']==orig or r['pre_id_segundo']==second for r in approved):
            blocked.append({'par':pair,'motivo':'Outra decisão já usa um destes registos'})
            continue
        approved.append(candidate)
    approved_second_ids = {c['pre_id_segundo'] for c in approved}
    clean_pre = [r for r in raw_clean if kobo_id(r) not in approved_second_ids]
    synthetic=[]
    for c in approved:
        source=by_kobo_id[c['pre_id_segundo']]
        mock=dict(source)
        mock['participante_id']=c['participante_id_original']
        mock['confirma_identidade']='sim'
        mock['_fbp_source']='segundo_pre_aprovado'
        mock['_fbp_source_pre_id']=c['pre_id_segundo']
        synthetic.append(mock)
    return {
        'pre':clean_pre,'pos':list(pos_raw)+synthetic,
        'duplicate_obvious': obvious, 'excluded_ids':excluded_ids,
        'candidates':all_candidates, 'approved':approved, 'blocked':blocked,
        'protected_ids':approved_second_ids,
        'raw_pre_count':len(pre_raw), 'raw_pos_count':len(pos_raw),
    }
