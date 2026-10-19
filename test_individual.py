import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import build_analysis
from demo import demo_data, make_record
from individual import participant_question_detail, selected_records, compact_status, short_institution
import json

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS=json.loads((ROOT/'questionario.json').read_text(encoding='utf8'))['questions']

class IndividualTest(unittest.TestCase):
    def test_15_questions_and_pairing(self):
        pre,post=demo_data()
        details=participant_question_detail(pre,post,'DEMO-0001',QUESTIONS)
        self.assertEqual(len(details),15)
        self.assertEqual(details[0]['Pergunta'],'P01')
        self.assertIn('Financiamento Baseado',details[0]['Enunciado'])
        self.assertEqual(details[0]['Pré'],'✓ Certa')
        self.assertEqual(details[0]['Pós'],'✓ Certa')
        self.assertEqual(details[0]['Resposta pré'],'B')
        self.assertEqual(details[14]['Pré'],'✕ Errada')
        self.assertEqual(details[14]['Pós'],'✕ Errada')
        self.assertEqual(details[6]['Evolução'],'Melhorou')

    def test_pending_post(self):
        pre,post=demo_data()
        detail=participant_question_detail(pre,post,'DEMO-0004',QUESTIONS)
        self.assertEqual(len(detail),15)
        self.assertEqual(detail[0]['Pós'],'—')
        self.assertEqual(detail[0]['Evolução'],'Pós pendente')

    def test_not_confirmed_post_ignored(self):
        pre,post=demo_data()
        post[0]['confirma_identidade']='nao'
        _,chosen=selected_records(pre,post,'DEMO-0001')
        self.assertIsNone(chosen)
        result=participant_question_detail(pre,post,'DEMO-0001',QUESTIONS)
        self.assertEqual(result[0]['Pós'],'—')

    def test_first_valid_post_matches_aggregate(self):
        pre,post=demo_data()
        post.append(make_record(1,'pos',15))
        _,selected=selected_records(pre,post,'DEMO-0001')
        df=build_analysis(pre,post)['participants']
        row=df.set_index('participante_id').loc['DEMO-0001']
        self.assertEqual(row['Acertos pós'],12)
        self.assertEqual(selected['total_acertos'],12)

    def test_clean_labels(self):
        self.assertEqual(short_institution('UC-PCH — Unidade de Coordenação do PCH'),'UC-PCH')
        self.assertEqual(compact_status('Pós-teste pendente'),'Pós pendente')

if __name__=='__main__':unittest.main()
