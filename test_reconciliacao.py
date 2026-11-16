import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from demo import make_record
from analysis import build_analysis, score_record
from reconciliacao import reconcile, read_decisions, decisions_csv
from individual import participant_question_detail
from quality import audit_records, can_delete_now


class ReconciliationTests(unittest.TestCase):
    def two_pre(self, same_id=False, same_answers=False):
        a=make_record(1,'pre',6)
        b=make_record(2,'pre',6 if same_answers else 12)
        b['nome_completo']=a['nome_completo']
        b['instituicao']=a['instituicao']
        b['instituicao_label']=a['instituicao_label']
        b['funcao']=a['funcao']
        b['_submission_time']='2026-10-18T16:15:00+00:00'
        if same_id:
            b['participante_id']=a['participante_id']
        return a,b

    def test_second_pre_not_counted_automatically(self):
        a,b=self.two_pre()
        result=reconcile([a,b],[])
        self.assertEqual(len(result['candidates']),1)
        self.assertEqual(len(result['approved']),0)
        analysis=build_analysis(result['pre'],result['pos'])
        self.assertEqual(analysis['participants']['Pós (%)'].notna().sum(),0)

    def test_approved_second_pre_as_post_cross_id(self):
        a,b=self.two_pre()
        dec=[{'pre_id_original':a['_id'],'pre_id_segundo':b['_id'],'decisao':'usar_como_pos',
              'responsavel':'Formador','nota':'Após sessão'}]
        result=reconcile([a,b],[],dec)
        self.assertEqual(len(result['pre']),1)
        self.assertEqual(len(result['pos']),1)
        analysis=build_analysis(result['pre'],result['pos'])
        self.assertEqual(len(analysis['participants']),1)
        row=analysis['participants'].iloc[0]
        self.assertEqual(row['Estado'],'Pré e pós recuperados')
        self.assertEqual(row['Origem pós'],'2.º pré validado')
        self.assertEqual(row['Acertos pré'],6)
        self.assertEqual(row['Acertos pós'],12)
        self.assertAlmostEqual(row['Evolução (pp)'],40,places=1)
        self.assertEqual(len(analysis['questions']),15)
        self.assertEqual(len(participant_question_detail(result['pre'], result['pos'],
          a['participante_id'],[{'prompt':str(n)} for n in range(15)])),15)
        self.assertIsNone(can_delete_now('pre',b['_id'],[a,b],[],dec))

    def test_approved_second_pre_same_id(self):
        a,b=self.two_pre(same_id=True)
        dec=[{'pre_id_original':a['_id'],'pre_id_segundo':b['_id'],'decisao':'usar_como_pos'}]
        result=reconcile([a,b],[],dec)
        self.assertEqual(len(result['approved']),1)
        self.assertEqual(len(build_analysis(result['pre'],result['pos'])['participants']),1)

    def test_redundant_exact_duplicate_suppressed(self):
        a,b=self.two_pre(same_answers=True)
        b['_submission_time']='2026-10-18T10:08:00+00:00'
        result=reconcile([a,b],[])
        self.assertEqual(len(result['duplicate_obvious']),1)
        self.assertEqual(len(result['pre']),1)
        self.assertEqual(len(result['candidates']),0)
        self.assertEqual(len(build_analysis(result['pre'],[])['participants']),1)

    def test_no_delete_different_answers_even_same_id(self):
        a,b=self.two_pre(same_id=True)
        report=audit_records([a,b],[])
        self.assertFalse(report['candidates'][('pre',b['_id'])]['eligible'])
        self.assertIsNone(can_delete_now('pre',b['_id'],[a,b],[]))

    def test_no_convert_if_real_post_exists(self):
        a,b=self.two_pre()
        actual=make_record(1,'pos',14)
        decision=[{'pre_id_original':a['_id'],'pre_id_segundo':b['_id'],'decisao':'usar_como_pos'}]
        result=reconcile([a,b],[actual],decision)
        self.assertEqual(len(result['candidates']),0)
        self.assertEqual(len(result['approved']),0)
        self.assertEqual(len(result['blocked']),1)

    def test_no_convert_short_gap(self):
        a,b=self.two_pre()
        b['_submission_time']='2026-10-18T10:10:00+00:00'
        result=reconcile([a,b],[],[{'pre_id_original':a['_id'],'pre_id_segundo':b['_id'],'decisao':'usar_como_pos'}])
        self.assertEqual(len(result['candidates']),0)
        self.assertEqual(len(result['approved']),0)

    def test_no_convert_three_pre(self):
        a,b=self.two_pre()
        c=dict(b);c['_id']=333;c['_submission_time']='2026-10-18T20:00:00+00:00'
        result=reconcile([a,b,c],[])
        self.assertEqual(len(result['candidates']),0)

    def test_decision_roundtrip(self):
        items=[{'pre_id_original':4,'pre_id_segundo':22,'decisao':'usar_como_pos','responsavel':'Técnico','nota':'OK','data_decisao':'2026-11-16'}]
        self.assertEqual(read_decisions(decisions_csv(items))[0]['decisao'],'usar_como_pos')
        self.assertEqual(read_decisions(decisions_csv(items))[0]['pre_id_segundo'],'22')

    def test_cannot_delete_lone_original(self):
        a=make_record(1,'pre',6)
        self.assertIsNone(can_delete_now('pre',a['_id'],[a],[]))

if __name__=='__main__':unittest.main()
