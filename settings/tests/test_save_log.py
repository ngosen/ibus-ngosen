# SPDX-FileCopyrightText: 2026 Ngó Sen contributors
#
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import tempfile
import threading
import time
import unittest

from ngosen_settings import save_log


class SaveLogTest(unittest.TestCase):
    def setUp(self):
        self.folder = os.path.join(tempfile.mkdtemp(), "ngosen")

    def names(self):
        return sorted(os.listdir(self.folder)) if os.path.isdir(self.folder) else []

    def answer(self, text):
        """Stands in for the engine: takes the request and answers with the saved file."""

        def run():
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                for name in self.names():
                    if name.startswith(save_log.REQUEST_PREFIX):
                        os.remove(os.path.join(self.folder, name))
                        suffix = name.removeprefix(save_log.REQUEST_PREFIX)
                        reply = os.path.join(self.folder, save_log.REPLY_PREFIX + suffix)
                        with open(reply, "w", encoding="utf-8") as f:
                            f.write(text)
                        return
                time.sleep(0.01)

        thread = threading.Thread(target=run)
        thread.start()
        return thread

    def run_save(self, engine="ngosen", running=True, wait=2):
        return save_log.save(self.folder, lambda: engine, lambda: running, wait)

    def test_prints_the_saved_path_and_leaves_nothing(self):
        thread = self.answer("/home/u/.local/state/ngosen/typing-1.log")
        code, message = self.run_save()
        thread.join()
        self.assertEqual(code, 0)
        self.assertTrue(message.endswith("/home/u/.local/state/ngosen/typing-1.log"))
        self.assertEqual(self.names(), [])

    def test_an_empty_answer_means_the_log_was_not_written(self):
        thread = self.answer("")
        code, message = self.run_save()
        thread.join()
        self.assertEqual(code, 1)
        self.assertIn("Could not save", message)

    def test_no_answer_takes_the_request_back(self):
        code, message = self.run_save(wait=0.2)
        self.assertEqual(code, 1)
        self.assertIn("did not answer", message)
        self.assertEqual(self.names(), [])

    def test_nothing_is_left_without_ibus(self):
        self.assertEqual(self.run_save(running=False), (1, "IBus is not running."))
        self.assertEqual(self.names(), [])

    def test_nothing_is_left_when_another_input_source_is_in_use(self):
        code, message = self.run_save(engine="xkb:us::eng")
        self.assertEqual(code, 1)
        self.assertIn("not the input source in use", message)
        self.assertEqual(self.names(), [])


if __name__ == "__main__":
    unittest.main()
