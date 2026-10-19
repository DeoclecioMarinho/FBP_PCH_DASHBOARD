"""Fichas de aprendizagem por participante, sem alterar a base de dados Kobo."""
from analysis import ANSWER_KEY, field, first_selected, normalize_id, score_record, sort_key


def selected_records(pre_raw, pos_raw, participant_id):
    """Mesmas regras de escolha usadas na análise agregada.

    Primeiro pré completo; primeiro pós completo com identidade confirmada.
    Um pós inválido não é tratado como avaliação final.
    """
    pre_candidates = [r for r in pre_raw if normalize_id(r) == participant_id]
    pos_candidates = sorted([r for r in pos_raw if normalize_id(r) == participant_id], key=sort_key)
    pre = first_selected(pre_candidates) if pre_candidates else None
    valid_posts = [r for r in pos_candidates if score_record(r)['completo']
                   and str(field(r, 'confirma_identidade') or '').strip().lower() == 'sim']
    post = valid_posts[0] if valid_posts else None
    return pre, post


def participant_question_detail(pre_raw, pos_raw, participant_id, question_catalog):
    """Lista das 15 questões, respostas originais, correção e situação de aprendizagem."""
    pre, post = selected_records(pre_raw, pos_raw, participant_id)
    if pre is None:
        return []
    a = score_record(pre)
    b = score_record(post) if post else None
    results = []
    for n, correct_choice in ANSWER_KEY.items():
        key = f'q{n:02d}'
        pa = a['responses'][key]
        pb = b['responses'][key] if b else ''
        correct_pre = a['correct'][key]
        correct_post = b['correct'][key] if b else None
        if correct_pre is None:
            evolution = 'Sem resposta inicial'
        elif correct_post is None:
            evolution = 'Pós pendente'
        elif not correct_pre and correct_post:
            evolution = 'Melhorou'
        elif correct_pre and not correct_post:
            evolution = 'Regrediu'
        else:
            evolution = 'Manteve'
        results.append({
            'Pergunta': f'P{n:02d}',
            'Enunciado': question_catalog[n-1]['prompt'],
            'Resposta pré': pa.upper() if pa else '—',
            'Pré': '✓ Certa' if correct_pre is True else ('✕ Errada' if correct_pre is False else '—'),
            'Resposta pós': pb.upper() if pb else '—',
            'Pós': '✓ Certa' if correct_post is True else ('✕ Errada' if correct_post is False else '—'),
            'Evolução': evolution,
            'Correta': correct_choice.upper(),
        })
    return results


def compact_status(raw):
    states = {
        'Pré e pós concluídos': 'Concluído',
        'Pós-teste pendente': 'Pós pendente',
        'Pós-teste incompleto': 'Pós incompleto',
        'Pré-teste incompleto': 'Pré incompleto',
        'Identidade não confirmada': 'Confirmar identidade',
    }
    return states.get(raw, raw)


def short_institution(label):
    """Só abrevia o rótulo visível; conserva texto integral nos ficheiros exportados."""
    return str(label or '—').split(' — ', 1)[0]
