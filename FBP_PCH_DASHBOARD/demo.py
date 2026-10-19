"""Dados SEM nomes reais; apenas para testar a interface sem ligação Kobo."""
from analysis import ANSWER_KEY


def make_record(n, kind, correct_num, edit="0001"):
    answers = {}
    for q, key in ANSWER_KEY.items():
        answers[f"q{q:02d}"] = key if q <= correct_num else ({"a": "b", "b": "c", "c": "d", "d": "a"}[key])
    base = {
        "participante_id": f"DEMO-{n:04d}", "edicao_id": edit,
        "_id": n+(0 if kind=="pre" else 100),
        "_submission_time": f"2026-10-{18 if kind=='pre' else 19}T10:0{n}:00+00:00",
        "total_acertos": correct_num, "percentagem": round(correct_num*100/15,1),
        **answers,
    }
    if kind == "pre":
        base.update({"nome_completo": f"Participante {n:02d} (DEMO)",
                     "instituicao": "inde" if n<=2 else "dgepase",
                     "instituicao_label": "INDE" if n<=2 else "DGEPASE",
                     "funcao": "Técnico(a)"})
    else:
        base["confirma_identidade"]="sim"
    return base


def demo_data():
    pre = [make_record(n,"pre",v) for n,v in [(1,6),(2,9),(3,5),(4,12)]]
    pos = [make_record(n,"pos",v) for n,v in [(1,12),(2,13),(3,10)]]
    return pre,pos
