"""The Synchronize tab: two Dwarfium Lite installations - the hub's own,
or any folder (a source run, a laptop's, a mini PC's through a Windows
share) - compared, then merged both ways (hub/lite_sync.py) after a
preview where every change can be unticked.

Dwarfium Lite must be stopped on both sides: for the hub's installation
the hub knows it (and can stop it), for another folder the user confirms.
The folders added here are the shares of the hub's instances
(hub/instances.py, also edited in the Installations tab).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

from nicegui import run, ui

from hub import config, instances
from hub.help_sync import help_sync
from hub import lite_sync as S
from hub.i18n import t

if TYPE_CHECKING:
    from hub.ui import HubPage

HUB_LITE = "hub"        # the hub's own Dwarfium Lite installation
# A network share not there (PC off, Tailscale down) can block a while:
# the startup check gives up on a folder after this
_CHECK_TIMEOUT_S = 20
UNREACHABLE = -1


class SyncView:
    def __init__(self, page: "HubPage"):
        self.page = page
        self.a: str | None = HUB_LITE
        self.b: str | None = None
        self.actions: list[S.Action] | None = None
        self.compared: tuple[str, str] | None = None
        self.confirmed_stopped = False
        self.busy = False
        # Startup check: folder -> number of changes with the hub's
        # Dwarfium Lite (UNREACHABLE: folder not reachable)
        self.startup: dict[str, int] = {}

    @property
    def lite(self):
        return self.page.card("astro_dwarf_session")

    # ── installations ─────────────────────────────────────────────────────
    def _folders(self) -> list[str]:
        return instances.shares(self.page.cfg)

    def _options(self) -> dict[str, str]:
        options = {}
        if self.lite.installed():
            options[HUB_LITE] = t("sy_hub_install", path=str(self.lite.folder))
        for folder in self._folders():
            name = self._label(folder)
            options[folder] = folder if name == Path(folder).name else f"{name} ({folder})"
        return options

    def _path(self, key: str) -> Path:
        return self.lite.folder if key == HUB_LITE else Path(key)

    def _label(self, key: str | None) -> str:
        if key is None:
            return "?"
        if key == HUB_LITE:
            return t("sy_hub_short")
        inst = instances.by_share(self.page.cfg, key)
        return inst["name"] if inst and inst.get("name") else Path(key).name or key

    async def add_folder(self) -> None:
        chosen = await self.page.pick_folder(t("sy_add_hint"))
        if not chosen:
            return
        if not (Path(chosen) / "devices.json").is_file():
            self.page.notify(t("sy_not_lite", path=chosen), type="warning", multi_line=True)
            return
        if chosen not in self._folders():
            self.page.cfg.setdefault("instances", []).append(
                {"id": instances.new_id(), "name": Path(chosen).name or chosen, "kind": "other",
                 "access": instances.LAN, "host": "", "port": instances.DEFAULT_PORT, "share": chosen})
            config.save(self.page.cfg)
            self.page.installations.render.refresh()
        if self.b is None:
            self.b = chosen
        self.actions = None
        self.render.refresh()

    def remove_folder(self, key: str) -> None:
        inst = instances.by_share(self.page.cfg, key)
        if inst:
            # An instance with an address stays on the map, without its share
            if inst.get("host"):
                inst["share"] = ""
            else:
                self.page.cfg["instances"].remove(inst)
            config.save(self.page.cfg)
            self.page.installations.render.refresh()
        self.a = None if self.a == key else self.a
        self.b = None if self.b == key else self.b
        self.actions = None
        self.render.refresh()

    def _select(self, side: str, value: str | None) -> None:
        setattr(self, side, value)
        self.actions = None
        self.render.refresh()

    # ── stopped on both sides ─────────────────────────────────────────────
    def _hub_lite_running(self) -> bool:
        return HUB_LITE in (self.a, self.b) and (self.lite.state is None or self.lite.active)

    def _other_folder_used(self) -> bool:
        return any(k and k != HUB_LITE for k in (self.a, self.b))

    def _can_write(self) -> bool:
        """The hub's own Dwarfium Lite is stopped by apply() itself; another
        folder's can't be stopped from here: the user confirms it."""
        return self.confirmed_stopped or not self._other_folder_used()

    # ── startup check ─────────────────────────────────────────────────────
    def _count_changes(self, folder: str) -> int:
        """Blocking. Changes between the hub's Dwarfium Lite and a folder
        (the differences only shown not counted)."""
        if not (Path(folder) / "devices.json").is_file():
            return UNREACHABLE
        actions = S.compare(S.read(self.lite.folder), S.read(Path(folder)))
        return sum(1 for x in actions if x.kind != S.CONFLICT)

    async def check_at_startup(self) -> None:
        """Once, when the hub opens: each added folder compared with the
        hub's Dwarfium Lite in the background - a notice when one differs,
        a line per folder in this tab. A folder not reachable (network
        share unavailable) is skipped after _CHECK_TIMEOUT_S."""
        if not self.lite.installed() or not self._folders():
            return
        for folder in self._folders():
            try:
                n = await asyncio.wait_for(run.io_bound(self._count_changes, folder), _CHECK_TIMEOUT_S)
            except (asyncio.TimeoutError, S.SyncError, OSError):
                n = UNREACHABLE
            self.startup[folder] = n
        differing = [f for f, n in self.startup.items() if n > 0]
        if differing:
            self.page.notify(t("sy_startup_notice", names=", ".join(self._label(f) for f in differing)),
                             type="info", multi_line=True, timeout=10000)
        if not self.busy:
            self.render.refresh()
        self.page.installations.render.refresh()

    async def compare_with(self, folder: str) -> None:
        self.a, self.b, self.actions = HUB_LITE, folder, None
        await self.compare()

    # ── compare / apply ───────────────────────────────────────────────────
    async def compare(self) -> None:
        if not self.a or not self.b or self.a == self.b:
            self.page.notify(t("sy_pick_two"), type="warning")
            return
        a, b = self._path(self.a), self._path(self.b)
        self.busy = True
        self.render.refresh()
        try:
            self.actions = await run.io_bound(lambda: S.compare(S.read(a), S.read(b)))
            self.compared = (self.a, self.b)
            # The hub's installation against a folder: what the map shows for it
            if HUB_LITE in self.compared:
                other = self.b if self.a == HUB_LITE else self.a
                self.startup[other] = sum(1 for x in self.actions if x.kind != S.CONFLICT)
                self.page.installations.render.refresh()
        except (S.SyncError, OSError) as e:
            self.actions = None
            self.page.notify(t("failed", e=e), type="negative", multi_line=True)
        finally:
            self.busy = False
        self.render.refresh()

    async def apply(self) -> None:
        if not self.actions or self.compared != (self.a, self.b):
            return
        if not self._can_write():
            self.page.notify(t("sy_stop_first"), type="warning", multi_line=True)
            return
        a, b = self._path(self.a), self._path(self.b)
        self.busy = True
        self.render.refresh()
        # The hub's Dwarfium Lite: stopped for the sync, started again after
        restart = self._hub_lite_running()
        if restart:
            self.page.notify(t("sy_stopping_lite"), type="info")
            await self.lite.stop()
            if self.lite.active:
                self.busy = False
                self.page.notify(t("sy_stop_failed"), type="negative", multi_line=True)
                self.render.refresh()
                return
        try:
            result = await run.io_bound(S.apply, a, b, self.actions)
            self.page.notify(t("sy_done", n=result["done"]) + "\n" + t("sy_backups", paths="\n".join(result["backups"])),
                             type="positive", multi_line=True, timeout=15000)
        except (S.SyncError, OSError) as e:
            self.page.notify(t("failed", e=e), type="negative", multi_line=True)
        finally:
            self.busy = False
            if restart:
                await self.lite.start(notify=False)
        await self.compare()        # what is left: nothing but the conflicts

    # ── display ───────────────────────────────────────────────────────────
    def _changes(self) -> list[S.Action]:
        return [x for x in self.actions or [] if x.kind != S.CONFLICT]

    def _preview_text(self) -> str:
        changes = self._changes()
        conflicts = len(self.actions or []) - len(changes)
        return t("sy_preview", s=sum(x.selected for x in changes), n=len(changes), c=conflicts)

    def _update_selection(self) -> None:
        """The count and the Synchronize button follow the ticks."""
        self._preview_label.set_text(self._preview_text())
        if self._apply_button is not None:
            self._apply_button.set_enabled(self._can_write() and any(x.selected for x in self._changes()))

    def _toggle(self, act: S.Action, value: bool) -> None:
        act.selected = value
        # A Dwarf copied or not: its dashboard preferences with it
        followers = [x for x in self._changes() if act.dwarf_key and x.follows == act.dwarf_key
                     and x.direction == act.direction and x.selected != value]
        for x in followers:
            x.selected = value
        if followers:
            self.render.refresh()
        else:
            self._update_selection()

    def _select_all(self, value: bool) -> None:
        for act in self._changes():
            act.selected = value
        self.render.refresh()

    def _action_row(self, act: S.Action) -> None:
        with ui.row().classes("w-full items-center gap-2 no-wrap py-1 border-b"):
            if act.kind == S.CONFLICT:
                ui.icon("warning", color="orange").classes("shrink-0")
            else:
                ui.checkbox(value=act.selected, on_change=lambda e, x=act: self._toggle(x, e.value)) \
                    .props("dense")
                left, right = self._label(self.compared[0]), self._label(self.compared[1])
                arrow = f"{left} → {right}" if act.direction == S.A2B else f"{right} → {left}"
                ui.label(arrow).classes("text-xs text-gray-500 w-40 shrink-0 truncate")
            with ui.column().classes("gap-0 min-w-0 flex-1"):
                title = f"{act.device} · {act.label}" if act.device and act.kind != S.DEVICE else act.label
                ui.label(title).classes("text-sm truncate")
                ui.label(t(f"sy_kind_{act.kind}") + " — " + t(act.detail, **act.detail_args)).classes("text-xs text-gray-500")
            if act.warning == "todo":
                ui.icon("report", color="orange").tooltip(t("sy_todo_warning"))

    def _startup_lines(self) -> None:
        if not self.startup:
            return
        with ui.card().classes("w-full p-3 gap-1"):
            ui.label(t("sy_startup_title")).classes("text-sm font-medium")
            for folder, n in self.startup.items():
                name = self._label(folder)
                with ui.row().classes("w-full items-center gap-2 no-wrap").tooltip(folder):
                    if n == UNREACHABLE:
                        ui.icon("cloud_off", color="grey")
                        ui.label(t("sy_startup_unreachable", name=name)).classes("text-sm text-gray-500")
                    elif n == 0:
                        ui.icon("check_circle", color="positive")
                        ui.label(t("sy_startup_same", name=name)).classes("text-sm")
                    else:
                        ui.icon("sync_problem", color="orange")
                        ui.label(t("sy_startup_diff", name=name, n=n)).classes("text-sm flex-1")
                        ui.button(t("sy_compare"), on_click=lambda f=folder: self.compare_with(f)) \
                            .props("dense flat no-caps")

    def show_help(self) -> None:
        ui.add_css(".sync-help h2 { font-size: 1.35rem; line-height: 1.3; margin: 0.4rem 0 0.6rem; }"
                   ".sync-help h3 { font-size: 1.05rem; font-weight: 600; margin: 1rem 0 0.3rem; }")
        with self.page.dialog_host, ui.dialog() as dialog, \
                ui.card().classes("w-full max-w-3xl").style("max-height: 85vh"):
            with ui.scroll_area().classes("w-full").style("height: 70vh"):
                ui.markdown(help_sync()).classes("w-full sync-help")
            with ui.row().classes("w-full justify-end"):
                ui.button(t("close"), on_click=dialog.close).props("flat")
        dialog.open()

    @ui.refreshable
    def render(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full items-start gap-2 no-wrap"):
                ui.label(t("sy_intro")).classes("text-sm text-gray-600 flex-1")
                ui.button(t("sy_help"), icon="help_outline", on_click=self.show_help).props("flat dense no-caps")
            self._startup_lines()
            options = self._options()
            with ui.row().classes("w-full items-end gap-3 flex-wrap"):
                ui.select(options, value=self.a if self.a in options else None, label=t("sy_side_a"),
                          on_change=lambda e: self._select("a", e.value)).classes("min-w-[260px] flex-1")
                ui.icon("sync_alt", size="md").classes("text-gray-500 mb-2")
                ui.select(options, value=self.b if self.b in options else None, label=t("sy_side_b"),
                          on_change=lambda e: self._select("b", e.value)).classes("min-w-[260px] flex-1")
            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.button(t("sy_add_folder"), icon="create_new_folder", on_click=self.add_folder).props("flat dense no-caps")
                for key in self._folders():
                    ui.chip(self._label(key), icon="folder", removable=True,
                            on_value_change=lambda e, k=key: None if e.value else self.remove_folder(k)) \
                        .props("dense outline").tooltip(key)
            ui.label(t("sy_share_hint")).classes("text-xs text-gray-500")

            # Stopped on both sides
            if self._hub_lite_running():
                with ui.row().classes("items-center gap-2"):
                    ui.icon("pause_circle", color="orange")
                    ui.label(t("sy_hub_lite_running")).classes("text-sm")
            if self._other_folder_used():
                ui.checkbox(t("sy_confirm_stopped"), value=self.confirmed_stopped,
                            on_change=lambda e: (setattr(self, "confirmed_stopped", e.value), self.render.refresh())) \
                    .classes("text-sm")

            with ui.row().classes("gap-2"):
                ui.button(t("sy_compare"), icon="compare_arrows", on_click=self.compare) \
                    .props("no-caps").set_enabled(not self.busy)
            if self.busy:
                ui.spinner(size="md")
                return
            if self.actions is None:
                return
            changes = [x for x in self.actions if x.kind != S.CONFLICT]
            conflicts = [x for x in self.actions if x.kind == S.CONFLICT]
            if not self.actions:
                ui.label(t("sy_same")).classes("text-positive")
                return
            self._apply_button = None
            with ui.card().classes("w-full p-3 gap-0"):
                with ui.row().classes("w-full items-center gap-2 mb-2"):
                    self._preview_label = ui.label(self._preview_text()).classes("font-medium flex-1")
                    if len(changes) > 1:
                        ui.button(t("sy_select_all"), on_click=lambda: self._select_all(True)) \
                            .props("flat dense no-caps size=sm")
                        ui.button(t("sy_select_none"), on_click=lambda: self._select_all(False)) \
                            .props("flat dense no-caps size=sm")
                for act in changes + conflicts:
                    self._action_row(act)
            if changes:
                with ui.row().classes("items-center gap-2"):
                    self._apply_button = ui.button(t("sy_apply"), icon="sync", on_click=self.apply) \
                        .props("no-caps color=primary")
                    if not self._can_write():
                        ui.label(t("sy_stop_first")).classes("text-xs text-orange-700")
                self._update_selection()
                ui.label(t("sy_backup_note")).classes("text-xs text-gray-500")
