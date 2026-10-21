"""Integration checks use a separate process and never touch player data."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec("PySide6"), "Qt is not installed")
class QtFrontendTests(unittest.TestCase):
    def test_motion_timer_sleeps_and_wakes_for_sprite_updates(self):
        self.run_game_script('''
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app = QApplication([])
from paths import ensure_app_dirs, find_app_asset
ensure_app_dirs()
from qt_frontend import QtGame
sys.excepthook = sys.__excepthook__
game = QtGame()
try:
    QTest.qWait(50)
    assert not game._motion.isActive()
    ticks = []
    game._motion.timeout.connect(lambda: ticks.append(1))
    QTest.qWait(80)
    assert not ticks
    sprite = game.create_sprite(find_app_asset('flesh.png'), pos=(0, 0))
    QTest.qWait(50)
    assert game.spriteModel.rowCount() == 1
    assert not game._motion.isActive()
    sprite.set_velocity(100, 0)
    assert game._motion.isActive()
    QTest.qWait(80)
    assert sprite.get_x() > 0
    sprite.set_velocity(0, 0)
    QTest.qWait(50)
    assert not game._motion.isActive()
    sprite.move_to(200, 30)
    QTest.qWait(50)
    record = game.spriteModel.data(game.spriteModel.index(0), game.spriteModel.SpriteRole)
    assert (record['x'], record['y']) == (200, 30)
    assert not game._motion.isActive()
    sprite.set_velocity(100, 0)
    sprite.step(0)
    QTest.qWait(50)
    assert not game._motion.isActive()
    x = sprite.get_x()
    sprite.set_auto_motion(True)
    assert game._motion.isActive()
    QTest.qWait(80)
    assert sprite.get_x() > x
    sprite.remove()
    QTest.qWait(50)
    assert game.spriteModel.rowCount() == 0
    assert not game._motion.isActive()
    game._active_mod_owner = 'motion-test'
    sprite = game.create_sprite(find_app_asset('flesh.png'))
    sprite.set_velocity(100, 0)
    game._remove_mod_runtime_objects()
    QTest.qWait(50)
    assert not game._motion.isActive()
finally:
    game.shutdown()
    assert not game._motion.isActive()
''')

    def test_leaderboard_refresh_submit_and_errors_are_nonblocking(self):
        self.run_game_script('''
import sys, time
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app = QApplication([])
from paths import ensure_app_dirs
ensure_app_dirs()
from qt_frontend import QtGame
sys.excepthook = sys.__excepthook__
with patch('qt_leaderboard._leaderboard_configured', return_value=True):
    game = QtGame()
try:
    controller = game.leaderboard
    def wait_for_idle():
        deadline = time.monotonic() + 3
        while controller.state['busy'] and time.monotonic() < deadline:
            QTest.qWait(10)
        assert not controller.state['busy'], controller.state
    def fetch():
        time.sleep(.04)
        return True, '', [{'username': 'Tester', 'flesh_amount': 5}]
    with patch('qt_leaderboard.fetch_leaderboard_entries', side_effect=fetch):
        controller.refresh()
        assert controller.state['busy']
        wait_for_idle()
        assert not controller.state['busy']
        assert controller.state['rows'][0]['username'] == 'Tester'
        game.set_currency('flesh', 17)
        with patch('qt_leaderboard.submit_leaderboard_entry', return_value=(True, {})) as submit:
            controller.submit('Tester')
            wait_for_idle()
            submit.assert_called_once_with('Tester', 17)
    with patch('qt_leaderboard.fetch_leaderboard_entries', return_value=(False, 'offline', [])):
        controller.refresh()
        wait_for_idle()
        assert 'offline' in controller.state['message']
        assert not controller.state['busy']
finally:
    game.shutdown()
''')

    def test_sprite_motion_keeps_qml_items_and_skips_full_ui_publish(self):
        self.run_game_script('''
import sys
from PySide6.QtCore import QPersistentModelIndex
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from qt_frontend import create_application
sys.excepthook = sys.__excepthook__
app, engine, game = create_application([])
window = engine.rootObjects()[0]
def find_sprite():
    pending = [window.contentItem()]
    while pending:
        candidate = pending.pop()
        if candidate.objectName() == 'sprite:' + sprite.id:
            return candidate
        pending.extend(candidate.childItems())
try:
    from paths import find_app_asset
    sprite = game.create_sprite(find_app_asset('flesh.png'), pos=(20, 20), size=(40, 40))
    QTest.qWait(80)
    model = game.spriteModel
    assert model.rowCount() == 1
    index = QPersistentModelIndex(model.index(0))
    item = find_sprite()
    assert item is not None
    changes, resets, live = [], [], []
    model.dataChanged.connect(lambda *args: changes.append(item.x()))
    model.modelReset.connect(lambda: resets.append(1))
    game.liveChanged.connect(lambda: live.append(1))
    sprite.set_velocity(100, 0)
    QTest.qWait(240)
    assert len(changes) >= 6, changes
    assert not resets
    assert index.isValid()
    assert item is find_sprite()
    assert item.x() > 30
    assert len(live) <= 1, live
    # Old mods advance their own physics, then store velocity for reporting.
    sprite.set_velocity(0, 0)
    sprite.bounce(2, 0)
    sprite.set_velocity(100, 0)
    x = sprite.get_x()
    QTest.qWait(80)
    assert sprite.get_x() == x
    sprite.set_auto_motion(True)
    QTest.qWait(80)
    assert sprite.get_x() > x
    sprite.remove()
    QTest.qWait(40)
    assert model.rowCount() == 0
finally:
    game.shutdown()
    window.close()
    app.processEvents()
''')

    def run_game_script(self, script):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, APPDATA=temp, XDG_CONFIG_HOME=temp,
                       QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
            result = subprocess.run([sys.executable, "-c", script], cwd=Path(__file__).resolve().parents[1],
                                    env=env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_runtime_gameplay_save_and_theme_without_gtk(self):
        self.run_game_script('''
import sys
from PySide6.QtWidgets import QApplication
app = QApplication([])
from paths import ensure_app_dirs
ensure_app_dirs()
from qt_frontend import QtGame
game = QtGame()
assert 'gi' in sys.modules and not hasattr(sys.modules['gi'], '__file__')
game.click()
assert game.flesh == 1
game.set_currency('flesh', 100)
game.buy('bigger_clicks')
assert game.get_upgrade_count('bigger_clicks') == 1
assert game.flesh == 90
first = game.active_save_id
game.createSave('Fresh')
assert game.flesh == 0
assert game.state['total_clicks'] == 0
game.loadSave(first)
assert game.flesh == 90
game.setPreference('theme', 'light')
assert game.darkMode is False
game.setPreference('theme', 'dark')
assert game.darkMode is True
game.executeCommand('/ac flesh 5')
assert game.flesh == 95
game.shutdown()
from save_manager import load_save_slot_data
assert load_save_slot_data(first)['state']['currencies']['flesh'] == 95
''')

    def test_mod_handles_button_and_reload_cleanup(self):
        self.run_game_script('''
from PySide6.QtWidgets import QApplication
app = QApplication([])
from paths import ensure_app_dirs
ensure_app_dirs()
from qt_frontend import QtGame
game = QtGame()
game._current_mod_info = {'id': 'sample', 'name': 'Sample', 'path': '.'}
page = game.add_tab('sample', 'Sample')
page.add_label('Mod content')
button = game.add_tab_button('sample', 'Add flesh', lambda button: game.add_currency('flesh', 10))
game._current_mod_info = None
game.activateModButton(button.id)
assert game.flesh == 10
game._publish()
assert game.catalog['buttons'][0]['label'] == 'Add flesh'
assert game.catalog['tabs'][0]['items'][0]['text'] == 'Mod content'
game.reload_mods()
assert not game._qt_buttons
assert not game._qt_tabs
game.shutdown()
''')

    def test_scheduler_repeat_and_cancel(self):
        self.run_game_script('''
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
app = QApplication([])
import runtime_scheduler as scheduler
scheduler.configure_qt()
hits = []
def tick():
    hits.append(1)
    return len(hits) < 3
source = scheduler.timeout_add(1, tick)
QTest.qWait(90)
assert len(hits) == 3, hits
assert scheduler.source_remove(source) is False
source = scheduler.timeout_add(1, lambda: hits.append(2))
assert scheduler.source_remove(source) is True
QTest.qWait(20)
assert len(hits) == 3
''')

    def test_missing_mod_save_is_not_overwritten_before_decision(self):
        self.run_game_script('''
from PySide6.QtWidgets import QApplication
app = QApplication([])
from paths import ensure_app_dirs
ensure_app_dirs()
from qt_frontend import QtGame
from save_manager import load_save_slot_data, write_save_slot_data
game = QtGame()
game.set_currency('flesh', 42)
game.shutdown()
slot = load_save_slot_data('main')
slot['required_mods'] = [{'id': 'missing', 'name': 'Missing Mod'}]
write_save_slot_data(slot)
guarded = QtGame()
assert guarded._startup_guard
guarded.click()
assert guarded.flesh == 42
guarded.shutdown()
assert load_save_slot_data('main')['state']['currencies']['flesh'] == 42
guarded = QtGame()
guarded.ready()
guarded.confirmPending(False)
assert not guarded._startup_guard
assert guarded.active_save_id != 'main'
assert guarded.flesh == 0
assert load_save_slot_data('main')['state']['currencies']['flesh'] == 42
guarded.shutdown()
''')


if __name__ == "__main__":
    unittest.main()
