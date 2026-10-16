"""The Dwarfs tab: the Dwarfs of Dwarfium Lite and of Scope Archive side
by side - linked, to link (same IP or name), or on one side only - and
what makes them one: link, create in Scope Archive, add to Dwarfium Lite
(its own page, filled in), copy a name or an IP from one side to the
other.

Dwarfium Lite's files are only changed while it is stopped (it reads them
when it starts): those buttons wait for it to be stopped.

The Dwarfium Lite shown is this PC's, or an instance of the Installations
tab with a shared folder (user-requested Oct 2026): its files read and
written through the share. Changed only when the instance says Dwarfium
Lite is stopped (the computer answers, not Dwarfium Lite) - or, without
an address to ask, when the user confirms it. Its link to Scope Archive is
written with the address of this PC's Scope Archive as that computer
reaches it (its Tailscale name), kept per instance ("archive_url").
"""
from __future__ import annotations

import socket
import webbrowser
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlsplit

from nicegui import run, ui

from hub import config, dwarfs as D, instances as I
from hub import lite_api
from hub import runner
from hub.i18n import t

if TYPE_CHECKING:
    from hub.ui import AppCard, HubPage


class DwarfsView:
    def __init__(self, page: "HubPage"):
        self.page = page
        self.lite_dwarfs: list[D.LiteDwarf] = []
        self.archive_dwarfs: list[D.ArchiveDwarf] | None = None
        self.rows: list[D.Row] = []
        self.error = ""
        self.loaded = False
        self.archive_keeps_ids = False     # Scope Archive V3.4.3+
        # The Dwarfium Lite shown: None this PC's, else an instance id
        self.target: str | None = None
        self.remote: I.Status | None = None     # that instance's state, asked at each reload
        self.confirmed_stopped = False

    @property
    def lite(self) -> "AppCard":
        return self.page.card("astro_dwarf_session")

    @property
    def archive(self) -> "AppCard":
        return self.page.card("scope_archive")

    # ── which Dwarfium Lite ───────────────────────────────────────────────
    def _instances(self) -> list[dict]:
        return [i for i in self.page.cfg.get("instances", []) if i.get("share")]

    def _inst(self) -> dict | None:
        if self.target is None:
            return None
        inst = next((i for i in self._instances() if i["id"] == self.target), None)
        if inst is None:            # removed meanwhile
            self.target = None
        return inst

    @property
    def lite_folder(self) -> Path:
        inst = self._inst()
        return Path(inst["share"]) if inst else self.lite.folder

    def _remote_running(self) -> bool:
        return self.remote is not None and self.remote.state == I.ACTIVE

    def lite_locked(self) -> bool:
        """Dwarfium Lite's files can't be changed while it runs (or while
        the hub doesn't know yet whether it runs)."""
        inst = self._inst()
        if inst is None:
            return self.lite.state is None or self.lite.active
        if self.remote is not None and self.remote.state == I.STOPPED:
            return False
        # Nothing to ask (no address) or no answer: the user says so
        return self._remote_running() or not self.confirmed_stopped

    def _default_archive_url(self) -> str:
        return f"http://{socket.gethostname().lower()}:{self.archive.port}"

    async def _select_target(self, value: str) -> None:
        self.target = None if value == "local" else value
        self.confirmed_stopped = False
        self.loaded = False
        self.render.refresh()
        await self.reload()

    def _set_archive_url(self, inst: dict, value: str) -> None:
        value = (value or "").strip().rstrip("/")
        if value != inst.get("archive_url", ""):
            inst["archive_url"] = value
            config.save(self.page.cfg)
            self.render.refresh()       # the links to update with it

    # ── data ──────────────────────────────────────────────────────────────
    def _read(self) -> None:
        self.error = ""
        inst = self._inst()
        self.remote = I.status_of(inst) if inst else None
        try:
            if inst is not None and not I.share_ok(inst["share"]):
                raise D.DwarfsError(t("in_chk_share_bad", path=inst["share"]))
            lite_there = inst is not None or self.lite.installed()
            self.lite_dwarfs = D.read_lite(self.lite_folder) if lite_there else []
            self.archive_dwarfs = D.read_archive(self.archive.folder) if self.archive.installed() else None
            self.archive_keeps_ids = self.archive_dwarfs is not None and D.archive_has_ble_id(self.archive.folder)
        except D.DwarfsError as e:
            self.lite_dwarfs, self.archive_dwarfs, self.error = [], None, str(e)
        self.rows = D.match(self.lite_dwarfs, self.archive_dwarfs)
        if not self.archive_keeps_ids:      # nothing to copy there before V3.4.3
            for row in self.rows:
                if "ble_id" in row.differences:
                    row.differences.remove("ble_id")
        self.loaded = True

    async def reload(self) -> None:
        await run.io_bound(self._read)
        self.render.refresh()

    async def _do(self, action, done_text: str = "") -> None:
        """Runs a change (blocking function) then shows the new state."""
        try:
            await run.io_bound(action)
            if done_text:
                self.page.notify(done_text, type="positive")
        except (D.DwarfsError, OSError, ValueError) as e:
            self.page.notify(t("failed", e=e), type="negative", multi_line=True)
        await self.reload()

    # ── actions ───────────────────────────────────────────────────────────
    def _archive_url(self) -> str:
        inst = self._inst()
        if inst is None:
            return D.archive_url(self.archive.port)
        return inst.get("archive_url") or self._default_archive_url()

    async def link(self, row: D.Row, archive: D.ArchiveDwarf | None = None) -> None:
        target = archive or row.archive
        await self._do(lambda: D.link(self.lite_folder, row.lite, target.id, self._archive_url()),
                       t("dw_linked_ok", lite=row.lite.name, archive=target.name))

    async def unlink(self, row: D.Row) -> None:
        await self._do(lambda: D.link(self.lite_folder, row.lite, None, ""), t("dw_unlinked_ok", lite=row.lite.name))

    async def create_in_archive(self, row: D.Row) -> None:
        def action():
            new_id = D.create_archive(self.archive.folder, row.lite)
            D.link(self.lite_folder, row.lite, new_id, self._archive_url())
        await self._do(action, t("dw_created_ok", name=row.lite.name))

    async def link_all(self) -> None:
        rows = [r for r in self.rows if r.status == D.SUGGESTED]

        def action():
            for r in rows:
                D.link(self.lite_folder, r.lite, r.archive.id, self._archive_url())
        await self._do(action, t("dw_linked_all_ok", n=len(rows)))

    async def create_all(self) -> None:
        rows = [r for r in self.rows if r.status == D.LITE_ONLY]

        def action():
            for r in rows:
                new_id = D.create_archive(self.archive.folder, r.lite)
                D.link(self.lite_folder, r.lite, new_id, self._archive_url())
        await self._do(action, t("dw_created_all_ok", n=len(rows)))

    @staticmethod
    def _same_url(a: str, b: str) -> bool:
        def norm(url: str) -> str:
            return (url or "").strip().rstrip("/").lower().replace("://127.0.0.1", "://localhost")
        return norm(a) == norm(b)

    def _stale_url(self, row: D.Row) -> bool:
        """A link written with another Scope Archive address than the one
        this Dwarfium Lite reaches it at (another port, localhost on a
        remote computer, an old name)."""
        if row.status != D.LINKED:
            return False
        current = row.lite.dwarfium_base_url
        if self._inst() is None:
            # This PC: localhost or its name both reach it - only the port matters
            try:
                return urlsplit(current or "").port != self.archive.port
            except ValueError:      # not a valid address
                return True
        return not self._same_url(current, self._archive_url())

    async def update_url(self, row: D.Row) -> None:
        await self._do(lambda: D.link(self.lite_folder, row.lite, row.archive.id, self._archive_url()),
                       t("dw_url_updated_ok", n=1))

    async def update_all_urls(self) -> None:
        rows = [r for r in self.rows if self._stale_url(r)]

        def action():
            for r in rows:
                D.link(self.lite_folder, r.lite, r.archive.id, self._archive_url())
        await self._do(action, t("dw_url_updated_ok", n=len(rows)))

    async def copy(self, row: D.Row, what: str, to_archive: bool) -> None:
        lite, archive = row.lite, row.archive
        if what == "ble_id":
            action = lambda: D.set_archive_ble_id(self.archive.folder, archive.id, D.normalize_ble_id(lite.uid))
        elif what == "name":
            action = (lambda: D.set_archive_name(self.archive.folder, archive.id, lite.name)) if to_archive else \
                     (lambda: D.set_lite_name(self.lite_folder, lite, archive.name))
        else:
            action = (lambda: D.set_archive_ip(self.archive.folder, archive.id, lite.ip)) if to_archive else \
                     (lambda: D.set_lite_ip(self.lite_folder, lite, archive.ip))
        await self._do(action, t("dw_copied_ok"))

    async def _lite_up(self) -> bool:
        """Dwarfium Lite running, started first if needed (an instance's
        can't be started from here)."""
        inst = self._inst()
        if inst is not None:
            if not self._remote_running():
                self.page.notify(t("dw_remote_not_running", name=inst.get("name") or ""), type="warning")
            return self._remote_running()
        if self.lite.running:
            return True
        if self.lite.state is not None and self.lite.state.state == runner.OTHER:
            self.page.notify(t("port_other", port=self.lite.port), type="warning")
            return False
        self.page.notify(t("dw_starting_lite"), type="info")
        return await self.lite.start(notify=False)

    async def open_lite_page(self, path: str, params: dict | None = None) -> None:
        """A page of Dwarfium Lite, started first if needed: in its own window
        (3.2.4+), else in the browser - said where either way."""
        if not await self._lite_up():
            return
        target = path + (f"?{urlencode(params)}" if params else "")
        if self._inst() is not None:    # in this PC's browser, not that computer's window
            await run.io_bound(webbrowser.open, f"http://{self.remote.host}:{self._remote_port()}{target}")
            self.page.notify(t("dw_opened_in_browser"), type="info", multi_line=True)
            return
        if await run.io_bound(lite_api.open_page, self.lite.port, target):
            self.page.notify(t("dw_opened_in_lite"), type="positive")
        else:
            await run.io_bound(webbrowser.open, f"http://localhost:{self.lite.port}{target}")
            self.page.notify(t("dw_opened_in_browser"), type="info", multi_line=True)

    async def identify(self, ip: str) -> None:
        """The Dwarf's ring light flashes - through Dwarfium Lite, which
        refuses during a capture."""
        if not await self._lite_up():
            return
        self.page.notify(t("identify_running"), type="info")
        if self._inst() is not None:
            result = await run.io_bound(lite_api.identify, self._remote_port(), ip, self.remote.host)
        else:
            result = await run.io_bound(lite_api.identify, self.lite.port, ip)
        result = result or "failed"     # None: the call cancelled (the hub closing)
        self.page.notify(t(f"identify_{result}", ip=ip), type="positive" if result == "ok" else "warning",
                         multi_line=True)

    async def add_to_lite(self, row: D.Row) -> None:
        a = row.archive
        # Dwarfium Lite (3.2.4+) saves the new device already linked to it
        await self.open_lite_page("/manual-config", {
            "name": a.name, "model": D.MODELS.get(a.model, ""), "ip": a.ip,
            "dwarfium_id": a.id, "dwarfium_base_url": self._archive_url()})

    def _remote_port(self) -> int:
        inst = self._inst()
        return int((inst or {}).get("port") or I.DEFAULT_PORT)

    async def stop_lite(self) -> None:
        await self.lite.stop()
        await self.reload()

    # ── view ──────────────────────────────────────────────────────────────
    @staticmethod
    def _side(title: str, name: str, model: str, ip: str, ble_id: str) -> None:
        with ui.column().classes("gap-0 min-w-0 flex-1"):
            ui.label(title).classes("text-xs text-gray-500")
            ui.label(name or "—").classes("font-medium break-all")
            ui.label(" · ".join(x for x in (D.MODELS.get(model, ""), ip) if x) or " ").classes("text-xs text-gray-500")
            ui.label(f"ID {ble_id}" if ble_id else t("dw_no_id")).classes("text-xs font-mono text-gray-500") \
                .tooltip(t("dw_id_hint"))

    @staticmethod
    def _empty_side(title: str, text: str) -> None:
        with ui.column().classes("gap-0 min-w-0 flex-1"):
            ui.label(title).classes("text-xs text-gray-500")
            ui.label(text).classes("text-sm text-gray-400 italic")

    def _lite_button(self, label: str, icon: str, handler, *, flat: bool = False):
        """A button that changes Dwarfium Lite's files: disabled while it runs."""
        button = ui.button(label, icon=icon, on_click=handler).props("dense no-caps" + (" flat" if flat else ""))
        if self.lite_locked():
            button.disable()
            button.tooltip(t("dw_stop_lite_first"))
        return button

    def _target_bar(self) -> None:
        """Which Dwarfium Lite: this PC's or an instance's (by its share)."""
        instances = self._instances()
        if not instances:
            return
        options = {"local": t("dw_target_local")}
        options.update({i["id"]: f"{i.get('name') or i['share']} ({i['share']})" for i in instances})
        ui.select(options, value=self.target or "local", label=t("dw_target"),
                  on_change=lambda e: self._select_target(e.value)).classes("w-full max-w-xl")
        inst = self._inst()
        if inst is None:
            return
        name = inst.get("name") or inst["share"]
        with ui.column().classes("w-full gap-2 bg-purple-50 rounded p-2"):
            with ui.row().classes("items-center gap-2 text-sm no-wrap"):
                if self._remote_running():
                    ui.icon("circle", color="positive", size="xs")
                    ui.label(t("dw_remote_running", name=name)).classes("flex-1")
                elif self.remote is not None and self.remote.state == I.STOPPED:
                    ui.icon("radio_button_unchecked", color="grey", size="xs")
                    ui.label(t("dw_remote_stopped", name=name)).classes("flex-1")
                else:
                    ui.icon("help_outline", color="grey", size="xs")
                    ui.label(t("dw_remote_unknown", name=name)).classes("flex-1")
            if not self._remote_running() and not (self.remote is not None and self.remote.state == I.STOPPED):
                ui.checkbox(t("dw_remote_confirm", name=name), value=self.confirmed_stopped,
                            on_change=lambda e: (setattr(self, "confirmed_stopped", e.value), self.render.refresh())) \
                    .classes("text-sm")
            url = ui.input(t("dw_archive_url", name=name), value=self._archive_url()).classes("w-full")
            url._props["hint"] = t("dw_archive_url_hint")
            url.on("blur", lambda e, i=inst, u=url: self._set_archive_url(i, u.value))

    def _row(self, row: D.Row) -> None:
        status_icon = {D.LINKED: ("link", "positive", "dw_status_linked"),
                       D.MISMATCH: ("error", "negative", "dw_status_mismatch"),
                       D.SUGGESTED: ("add_link", "primary", "dw_status_suggested"),
                       D.BROKEN: ("link_off", "negative", "dw_status_broken"),
                       D.LITE_ONLY: ("arrow_forward", "grey", "dw_status_lite_only"),
                       D.ARCHIVE_ONLY: ("arrow_back", "grey", "dw_status_archive_only")}[row.status]
        if row.verified:        # same identifier on both sides: the same Dwarf for sure
            status_icon = ("verified", "positive",
                           "dw_status_linked_verified" if row.status == D.LINKED else "dw_status_verified")
        with ui.card().classes("w-full p-3"):
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                if row.lite:
                    self._side("Dwarfium Lite", row.lite.name, row.lite.model, row.lite.ip, D.normalize_ble_id(row.lite.uid))
                else:
                    self._empty_side("Dwarfium Lite", t("dw_none"))
                with ui.column().classes("items-center gap-0 w-28 shrink-0"):
                    ui.icon(status_icon[0], color=status_icon[1], size="md")
                    ui.label(t(status_icon[2])).classes("text-xs text-center")
                if row.archive:
                    self._side("Scope Archive", row.archive.name, row.archive.model, row.archive.ip, row.archive.ble_id)
                elif row.status == D.BROKEN:
                    self._empty_side("Scope Archive", t("dw_missing", id=row.lite.dwarfium_id))
                else:
                    self._empty_side("Scope Archive", t("dw_none"))

            with ui.row().classes("w-full items-center gap-2 flex-wrap justify-end"):
                ip = (row.lite.ip if row.lite else "") or (row.archive.ip if row.archive else "")
                if ip:      # left of the row's actions
                    ui.button(icon="flare", on_click=lambda i=ip: self.identify(i)) \
                        .props("flat round dense").classes("mr-auto").tooltip(t("identify_hint", ip=ip))
                if row.status == D.SUGGESTED:
                    if row.differences:
                        ui.label(t("dw_differs", what=", ".join(t(f"dw_{d}") for d in row.differences))) \
                            .classes("text-xs text-gray-500 mr-auto")
                    self._lite_button(t("dw_link"), "link", lambda r=row: self.link(r))
                elif row.status == D.MISMATCH:
                    ui.label(t("dw_mismatch_hint")).classes("text-xs text-negative mr-auto")
                    self._lite_button(t("dw_unlink"), "link_off", lambda r=row: self.unlink(r))
                elif row.status == D.LINKED:
                    if row.differences:
                        ui.label(t("dw_differs", what=", ".join(t(f"dw_{d}") for d in row.differences))) \
                            .classes("text-xs text-orange-700 mr-auto")
                    if "ble_id" in row.differences:
                        ui.button(t("dw_ble_id_to_archive"),
                                  on_click=lambda r=row: self.copy(r, "ble_id", True)).props("dense no-caps flat")
                    for what in ("name", "ip"):
                        if what in row.differences:
                            ui.button(t(f"dw_{what}_to_archive"),
                                      on_click=lambda r=row, w=what: self.copy(r, w, True)).props("dense no-caps flat")
                            self._lite_button(t(f"dw_{what}_to_lite"), None,
                                              lambda r=row, w=what: self.copy(r, w, False), flat=True)
                    self._lite_button(t("dw_unlink"), "link_off", lambda r=row: self.unlink(r), flat=True)
                    if self._stale_url(row):
                        with ui.row().classes("w-full items-center gap-2 no-wrap"):
                            ui.icon("swap_horiz", color="orange", size="xs")
                            ui.label(t("dw_url_differs", old=row.lite.dwarfium_base_url or "—",
                                       new=self._archive_url())).classes("text-xs text-orange-700 flex-1 break-all")
                            self._lite_button(t("dw_update_url"), "sync", lambda r=row: self.update_url(r), flat=True)
                elif row.status in (D.LITE_ONLY, D.BROKEN):
                    if self.archive_dwarfs is not None:
                        # never a Dwarf whose identifier says it is another one
                        lite_id = D.normalize_ble_id(row.lite.uid)
                        free = [r.archive for r in self.rows if r.status == D.ARCHIVE_ONLY
                                and not (lite_id and r.archive.ble_id and r.archive.ble_id != lite_id)]
                        if free and not self.lite_locked():
                            ui.select({a.id: a.name for a in free}, label=t("dw_link_to"),
                                      on_change=lambda e, r=row, f=free: self.link(r, next(a for a in f if a.id == e.value))) \
                                .props("dense outlined options-dense").classes("w-48")
                        self._lite_button(t("dw_create_archive"), "add", lambda r=row: self.create_in_archive(r))
                    if row.status == D.BROKEN:
                        self._lite_button(t("dw_unlink"), "link_off", lambda r=row: self.unlink(r), flat=True)
                elif row.status == D.ARCHIVE_ONLY:
                    ui.label(t("dw_add_lite_hint")).classes("text-xs text-gray-500 mr-auto")
                    ui.button(t("dw_add_lite"), icon="open_in_new", on_click=lambda r=row: self.add_to_lite(r)) \
                        .props("dense no-caps")

    @ui.refreshable_method
    def render(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full items-center justify-between"):
                ui.label(t("dw_intro")).classes("text-sm text-gray-600 flex-1")
                ui.button(icon="refresh", on_click=self.reload).props("flat round dense").tooltip(t("dw_refresh"))
            if not self.loaded:
                ui.spinner()
                return
            self._target_bar()
            if not ((self._inst() is not None or self.lite.installed()) and self.archive.installed()):
                ui.label(t("dw_install_both")).classes("text-gray-600")
                return
            if self.error:
                ui.label(t("failed", e=self.error)).classes("text-negative")
            if self.archive_dwarfs is None and not self.error:
                with ui.row().classes("items-center gap-2 text-sm text-orange-800 bg-orange-50 rounded p-2 w-full"):
                    ui.icon("info")
                    ui.label(t("dw_archive_no_db"))
            if self.lite_locked() and self._inst() is None:
                with ui.row().classes("items-center gap-2 text-sm bg-blue-50 rounded p-2 w-full"):
                    ui.icon("info", color="primary")
                    ui.label(t("dw_lite_running")).classes("flex-1")
                    ui.button(t("dw_stop_lite"), icon="stop", on_click=self.stop_lite).props("dense no-caps color=negative")

            if not self.rows:
                # Nothing on either side: a Dwarf is first added in Dwarfium Lite
                # (it needs Bluetooth pairing or the Dwarf's IP + UID)
                with ui.card().classes("w-full items-start"):
                    ui.label(t("dw_empty_title")).classes("text-lg font-semibold")
                    ui.label(t("dw_empty_text")).classes("text-sm")
                    with ui.row().classes("gap-2"):
                        ui.button(t("dw_pair_ble"), icon="bluetooth",
                                  on_click=lambda: self.open_lite_page("/pairing")).props("no-caps")
                        ui.button(t("dw_manual"), icon="edit_note",
                                  on_click=lambda: self.open_lite_page("/manual-config")).props("no-caps flat")
                return

            suggested = sum(r.status == D.SUGGESTED for r in self.rows)
            lite_only = sum(r.status == D.LITE_ONLY for r in self.rows)
            stale = sum(self._stale_url(r) for r in self.rows)
            if (suggested > 1 or lite_only > 1 or stale > 1) and self.archive_dwarfs is not None:
                with ui.row().classes("gap-2"):
                    if stale > 1:
                        self._lite_button(t("dw_update_url_all", n=stale), "sync", self.update_all_urls)
                    if suggested > 1:
                        self._lite_button(t("dw_link_all", n=suggested), "link", self.link_all)
                    if lite_only > 1:
                        self._lite_button(t("dw_create_all", n=lite_only), "add", self.create_all)
            for row in self.rows:
                self._row(row)
            ui.label(t("dw_footer")).classes("text-xs text-gray-500")
