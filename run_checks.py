import ast
import asyncio
from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import time
import types
import unittest
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
VARIANT = sys.argv[1]
assert VARIANT in {'baseline','fixed'}
SNAPSHOT = ROOT / VARIANT
sys.dont_write_bytecode = True
sys.path.insert(0, str(SNAPSHOT))
os.environ.update({
    'LANGCHAIN_TRACING_V2':'false',
    'LANGSMITH_TRACING':'false',
    'HF_HUB_OFFLINE':'1',
    'TRANSFORMERS_OFFLINE':'1',
    'ANONYMIZED_TELEMETRY':'False',
})

EVENTS = []
DENIED_NETWORK = []
_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex

def _allow_local(address):
    return isinstance(address, tuple) and address[0] in {'127.0.0.1','::1','localhost'}

def guarded_connect(self, address):
    if _allow_local(address):
        return _original_connect(self, address)
    DENIED_NETWORK.append(str(address))
    raise AssertionError('External networking is disabled in this test harness')

def guarded_connect_ex(self, address):
    if _allow_local(address):
        return _original_connect_ex(self, address)
    DENIED_NETWORK.append(str(address))
    raise AssertionError('External networking is disabled in this test harness')

socket.socket.connect = guarded_connect
socket.socket.connect_ex = guarded_connect_ex

def module(name, **attributes):
    item = types.ModuleType(name)
    item.__dict__.update(attributes)
    sys.modules[name] = item
    return item

for name in ['app.plugins','app.plugins.travel_assistant','app.plugins.novel_writer',
             'app.plugins.finance_assistant','app.data','app.data.novel_settings']:
    item = module(name)
    item.__path__ = []

async def fake_travel(user_input, session_id):
    EVENTS.append({'kind':'travel_stub','session_id':session_id})
    return 'SYNTHETIC_TRAVEL_REPLY'

def fake_get_llm():
    EVENTS.append({'kind':'get_llm_stub'})
    return object()

module('app.engine.llm_client', get_llm=fake_get_llm)
module('app.plugins.travel_assistant.graph', run_travel_agent=fake_travel)
module('app.plugins.novel_writer.prompts', NOVEL_WRITER_PROMPT='SYNTHETIC_PROMPT')
module('app.plugins.finance_assistant.prompts', FINANCE_ASSISTANT_PROMPT='SYNTHETIC_PROMPT')
module('app.plugins.finance_assistant.tools', FINANCE_TOOLS=[])
module('app.data.novel_settings.rag_tool', retrieve_novel_settings=lambda query:'SYNTHETIC_RAG')

from fastapi.testclient import TestClient
from app.engine.guardrail import guardrail_node
import app.engine.agent_executor as engine
import app.main as api

class FakeReactAgent:
    async def ainvoke(self, inputs, config):
        EVENTS.append({'kind':'react_agent_stub','content':inputs['messages'][0].content,
                       'thread_id':config['configurable']['thread_id']})
        return {'messages':[types.SimpleNamespace(content='SYNTHETIC_AGENT_REPLY')]}

OBSERVATIONS = {}
NODE = os.environ.get('AGENT_TEST_NODE') or shutil.which('node')
if not NODE:
    raise RuntimeError('Node.js is required; install Node.js 22 or set AGENT_TEST_NODE')

def configured_client():
    EVENTS.clear()
    engine.create_react_agent = MagicMock(return_value=FakeReactAgent())
    async def classify(message):
        EVENTS.append({'kind':'classify_stub','message':message})
        return 'finance_assistant'
    api.classify_intent = AsyncMock(side_effect=classify)
    return TestClient(api.app, raise_server_exceptions=False)

