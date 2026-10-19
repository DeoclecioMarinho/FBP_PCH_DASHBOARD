import sys, unittest
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from kobo_client import delete_submission, KoboAPIError

class DeleteAPITests(unittest.TestCase):
    @patch('kobo_client.requests.delete')
    def test_delete_one_submission_endpoint(self, mocked):
        mocked.return_value=Mock(status_code=204)
        result=delete_submission('https://kf.kobo.ucp-pch.org','testUidXYZ',345,'not-a-real-token')
        self.assertTrue(result)
        args,kwargs=mocked.call_args
        self.assertEqual(args[0],'https://kf.kobo.ucp-pch.org/api/v2/assets/testUidXYZ/data/345/')
        self.assertFalse(kwargs['allow_redirects'])

    @patch('kobo_client.requests.delete')
    def test_no_delete_on_403(self, mocked):
        mocked.return_value=Mock(status_code=403)
        with self.assertRaises(KoboAPIError):
            delete_submission('https://kf.kobo.ucp-pch.org','testUidXYZ',345,'not-a-real-token')

    def test_reject_nonpositive_ids(self):
        with self.assertRaises(KoboAPIError):
            delete_submission('https://kf.kobo.ucp-pch.org','testUidXYZ',0,'token')

if __name__=='__main__':unittest.main()
