from nicegui import events, Client, ui, app
from typing import Optional, Callable
from fastapi import UploadFile, File
from back import fft, wui
import numpy as np
import threading
import time


_audio_player: Optional[ui.audio] = None
_audio_selector: Optional[ui.switch] = None
_record_indicator: Optional[ui.icon] = None
_record_button: Optional[ui.button] = None
_toggle_button: Optional[ui.button] = None
d: Optional[fft.AudioData] = None
dark_mode_enabled = False
menu_open = True
playing_file = False
recording = False
python_audio = True


async def _update_file_reading():
    t = await ui.run_javascript(f"getHtmlElement({_audio_player.id}).currentTime")
    wui.process_file_at_t(d, t)


async def update_file_reading(_):
    global playing_file
    if playing_file:
        ui.notify("No es posible analizar más de una fuente de audio a la vez")
        return

    if recording:
        _audio_player.pause()
        ui.notify("No puede analizarse un archivo si se esta analizando una grabación")
        return

    playing_file = True

    while playing_file:
        await _update_file_reading()


def stop():
    global playing_file
    playing_file = False


async def handle_file_update(e: events.UploadEventArguments):
    global d  # TODO: Eliminar variable global, para permitir concurrencia con más usuarios

    ui.notify(f"Subido {e.file.name}")
    _audio_player.source = e.file.name

    d = wui.create_audio_data(e.file.name)


@app.post("/blob")
async def receive_blob(file: UploadFile = File(...)):
    content = await file.read()

    len_content = len(content)
    c = content[:len_content - len_content % 16]
    try:
        audio_array = np.frombuffer(c, dtype=np.int16)
    except ValueError as e:
        # Esta excepción sucede cuando el tamaño del blob no es multiplo de 16,
        # por esta razón se trunca
        print(e, len_content, len(c), np.int16)
        return

    fft.audio_queue.put(audio_array, True)
    try:
        volume, freq_detected = fft.process_chunk()
    except ValueError:
        return

    # Sin embargo, no parece funcionar adecuadamente tal como lo hace la implementación
    # desde Python... Podría hostearse en Azure functions, pero el inadecuado procesamiento
    # del audio web limita la posibilidad y, a falta de más tiempo, la solución será poner un
    # switch en la interfaz para cambiar entre audio desde el backend y el frontend.
    wui.update_based_on_chunk_info(volume, freq_detected)


def toggle_audio_source(e: events.ValueChangeEventArguments):
    global python_audio
    if recording:
        _audio_selector.set_value(e.previous_value)
        ui.notify("Acción no realizada")

        return

    python_audio = e.value == 1


async def record_toggle():
    global recording

    if playing_file:
        ui.notify("No puede empezarse una grabación si se esta analizando un archivo")
        return

    if python_audio:
        def update_ui():
            print("thread running")
            while recording:
                volume, freq_detected = fft.process_chunk()
                wui.update_based_on_chunk_info(volume, freq_detected, True)
                time.sleep(0.05)

            print("thread stopped")

        if not recording:
            recording = True
            _record_indicator.classes("animate-pulse")
            fft.start_mic()
            threading.Thread(target=update_ui).start()
            return

        recording = False
        _record_indicator.classes(remove="animate-pulse")
        fft.stop_mic()
        return

    recording = await ui.run_javascript("mediaRecorder !== null")

    if recording:
        _record_indicator.classes(remove="animate-pulse")
        ui.run_javascript("stop_recording()")
        recording = False
        return

    _record_indicator.classes("animate-pulse")
    ui.run_javascript("start_recording()")


def create_audio_manager_div():
    global _audio_player, _audio_selector, _record_indicator, _record_button

    menu = ui.element().classes("w-full h-full absolute lg:static lg:w-96 lg:p-8 transition-[translate] duration-300")
    with menu:
        c = "flex flex-col justify-between space-y-4 p-4 w-full h-full rounded-xl shadow-lg lg:border border-gray-300"
        c += " !bg-white dark:!bg-black"
        with ui.element().classes(c):
            with ui.element().classes("flex flex-row"):
                _record_indicator = ui.icon("fiber_manual_record").classes("text-red-600 text-6xl self-center")
                ui.label("Grabar").classes("self-center ps-2 text-4xl font-bold")

            with ui.element().classes("flex flex-col justify-between h-1/2"):
                with ui.element().classes("flex justify-center"):
                    _record_button = ui.button(
                        icon="mic", on_click=record_toggle
                    ).classes("rounded-full w-40 h-40 text-6xl")

                with ui.element().classes("flex flex-col space-y-4"):
                    _audio_player = ui.audio("").classes("w-full")
                    _audio_selector = ui.switch(
                        "Usar Python Audio", value=True, on_change=toggle_audio_source
                    ).classes("self-center")
                    ui.button("Descargar grabación", icon="save_alt").classes("w-full invisible")

            with ui.element().classes("flex flex-col justify-between space-y-4"):
                ui.label("Cargar desde archivo...").classes("indent-4 uppercase text-base font-bold")
                ui.upload(on_upload=handle_file_update).props("accept=.mp3,.wav").classes("w-full")

    _audio_player.on("play", update_file_reading)
    _audio_player.on("pause", lambda _: stop())
    return menu


def create_visualizer(toggle_mode: Callable):
    global _toggle_button

    with ui.element().classes("flex flex-col flex-grow p-8"):
        with ui.element().classes("flex justify-between"):
            ui.label("Análisis de muestra en vivo").classes("text-4xl font-bold tracking-tight")
            _toggle_button = ui.button(icon="dark_mode", on_click=toggle_mode).classes("rounded-lg invisible")

        with ui.element().classes("flex flex-col justify-center space-y-4 flex-grow"):
            with ui.element().classes("flex flex-col justify-center self-center w-60 h-60 rounded-full border "
                                      "border-gray-300"):
                wui.label_note = ui.label("--").classes("text-center text-8xl font-bold")

            with ui.element().classes("self-center p-4 rounded-lg border border-gray-300"):
                wui.label_freq = ui.label("0.0 Hz").classes("text-center text-lg lg:text-2xl")
                wui.label_status = ui.label("En espera").classes("text-center text-xl lg:text-3xl font-semibold")


@ui.page("/")
def main(client: Client):
    client.content.classes("flex flex-row w-full h-dvh touch-manipulation", remove="nicegui-content q-pa-md")
    dark = ui.dark_mode(None)
    ui.colors(primary="#1E1E1E")

    app.add_static_file(local_file="record.js", url_path="/record.js")
    ui.add_head_html("<script src=\"record.js\"></script>", shared=False)

    def toggle_mode():
        global dark_mode_enabled
        if dark_mode_enabled:
            _toggle_button.icon = "dark_mode"
            dark.disable()
        else:
            _toggle_button.icon = "light_mode"
            dark.enable()

        dark_mode_enabled = not dark_mode_enabled

    def toggle_menu():
        global menu_open
        if menu_open:
            menu.classes("-translate-x-full lg:translate-x-0")
            menu_toggle.classes("rotate-180")
        else:
            menu.classes(remove="-translate-x-full lg:translate-x-0")
            menu_toggle.classes(remove="rotate-180")

        menu_open = not menu_open

    with client.content:
        menu_toggle = ui.button(icon="chevron_left", on_click=toggle_menu).classes(
            "fixed top-4 right-4 text-xl rounded-lg lg:hidden z-50 transition-[transform] duration-300"
        )

        menu = create_audio_manager_div()
        create_visualizer(toggle_mode)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Afinador")