class AgentChecks(unittest.TestCase):
    def test_01_guardrail_rules_and_normal_input(self):
        cases = [
            ('请介绍指数基金','finance_assistant',True,''),
            ('帮我查天气','travel_assistant',True,''),
            ('内幕交易','finance_assistant',False,'金融合规'),
            ('保证暴利','finance_assistant',False,'金融合规'),
            ('极度虐主','novel_writer',False,'网文风控'),
            ('全员黑化','novel_writer',False,'网文风控'),
        ]
        for message, plugin, safe, reason in cases:
            with self.subTest(message=message):
                result = asyncio.run(guardrail_node({'user_input':message,'plugin_name':plugin,'session_id':'case'}))
                self.assertEqual(result['is_safe'],safe)
                self.assertIn(reason,result['risk_reason'])

    def test_02_multiple_rules_have_documented_current_precedence(self):
        result = asyncio.run(guardrail_node({'user_input':'内幕交易与全员黑化','plugin_name':'finance_assistant','session_id':'mixed'}))
        self.assertFalse(result['is_safe'])
        self.assertIn('网文风控',result['risk_reason'])
        OBSERVATIONS['multiple_rule_reason']='Novel rule overwrites finance reason; desired precedence needs product confirmation.'

    def test_03_blocked_graph_skips_agent_execution(self):
        configured_client()
        result = asyncio.run(engine.run_agent('内幕交易','finance_assistant','blocked-session'))
        self.assertIn('拦截',result)
        engine.create_react_agent.assert_not_called()
        self.assertFalse(any(event['kind']=='get_llm_stub' for event in EVENTS))

    def test_04_allowed_graph_preserves_session_and_string_api(self):
        configured_client()
        result = asyncio.run(engine.run_agent('介绍指数基金','finance_assistant','session-explicit'))
        self.assertEqual(result,'SYNTHETIC_AGENT_REPLY')
        calls = [event for event in EVENTS if event['kind']=='react_agent_stub']
        self.assertEqual(calls,[{'kind':'react_agent_stub','content':'介绍指数基金','thread_id':'session-explicit'}])

    def test_05_api_rejects_invalid_request_before_model_routing(self):
        client = configured_client()
        for payload in [{},{'message':None},{'message':[]}]:
            with self.subTest(payload=payload):
                response = client.post('/api/chat',json=payload)
                self.assertEqual(response.status_code,422)
        api.classify_intent.assert_not_awaited()

    def test_06_api_success_and_session_transmission(self):
        client = configured_client()
        response = client.post('/api/chat',json={'message':'介绍指数基金','session_id':'api-session'})
        self.assertEqual(response.status_code,200)
        data = response.json()
        self.assertEqual(data['reply'],'SYNTHETIC_AGENT_REPLY')
        self.assertEqual(data['plugin_used'],'finance_assistant')
        self.assertTrue(any(event.get('thread_id')=='api-session' for event in EVENTS))
        OBSERVATIONS['successful_response_keys']=sorted(data)

    def test_07_blocked_api_exposes_guardrail_contract(self):
        client = configured_client()
        response = client.post('/api/chat',json={'message':'内幕交易','session_id':'blocked-api-session'})
        self.assertEqual(response.status_code,200)
        data = response.json()
        self.assertIn('拦截',data['reply'])
        OBSERVATIONS['blocked_api_response'] = data
        self.assertIn('is_safe',data,'Blocked result loses safety state required by the frontend warning branch')
        self.assertIs(data['is_safe'],False)
        self.assertTrue(data['risk_reason'])

    def test_08_frontend_hook_preserves_blocked_state(self):
        completed = subprocess.run([NODE,str(ROOT/'test_frontend_hook.cjs'),
                                    str(SNAPSHOT/'frontend/src/hooks/useAgentChat.ts')],
                                   capture_output=True,text=True,encoding='utf-8',timeout=15,cwd=ROOT)
        self.assertEqual(completed.returncode,0,completed.stderr)
        data = json.loads(completed.stdout)
        OBSERVATIONS['frontend_hook_state']=data
        self.assertIs(data['blocked']['is_safe'],False,'Hook overwrites an explicit blocked flag with true')
        self.assertEqual(data['blocked']['risk_reason'],'synthetic block')
        self.assertIs(data['allowed']['is_safe'],True)

    def test_09_existing_memory_probe_targets_live_api_route(self):
        tree = ast.parse((SNAPSHOT/'test_memory.py').read_text(encoding='utf-8'))
        base_url = next(ast.literal_eval(node.value) for node in tree.body
                        if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='BASE_URL' for target in node.targets))
        path = urlsplit(base_url).path
        response = configured_client().post(path,json={'message':'介绍指数基金','session_id':'probe-session'})
        OBSERVATIONS['memory_probe']={'path':path,'http_status':response.status_code}
        self.assertEqual(response.status_code,200,'Existing probe targets a route not registered by the current app')

    def test_10_routing_before_guardrail_and_exception_behavior(self):
        client = configured_client()
        blocked = client.post('/api/chat',json={'message':'内幕交易','session_id':'ordering-session'})
        self.assertEqual(blocked.status_code,200)
        api.classify_intent.assert_awaited_once()
        engine.create_react_agent.assert_not_called()
        OBSERVATIONS['blocked_request_classifier_awaits']=api.classify_intent.await_count
        api.classify_intent = AsyncMock(side_effect=TimeoutError('synthetic model timeout'))
        failure = client.post('/api/chat',json={'message':'介绍指数基金','session_id':'failure-session'})
        self.assertEqual(failure.status_code,500)
        OBSERVATIONS['upstream_timeout']={'http_status':failure.status_code,'body':failure.text,
                                         'classification':'Observed behavior; desired degradation and error contract need product confirmation.'}

