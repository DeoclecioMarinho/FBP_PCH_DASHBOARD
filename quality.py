"""Auditoria por submissão e regras de eliminação segura de duplicados."""
from collections import defaultdict
import json
from analysis import field, normalize_id, score_record, institution_from, first_selected, sort_key
from monitor import normalize_person_name


def rec_id(record):
    value = field(record, '_id')
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _post_selected(records):
    recs = sorted(records, key=sort_key)
    confirmed = [x for x in recs if score_record(x)['completo'] and str(field(x, 'confirma_identidade') or '').lower() == 'sim']
    return confirmed[0] if confirmed else first_selected(recs)


def audit_records(raw_pre, raw_pos):
    """Devolve grupos de duplicados, mantendo IDs reais de submissão do Kobo.

    Grupos de nome são meros indícios; não são fundidos automaticamente.
    """
    groups = []
    rows = []
    by_pre_pid = defaultdict(list)
    by_pos_pid = defaultdict(list)
    for phase, records in [('pre', raw_pre), ('pos', raw_pos)]:
        for rec in records:
            pid = normalize_id(rec)
            name = str(field(rec, 'nome_completo') or field(rec, 'nome_pre') or '') if phase=='pre' else ''
            row = {'phase': phase, 'record': rec, 'id': rec_id(rec), 'pid': pid,
                   'time': str(field(rec, '_submission_time') or field(rec, 'fim') or ''),
                   'score': score_record(rec)}
            rows.append(row)
            if pid:
                (by_pre_pid if phase == 'pre' else by_pos_pid)[pid].append(row)
    for phase, mapping in [('pre',by_pre_pid),('pos',by_pos_pid)]:
        for pid, bucket in mapping.items():
            if len(bucket) < 2:
                continue
            preferred = first_selected([x['record'] for x in bucket]) if phase=='pre' else _post_selected([x['record'] for x in bucket])
            keeper_id = rec_id(preferred)
            groups.append({'key': f'{phase}:pid:{pid}', 'type':'ID repetido', 'phase':phase,
                           'label':f"{'Pré' if phase == 'pre' else 'Pós'} · {pid}",
                           'rows':bucket, 'keeper_id':keeper_id,
                           'reason':'Várias submissões com o mesmo identificador.'})
    # Homónimos + instituição: criar grupos no PRÉ com IDs distintos.
    by_person = defaultdict(list)
    for pid, bucket in by_pre_pid.items():
        canonical = first_selected([x['record'] for x in bucket])
        chosen = next((r for r in bucket if r['id']==rec_id(canonical)),bucket[0])
        name = str(field(canonical, 'nome_completo') or '').strip()
        inst = institution_from(canonical)
        norm = normalize_person_name(name)
        if norm:
            edition = str(field(canonical, 'edicao_id') or '0001')
            by_person[(norm, normalize_person_name(inst), edition)].append((pid, chosen, name, inst))
    for _, entries in by_person.items():
        if len(entries)<2:
            continue
        keeper = min((rec for _,rec,_,_ in entries), key=lambda r: sort_key(r['record']))
        groups.append({'key': 'pre:name:'+str(keeper['id']), 'type':'Nome semelhante', 'phase':'pre',
                       'label':f"{entries[0][2]} · {entries[0][3]}",
                       'rows':[x[1] for x in entries], 'keeper_id':keeper['id'],
                       'reason':'Mesmo nome e instituição, mas IDs de participante diferentes. Confirmar se são pessoas distintas.'})
    # Todos os elegíveis em ordem; conservador nas relações pré/pós.
    by_phase_id = {(r['phase'],r['id']):r for r in rows if r['id'] is not None}
    protected = set()
    candidates = {}
    for group in groups:
        for r in group['rows']:
            key=(r['phase'],r['id'])
            if r['id'] is None:
                continue
            if r['id'] == group['keeper_id']:
                protected.add(key)
                continue
            if group['type']=='ID repetido':
                eligible=True
                reason='Existe outra submissão do mesmo formulário e identificador para conservar.'
            else:
                # Com IDs distintos, se já houver pós ligado, nunca apagar daqui.
                linked = len(by_pos_pid.get(r['pid'], []))
                eligible=(linked==0)
                reason=('Sem pós-teste associado. Confirmar manualmente a identidade.' if eligible
                        else 'Existe pós-teste associado a este ID: eliminação bloqueada.')
            previous=candidates.get(key)
            candidates[key]={'phase':r['phase'],'id':r['id'],'pid':r['pid'],
                             'eligible':bool(eligible and (previous is None or previous['eligible'])),
                             'reason':reason, 'time':r['time'], 'score':r['score']['acertos'],
                             'record':r['record']}
    for k in protected:
        if k in candidates:
            candidates[k]['eligible']=False
            candidates[k]['reason']='Submissão a conservar em outro grupo de duplicados.'
    # Segurança adicional: no máximo total -1 de cada ID, nunca uma única entrada.
    for key, c in candidates.items():
        mapping = by_pre_pid if c['phase']=='pre' else by_pos_pid
        if len(mapping.get(c['pid'],[]))==1 and (c['phase']=='pos' or not any(g['type']=='Nome semelhante' and any(r['id']==c['id'] for r in g['rows']) for g in groups)):
            c['eligible']=False
            c['reason']='Última submissão deste identificador: bloqueada.'
    return {'groups':groups,'candidates':candidates,'rows':rows,
            'n_repeat_groups':sum(g['type']=='ID repetido' for g in groups),
            'n_name_groups':sum(g['type']=='Nome semelhante' for g in groups)}


def can_delete_now(phase, submission_id, raw_pre, raw_pos):
    """Revalida cada eliminação sobre dados ACABADOS de consultar no Kobo."""
    report=audit_records(raw_pre,raw_pos)
    candidate=report['candidates'].get((phase,int(submission_id)))
    return candidate if candidate and candidate['eligible'] else None


def backup_json(candidate):
    return json.dumps({'formulario':candidate['phase'],'kobo_id':candidate['id'],
                       'dados_originais':candidate['record']}, ensure_ascii=False,indent=2,default=str).encode('utf8')
