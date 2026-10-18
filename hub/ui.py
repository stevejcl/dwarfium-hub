"""The hub's page: one card per application (installed / latest version,
install - update - rollback, start - stop, port, folder, start with the
hub / restart - hub/watchdog.py), and both apps started or stopped
together.

Network, download and install run in worker threads (run.io_bound): the
window never freezes.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from nicegui import app, run, ui

from hub import autorun, config, installer, instances, releases, runner, watchdog
from hub.dwarfs_ui import DwarfsView
from hub.help_apps import help_apps
from hub.installations_ui import InstallationsView
from hub.sync_ui import SyncView
from hub.apps import APPS, AppSpec, exe_name
from hub.i18n import language, set_language, system_language, t
from hub.app_version import get_version
from hub.logo import LOGO_SVG


class AppCard:
    def __init__(self, page: "HubPage", spec: AppSpec):
        self.page, self.spec = page, spec
        self.release: releases.Release | None = None
        self.release_error = ""
        self.busy = False
        self.launching = False          # its process being created (start())
        self.progress_value = 0.0
        self.progress_text = ""
        # What answers on the app's port (runner.probe), None until asked
        self.state: runner.Probe | None = None

    def notify(self, *args, **kwargs) -> None:
        # From the page, not the card: an action may have rebuilt the card
        # (and the button it was started from) meanwhile
        with self.page.dialog_host:
            ui.notify(*args, **kwargs)

    # ── settings ──────────────────────────────────────────────────────────
    @property
    def settings(self) -> dict:
        return config.app_settings(self.page.cfg, self.spec.id)

    @property
    def folder(self) -> Path:
        return config.app_folder(self.page.cfg, self.spec)

    @property
    def port(self) -> int:
        return config.app_port(self.page.cfg, self.spec)

    def installed(self) -> bool:
        return (self.folder / exe_name(self.spec)).is_file()

    def installed_version(self) -> str | None:
        return installer.installed_version(self.folder)

    @property
    def running(self) -> bool:
        return self.state is not None and self.state.state == runner.RUNNING

    @property
    def active(self) -> bool:
        """Running or still starting."""
        return self.state is not None and self.state.state in (runner.RUNNING, runner.STARTING)

    def _probe(self) -> runner.Probe:
        """Blocking. The version the running app gives is recorded for an
        installation the hub didn't make (no version file)."""
        if not self.installed():
            return runner.Probe(runner.STOPPED)
        state = runner.probe(self.spec, self.port)
        if state.state == runner.RUNNING and state.version:
            installer.record_running_version(self.folder, state.version)
        return state

    async def update_state(self) -> bool:
        """Asks the app's port again; True when something changed."""
        before = (self.state, self.installed_version())
        self.state = await run.io_bound(self._probe)
        return (self.state, self.installed_version()) != before

    # ── release ───────────────────────────────────────────────────────────
    async def check_release(self) -> None:
        try:
            self.release = await run.io_bound(releases.latest_release, self.spec)
            self.release_error = "" if self.release.asset_url else t("no_asset")
        except Exception:
            self.release, self.release_error = None, t("no_network")
        self.render.refresh()

    # ── actions ───────────────────────────────────────────────────────────
    async def install_or_update(self) -> None:
        rel = self.release
        if not rel or not rel.asset_url:
            return
        await self.update_state()
        if self.active:
            self.notify(t("stop_first", name=self.spec.name), type="warning")
            return
        self.busy, self.progress_value, self.progress_text = True, 0, t("downloading", v=rel.version)
        self.render.refresh()
        tmp_dir = Path(tempfile.mkdtemp(prefix="dwarfium_hub_"))
        try:
            zip_path = tmp_dir / f"{self.spec.asset_prefix}.zip"

            def on_download(done, total):
                self.progress_value = done / total if total else 0
            await run.io_bound(installer.download, rel.asset_url, zip_path, rel.sha256, on_download)
            self.progress_text, self.progress_value = t("installing"), 0

            def on_install(done, total):
                self.progress_value = done / total if total else 0
            await run.io_bound(installer.install, zip_path, self.folder, rel.version, exe_name(self.spec), on_install)
            self.settings["path"] = str(self.folder)
            self.settings.setdefault("port", self.spec.default_port)
            config.save(self.page.cfg)
            self.notify(t("installed_ok", name=self.spec.name, v=rel.version), type="positive")
        except Exception as e:
            self.notify(t("failed", e=e), type="negative", multi_line=True)
        finally:
            self.busy = False
            for f in tmp_dir.glob("*"):
                f.unlink(missing_ok=True)
            tmp_dir.rmdir()
            self.render.refresh()

    async def rollback(self) -> None:
        await self.update_state()
        if self.active:
            self.notify(t("stop_first", name=self.spec.name), type="warning")
            return
        try:
            version = await run.io_bound(installer.rollback, self.folder)
            self.notify(t("rolled_back", name=self.spec.name, v=version or "?"), type="positive")
        except Exception as e:
            self.notify(t("failed", e=e), type="negative")
        self.render.refresh()

    async def start(self, notify: bool = True) -> bool:
        await self.update_state()
        if self.active:
            return True
        clash = self.page.port_clash(self, self.port)
        if clash:
            self.notify(t("port_taken_start", name=self.spec.name, port=self.port, other=clash.spec.name),
                        type="warning", multi_line=True)
            return False
        if self.state.state == runner.OTHER:
            self.notify(t("port_other_start", name=self.spec.name, port=self.port), type="warning", multi_line=True)
            self.render.refresh()
            return False
        # "Starting..." at once, and watch_running() leaves this card alone
        # until the process exists (it would read "Stopped" meanwhile)
        self.state, self.launching = runner.Probe(runner.STARTING), True
        self.render.refresh()
        try:
            # In a worker thread: on Windows, creating the process of a big
            # one-file exe can take seconds (the antivirus scans it first) -
            # the hub's window would lose its server meanwhile ("Connection lost")
            await run.io_bound(runner.start, self.spec, self.folder, self.port, lan=self.lan)
        except Exception as e:
            self.notify(t("start_failed", name=self.spec.name, e=e), type="negative")
            await self.update_state()
            self.render.refresh()
            return False
        finally:
            self.launching = False
        await run.io_bound(runner.wait_until_up, self.spec, self.port, 180)
        await self.update_state()       # records the version it gives
        self.render.refresh()
        if self.running:
            if notify:
                self.notify(t("started", name=self.spec.name), type="positive")
            return True
        if self.state.state == runner.STARTING:     # slow, but still on its way
            self.notify(t("still_starting", name=self.spec.name), type="info")
        else:
            self.notify(t("start_failed", name=self.spec.name, e=t("exited")), type="warning")
        return False

    async def stop(self) -> None:
        stopped = await run.io_bound(runner.stop, self.spec)
        await self.update_state()
        if not stopped and self.active:
            self.notify(t("stop_outside", name=self.spec.name), type="warning")
        self.render.refresh()

    async def open_folder(self) -> None:
        path = str(self.folder)

        def open_it() -> None:          # in a worker thread, like any process start
            if sys.platform == "win32":
                os.startfile(path)  # noqa: S606 - the user's own folder
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", path])
        await run.io_bound(open_it)

    async def adopt(self) -> None:
        """Use an installation made outside the hub (keeps its data)."""
        exe = exe_name(self.spec)
        chosen = await self.page.pick_folder(t("adopt_hint", exe=exe), str(self.folder.parent))
        if not chosen:
            return
        if not (Path(chosen) / exe).is_file():
            self.notify(t("adopt_bad", exe=exe), type="warning")
            return
        self.settings["path"] = str(Path(chosen))
        config.save(self.page.cfg)
        self.render.refresh()

    @property
    def lan(self) -> bool:
        return config.app_lan(self.page.cfg, self.spec)

    def set_flag(self, key: str, value: bool) -> None:
        """Start with the hub (autostart) / restart when it stopped by
        itself (restart) - hub/watchdog.py."""
        self.settings[key] = bool(value)
        config.save(self.page.cfg)
        if key == "restart" and value:
            watchdog.forgive(self.spec.id)
        self.render.refresh()

    def set_lan(self, value: bool) -> None:
        self.settings["lan"] = bool(value)
        config.save(self.page.cfg)
        if self.running:
            self.notify(t("lan_restart", name=self.spec.name), type="info")

    def set_port(self, value) -> None:
        try:
            port = int(value)
        except (TypeError, ValueError):
            return
        if 1024 <= port <= 65535 and not self.page.port_clash(self, port):
            self.settings["port"] = port
            config.save(self.page.cfg)

    def show_notes(self) -> None:
        if not self.release:
            return
        # Outside the card: a card refresh would delete it
        with self.page.dialog_host, ui.dialog() as dialog, ui.card().classes("w-[min(92vw,720px)] max-h-[80vh]"):
            ui.label(f"{self.spec.name} {self.release.version} · {self.release.published}").classes("text-lg font-semibold")
            with ui.scroll_area().classes("h-[55vh] w-full"):
                ui.markdown(self.release.notes or "-")
            with ui.row().classes("justify-end w-full"):
                ui.link("GitHub", self.release.page_url, new_tab=True)
                ui.button(t("ok"), on_click=dialog.close)
        dialog.open()

    # ── view ──────────────────────────────────────────────────────────────
    def _port_field(self) -> None:
        ui.number(t("port"), value=self.port, min=1024, max=65535, format="%d",
                  validation={t("port_taken"): lambda v: not self.page.port_clash(self, v)},
                  on_change=lambda e: self.set_port(e.value)).classes("w-16").props("dense no-error-icon")

    @ui.refreshable_method
    def render(self) -> None:
        installed, version = self.installed(), self.installed_version()
        state = self.state.state if installed and self.state else None
        running, other = state == runner.RUNNING, state == runner.OTHER
        starting = state == runner.STARTING
        rel = self.release
        with ui.card().classes("w-full"):
            with ui.row().classes("items-start justify-between w-full"):
                with ui.column().classes("gap-0"):
                    ui.label(self.spec.name).classes("text-lg font-semibold")
                    ui.label(t(f"desc_{self.spec.id}")).classes("text-sm text-gray-500")
                if running:
                    ui.badge(t("running", port=self.port), color="positive").classes("text-sm")
                elif starting:
                    with ui.badge(color="info").classes("text-sm items-center gap-1"):
                        ui.spinner(size="xs", color="white")
                        ui.label(t("starting"))
                elif other:
                    ui.badge(t("port_other", port=self.port), color="warning").classes("text-sm") \
                        .tooltip(t("port_other_hint"))
                elif installed and state is None:
                    ui.badge(t("checking"), color="grey").classes("text-sm")
                else:
                    ui.badge(t("stopped"), color="grey").classes("text-sm")
            with ui.row().classes("gap-6 text-sm"):
                ui.label(f"{t('installed')} : " + ((version or t("unknown_version")) if installed else t("not_installed")))
                ui.label(f"{t('latest')} : " + (f"{rel.version} ({rel.published})" if rel else (self.release_error or t("checking"))))
            if installed:
                ui.label(str(self.folder)).classes("text-xs text-gray-500")
            if self.busy:
                ui.label(self.progress_text).classes("text-sm")
                ui.linear_progress(show_value=False).bind_value_from(self, "progress_value").classes("w-full")
                return
            with ui.row().classes("items-center gap-2 flex-wrap"):
                can_get = rel is not None and rel.asset_url is not None
                if not installed:
                    ui.button(t("install"), icon="download", on_click=self.install_or_update).set_enabled(can_get)
                    ui.button(t("adopt"), icon="folder_open", on_click=self.adopt).props("flat")
                else:
                    # An app that updates itself (hub_updates=False) is only started here
                    if self.spec.hub_updates and can_get and releases.is_newer(rel.version, version):
                        ui.button(t("update", v=rel.version), icon="system_update", on_click=self.install_or_update)
                    elif self.spec.hub_updates and can_get:
                        ui.button(t("reinstall"), icon="refresh", on_click=self.install_or_update).props("flat")
                    if running or starting:
                        ui.button(t("stop"), icon="stop", on_click=self.stop).props("color=negative")
                    else:
                        start = ui.button(t("start"), icon="play_arrow", on_click=self.start).props("color=positive")
                        start.set_enabled(not other)
                        if other:
                            start.tooltip(t("port_other_hint"))
                    # An icon: the row of buttons on one line (a shorter page)
                    ui.button(icon="folder", on_click=self.open_folder).props("flat round") \
                        .tooltip(t("open_folder"))
                    previous = installer.has_backup(self.folder)
                    if previous:
                        label = t("rollback", v=previous) if previous != "?" else t("rollback_previous")
                        ui.button(label, icon="undo", on_click=self.rollback).props("flat")
                if rel:
                    ui.button(t("whats_new"), icon="article", on_click=self.show_notes).props("flat")
                if not installed:
                    self._port_field()
            if installed:
                # LAN access with the start options, on one line (user-
                # requested: a shorter page)
                with ui.row().classes("items-center gap-4"):
                    self._port_field()
                    if self.spec.lan_args:
                        ui.checkbox(t("lan"), value=self.lan, on_change=lambda e: self.set_lan(e.value)) \
                            .tooltip(t("lan_hint"))
                    ui.checkbox(t("autostart"), value=bool(self.settings.get("autostart")),
                                on_change=lambda e: self.set_flag("autostart", e.value)).tooltip(t("autostart_hint"))
                    ui.checkbox(t("auto_restart"), value=bool(self.settings.get("restart")),
                                on_change=lambda e: self.set_flag("restart", e.value)).tooltip(t("auto_restart_hint"))
                note = watchdog.status(self.spec.id)
                if note:
                    ui.label(note).classes("text-xs " + ("text-negative" if watchdog.gave_up(self.spec.id) else "text-gray-500"))


