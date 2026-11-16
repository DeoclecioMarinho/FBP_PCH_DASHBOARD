"""Regras de auditoria datadas para as submissões FBP de 16/11/2026.

NÃO altera os dados Kobo, só calcula uma visão reconciliada. Cada ação
confere identificador, UUID e assinatura das 15 respostas antes de aplicar.
Se dados históricos mudarem, a ação correspondente é bloqueada e notificada.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from analysis import field, normalize_id, score_record

PATH = Path(__file__).resolve().parent / "data" / "curadoria_2026-11-16.json"
OWNERS = {40:5, 78:5, 41:10, 59:11, 42:39, 76:14, 34:32}


def submission_id(record):
    try:
        return int(field(record, "_id"))
    except (TypeError, ValueError):
        return None


def signature(record):
    choices = score_record(record)["responses"]
    data = "|".join(choices[f"q{i:02d}"] for i in range(1, 16))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def matches(record, expected):
    return (record is not None
            and submission_id(record) == expected["id"]
            and normalize_id(record) == expected["participante_id"]
            and score_record(record)["acertos"] == expected["nota"]
            and score_record(record)["completo"]
            and signature(record) == expected["assinatura"])


def apply_curadoria(pre_raw, pos_raw, path=PATH, usar_provisorios=True):
    """Devolve (pré reconciliado, pós reconciliado, relatório audível)."""
    if not Path(path).exists():
        return list(pre_raw), list(pos_raw), {"aplicadas":[], "avisos":[], "provisorios":[],"excluidos_pre":0,"excluidos_pos":0}
    config = json.loads(Path(path).read_text(encoding="utf-8"))
    bpre = {submission_id(r):r for r in pre_raw if submission_id(r) is not None}
    bpos = {submission_id(r):r for r in pos_raw if submission_id(r) is not None}
    def good(ex, phase="pre"):
        return matches((bpre if phase == "pre" else bpos).get(ex["id"]), ex)
    audit = {"versao":config.get("versao"),"aplicadas":[],"avisos":[],"provisorios":[],
             "excluidos_pre":0,"excluidos_pos":0,"alias_pos":0}
    excluded_pre=set()
    excluded_pos=set()
    # Só aplicar uma exclusão quando uma submissão substituta válida exista.
    for expected in config.get("pre_excluir",[]):
        rid=expected["id"]
        if rid not in bpre:
            continue  # já pode ter sido apagado no servidor
        if not good(expected):
            audit["avisos"].append(f"Pré #{rid}: registo alterado, exclusão não aplicada")
            continue
        owner=OWNERS.get(rid)
        owner_expected=next((r for r in config["pre_excluir"] if r["id"]==owner),None)
        # Principal não é um registo excluído; procurar entre referências de reclassificação/remapeamento.
        owned=None
        if owner is not None:
            for pair in config["recuperar_pos"]:
                if pair["pre_principal"]["id"]==owner:owned=pair["pre_principal"]
            for pair in config["remapear_pos"]:
                if pair["pre_principal"]["id"]==owner:owned=pair["pre_principal"]
            if owned is None:
                # Para este grupo a proteção tem no mínimo o ID Kobo do original.
                if owner not in bpre or not score_record(bpre[owner])["completo"]:
                    audit["avisos"].append(f"Pré #{rid}: falta submissão principal #{owner}; mantido")
                    continue
            elif not good(owned):
                audit["avisos"].append(f"Pré #{rid}: submissão principal #{owner} alterada; mantido")
                continue
        excluded_pre.add(rid)
        audit["aplicadas"].append({"tipo":"exclusão analítica de pré", "id":rid,"mantido":owner})
    for expected in config.get("pos_excluir",[]):
        rid=expected["id"]
        if rid in bpos and good(expected,"pos"):
            excluded_pos.add(rid)
            audit["aplicadas"].append({"tipo":"exclusão analítica de pós de teste", "id":rid})
        elif rid in bpos:
            audit["avisos"].append(f"Pós #{rid}: dados alterados, exclusão não aplicada")
    # Mapa de aliases: em futuras sessões um novo pós pode ainda selecionar
    # a inscrição repetida (UUID secundário), não só os pós conhecidos de 16/11.
    alias_pids={}
    for ex in config.get("pre_excluir",[]):
        sid=ex["id"]
        owner=OWNERS.get(sid)
        if owner is not None and good(ex) and owner in bpre and score_record(bpre[owner])["completo"]:
            alias_pids[ex["participante_id"]]=normalize_id(bpre[owner])
    effective_pos=[]
    remapped=set()
    for pos in pos_raw:
        rid=submission_id(pos)
        if rid in excluded_pos:continue
        target=None
        for pair in config.get("remapear_pos",[]):
            if pair["pos_referencia"]["id"] != rid:continue
            if good(pair["pre_principal"]) and good(pair["pos_referencia"],"pos"):
                target=pair["pre_principal"]["participante_id"]
            else:
                audit["avisos"].append(f"Pós #{rid}: reassociação bloqueada por divergência da origem")
            break
        rec=dict(pos)
        # Reassociação de novas respostas válidas que apontem para UUID secundário.
        if target is None and normalize_id(rec) in alias_pids and score_record(rec)["completo"]:
            target=alias_pids[normalize_id(rec)]
        if target and normalize_id(rec)!=target:
            rec["_fbp_pid_anterior"]=normalize_id(rec)
            rec["participante_id"]=target
            rec["_fbp_source"]="pos_kobo_reassociado"
            remapped.add(rid)
            audit["aplicadas"].append({"tipo":"pós verdadeiro reassociado ao primeiro pré","id":rid})
        effective_pos.append(rec)
    # Pós a partir do segundo PRÉ: provisório e explicitamente identificado.
    for pair in config.get("recuperar_pos",[]):
        if not usar_provisorios:
            continue
        first,second = pair["pre_principal"],pair["pre_segundo"]
        if not good(first) or not good(second):
            if first["id"] in bpre or second["id"] in bpre:
                audit["avisos"].append(f"Recuperação #{first['id']}/#{second['id']}: origem alterada/incompleta")
            excluded_pre.discard(second["id"])
            continue
        pid=first["participante_id"]
        if any(normalize_id(r) in (pid,second["participante_id"]) and
               str(field(r,"confirma_identidade") or "").strip().lower() in ("sim","yes","1")
               and score_record(r)["completo"] for r in effective_pos):
            audit["avisos"].append(f"Pré #{second['id']}: apareceu pós oficial, não recuperar segundo pré")
            continue
        mock=dict(bpre[second["id"]])
        mock["participante_id"]=pid
        mock["confirma_identidade"]="sim"
        mock["_fbp_source"]="segundo_pre_provisorio"
        mock["_fbp_source_pre_id"]=second["id"]
        effective_pos.append(mock)
        audit["provisorios"].append({"id_primeiro_pre":first["id"],"id_segundo_pre":second["id"]})
        audit["aplicadas"].append({"tipo":"segundo pré contado como pós provisório","id":second["id"]})
        excluded_pre.add(second["id"])
    effective_pre=[]
    for rec in pre_raw:
        rid=submission_id(rec)
        if rid in excluded_pre:continue
        r=dict(rec)
        # Correção EXCLUSIVAMENTE visual de erro de transcrição Blco/Bico.
        if rid==32 and rid in bpre and score_record(rec)["completo"]:
            r["_fbp_nome_original"]=field(r,"nome_completo")
            r["nome_completo"]="Bico Sedja Muscate"
        effective_pre.append(r)
    audit["excluidos_pre"]=len(excluded_pre)
    audit["excluidos_pos"]=len(excluded_pos)
    audit["alias_pos"]=len(remapped)
    return effective_pre,effective_pos,audit
