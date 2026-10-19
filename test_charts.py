import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from charts import bar_figure
from monitor import pre_per_question
from demo import demo_data
from analysis import normalize_id
import json
import html

ROOT=Path(__file__).resolve().parents[1]
CAT=json.loads((ROOT/'questionario.json').read_text(encoding='utf8'))['questions']

class ChartTests(unittest.TestCase):
    def test_hover_contains_complete_question_and_axis_code(self):
        pre,_=demo_data()
        ids={normalize_id(x) for x in pre}
        qpre=pre_per_question(pre,ids,CAT)
        weakest=qpre.sort_values(['Acerto (%)','Número']).head(5)
        fig=bar_figure(weakest,'Pergunta','Acerto (%)')
        points=fig.data[0]
        self.assertTrue(all(str(code).startswith('P') for code in points.y))
        self.assertIn('customdata[0]',points.hovertemplate)
        for code,hover in zip(points.y,points.customdata):
            num=int(str(code)[1:]); original=CAT[num-1]['prompt']
            # quebras de linha no hover estão representadas por HTML <br>
            self.assertEqual(html.unescape(hover[0].replace('<br>',' ')),original)

    def test_non_question_chart_is_default_hover(self):
        import pandas as pd
        df=pd.DataFrame([{'Tema':'Conceitos','Acerto (%)':70}])
        fig=bar_figure(df,'Tema','Acerto (%)')
        self.assertNotIn('customdata[0]',fig.data[0].hovertemplate)

if __name__=='__main__':unittest.main()
