from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4
from urllib.request import Request, build_opener, ProxyHandler
urlopen = build_opener(ProxyHandler({})).open
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / 'project' / 'backend'

class RunningServer:
    def __init__(self, module, extra_env):
        self.temp = tempfile.TemporaryDirectory()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.shutdown_token = uuid4().hex
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', QA_SHUTDOWN_TOKEN=self.shutdown_token, **extra_env)
        if module == 'main:app':
            env['DATABASE_URL'] = 'sqlite://' + (Path(self.temp.name) / 'demo.sqlite3').as_posix()
            env['UPLOAD_DIR'] = str(Path(self.temp.name) / 'uploads')
        self.log = open(Path(self.temp.name) / 'server.log', 'w+', encoding='utf-8', errors='replace')
        self.process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'test_server.py'), module, str(self.port)], cwd=BACKEND, env=env,
            stdout=self.log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(200):
                if self.process.poll() is not None:
                    self.log.seek(0)
                    raise RuntimeError(self.log.read())
                try:
                    with urlopen(self.url + '/openapi.json', timeout=1) as response:
                        if response.status == 200:
                            return
                except (URLError, OSError):
                    time.sleep(0.1)
            raise RuntimeError('Local application did not become ready')
        except BaseException:
            self.close()
            raise

    def request(self, path, data=None, method=None, headers=None, raw=None):
        if raw is None and data is not None:
            raw = json.dumps(data).encode('utf-8')
        headers = headers or {'Content-Type': 'application/json'}
        request = Request(self.url + path, data=raw, method=method, headers=headers)
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            if 'application/json' in response.headers.get('Content-Type', ''):
                payload = json.loads(payload)
            return response.status, payload

    def close(self):
        if hasattr(self, 'process') and self.process.poll() is None:
            try:
                self.request('/__qa_shutdown__', method='POST', raw=b'',
                    headers={'X-QA-Shutdown': self.shutdown_token})
                self.process.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                self.process.wait(timeout=5)
                raise
        self.log.close()
        self.temp.cleanup()

class ApplicationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = RunningServer('app.main:app', {'DEMO_MODE': 'true', 'DEEPSEEK_API_KEY': '', 'TAVILY_API_KEY': ''})

    @classmethod
    def tearDownClass(cls):
        cls.server.close()

    def chat(self, message):
        status, payload = self.server.request('/api/chat', {'message': message, 'session_id': 'qa-http-demo'})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['mode'], 'demo')
        return payload

    def test_01_health_and_default_chat(self):
        self.assertEqual(self.server.request('/health'), (200, {'status': 'ok', 'mode': 'demo'}))
        response = self.chat('你好')
        self.assertEqual(response['plugin_used'], 'default')
        self.assertIn('演示模式', response['reply'])

    def test_02_real_travel_graph(self):
        response = self.chat('安排两天旅行')
        self.assertEqual(response['plugin_used'], 'travel_assistant')
        self.assertIn('第一天', response['reply'])
        self.assertIn('调查节点提供', response['reply'])
        self.assertTrue(response['is_safe'])

    def test_03_novel_public_sample_and_finance(self):
        novel = self.chat('给我小说设定')
        self.assertEqual(novel['plugin_used'], 'novel_writer')
        self.assertIn('demo_setting.md', novel['reply'])
        self.assertIn('借书卡', novel['reply'])
        finance = self.chat('查询 AAPL 股票行情')
        self.assertEqual(finance['plugin_used'], 'finance_assistant')
        self.assertIn('不提供虚构报价', finance['reply'])

    def test_04_blocked_contract_reaches_http(self):
        response = self.chat('推荐个股保证暴利')
        self.assertFalse(response['is_safe'])
        self.assertTrue(response['risk_reason'])
        self.assertIn(response['risk_reason'], response['reply'])

    def test_05_request_schema_and_current_route(self):
        self.assertEqual(self.server.request('/api/chat', {'message': ''})[0], 422)
        self.assertEqual(self.server.request('/api/chat', {})[0], 422)
        self.assertEqual(self.server.request('/api/v1/chat', {'message': 'hello'})[0], 404)

    def test_06_live_mode_missing_key_is_actionable(self):
        server = RunningServer('app.main:app', {'DEMO_MODE': 'false', 'DEEPSEEK_API_KEY': '', 'TAVILY_API_KEY': ''})
        try:
            status, payload = server.request('/api/chat', {'message': 'hello'})
            self.assertEqual(status, 503)
            self.assertIn('运行配置', payload['detail'])
        finally:
            server.close()

if __name__ == '__main__':
    unittest.main(verbosity=2)
