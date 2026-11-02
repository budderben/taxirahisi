import unittest
from app import create_app

class ApkDownloadTestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config['TESTING'] = True
        cls.client = cls.app.test_client()

    def test_apk_download_endpoint(self):
        """Verify /download-apk delivers TaxRahisi.apk with correct Android package headers."""
        res = self.client.get('/download-apk')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/vnd.android.package-archive')
        content_disp = res.headers.get('Content-Disposition', '')
        self.assertIn('TaxRahisi.apk', content_disp)
        # Verify it has substantial payload size (> 4 MB)
        self.assertGreater(len(res.data), 4000000)

    def test_apk_download_alias_endpoint(self):
        """Verify /download/TaxRahisi.apk alias delivers the same package."""
        res = self.client.get('/download/TaxRahisi.apk')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, 'application/vnd.android.package-archive')

    def test_mobile_app_page(self):
        """Verify /app renders the mobile app landing and instructions page."""
        res = self.client.get('/app')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"TaxRahisi Kwenye Simu Yako ya Mkononi", res.data)
        self.assertIn(b"/download-apk", res.data)
        self.assertIn(b"Offline", res.data)

    def test_index_page_contains_download_links(self):
        """Verify home page features both the hero APK button and showcase section."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"/download-apk", res.data)
        self.assertIn(b"Pakua TaxRahisi.apk", res.data)

if __name__ == '__main__':
    unittest.main()
