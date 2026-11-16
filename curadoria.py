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



# Cópia integrada das regras de reconciliação: evita que a falta da pasta data/
# devolva silenciosamente os registos brutos como pessoas distintas.
EMBEDDED_RULES = json.loads(r'''
{
  "versao": "2026-11-16",
  "fonte": "Auditoria local dos dois exportes Kobo de 16/11/2026",
  "modo": "provisorio_auditavel",
  "pre_excluir": [
    {
      "id": 3,
      "participante_id": "07b64cba-f0aa-4b2b-9065-aac7aba47627",
      "nota": 5,
      "assinatura": "9ae4fe9e5078ed90446f82c4ebd9783e5a8fb20b390d882c32202ad22e03c1d9"
    },
    {
      "id": 34,
      "participante_id": "5c921e14-9a7d-4dac-97cf-5a8beb5e1ddc",
      "nota": 4,
      "assinatura": "2dea437e68587983467957a03bf139378b7b080a2525bb6d5d5342a3384bfc1c"
    },
    {
      "id": 40,
      "participante_id": "8f65c192-907d-4a41-b060-7c27bd5b686f",
      "nota": 13,
      "assinatura": "88f006bdd01c679836d912ad3631c60b94e98ba37fb040f52fc91ec890d06d88"
    },
    {
      "id": 41,
      "participante_id": "26430c52-7df4-41c0-b5b0-e94142331d5e",
      "nota": 15,
      "assinatura": "c069a0e1de6ef5c5e34f92871a40da1a6b861da6f4ff6bf30f049f5864bac1df"
    },
    {
      "id": 42,
      "participante_id": "54bd8f55-992d-4f10-998c-e2a245d79b29",
      "nota": 11,
      "assinatura": "c24686bd45ebc634a9a7fc5a8582ece083c4702f5855554188cb9d6bd1de9756"
    },
    {
      "id": 59,
      "participante_id": "a8d851ae-c578-4935-82e9-2e58eada9089",
      "nota": 14,
      "assinatura": "f675079252cbd331690add42c7202ec30653aca83816891d3d38b973755127e0"
    },
    {
      "id": 76,
      "participante_id": "c5709259-fbe9-4a04-9198-6cfd44712a74",
      "nota": 11,
      "assinatura": "88dd0259748dd9b5a903c5d0134ce6d995d773f7111b5af3fb74d36a20da0914"
    },
    {
      "id": 78,
      "participante_id": "a96926b8-84e2-4d47-acad-1da90b9a5cc0",
      "nota": 14,
      "assinatura": "6d711dfdebcc65e0db424405e18576ab39f2b15588691152505d73016a0bacfa"
    }
  ],
  "pos_excluir": [
    {
      "id": 4,
      "participante_id": "07b64cba-f0aa-4b2b-9065-aac7aba47627",
      "nota": 5,
      "assinatura": "8d087f95ae22dad7115c966527f3694ae90f7552ac27cc452344459850884561"
    }
  ],
  "remapear_pos": [
    {
      "pre_referencia": {
        "id": 59,
        "participante_id": "a8d851ae-c578-4935-82e9-2e58eada9089",
        "nota": 14,
        "assinatura": "f675079252cbd331690add42c7202ec30653aca83816891d3d38b973755127e0"
      },
      "pre_principal": {
        "id": 11,
        "participante_id": "95661352-4ab2-47e9-bddc-d6e9f8544275",
        "nota": 14,
        "assinatura": "dd708c4644a4b282632d2b6b4318351765c6c1f3adeefe96d5475e77851094d5"
      },
      "pos_referencia": {
        "id": 70,
        "participante_id": "a8d851ae-c578-4935-82e9-2e58eada9089",
        "nota": 14,
        "assinatura": "f675079252cbd331690add42c7202ec30653aca83816891d3d38b973755127e0"
      },
      "motivo": "Pós verdadeiro ligado a reentrada do pré; cruzamento recuperado com o pré inicial."
    },
    {
      "pre_referencia": {
        "id": 34,
        "participante_id": "5c921e14-9a7d-4dac-97cf-5a8beb5e1ddc",
        "nota": 4,
        "assinatura": "2dea437e68587983467957a03bf139378b7b080a2525bb6d5d5342a3384bfc1c"
      },
      "pre_principal": {
        "id": 32,
        "participante_id": "984dcd4c-4404-4bc8-89e8-9984ab8c1f81",
        "nota": 7,
        "assinatura": "128107edc619442860a4daa205823153c209a460525adafdaceadc8c85ec3061"
      },
      "pos_referencia": {
        "id": 49,
        "participante_id": "5c921e14-9a7d-4dac-97cf-5a8beb5e1ddc",
        "nota": 11,
        "assinatura": "1ef9b4ddbeb4e0afed5e766cd225726ec8d070cfcf9542e69d28bde61392d308"
      },
      "motivo": "Pós verdadeiro ligado a reentrada do pré; cruzamento recuperado com o pré inicial."
    }
  ],
  "recuperar_pos": [
    {
      "pre_principal": {
        "id": 5,
        "participante_id": "892a964a-baa4-4f45-9f59-cd39410a7403",
        "nota": 13,
        "assinatura": "59c6bc792dbde00496957d42615fd6f8f4479677ee9a57d413f7de6d10f519de"
      },
      "pre_segundo": {
        "id": 40,
        "participante_id": "8f65c192-907d-4a41-b060-7c27bd5b686f",
        "nota": 13,
        "assinatura": "88f006bdd01c679836d912ad3631c60b94e98ba37fb040f52fc91ec890d06d88"
      },
      "motivo": "Segundo pré posterior ao primeiro e sem pós Kobo confirmado; classificação provisória.",
      "estado": "provisorio"
    },
    {
      "pre_principal": {
        "id": 14,
        "participante_id": "1b1aaab9-cd59-453f-8cfd-19d73a913e21",
        "nota": 9,
        "assinatura": "eaa126c54d336193a38bb2b9d743127d48e61533129e59c2fc3fea0960a3c8ae"
      },
      "pre_segundo": {
        "id": 76,
        "participante_id": "c5709259-fbe9-4a04-9198-6cfd44712a74",
        "nota": 11,
        "assinatura": "88dd0259748dd9b5a903c5d0134ce6d995d773f7111b5af3fb74d36a20da0914"
      },
      "motivo": "Segundo pré posterior ao primeiro e sem pós Kobo confirmado; classificação provisória.",
      "estado": "provisorio"
    }
  ],
  "exclusao_teste": [
    3
  ],
  "alertas": [
    {
      "ids_pre": [
        32,
        33,
        34
      ],
      "codigo": "bico_homonimo",
      "motivo": "Rever identidade, cronologia e submissões adicionais antes de finalizar os indicadores."
    },
    {
      "ids_pre": [
        5,
        40,
        78
      ],
      "codigo": "carlos_terceira",
      "motivo": "Rever identidade, cronologia e submissões adicionais antes de finalizar os indicadores."
    },
    {
      "ids_pre": [
        14,
        76
      ],
      "codigo": "idrissa_reclassificacao",
      "motivo": "Rever identidade, cronologia e submissões adicionais antes de finalizar os indicadores."
    },
    {
      "ids_pre": [
        3
      ],
      "ids_pos": [
        4
      ],
      "codigo": "registo_teste",
      "motivo": "Rever identidade, cronologia e submissões adicionais antes de finalizar os indicadores."
    }
  ]
}
''')

