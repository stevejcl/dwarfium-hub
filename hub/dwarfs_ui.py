"""The Dwarfs tab: the Dwarfs of Dwarfium Lite and of Scope Archive side
by side - linked, to link (same IP or name), or on one side only - and
what makes them one: link, create in Scope Archive, add to Dwarfium Lite
(its own page, filled in), copy a name or an IP from one side to the
other.

Dwarfium Lite's files are only changed while it is stopped (it reads them
when it starts): those buttons wait for it to be stopped.
"""
from __future__ import annotations

import webbrowser
from typing import TYPE_CHECKING
from urllib.parse import urlencode

from nicegui import run, ui

from hub import dwarfs as D
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

    @property
    def lite(self) -> "AppCard":
        return self.page.card("astro_dwarf_session")

    @property
    def archive(self) -> "AppCard":
        return self.page.card("scope_archive")

    def lite_locked(self) -> bool:
        """Dwarfium Lite's files can't be changed while it runs (or while
        the hub doesn't know yet whether it runs)."""
        return self.lite.state is None or self.lite.active

    # ── data ──────────────────────────────────────────────────────────────
    def _read(self) -> None:
        self.error = ""
        try:
            self.lite_dwarfs = D.read_lite(self.lite.folder) if self.lite.installed() else []
            self.archive_dwarfs = D.read_archive(self.archive.folder) if self.archive.installed() else None
        except D.DwarfsError as e:
            self.lite_dwarfs, self.archive_dwarfs, self.error = [], None, str(e)
        self.rows = D.match(self.lite_dwarfs, self.archive_dwarfs)
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
        return D.archive_url(self.archive.port)

    async def link(self, row: D.Row, archive: D.ArchiveDwarf | None = None) -> None:
        target = archive or row.archive
        await self._do(lambda: D.link(self.lite.folder, row.lite, target.id, self._archive_url()),
                       t("dw_linked_ok", lite=row.lite.name, archive=target.name))

    async def unlink(self, row: D.Row) -> None:
        await self._do(lambda: D.link(self.lite.folder, row.lite, None, ""), t("dw_unlinked_ok", lite=row.lite.name))

    async def create_in_archive(self, row: D.Row) -> None:
        def action():
            new_id = D.create_archive(self.archive.folder, row.lite)
            D.link(self.lite.folder, row.lite, new_id, self._archive_url())
        await self._do(action, t("dw_created_ok", name=row.lite.name))

    async def link_all(self) -> None:
        rows = [r for r in self.rows if r.status == D.SUGGESTED]

        def action():
            for r in rows:
                D.link(self.lite.folder, r.lite, r.archive.id, self._archive_url())
        await self._do(action, t("dw_linked_all_ok", n=len(rows)))

    async def create_all(self) -> None:
        rows = [r for r in self.rows if r.status == D.LITE_ONLY]

        def action():
            for r in rows:
                new_id = D.create_archive(self.archive.folder, r.lite)
                D.link(self.lite.folder, r.lite, new_id, self._archive_url())
        await self._do(action, t("dw_created_all_ok", n=len(rows)))

    async def copy(self, row: D.Row, what: str, to_archive: bool) -> None:
        lite, archive = row.lite, row.archive
        if what == "name":
            action = (lambda: D.set_archive_name(self.archive.folder, archive.id, lite.name)) if to_archive else \
                     (lambda: D.set_lite_name(self.lite.folder, lite, archive.name))
        else:
            action = (lambda: D.set_archive_ip(self.archive.folder, archive.id, lite.ip)) if to_archive else \
                     (lambda: D.set_lite_ip(self.lite.folder, lite, archive.ip))
        await self._do(action, t("dw_copied_ok"))

    async def open_lite_page(self, path: str, params: dict | None = None) -> None:
        """A page of Dwarfium Lite in the browser, started first if needed."""
        if not self.lite.running:
            if self.lite.state is not None and self.lite.state.state == runner.OTHER:
                self.page.notify(t("port_other", port=self.lite.port), type="warning")
                return
            self.page.notify(t("dw_starting_lite"), type="info")
            if not await self.lite.start(notify=False):
                return
        query = f"?{urlencode(params)}" if params else ""
        webbrowser.open(f"http://localhost:{self.lite.port}{path}{query}")

    async def add_to_lite(self, row: D.Row) -> None:
        a = row.archive
        # Dwarfium Lite (3.2.4+) saves the new device already linked to it
        await self.open_lite_page("/manual-config", {
            "name": a.name, "model": D.MODELS.get(a.model, ""), "ip": a.ip,
            "dwarfium_id": a.id, "dwarfium_base_url": self._archive_url()})

    async def stop_lite(self) -> None:
        await self.lite.stop()
        await self.reload()

    # ── view ──────────────────────────────────────────────────────────────
    @staticmethod
    def _side(title: str, name: str, model: str, ip: str) -> None:
        with ui.column().classes("gap-0 min-w-0 flex-1"):
            ui.label(title).classes("text-xs text-gray-500")
            ui.label(name or "—").classes("font-medium break-all")
            ui.label(" · ".join(x for x in (D.MODELS.get(model, ""), ip) if x) or " ").classes("text-xs text-gray-500")

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

    def _row(self, row: D.Row) -> None:
        status_icon = {D.LINKED: ("link", "positive", "dw_status_linked"),
                       D.SUGGESTED: ("add_link", "primary", "dw_status_suggested"),
                       D.BROKEN: ("link_off", "negative", "dw_status_broken"),
                       D.LITE_ONLY: ("arrow_forward", "grey", "dw_status_lite_only"),
                       D.ARCHIVE_ONLY: ("arrow_back", "grey", "dw_status_archive_only")}[row.status]
        with ui.card().classes("w-full p-3"):
            with ui.row().classes("w-full items-center gap-3 no-wrap"):
                if row.lite:
                    self._side("Dwarfium Lite", row.lite.name, row.lite.model, row.lite.ip)
                else:
                    self._empty_side("Dwarfium Lite", t("dw_none"))
                with ui.column().classes("items-center gap-0 w-28 shrink-0"):
                    ui.icon(status_icon[0], color=status_icon[1], size="md")
                    ui.label(t(status_icon[2])).classes("text-xs text-center")
                if row.archive:
                    self._side("Scope Archive", row.archive.name, row.archive.model, row.archive.ip)
                elif row.status == D.BROKEN:
                    self._empty_side("Scope Archive", t("dw_missing", id=row.lite.dwarfium_id))
                else:
                    self._empty_side("Scope Archive", t("dw_none"))

            with ui.row().classes("w-full items-center gap-2 flex-wrap justify-end"):
                if row.status == D.SUGGESTED:
                    if row.differences:
                        ui.label(t("dw_differs", what=", ".join(t(f"dw_{d}") for d in row.differences))) \
                            .classes("text-xs text-gray-500 mr-auto")
                    self._lite_button(t("dw_link"), "link", lambda r=row: self.link(r))
                elif row.status == D.LINKED:
                    if row.differences:
                        ui.label(t("dw_differs", what=", ".join(t(f"dw_{d}") for d in row.differences))) \
                            .classes("text-xs text-orange-700 mr-auto")
                    for what in ("name", "ip"):
                        if what in row.differences:
                            ui.button(t(f"dw_{what}_to_archive"),
                                      on_click=lambda r=row, w=what: self.copy(r, w, True)).props("dense no-caps flat")
                            self._lite_button(t(f"dw_{what}_to_lite"), None,
                                              lambda r=row, w=what: self.copy(r, w, False), flat=True)
                    self._lite_button(t("dw_unlink"), "link_off", lambda r=row: self.unlink(r), flat=True)
                elif row.status in (D.LITE_ONLY, D.BROKEN):
                    if self.archive_dwarfs is not None:
                        free = [r.archive for r in self.rows if r.status == D.ARCHIVE_ONLY]
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
            if not (self.lite.installed() and self.archive.installed()):
                ui.label(t("dw_install_both")).classes("text-gray-600")
                return
            if self.error:
                ui.label(t("failed", e=self.error)).classes("text-negative")
            if self.archive_dwarfs is None and not self.error:
                with ui.row().classes("items-center gap-2 text-sm text-orange-800 bg-orange-50 rounded p-2 w-full"):
                    ui.icon("info")
                    ui.label(t("dw_archive_no_db"))
            if self.lite_locked():
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
            if (suggested > 1 or lite_only > 1) and self.archive_dwarfs is not None:
                with ui.row().classes("gap-2"):
                    if suggested > 1:
                        self._lite_button(t("dw_link_all", n=suggested), "link", self.link_all)
                    if lite_only > 1:
                        self._lite_button(t("dw_create_all", n=lite_only), "add", self.create_all)
            for row in self.rows:
                self._row(row)
            ui.label(t("dw_footer")).classes("text-xs text-gray-500")
