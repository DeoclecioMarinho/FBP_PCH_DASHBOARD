import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import build_analysis, score_record, field
from demo import demo_data, make_record

class TestFBP(unittest.TestCase):
    def test_demo_pair_coverage(self):
        pre,pos=demo_data()
        info=build_analysis(pre,pos)
        df=info['participants']
        self.assertEqual(len(df),4)
        self.assertEqual((df['Estado']=='Pré e pós concluídos').sum(),3)
        first=df[df['participante_id']=='DEMO-0001'].iloc[0]
        self.assertEqual(first['Acertos pré'],6)
        self.assertEqual(first['Acertos pós'],12)
        self.assertEqual(first['Ganho (acertos)'],6)
        self.assertEqual(first['Evolução (pp)'],40.0)
        self.assertEqual(len(info['questions']),3*15)

    def test_group_paths(self):
        record={'avaliacao/q01':'b','avaliacao/q02':'c','_id':1}
        self.assertEqual(field(record,'q01'),'b')
        self.assertEqual(field(record,'q02'),'c')
        self.assertEqual(score_record(record)['respondidas'],2)
        self.assertFalse(score_record(record)['completo'])

    def test_orphan_and_duplicates(self):
        pre,pos=demo_data()
        pos.append(make_record(99,'pos',15))
        pos.append(make_record(1,'pos',15))
        info=build_analysis(pre,pos)
        self.assertEqual(info['orphan_post_count'],1)
        self.assertTrue(any(info['anomalies']['Tipo'].str.contains('repetido')))
        selected=info['participants'].set_index('participante_id').loc['DEMO-0001']
        self.assertEqual(selected['Acertos pós'],12) # primeira resposta completa

    def test_discrepancy_kobo(self):
        rec=make_record(1,'pre',6)
        rec['total_acertos']=10
        self.assertTrue(score_record(rec)['inconsistencia_nota'])

    def test_rejected_confirmation(self):
        pre,pos=demo_data()
        pos[0]['confirma_identidade']='nao'
        info=build_analysis(pre,pos)
        states=info['participants'].set_index('participante_id')['Estado']
        self.assertEqual(states.loc['DEMO-0001'],'Identidade não confirmada')

if __name__=='__main__':unittest.main()
