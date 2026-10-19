import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json

from demo import demo_data, make_record
from analysis import build_analysis
from monitor import pre_per_question, topic_performance, suspected_duplicate_names, normalize_person_name

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'questionario.json').read_text(encoding='utf-8'))['questions']


def test_pre_question_metrics_do_not_require_pos():
    pre, _ = demo_data()
    ids = set(build_analysis(pre, [])['participants']['participante_id'])
    q = pre_per_question(pre, ids, CATALOG)
    assert len(q) == 15
    assert q['N'].eq(4).all()
    assert q.loc[q['Pergunta'].eq('P01'), 'Acerto (%)'].iat[0] == 100.0
    assert q.loc[q['Pergunta'].eq('P15'), 'Acerto (%)'].iat[0] == 0.0
    topics = topic_performance(q)
    assert len(topics) == 4
    assert topics['Respostas'].sum() == 60


def test_dedup_keeps_first_complete():
    pre, _ = demo_data()
    # Record second answer for same ID with better score - should not inflate it.
    replay = make_record(1, 'pre', 15)
    replay['_submission_time'] = '2026-10-20T10:00:00+00:00'
    pre.append(replay)
    q = pre_per_question(pre, {f'DEMO-{x:04d}' for x in range(1,5)}, CATALOG)
    assert q['N'].eq(4).all()
    assert q.loc[q['Pergunta'].eq('P15'), 'Acerto (%)'].iat[0] == 0.0


def test_suspected_duplicate_fullname_institution_only():
    pre, _ = demo_data()
    pre[0]['nome_completo'] = 'Maria   Sança'
    other = make_record(7, 'pre', 7)
    other['instituicao'] = 'inde'
    other['instituicao_label'] = 'INDE'
    other['nome_completo'] = 'MARIA SANÇA'
    pre.append(other)
    ids = {r['participante_id'] for r in pre}
    suspects = suspected_duplicate_names(pre, ids)
    assert len(suspects) == 1
    assert suspects.iloc[0]['Registos'] == 2
    assert normalize_person_name('João  SANCÁ') == 'joao sanca'


def test_missing_names_and_other_institutions_not_reported():
    pre, _ = demo_data()
    pre[0]['nome_completo'] = 'Maria Silva'
    pre[1]['nome_completo'] = 'Maria Silva'
    pre[1]['instituicao'] = 'dgebs'
    pre[1]['instituicao_label'] = 'DGEBS'
    assert suspected_duplicate_names(pre, {x['participante_id'] for x in pre}).empty
