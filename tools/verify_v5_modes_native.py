"""Windows V5 menu/cadence/restart evidence using production widgets.

Qt public mouse events drive actual Windows popups; these are not OS-injected
mouse inputs. A separate interactive session can supplement this evidence.
Preferences are confined to the chosen output directory.
"""

import argparse
import gzip
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu

from sukuna_pet.desktop import PetWindow
from sukuna_pet.playback import PetApplication


def session(name: str, output: Path) -> int:
    app = QApplication([])
    assert app.platformName() == 'windows', 'Requires a visible Windows desktop'
    settings = output / 'preferences.json'
    expected_mode, expected_size = {
        'select-always': ('click', 320),
        'restore-always': ('always', 188),
        'restore-click': ('click', 271),
    }[name]
    pet = PetApplication(settings_path=settings)
    window = PetWindow(pet, settings_path=settings)
    window.move(650, 300)
    window.show()
    failures, samples, actions = [], [], []
    start = perf_counter()
    stopped_stage = None

    def sample() -> None:
        samples.append({'elapsed_ms': (perf_counter() - start) * 1000,
                        'mode': pet.mode, 'height': window.height(), 'view': asdict(pet.view)})

    def menu(choose: str, suffix: str) -> None:
        def act() -> None:
            try:
                popup = QApplication.activePopupWidget()
                assert isinstance(popup, QMenu)
                top = popup.actions()
                checked = [a.text() for a in top if a.isChecked()]
                assert checked == ['持续跳动' if pet.mode == 'always' else '点击跳动']
                submenu = next(a.menu() for a in top if a.text() == '调整大小')
                assert submenu is not None
                sizes = submenu.actions()
                assert [a.text() for a in sizes] == ['188px', '271px', '320px']
                assert [a.text() for a in sizes if a.isChecked()] == [f'{window.height()}px']
                assert popup.grab().save(str(output / f'{name}-{suffix}-menu.png'))
                target = popup
                if choose.endswith('px'):
                    a = next(a for a in top if a.text() == '调整大小')
                    submenu.popup(popup.mapToGlobal(popup.actionGeometry(a).topRight()))
                    QTest.qWait(80)
                    assert submenu.isVisible()
                    target = submenu
                    assert target.grab().save(str(output / f'{name}-{suffix}-sizes.png'))
                a = next(a for a in target.actions() if a.text() == choose)
                QTest.mouseClick(target, Qt.MouseButton.LeftButton, pos=target.actionGeometry(a).center())
                if target is not popup:
                    popup.close()  # Explicitly popped submenu does not dismiss its parent.
                actions.append({'elapsed_ms': (perf_counter()-start)*1000, 'choose': choose})
            except Exception as error:
                failures.append(__import__("traceback").format_exc())
                app.exit(1)
        QTimer.singleShot(80, act)
        point = window.mask().boundingRect().center()
        QApplication.sendEvent(window, QContextMenuEvent(
            QContextMenuEvent.Reason.Mouse, point, window.mapToGlobal(point)))

    def begin() -> None:
        try:
            assert pet.mode == expected_mode and window.height() == expected_size
            window.frame.save(str(output / f'{name}-startup.png'))
            sample()
            if name == 'select-always':
                menu('188px', 'size')
                menu('持续跳动', 'mode')
            elif name == 'restore-always':
                menu('271px', 'size')
            else:
                menu('320px', 'size')
            QTimer.singleShot(950, manual_click)
            QTimer.singleShot(2600, stop_or_finish)
        except Exception as error:
            failures.append(__import__("traceback").format_exc())
            app.exit(1)

    def manual_click() -> None:
        before = pet.view.stage
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=window.mask().boundingRect().center())
        actions.append({'elapsed_ms': (perf_counter()-start)*1000, 'choose': 'character click',
                        'before_stage': before, 'after_stage': pet.view.stage})
        window.frame.save(str(output / f'{name}-manual-click.png'))

    def stop_or_finish() -> None:
        nonlocal stopped_stage
        if name == 'restore-always':
            menu('点击跳动', 'stop')
            stopped_stage = pet.view.stage
        QTimer.singleShot(500, finish)

    def finish() -> None:
        try:
            if stopped_stage is not None:
                assert pet.view.stage == stopped_stage and pet.view.holding
                assert pet.view.eyelid_closure == 0 and pet.view.bounce_scale == (1, 1)
            expected = {'mode': 'always' if name == 'select-always' else 'click',
                        'size': {'select-always': 188, 'restore-always': 271, 'restore-click': 320}[name]}
            assert json.loads(settings.read_text()) == expected
            window.frame.save(str(output / f'{name}-final.png'))
            menu('退出', 'exit')
        except Exception as error:
            failures.append(__import__("traceback").format_exc())
            app.exit(1)

    timer = QTimer()
    timer.timeout.connect(sample)
    timer.start(8)
    QTimer.singleShot(100, begin)
    QTimer.singleShot(15000, lambda: app.exit(2))
    result = app.exec()
    record = {'session': name, 'platform': app.platformName(), 'exit_code': result,
              'input': 'Qt public events on real Windows menus; not OS mouse injection',
              'screens': [{'name': s.name(), 'geometry': s.geometry().getRect(),
                           'dpr': s.devicePixelRatio()} for s in app.screens()],
              'failures': failures, 'actions': actions, 'samples': samples,
              'saved': json.loads(settings.read_text())}
    (output / f'{name}-trace.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'session': name, 'exit_code': result, 'failures': failures}))
    return 1 if failures else result


def interactive(output: Path) -> int:
    app = QApplication([])
    assert app.platformName() == "windows"
    path = output / "os-preferences.json"
    path.write_text('{"mode":"click","size":320}\n')
    pet = PetApplication(settings_path=path)
    window = PetWindow(pet, settings_path=path)
    window.move(650, 300)
    window.show()
    stream = gzip.open(output / "os-input-trace.jsonl.gz", "wt", encoding="utf-8")
    start = perf_counter()
    previous_menu = False
    menu_count = 0

    def sample() -> None:
        nonlocal previous_menu, menu_count
        popup = QApplication.activePopupWidget()
        menu_visible = isinstance(popup, QMenu)
        entry = {"elapsed_ms": (perf_counter()-start)*1000, "mode": pet.mode,
                 "view": asdict(pet.view), "height": window.height(),
                 "visible": window.isVisible(), "menu_visible": menu_visible}
        stream.write(json.dumps(entry, ensure_ascii=False) + "\n")
        stream.flush()
        if menu_visible and not previous_menu:
            menu_count += 1
            popup.grab().save(str(output / f"os-menu-{menu_count}.png"))
        previous_menu = menu_visible

    timer = QTimer()
    timer.timeout.connect(sample)
    timer.start(10)
    QTimer.singleShot(180000, app.quit)
    result = app.exec()
    sample()
    stream.close()
    (output / "os-session-result.json").write_text(json.dumps({
        "exit_code": result, "closed": not window.isVisible(),
        "saved": json.loads(path.read_text()), "input": "Real OS mouse via computer-use",
        "platform": app.platformName(), "menus_observed": menu_count,
    }, indent=2), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('docs/verification/issue-25'))
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--session', choices=['select-always', 'restore-always', 'restore-click'])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.interactive:
        return interactive(args.output)
    if args.session:
        return session(args.session, args.output)
    # This is an explicitly isolated evidence profile, never user preferences.
    (args.output / 'preferences.json').write_text('{}\n')
    for name in ('select-always', 'restore-always', 'restore-click'):
        subprocess.run([sys.executable, __file__, '--output', str(args.output), '--session', name],
                       check=True, timeout=25)
    print('PASS: Windows V5 cadence, clicks, mode/size menus and three independent launches')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