class RecordedResult(unittest.TextTestResult):
    records = []
    def startTest(self,test):
        self._started=time.perf_counter()
        super().startTest(test)
    def addSuccess(self,test):
        self.records.append({'test':test.id(),'status':'passed','seconds':round(time.perf_counter()-self._started,4)})
        super().addSuccess(test)
    def addFailure(self,test,err):
        self.records.append({'test':test.id(),'status':'failed','seconds':round(time.perf_counter()-self._started,4),
                             'detail':self._exc_info_to_string(err,test)})
        super().addFailure(test,err)
    def addError(self,test,err):
        self.records.append({'test':test.id(),'status':'error','seconds':round(time.perf_counter()-self._started,4),
                             'detail':self._exc_info_to_string(err,test)})
        super().addError(test,err)

log=io.StringIO()
with redirect_stdout(log),redirect_stderr(log):
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(AgentChecks))
(ROOT/f'{VARIANT}_raw.log').write_text(log.getvalue().replace(str(ROOT),'<repo>'),encoding='utf-8')
summary={
    'variant':VARIANT,'tests_run':result.testsRun,'passed':result.testsRun-len(result.failures)-len(result.errors),
    'failed':len(result.failures),'errors':len(result.errors),'tests':result.records,
    'observations':OBSERVATIONS,'denied_external_network_attempts':DENIED_NETWORK,
    'scope':'Real snapshot FastAPI, Pydantic validation, LangGraph guardrail workflow; fake model, planner and external tools; real TS hook in a fake React/fetch VM.',
    'limitations':['No live LLM evaluation','No RAG retrieval or real Chroma data','No browser rendering or DOM test','No real model token or latency measurement','Not evidence of historical user testing work'],
}
for entry in summary['tests']:
    if 'detail' in entry:
        entry['detail'] = entry['detail'].replace(str(ROOT), '<repo>')
(ROOT/f'{VARIANT}_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'variant':VARIANT,'tests_run':result.testsRun,'passed':summary['passed'],
                  'failed':summary['failed'],'errors':summary['errors'],'external_attempts':len(DENIED_NETWORK)},ensure_ascii=False))
sys.exit(0 if result.wasSuccessful() else 1)