class CuradoriaConfigError(RuntimeError):
    """O painel não deve mostrar indicadores como limpos sem regras válidas."""


def load_curadoria_rules(path=PATH):
    """Valida as regras; usa cópia integrada quando o JSON não foi publicado."""
    file_path = Path(path)
    if not file_path.exists():
        return EMBEDDED_RULES, "integrada"
    try:
        content = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CuradoriaConfigError("Ficheiro de curadoria inválido. Corrige ou remove o JSON de regras.") from exc
    for key in ("pre_excluir", "pos_excluir", "remapear_pos", "recuperar_pos"):
        if not isinstance(content.get(key), list):
            raise CuradoriaConfigError(f"Configuração de curadoria inválida: falta {key}.")
    if content.get("versao") != EMBEDDED_RULES.get("versao"):
        raise CuradoriaConfigError("Versão de curadoria divergente; verifica os ficheiros publicados.")
    return content, "ficheiro"


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
    config, origem_regras = load_curadoria_rules(path)
    bpre = {submission_id(r):r for r in pre_raw if submission_id(r) is not None}
    bpos = {submission_id(r):r for r in pos_raw if submission_id(r) is not None}
    def good(ex, phase="pre"):
        return matches((bpre if phase == "pre" else bpos).get(ex["id"]), ex)
    audit = {"versao":config.get("versao"),"origem_regras":origem_regras,
             "aplicadas":[],"avisos":[],"provisorios":[],
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
