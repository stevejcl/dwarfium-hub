"""The Installations tab (user-requested Oct 2026): a map of the Dwarfium
Lite installations - this PC (the hub's own, with Scope Archive) and the
instances added here (hub/instances.py): a source run, a laptop, a mini
PC, on the home network or reached through Tailscale.

Each card shows the live state read from that Dwarfium Lite's API
(running, its version, its Dwarfs - connected, capturing), and how it
stands against the hub's own installation (the Synchronize tab's startup
check). The same dialog adds an instance and changes one (new address,
new share) and checks it: Dwarfium Lite answers, the share is reachable.

The states are asked again every _REFRESH_S while this tab is shown.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from nicegui import run, ui

from hub import config, instances as I
from hub.help_installations import help_installations
from hub.i18n import t

if TYPE_CHECKING:
    from hub.ui import HubPage

_REFRESH_S = 20
_STATUS_TIMEOUT_S = 10
_SHARE_TIMEOUT_S = 20
HOME = "home"

ui.add_css("""
.inst-band { border-radius: 16px; padding: 14px; }
.inst-band-lan { background: #E3E8EF; }
.inst-band-ts { background: #ECE8F5; }
.inst-card { width: 290px; max-width: 100%; border-radius: 12px; }
.inst-home { border: 2px solid #2B4A9E; }
.inst-ts { border: 1px solid #B9AEDA; }
.inst-add { border: 2px dashed #9C8FC6; background: transparent; box-shadow: none; cursor: pointer;
            min-height: 110px; }
.inst-band-title { font-size: 12px; font-weight: 600; letter-spacing: .08em; color: #5A6578; }
""", shared=True)


class InstallationsView:
    def __init__(self, page: "HubPage"):
        self.page = page
        self.status: dict[str, I.Status] = {}      # instance id (or HOME) -> live state
        self.refreshing = False

    @property
    def lite(self):
        return self.page.card("astro_dwarf_session")

    @property
    def archive(self):
        return self.page.card("scope_archive")

    def _instances(self) -> list[dict]:
        return self.page.cfg.setdefault("instances", [])

    # ── live state ────────────────────────────────────────────────────────
    async def _one(self, key: str, host: str, port: int) -> None:
        try:
            self.status[key] = await asyncio.wait_for(run.io_bound(I.status, host, port), _STATUS_TIMEOUT_S)
        except asyncio.TimeoutError:
            self.status[key] = I.Status(I.UNREACHABLE)

    async def refresh_status(self) -> None:
        if self.refreshing:
            return
        self.refreshing = True
        try:
            jobs = [self._one(i["id"], i.get("host") or "", int(i.get("port") or I.DEFAULT_PORT))
                    for i in self._instances()]
            if self.lite.running:
                jobs.append(self._one(HOME, "127.0.0.1", self.lite.port))
            else:
                self.status.pop(HOME, None)
            await asyncio.gather(*jobs)
        finally:
            self.refreshing = False
        self.render.refresh()

    async def tick(self) -> None:
        if self.page.current_tab == "installations":
            await self.refresh_status()

    # ── a Dwarf connected to two instances ────────────────────────────────
    def _double_connections(self) -> list[tuple[str, list[str]]]:
        names = {HOME: t("in_this_pc")}
        names.update({i["id"]: i.get("name") or i.get("host") or "?" for i in self._instances()})
        seen: dict[str, tuple[str, list[str]]] = {}
        for key, st in self.status.items():
            for d in st.dwarfs:
                if d.connected:
                    uid = I.short_uid(d.uid)
                    seen.setdefault(uid, (d.name, []))[1].append(names.get(key, "?"))
        return [(name, where) for name, where in seen.values() if len(where) > 1]

    # ── display ───────────────────────────────────────────────────────────
    @staticmethod
    def _state_line(st: I.Status | None, port: int) -> None:
        with ui.row().classes("items-center gap-1 no-wrap text-sm"):
            if st is None:
                ui.icon("hourglass_empty", color="grey", size="xs")
                ui.label(t("in_checking")).classes("text-gray-500")
            elif st.state == I.ACTIVE:
                ui.icon("circle", color="positive", size="xs")
                ui.label(f"Dwarfium Lite {st.version}").classes("font-medium")
                ui.label(f":{port}").classes("text-gray-500")
            elif st.state == I.NO_ADDRESS:
                ui.icon("link_off", color="grey", size="xs")
                ui.label(t("in_no_address")).classes("text-gray-500")
            else:
                icon = {I.STOPPED: "radio_button_unchecked", I.OTHER: "help_outline"}.get(st.state, "cloud_off")
                ui.icon(icon, color="grey", size="xs")
                ui.label(t(f"in_state_{st.state}", port=port)).classes("text-gray-600")

    @staticmethod
    def _dwarf_lines(st: I.Status | None) -> None:
        if st is None or st.state != I.ACTIVE:
            return
        if not st.dwarfs:
            ui.label(t("in_no_dwarf")).classes("text-xs text-gray-500")
            return
        ui.label(t("in_dwarfs")).classes("text-xs text-gray-500 mt-1")
        for d in st.dwarfs:
            with ui.row().classes("items-center gap-1 no-wrap text-sm"):
                if d.busy:
                    ui.icon("motion_photos_on", color="orange", size="xs")
                    state = t("in_dw_busy")
                elif d.connected:
                    ui.icon("circle", color="positive", size="xs")
                    state = t("in_dw_connected")
                else:
                    ui.icon("radio_button_unchecked", color="grey", size="xs")
                    state = t("in_dw_known")
                ui.label(d.name).classes("truncate")
                ui.label(I.short_uid(d.uid)).classes("font-mono text-xs text-gray-500")
                ui.label("— " + state).classes("text-gray-600 truncate")
                if d.pending:
                    ui.icon("schedule_send", color="primary", size="xs").tooltip(t("in_dw_pending"))

    def _sync_line(self, share: str) -> None:
        if not share:
            return
        n = self.page.sync.startup.get(share)
        with ui.row().classes("items-center gap-1 no-wrap text-sm"):
            if n is None:
                ui.icon("sync", color="grey", size="xs")
                ui.label(t("in_sync_unknown")).classes("text-gray-500")
            elif n < 0:
                ui.icon("cloud_off", color="grey", size="xs")
                ui.label(t("in_share_unreachable")).classes("text-gray-500")
            elif n == 0:
                ui.icon("check_circle", color="positive", size="xs")
                ui.label(t("in_sync_same"))
            else:
                ui.icon("sync_problem", color="orange", size="xs")
                ui.label(t("in_sync_diff", n=n)).classes("text-orange-800 font-medium")
            ui.button(t("sy_compare"), on_click=lambda: self.compare(share)).props("dense flat no-caps size=sm")

    async def compare(self, share: str) -> None:
        self.page.tabs.set_value("sync")
        await self.page.sync.compare_with(share)

    def _home_card(self) -> None:
        with ui.card().classes("inst-card inst-home p-4 gap-1"):
            with ui.row().classes("items-baseline gap-2"):
                ui.label(t("in_this_pc")).classes("text-lg font-bold")
                ui.label(t("in_hub_badge")).classes("text-xs font-semibold text-primary")
            if not self.lite.installed():
                ui.label(t("in_lite_missing")).classes("text-sm text-gray-600")
                ui.button(t("tab_apps"), icon="apps", on_click=lambda: self.page.tabs.set_value("apps")) \
                    .props("dense flat no-caps")
            elif self.lite.running:
                self._state_line(self.status.get(HOME), self.lite.port)
            else:
                self._state_line(I.Status(I.STOPPED), self.lite.port)
            if self.archive.installed():
                with ui.row().classes("items-center gap-1 no-wrap text-sm"):
                    on = self.archive.running
                    ui.icon("circle" if on else "radio_button_unchecked", color="positive" if on else "grey",
                            size="xs")
                    version = self.archive.installed_version() or ""
                    ui.label(f"Scope Archive {version}").classes("font-medium" if on else "text-gray-600")
                    ui.label(f":{self.archive.port}" if on else t("in_stopped_short")).classes("text-gray-500")
            if self.lite.running:
                self._dwarf_lines(self.status.get(HOME))

    def _instance_card(self, inst: dict) -> None:
        tailscale = inst.get("access") == I.TAILSCALE
        port = int(inst.get("port") or I.DEFAULT_PORT)
        with ui.card().classes("inst-card p-4 gap-1" + (" inst-ts" if tailscale else "")):
            with ui.row().classes("w-full items-start no-wrap gap-1"):
                with ui.column().classes("gap-0 flex-1 min-w-0"):
                    ui.label(inst.get("name") or inst.get("host") or "?").classes("text-lg font-bold truncate")
                    ui.label(t(f"in_kind_{inst.get('kind') or 'other'}")).classes("text-xs text-gray-500")
                ui.button(icon="edit", on_click=lambda i=inst: self.edit(i)).props("flat dense round size=sm") \
                    .tooltip(t("in_edit"))
            address = " · ".join(x for x in (inst.get("host") or "", inst.get("share") or "") if x)
            if address:
                ui.label(address).classes("font-mono text-xs text-gray-600 break-all")
            st = self.status.get(inst["id"])
            self._state_line(st, port)
            self._dwarf_lines(st)
            self._sync_line(inst.get("share") or "")
            if st is not None and st.state == I.ACTIVE:
                ui.link(t("in_open"), f"http://{inst['host']}:{port}", new_tab=True).classes("text-sm")

    def _add_card(self) -> None:
        with ui.card().classes("inst-card inst-add p-4 items-center justify-center text-center") \
                .on("click", lambda: self.edit(None)):
            ui.label("+ " + t("in_add")).classes("font-bold text-[#4B3A84]")
            ui.label(t("in_add_hint")).classes("text-xs text-[#5B4E86]")

    @ui.refreshable
    def render(self) -> None:
        with ui.column().classes("w-full gap-3"):
            with ui.row().classes("w-full items-start gap-2 no-wrap"):
                ui.label(t("in_intro")).classes("text-sm text-gray-600 flex-1")
                ui.button(icon="refresh", on_click=self.refresh_status).props("flat dense round") \
                    .tooltip(t("in_refresh"))
                ui.button(t("sy_help"), icon="help_outline", on_click=self.show_help).props("flat dense no-caps")
            for name, where in self._double_connections():
                with ui.row().classes("w-full items-center gap-2 p-2 rounded bg-red-50 text-red-800 text-sm no-wrap"):
                    ui.icon("warning", color="negative")
                    ui.label(t("in_double", name=name, where=", ".join(where)))
            local = [i for i in self._instances() if i.get("access") != I.TAILSCALE]
            remote = [i for i in self._instances() if i.get("access") == I.TAILSCALE]
            with ui.row().classes("w-full gap-3 items-stretch"):
                with ui.column().classes("inst-band inst-band-lan gap-3 flex-[2] min-w-[300px]"):
                    ui.label(t("in_band_home")).classes("inst-band-title")
                    with ui.row().classes("w-full gap-3"):
                        self._home_card()
                        for inst in local:
                            self._instance_card(inst)
                with ui.column().classes("inst-band inst-band-ts gap-3 flex-1 min-w-[300px]"):
                    ui.label(t("in_band_remote")).classes("inst-band-title text-[#5B4E86]")
                    with ui.row().classes("w-full gap-3"):
                        for inst in remote:
                            self._instance_card(inst)
                        self._add_card()
            ui.label(t("in_rule")).classes("text-xs text-gray-500")

    def show_help(self) -> None:
        ui.add_css(".sync-help h2 { font-size: 1.35rem; line-height: 1.3; margin: 0.4rem 0 0.6rem; }"
                   ".sync-help h3 { font-size: 1.05rem; font-weight: 600; margin: 1rem 0 0.3rem; }")
        with self.page.dialog_host, ui.dialog() as dialog, \
                ui.card().classes("w-full max-w-3xl").style("max-height: 85vh"):
            with ui.scroll_area().classes("w-full").style("height: 70vh"):
                ui.markdown(help_installations()).classes("w-full sync-help")
            with ui.row().classes("w-full justify-end"):
                ui.button(t("close"), on_click=dialog.close).props("flat")
        dialog.open()

    # ── add / change an instance ──────────────────────────────────────────
    def edit(self, inst: dict | None) -> None:
        new = inst is None
        data = dict(inst or {"id": I.new_id(), "name": "", "kind": "laptop", "access": I.LAN,
                             "host": "", "port": I.DEFAULT_PORT, "share": ""})
        with self.page.dialog_host, ui.dialog() as dialog, \
                ui.card().classes("p-5 gap-3").style("width: min(95vw, 640px); max-width: none"):
            ui.label(t("in_add") if new else t("in_edit")).classes("text-lg font-bold")
            ui.input(t("in_name"), value=data["name"], on_change=lambda e: data.update(name=e.value.strip())) \
                .classes("w-full")
            with ui.column().classes("gap-1"):
                ui.label(t("in_kind")).classes("text-xs text-gray-500")
                ui.toggle({k: t(f"in_kind_{k}") for k in I.KINDS}, value=data["kind"],
                          on_change=lambda e: data.update(kind=e.value)).props("no-caps dense")
            with ui.column().classes("gap-1"):
                ui.label(t("in_access")).classes("text-xs text-gray-500")
                ui.toggle({I.LAN: t("in_access_lan"), I.TAILSCALE: "Tailscale"}, value=data["access"],
                          on_change=lambda e: data.update(access=e.value)).props("no-caps dense")
            with ui.row().classes("w-full gap-3 no-wrap"):
                _hint(ui.input(t("in_host"), value=data["host"], on_change=lambda e: data.update(host=e.value.strip()))
                      .classes("flex-1"), t("in_host_hint"))
                ui.number(t("in_port"), value=data["port"], min=1, max=65535, format="%d",
                          on_change=lambda e: data.update(port=int(e.value or I.DEFAULT_PORT))).classes("w-24")
            with ui.row().classes("w-full gap-2 no-wrap items-start"):
                share = _hint(ui.input(t("in_share"), value=data["share"],
                                       on_change=lambda e: data.update(share=e.value.strip())).classes("flex-1"),
                              t("in_share_hint"))

                async def browse():
                    chosen = await self.page.pick_folder(t("sy_add_hint"), data["share"] or None)
                    if chosen:
                        share.set_value(chosen)
                ui.button(icon="folder_open", on_click=browse).props("flat dense round").classes("mt-3")
            checks = ui.column().classes("w-full gap-1 mt-2")

            async def check():
                checks.clear()
                with checks:
                    ui.spinner(size="sm")
                lines = await self._check(data)
                checks.clear()
                with checks:
                    for ok, text in lines:
                        with ui.row().classes("items-center gap-2 no-wrap text-sm"):
                            ui.icon("check_circle" if ok else ("warning" if ok is None else "error"),
                                    color="positive" if ok else ("orange" if ok is None else "negative"), size="xs")
                            ui.label(text).classes("break-all")

            def save():
                if not data["name"]:
                    data["name"] = data["host"] or (data["share"].rstrip("\\/").split("\\")[-1].split("/")[-1])
                if not (data["host"] or data["share"]):
                    ui.notify(t("in_need_address"), type="warning")
                    return
                if data["share"] and any(i.get("share") == data["share"] and i["id"] != data["id"]
                                         for i in self._instances()):
                    ui.notify(t("in_share_taken"), type="warning")
                    return
                if new:
                    self._instances().append(data)
                else:
                    inst.clear()
                    inst.update(data)
                config.save(self.page.cfg)
                dialog.close()
                self.page.sync.render.refresh()
                self.render.refresh()
                asyncio.create_task(self.refresh_status())

            def delete():
                self._instances().remove(inst)
                self.status.pop(inst["id"], None)
                config.save(self.page.cfg)
                dialog.close()
                self.page.sync.render.refresh()
                self.render.refresh()

            with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                if not new:
                    ui.button(t("in_delete"), icon="delete", on_click=delete).props("flat color=negative no-caps")
                ui.space()
                ui.button(t("in_check"), icon="fact_check", on_click=check).props("flat no-caps")
                ui.button(t("cancel"), on_click=dialog.close).props("flat")
                ui.button(t("in_save"), on_click=save).props("no-caps")
        dialog.open()

    async def _check(self, data: dict) -> list[tuple[bool | None, str]]:
        """(ok, text): ok True, False (a problem) or None (nothing to check)."""
        lines: list[tuple[bool | None, str]] = []
        host, port = data["host"], int(data["port"] or I.DEFAULT_PORT)
        if host:
            try:
                st = await asyncio.wait_for(run.io_bound(I.status, host, port), _STATUS_TIMEOUT_S)
            except asyncio.TimeoutError:
                st = I.Status(I.UNREACHABLE)
            if st.state == I.ACTIVE:
                lines.append((True, t("in_chk_lite_ok", addr=f"{host}:{port}", v=st.version)))
                connected = sum(1 for d in st.dwarfs if d.connected)
                lines.append((True, t("in_chk_dwarfs", n=len(st.dwarfs), c=connected)))
            else:
                lines.append((False, t(f"in_chk_{st.state}", addr=f"{host}:{port}")))
        else:
            lines.append((None, t("in_chk_no_host")))
        if data["share"]:
            try:
                ok = await asyncio.wait_for(run.io_bound(I.share_ok, data["share"]), _SHARE_TIMEOUT_S)
            except asyncio.TimeoutError:
                ok = False
            lines.append((ok, t("in_chk_share_ok" if ok else "in_chk_share_bad", path=data["share"])))
        else:
            lines.append((None, t("in_chk_no_share")))
        return lines


def _hint(element, text: str):
    """Set as is: props() would read the backslashes of \\\\host\\share."""
    element._props["hint"] = text
    return element