START_GAP_S = 5     # between the apps of "Start both"


class HubPage:
    def __init__(self):
        self.cfg = config.load()
        if instances.migrate(self.cfg):
            config.save(self.cfg)
        set_language(self.cfg.get("language") or system_language())
        self.cards = [AppCard(self, spec) for spec in APPS]
        self.dwarfs = DwarfsView(self)
        self.sync = SyncView(self)
        self.installations = InstallationsView(self)
        self.current_tab = "apps"

    def card(self, app_id: str) -> AppCard:
        return next(c for c in self.cards if c.spec.id == app_id)

    def closed(self) -> bool:
        """This page's browser client is gone (window reloaded or closed) -
        what a long background task finishes with has nowhere to go."""
        return self.dialog_host.is_deleted

    def notify(self, *args, **kwargs) -> None:
        if self.closed():
            return
        with self.dialog_host:
            ui.notify(*args, **kwargs)

    def port_clash(self, card: AppCard, port) -> AppCard | None:
        """The other installed application already given this port."""
        try:
            port = int(port)
        except (TypeError, ValueError):
            return None
        return next((c for c in self.cards if c is not card and c.installed() and c.port == port), None)

    async def start_both(self) -> None:
        """Together, a few seconds apart: Scope Archive first, Dwarfium Lite
        then says hello to it (and retries every 10 s while it isn't up)."""
        cards = [c for c in self.cards if c.installed()]
        ports = [c.port for c in cards]
        if len(set(ports)) < len(ports):
            ui.notify(t("same_port"), type="warning", multi_line=True)
            return

        async def start(card: AppCard, delay: float) -> bool:
            await asyncio.sleep(delay)
            return await card.start(notify=False)
        results = await asyncio.gather(*(start(c, i * START_GAP_S) for i, c in enumerate(cards)))
        started = [c.spec.name for c, ok in zip(cards, results) if ok]
        if started:
            ui.notify(t("started_list", names=", ".join(started)), type="positive")

    async def stop_both(self) -> None:
        for card in reversed(self.cards):
            if card.installed():
                await card.stop()

    def show_apps_help(self) -> None:
        ui.add_css(".sync-help h2 { font-size: 1.35rem; line-height: 1.3; margin: 0.4rem 0 0.6rem; }"
                   ".sync-help h3 { font-size: 1.05rem; font-weight: 600; margin: 1rem 0 0.3rem; }")
        with self.dialog_host, ui.dialog() as dialog, \
                ui.card().classes("w-full max-w-3xl").style("max-height: 85vh"):
            with ui.scroll_area().classes("w-full").style("height: 70vh"):
                ui.markdown(help_apps()).classes("w-full sync-help")
            with ui.row().classes("w-full justify-end"):
                ui.button(t("close"), on_click=dialog.close).props("flat")
        dialog.open()

    def set_autorun(self, e) -> None:
        try:
            autorun.set_enabled(bool(e.value))
        except OSError as err:
            ui.notify(t("failed", e=err), type="negative")

    def set_language(self, lang: str) -> None:
        self.cfg["language"] = lang
        config.save(self.cfg)
        ui.navigate.reload()

    async def pick_folder(self, hint: str, start: str | None = None) -> str | None:
        """A folder: the system dialog in the hub's window, else (browser,
        or the dialog failed) a path typed in a small dialog."""
        if app.native.main_window is not None:
            try:
                import webview
                # FileDialog.FOLDER since pywebview 5; FOLDER_DIALOG before
                mode = webview.FileDialog.FOLDER if hasattr(webview, "FileDialog") else webview.FOLDER_DIALOG
                kwargs = {"allow_multiple": False}
                if start and os.path.isdir(start):
                    kwargs["directory"] = start
                result = await app.native.main_window.create_file_dialog(mode, **kwargs)
                if not result:
                    return None
                return result if isinstance(result, str) else result[0]
            except Exception as e:  # the typed path below still works
                print(f"[hub] folder dialog failed: {e!r}")
        with self.dialog_host, ui.dialog() as dialog, ui.card().classes("min-w-[460px]"):
            ui.label(hint)
            path_input = ui.input(value=start or "").classes("w-full")
            with ui.row().classes("justify-end w-full"):
                ui.button(t("cancel"), on_click=lambda: dialog.submit(None)).props("flat")
                ui.button(t("ok"), on_click=lambda: dialog.submit(path_input.value.strip()))
        return await dialog

    async def change_root(self) -> None:
        chosen = await self.pick_folder(t("install_root"), self.cfg["install_root"])
        if chosen:
            self.cfg["install_root"] = chosen
            config.save(self.cfg)
            self.root_label.set_text(chosen)
            for card in self.cards:
                card.render.refresh()

    def build(self) -> None:
        set_language(self.cfg.get("language") or system_language())
        with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
            with ui.row().classes("items-center justify-between w-full"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.html(LOGO_SVG, sanitize=False).classes("w-12 h-12 shrink-0")  # our own constant
                    with ui.column().classes("gap-0"):
                        ui.label(f"Dwarfium-Hub {get_version()}").classes("text-2xl font-bold")
                        ui.label(t("subtitle")).classes("text-gray-500")
                ui.toggle({"en": "EN", "fr": "FR"}, value=language(), on_change=lambda e: self.set_language(e.value)) \
                    .props("dense")
            with ui.row().classes("items-center gap-2 text-sm w-full"):
                ui.label(f"{t('install_root')} :")
                self.root_label = ui.label(self.cfg["install_root"]).classes("font-mono")
                ui.button(t("change"), on_click=self.change_root).props("flat dense")
                if autorun.supported():
                    # Windows: the hub at the session's opening, which starts the
                    # applications ticked "Start with the hub" - on this line,
                    # a shorter page (user-requested)
                    ui.checkbox(t("hub_autorun"), value=autorun.enabled(), on_change=self.set_autorun) \
                        .tooltip(t("hub_autorun_hint")).classes("text-sm ml-auto")
            with ui.tabs(on_change=self.tab_changed).classes("w-full").props("align=left") as tabs:
                apps_tab = ui.tab("apps", t("tab_apps"), icon="apps")
                ui.tab("installations", t("tab_installations"), icon="hub")
                ui.tab("dwarfs", t("tab_dwarfs"), icon="satellite_alt")
                ui.tab("sync", t("tab_sync"), icon="sync_alt")
            self.tabs = tabs
            with ui.tab_panels(tabs, value=apps_tab).classes("w-full bg-transparent"):
                with ui.tab_panel("apps").classes("p-0 gap-4"):
                    for card in self.cards:
                        card.render()
                    with ui.row().classes("gap-2"):
                        ui.button(t("start_both"), icon="play_circle", on_click=self.start_both).props("color=positive")
                        ui.button(t("stop_both"), icon="stop_circle", on_click=self.stop_both) \
                            .props("flat color=negative")
                        ui.button(t("sy_help"), icon="help_outline", on_click=self.show_apps_help) \
                            .props("flat dense no-caps")
                    ui.label(t("data_safe")).classes("text-xs text-gray-500")
                with ui.tab_panel("installations").classes("p-0"):
                    self.installations.render()
                with ui.tab_panel("dwarfs").classes("p-0"):
                    self.dwarfs.render()
                with ui.tab_panel("sync").classes("p-0"):
                    self.sync.render()
        self.dialog_host = ui.element()
        for card in self.cards:
            ui.timer(0.1, card.check_release, once=True)
        self._watching = False
        ui.timer(0.1, self.watch_running, once=True)
        ui.timer(2, self.sync.check_at_startup, once=True)
        ui.timer(3, self.watch_running)
        ui.timer(20, self.installations.tick)

    async def tab_changed(self, e) -> None:
        self.current_tab = e.value
        if e.value == "installations":
            await self.installations.refresh_status()
        if e.value == "dwarfs":
            await self.dwarfs.reload()

    async def watch_running(self) -> None:
        """A card is rebuilt only when what answers on its port changed
        (its app started or stopped, also outside the hub): rebuilding it
        every time would close its dialogs and lose a port being typed."""
        if self._watching:      # a slow answer: the previous round still runs
            return
        self._watching = True
        try:
            for card in self.cards:
                if card.busy or card.launching:
                    continue
                if await card.update_state() and not (card.busy or card.launching):
                    card.render.refresh()
                    self.dwarfs.render.refresh()    # Dwarfium Lite running or not: its buttons
                    self.installations.render.refresh()
                    if not self.sync.busy:
                        self.sync.render.refresh()
        finally:
            self._watching = False


def register() -> None:
    @ui.page("/")
    def index():
        ui.query("body").classes("bg-slate-50")
        HubPage().build()
