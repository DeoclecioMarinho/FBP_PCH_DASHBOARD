import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from demo import make_record
from quality import audit_records,can_delete_now,backup_json

class QualityTests(unittest.TestCase):
    def test_same_id_duplicate_keeps_first(self):
        p1=make_record(1,'pre',6)
        p2=dict(p1); p2['_id']=999;p2['_submission_time']='2026-10-19T20:00:00+00:00'
        report=audit_records([p1,p2],[])
        self.assertEqual(report['n_repeat_groups'],1)
        self.assertFalse(report['candidates'].get(('pre',p1['_id']),{}).get('eligible',False))
        self.assertTrue(report['candidates'][('pre',999)]['eligible'])
        self.assertIsNotNone(can_delete_now('pre',999,[p1,p2],[]))
        self.assertIsNone(can_delete_now('pre',p1['_id'],[p1,p2],[]))

    def test_recheck_blocks_last_submission(self):
        pre=make_record(1,'pre',5)
        self.assertIsNone(can_delete_now('pre',pre['_id'],[pre],[]))

    def test_different_id_same_name_is_suspected(self):
        a=make_record(1,'pre',5)
        b=make_record(2,'pre',4)
        b['nome_completo']=a['nome_completo'];b['instituicao']=a['instituicao'];b['instituicao_label']=a['instituicao_label']
        report=audit_records([a,b],[])
        self.assertEqual(report['n_name_groups'],1)
        self.assertTrue(report['candidates'][('pre',b['_id'])]['eligible'])
        post=make_record(2,'pos',10)
        report2=audit_records([a,b],[post])
        self.assertFalse(report2['candidates'][('pre',b['_id'])]['eligible'])

    def test_same_name_different_edition_is_not_duplicate(self):
        a=make_record(1,'pre',5)
        b=make_record(2,'pre',7,edit='0002')
        b['nome_completo']=a['nome_completo'];b['instituicao']=a['instituicao'];b['instituicao_label']=a['instituicao_label']
        self.assertEqual(audit_records([a,b],[])['n_name_groups'],0)

    def test_json_backup_contains_submission(self):
        a=make_record(1,'pre',5);b=dict(a);b['_id']=999
        r=audit_records([a,b],[])['candidates'][('pre',999)]
        self.assertIn(b'"kobo_id": 999',backup_json(r))

if __name__=='__main__':unittest.main()
