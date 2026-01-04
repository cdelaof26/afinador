from nicegui import events, Client, ui
from typing import Optional
from back import fft, wui


_audio_player: Optional[ui.audio] = None
d: Optional[fft.AudioData] = None


async def update():
    time = await ui.run_javascript(f"getHtmlElement({_audio_player.id}).currentTime")
    wui.process_file_at_t(d, time)


async def stalk(_):
    # TODO: Come up with a better name...
    fft.RUNNING = True

    while fft.RUNNING:
        await update()


def stop():
    fft.RUNNING = False


async def handle_file_update(e: events.UploadEventArguments):
    global d  # TODO: Eliminar variable global, para permitir concurrencia con más usuarios

    ui.notify(f"Subido {e.file.name}")
    _audio_player.source = e.file.name

    d = wui.create_audio_data(e.file.name)

    _audio_player.play()

    # Comportamiento anterior
    # threading.Thread(target=wui.play_file_thread, args=(e.file.name,)).start()
    # _audio_player.play()


def create_audio_manager_div():
    global _audio_player

    with ui.element().classes("w-1/3 p-8"):
        c = "flex flex-col justify-between space-y-4 p-4 w-full h-full rounded-xl shadow-lg border border-gray-300"
        with ui.element().classes(c):
            with ui.element().classes("flex flex-row"):
                ui.icon("fiber_manual_record").classes("text-red-400 text-6xl self-center")
                ui.label("Grabar").classes("self-center ps-2 text-4xl font-bold")

            with ui.element().classes("flex flex-col justify-between h-1/2"):
                with ui.element().classes("flex justify-center"):
                    ui.button(icon="mic").classes("rounded-full w-40 h-40 text-6xl")

                with ui.element().classes("space-y-4"):
                    _audio_player = ui.audio("").classes("w-full")
                    ui.button("Descargar grabación", icon="save_alt").classes("w-full")

            with ui.element().classes("flex flex-col justify-between space-y-4"):
                ui.label("Cargar desde archivo...").classes("indent-4 uppercase text-base font-bold")
                ui.upload(on_upload=handle_file_update).props("accept=.mp3,.wav").classes("w-full")

    _audio_player.on("play", stalk)
    _audio_player.on("pause", lambda _: stop())


dark_mode_enabled = False


@ui.page("/")
def main(client: Client):
    client.content.classes("flex flex-row w-full h-dvh", remove="nicegui-content q-pa-md")
    dark = ui.dark_mode()
    ui.colors(primary="#1E1E1E")

    toggle_button = None

    def toggle_mode():
        global dark_mode_enabled
        if dark_mode_enabled:
            toggle_button.icon = "dark_mode"
            dark.disable()
        else:
            toggle_button.icon = "light_mode"
            dark.enable()

        dark_mode_enabled = not dark_mode_enabled

    with client.content:
        create_audio_manager_div()

        with ui.element().classes("w-2/3 p-8"):
            with ui.element().classes("flex justify-between"):
                ui.label("Análisis de muestra en vivo").classes("text-4xl font-bold tracking-tight")
                toggle_button = ui.button(icon="dark_mode", on_click=toggle_mode).classes("rounded-lg")

            wui.label_note = ui.label("--").classes("text-4xl font-bold")
            wui.label_freq = ui.label("0.0 Hz").classes("text-2xl")
            wui.label_status = ui.label("En espera").classes("text-2xl font-bold")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Afinador")
