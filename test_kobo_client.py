import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kobo_client import fetch_submissions, KoboAPIError

class Resp:
    def __init__(self, body, code=200):self.body=body;self.status_code=code
    def json(self):return self.body

class MockSession:
    def __init__(self, responses): self.headers={};self.responses=list(responses);self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def get(self, url, **kwargs):
        self.calls.append((url,kwargs))
        return self.responses.pop(0)

class APITests(unittest.TestCase):
    def test_pagination(self):
        url='https://kf.kobo.ucp-pch.org/api/v2/assets/a9UStPiv4QDyzfZeHiBzwu/data/'
        client=MockSession([Resp({'results':[{'_id':1}],'next':url+'?start=1000'}),Resp({'results':[{'_id':2}],'next':None})])
        with patch('kobo_client.requests.Session', return_value=client):
            data=fetch_submissions('https://kf.kobo.ucp-pch.org','a9UStPiv4QDyzfZeHiBzwu','TEST_NOT_A_REAL_TOKEN')
        self.assertEqual(len(data),2)
        self.assertTrue(client.calls[0][1]['params']['limit']==1000)
        self.assertTrue(client.calls[1][1]['params'] is None)

    def test_no_redirect_to_third_party(self):
        client=MockSession([Resp({'results':[],'next':'https://example.com/attack'})])
        with patch('kobo_client.requests.Session', return_value=client):
            with self.assertRaises(KoboAPIError):
                fetch_submissions('https://kf.kobo.ucp-pch.org','a9UStPiv4QDyzfZeHiBzwu','TEST_NOT_A_REAL_TOKEN')

    def test_invalid_token_response(self):
        client=MockSession([Resp({'detail':'Invalid token'},401)])
        with patch('kobo_client.requests.Session', return_value=client):
            with self.assertRaisesRegex(KoboAPIError,'Acesso recusado'):
                fetch_submissions('https://kf.kobo.ucp-pch.org','a9UStPiv4QDyzfZeHiBzwu','TEST_NOT_A_REAL_TOKEN')

if __name__=='__main__':unittest.main()
