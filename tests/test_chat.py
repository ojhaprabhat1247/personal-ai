"""Isolated chat tests: no Ollama calls, personal files, or Chroma imports."""

import importlib.util
import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import anyio
from fastapi.testclient import TestClient
from starlette.requests import ClientDisconnect


APP_DIR = Path(__file__).resolve().parents[1] / "app"


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    return result


def chunk(text="", done=False):
    return {"message": {"content": text}, "done": done}


class ChatTests(unittest.TestCase):
    def setUp(self):
        self.memory = module(
            "memory", messages=[{"role": "system", "content": "legacy prompt"}],
            load_memory=Mock(), save_memory=Mock(),
        )
        self.memory.add_message = Mock(side_effect=lambda role, content:
            self.memory.messages.append({"role": role, "content": content}))
        self.profile = module(
            "profile", profile={}, load_profile=Mock(), update_profile=Mock(),
        )
        self.vector = module("vectordb", search_memory=Mock(return_value=[]), clear_memory=Mock())
        self.classifier = module(
            "memory_classifier", classify=Mock(return_value={"save": False}),
        )
        self.manager = module("memory_manager", save_memory=Mock())
        self.llm = module("llm", generate=Mock(
            return_value={"message": {"content": "A useful answer."}},
        ))
        fakes = {
            item.__name__: item for item in (
                self.memory, self.profile, self.vector, self.classifier,
                self.manager, self.llm,
            )
        }
        self.modules = {}
        # Load real application code against fake storage/providers from the start.
        # Importing the real vectordb module would create a persistent database.
        with patch.dict(sys.modules, fakes):
            for name in (
                "chat_prompts", "privacy_guard", "cloud_llm", "chat_router",
                "retriever", "chat_service", "api", "main",
            ):
                spec = importlib.util.spec_from_file_location(name, APP_DIR / f"{name}.py")
                loaded = importlib.util.module_from_spec(spec)
                sys.modules[name] = loaded
                spec.loader.exec_module(loaded)
                self.modules[name] = loaded
        self.api = self.modules["api"]
        self.service = self.api.chat_service
        self.router_module = self.modules["chat_router"]
        self.mode = self.router_module.PrivacyMode

    def test_explicit_language_directives_are_near_current_turn(self):
        prompts = self.modules["chat_prompts"]
        history = [
            {"role": "user", "content": "Use Hindi from now on."},
            {"role": "assistant", "content": "ठीक है।"},
        ]
        cases = {
            "answer in English": "Respond entirely in English using Latin script.",
            "English me do": "Respond entirely in English using Latin script.",
            "reply in English": "Respond entirely in English using Latin script.",
            "reply in Hindi": "Respond in Hindi using Devanagari script.",
            "Hindi me batao": "Respond in Hindi using Devanagari script.",
            "Hinglish me samjhao":
                "Respond in natural Hinglish using primarily Latin/Roman script.",
            "Roman Hindi me batao":
                "Respond in Hindi using Latin/Roman script, not Devanagari.",
        }

        for request, expected in cases.items():
            with self.subTest(request=request):
                result = prompts.build_chat_messages(request, "{}", history, [])

                self.assertEqual(result[0]["role"], "system")
                self.assertIn(
                    "Never invent unavailable personal or document information",
                    result[0]["content"],
                )
                self.assertEqual(result[2:4], history)

                directive = result[-2]
                self.assertEqual(directive["role"], "system")
                self.assertIn(
                    "Current-turn response requirements",
                    directive["content"],
                )
                self.assertIn(expected, directive["content"])

                self.assertEqual(
                    result[-1],
                    {"role": "user", "content": request},
                )
                self.assertEqual(
                    sum(m["content"] == request for m in result),
                    1,
                )

    def test_no_turn_directive_when_user_did_not_request_one(self):
        prompts = self.modules["chat_prompts"]
        history = [
            {"role": "user", "content": "Earlier question"},
            {"role": "assistant", "content": "Earlier answer"},
        ]

        result = prompts.build_chat_messages(
            "Define science.", "{}", history, []
        )

        self.assertEqual(
            [m["role"] for m in result],
            ["system", "system", "user", "assistant", "user"],
        )
        self.assertEqual(result[2:-1], history)
        self.assertEqual(
            result[-1],
            {"role": "user", "content": "Define science."},
        )
        self.assertIn(
            "normally answer in 1 to 3 sentences",
            result[0]["content"],
        )

    def test_explicit_hinglish_and_length_reach_both_generation_paths(self):
        request = (
            "Binary search mujhe simple Hinglish me samjhao, "
            "3 lines se zyada nahi."
        )
        history = [
            {"role": "user", "content": "Hindi me batao"},
            {"role": "assistant", "content": "यह पिछला हिंदी उत्तर है।"},
        ]

        submitted_contexts = []

        for streaming in (False, True):
            with self.subTest(streaming=streaming):
                self.memory.messages[1:] = history
                self.llm.generate.return_value = (
                    iter([chunk("Mock output"), chunk(done=True)])
                    if streaming
                    else {"message": {"content": "Mock output"}}
                )

                if streaming:
                    list(self.service.stream_chat(request))
                else:
                    self.service.chat(request)

                context = self.llm.generate.call_args.kwargs["messages"]
                submitted_contexts.append(context)

                directive = context[-2]
                self.assertEqual(directive["role"], "system")
                self.assertIn(
                    "Respond in natural Hinglish using primarily Latin/Roman script.",
                    directive["content"],
                )
                self.assertIn(
                    "Use no more than 3 lines.",
                    directive["content"],
                )

                self.assertEqual(context[2:-2], history)
                self.assertEqual(
                    context[-1],
                    {"role": "user", "content": request},
                )
                self.assertEqual(
                    sum(m["content"] == request for m in context),
                    1,
                )

        self.assertEqual(submitted_contexts[0], submitted_contexts[1])

    def test_context_bounds_history_and_deduplicates_only_background(self):
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"turn {i}"}
            for i in range(14)
        ]
        # Intentional repeated prior user turns must remain intact.
        history[8]["content"] = history[10]["content"] = "Same question"
        retrieved = [
            {"text": "Current question"}, {"text": "  SAME   QUESTION "},
            {"text": "I enjoy cycling"}, {"text": " i enjoy CYCLING "},
        ]
        result = self.modules["chat_prompts"].build_chat_messages(
            "Current question", '{"name":"Alex"}', history, retrieved,
        )
        self.assertEqual(result[2:-1], history[-10:])
        background = json.loads(result[1]["content"].split("\n", 1)[1])
        self.assertEqual(background["relevant_memories"], ["I enjoy cycling"])
        self.assertEqual(sum(m["content"] == "Current question" for m in result), 1)
        self.assertEqual(sum(m["content"] == "Same question" for m in result), 2)

    def test_service_includes_current_turn_once_and_persists_complete_pair(self):
        self.vector.search_memory.return_value = [{"text": "Hello"}]
        output = io.StringIO()
        with redirect_stdout(output):
            result = self.service.chat("  Hello  ")
        context = self.llm.generate.call_args.kwargs["messages"]
        self.assertEqual(context[-1], {"role": "user", "content": "Hello"})
        self.assertEqual(sum(m["content"] == "Hello" for m in context), 1)
        self.assertEqual([m["role"] for m in self.memory.messages[1:]], ["user", "assistant"])
        self.assertEqual(result.reply, "A useful answer.")
        self.memory.save_memory.assert_called_once()
        self.assertEqual(output.getvalue(), "")

    def test_privacy_routing_matrix_and_nonstream_cloud_fallback(self):
        for available in (False, True):
            for sensitive in (False, True):
                for mode in self.mode:
                    with self.subTest(available=available, sensitive=sensitive, mode=mode):
                        cloud = Mock()
                        cloud.is_available.return_value = available
                        router = self.router_module.ChatRouter(cloud=cloud)
                        request = self.router_module.ChatRoutingRequest(
                            messages=[], privacy_mode=mode, sensitive=sensitive,
                        )
                        expected_cloud = available and not sensitive and mode in (
                            self.mode.AUTO, self.mode.MAX_QUALITY,
                        )
                        self.assertEqual(router.select_target(request).value,
                                         "cloud" if expected_cloud else "local")
        cloud.generate.side_effect = RuntimeError("unavailable")
        request.sensitive = False
        request.privacy_mode = self.mode.MAX_QUALITY
        with self.assertLogs("chat_router", level="WARNING"):
            self.assertEqual(router.generate(request)["message"]["content"], "A useful answer.")

    def test_sensitivity_in_history_profile_and_retrieval_stays_local(self):
        cloud = Mock()
        cloud.is_available.return_value = True
        self.service.chat_router = self.router_module.ChatRouter(cloud=cloud)
        for source in ("history", "profile", "retrieval"):
            with self.subTest(source=source):
                self.memory.messages[:] = self.memory.messages[:1]
                self.profile.profile = {}
                self.vector.search_memory.return_value = []
                if source == "history":
                    self.memory.messages.append({"role": "user", "content": "My password is private"})
                elif source == "profile":
                    self.profile.profile = {"note": "medical report"}
                else:
                    self.vector.search_memory.return_value = [{"text": "confidential project"}]
                result = self.service.chat("Explain that", self.mode.MAX_QUALITY)
                self.assertTrue(result.sensitive)
                self.assertTrue(result.sensitivity_reasons)
        cloud.generate.assert_not_called()

    def test_failed_generation_and_failed_persistence_leave_no_new_turn(self):
        self.llm.generate.side_effect = RuntimeError("provider unavailable")
        with self.assertRaises(RuntimeError):
            self.service.chat("Hello")
        self.assertEqual(len(self.memory.messages), 1)
        self.classifier.classify.assert_not_called()
        self.llm.generate.side_effect = None
        self.memory.save_memory.side_effect = OSError("disk unavailable")
        with self.assertRaises(OSError):
            self.service.chat("Hello")
        self.assertEqual(len(self.memory.messages), 1)

    def test_auxiliary_extraction_failure_does_not_discard_answer(self):
        self.classifier.classify.side_effect = RuntimeError("classifier unavailable")
        self.profile.update_profile.side_effect = RuntimeError("profile unavailable")
        with self.assertLogs("chat_service", level="WARNING"):
            result = self.service.chat("My name is Alex")
        self.assertEqual(result.reply, "A useful answer.")
        self.assertEqual(len(self.memory.messages), 3)

    def test_chat_json_contract_and_validation(self):
        with TestClient(self.api.app) as client:
            response = client.post("/chat", json={"message": "Hello"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {
                "reply": "A useful answer.", "privacy_mode": "auto",
                "sensitive": False, "sensitivity_reasons": [],
            })
            for endpoint in ("/chat", "/chat/stream"):
                for payload in (
                    {"message": "   "}, {"message": "Hi", "privacy_mode": "unknown"},
                ):
                    self.assertEqual(client.post(endpoint, json=payload).status_code, 400)
            self.llm.generate.side_effect = RuntimeError("secret provider detail")
            failure = client.post("/chat", json={"message": "Hi"})
            self.assertEqual(failure.status_code, 500)
            self.assertNotIn("secret provider detail", failure.text)

    def test_stream_events_and_completion_metadata(self):
        self.llm.generate.return_value = iter([chunk("नमस्ते "), chunk("world"), chunk(done=True)])
        with TestClient(self.api.app) as client:
            response = client.post("/chat/stream", json={"message": "Hi", "privacy_mode": "local_only"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers["content-type"])
        events = self.parse_events(response.text)
        self.assertEqual([kind for kind, data in events], ["delta", "delta", "done"])
        self.assertEqual("".join(data["text"] for kind, data in events if kind == "delta"), "नमस्ते world")
        self.assertEqual(events[-1][1], {
            "privacy_mode": "local_only", "sensitive": False, "sensitivity_reasons": [],
        })
        self.assertEqual(self.memory.messages[-1]["content"], "नमस्ते world")

    def test_stream_failure_returns_error_without_done_or_persistence(self):
        def broken():
            yield chunk("Partial answer")
            raise RuntimeError("sensitive provider diagnostics")

        self.llm.generate.return_value = broken()
        with TestClient(self.api.app) as client:
            response = client.post("/chat/stream", json={"message": "Hi"})
        self.assertEqual([kind for kind, data in self.parse_events(response.text)], ["delta", "error"])
        self.assertNotIn("sensitive provider diagnostics", response.text)
        self.assertEqual(len(self.memory.messages), 1)
        self.memory.save_memory.assert_not_called()

    def test_cloud_stream_fallback_only_before_text(self):
        for has_text in (False, True):
            with self.subTest(has_text=has_text):
                def broken():
                    yield chunk("Cloud text" if has_text else "")
                    raise RuntimeError("cloud interrupted")

                cloud = Mock()
                cloud.is_available.return_value = True
                cloud.generate.return_value = broken()
                router = self.router_module.ChatRouter(cloud=cloud)
                self.llm.generate.reset_mock()
                self.llm.generate.return_value = iter([chunk("Local text"), chunk(done=True)])
                request = self.router_module.ChatRoutingRequest(messages=[], stream=True)
                stream = router.generate(request)
                if has_text:
                    self.assertEqual(next(stream)["message"]["content"], "Cloud text")
                    with self.assertRaises(RuntimeError):
                        list(stream)
                    self.llm.generate.assert_not_called()
                else:
                    with self.assertLogs("chat_router", level="WARNING"):
                        text = "".join(part["message"]["content"] for part in stream)
                    self.assertEqual(text, "Local text")
                    self.llm.generate.assert_called_once()

    def test_eof_without_provider_done_is_not_success(self):
        self.llm.generate.return_value = iter([chunk("Truncated")])
        stream = self.service.stream_chat("Hello")
        self.assertEqual(next(stream).event, "delta")
        with self.assertRaisesRegex(RuntimeError, "before completion"):
            list(stream)
        self.assertEqual(len(self.memory.messages), 1)

    def test_browser_disconnect_closes_provider_and_releases_turn(self):
        for version in ("2.3", "2.4"):
            with self.subTest(asgi_version=version):
                closed = []

                def provider():
                    try:
                        yield chunk("First text")
                        yield chunk("More text")
                        yield chunk(done=True)
                    finally:
                        closed.append(True)

                self.llm.generate.return_value = provider()
                response = self.api.chat_stream(self.api.ChatRequest(message="Hello"))

                async def run():
                    transmitted = anyio.Event()

                    async def receive():
                        await transmitted.wait()
                        return {"type": "http.disconnect"}

                    async def send(message):
                        if message["type"] == "http.response.body":
                            transmitted.set()
                            if version == "2.4":
                                raise OSError("browser disconnected")
                            await anyio.sleep_forever()  # Cancelled by the disconnect listener.

                    scope = {"type": "http", "asgi": {"spec_version": version}}
                    if version == "2.4":
                        with self.assertRaises(ClientDisconnect):
                            await response(scope, receive, send)
                    else:
                        await response(scope, receive, send)

                anyio.run(run)
                self.assertEqual(closed, [True])
                self.assertEqual(len(self.memory.messages), 1)
                acquired = self.service._turn_lock.acquire(blocking=False)
                self.assertTrue(acquired)
                if acquired:
                    self.service._turn_lock.release()

    def test_local_provider_model_is_configurable_and_stream_flag_is_preserved(self):
        client = Mock()
        ollama = module("ollama", Client=Mock(return_value=client))
        with patch.dict(sys.modules, {"ollama": ollama}), \
             patch.dict(os.environ, {"PERSONAL_AI_MODEL": "configured-model"}):
            spec = importlib.util.spec_from_file_location("local_provider_test", APP_DIR / "llm.py")
            provider = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(provider)
            provider.generate([], stream=True)
            client.chat.assert_called_with(model="configured-model", messages=[], stream=True)
            provider.generate([], model="replacement-model")
            client.chat.assert_called_with(model="replacement-model", messages=[], stream=False)
            ollama.Client.assert_called_once_with(timeout=120.0)

    def use_temporary_history(self, directory):
        # Exercise the real history reset/persistence code only in a temporary folder.
        with patch.dict(sys.modules, {"chat_prompts": self.modules["chat_prompts"]}):
            spec = importlib.util.spec_from_file_location("isolated_history", APP_DIR / "memory.py")
            history = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(history)
        history.MEMORY_PATH = Path(directory) / "memory.json"
        history.add_message("user", "Old question")
        history.add_message("assistant", "पुराना जवाब")
        history.save_memory()
        self.modules["chat_service"].memory = history
        self.modules["retriever"].memory = history
        return history

    def test_new_chat_clears_only_history_and_both_chat_endpoints_still_work(self):
        self.profile.profile = {"name": "Kept Profile"}
        saved_profile = self.profile.profile.copy()
        semantic_memories = [{"text": "I enjoy cycling"}]
        self.vector.search_memory.return_value = semantic_memories
        with TemporaryDirectory() as directory:
            history = self.use_temporary_history(directory)
            base = history.messages[0].copy()
            with TestClient(self.api.app) as client:
                response = client.post("/chat/reset")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"status": "ok"})
                self.assertEqual(history.messages, [base])
                self.assertEqual(json.loads(history.MEMORY_PATH.read_text(encoding="utf-8")), [])
                history.load_memory()
                self.assertEqual(history.messages, [base])
                self.assertEqual(self.profile.profile, saved_profile)
                self.profile.update_profile.assert_not_called()
                self.vector.search_memory.assert_not_called()
                self.vector.clear_memory.assert_not_called()
                self.classifier.classify.assert_not_called()
                self.manager.save_memory.assert_not_called()

                for endpoint in ("/chat", "/chat/stream"):
                    with self.subTest(endpoint=endpoint):
                        self.llm.generate.return_value = (
                            iter([chunk("New answer"), chunk(done=True)]) if endpoint.endswith("stream")
                            else {"message": {"content": "New answer"}}
                        )
                        response = client.post(endpoint, json={"message": "What do you remember?"})
                        self.assertEqual(response.status_code, 200)
                        context = self.llm.generate.call_args.kwargs["messages"]
                        self.assertEqual(context[0], base)
                        self.assertFalse(any(m["content"] in ("Old question", "पुराना जवाब") for m in context))
                        self.assertIn("Kept Profile", context[1]["content"])
                        self.assertIn("I enjoy cycling", context[1]["content"])
                        if endpoint.endswith("stream"):
                            self.assertEqual(self.parse_events(response.text)[-1][0], "done")
                        else:
                            self.assertEqual(response.json()["reply"], "New answer")
                self.assertEqual(self.profile.profile, saved_profile)
                self.assertEqual(self.vector.search_memory.return_value, semantic_memories)
                self.vector.clear_memory.assert_not_called()

    def test_new_chat_write_failure_keeps_history_in_memory_and_on_disk(self):
        with TemporaryDirectory() as directory:
            history = self.use_temporary_history(directory)
            prior_messages = history.messages[:]
            prior_bytes = history.MEMORY_PATH.read_bytes()
            with TestClient(self.api.app) as client, \
                 patch.object(history.os, "replace", side_effect=OSError("private storage details")):
                response = client.post("/chat/reset")
            self.assertEqual(response.status_code, 500)
            self.assertIn("conversation has been kept", response.json()["detail"])
            self.assertNotIn("private storage details", response.text)
            self.assertEqual(history.messages, prior_messages)
            self.assertEqual(history.MEMORY_PATH.read_bytes(), prior_bytes)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])
            self.vector.clear_memory.assert_not_called()
            self.profile.update_profile.assert_not_called()

    def test_cli_uses_shared_streaming_and_policy_commands(self):
        self.llm.generate.return_value = iter([chunk("CLI answer"), chunk(done=True)])
        main = self.modules["main"]
        with patch.object(main, "ChatService", return_value=self.service), \
             patch("builtins.input", side_effect=["/local", "Hello", "exit"]), \
             redirect_stdout(io.StringIO()) as output:
            main.main()
        self.assertIn("CLI answer", output.getvalue())
        self.assertIn("local_only", output.getvalue())
        self.assertTrue(self.llm.generate.call_args.kwargs["stream"])

    @staticmethod
    def parse_events(text):
        result = []
        for frame in text.strip().split("\n\n"):
            event_line, data_line = frame.split("\n", 1)
            result.append((event_line.removeprefix("event: "),
                           json.loads(data_line.removeprefix("data: "))))
        return result


if __name__ == "__main__":
    unittest.main()
