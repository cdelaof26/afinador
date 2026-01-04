from nicegui import events, Client, ui
from typing import Optional
import sounddevice as sd
from back import fft, wui
import threading
import sys


_audio_player: Optional[ui.audio] = None


def on_closing():
    fft.RUNNING = False

    try:
        if fft.stream.active:
            fft.stream.stop()
            fft.stream.close()
    except sd.PortAudioError:
        pass

    sys.exit()


def select_mode():
    mode = "file"

    if mode == "mic":
        # start_mic()
        pass
    elif mode == "file":
        t = threading.Thread(target=fft.play_file_thread, args=(filename,), daemon=True)
        t.start()

    # Iniciar el ciclo de análisis FFT
    # root.after(100, fft.process_audio_fft)


async def handle_file_update(e: events.UploadEventArguments):
    ui.notify(f"Subido {e.file.name}")
    _audio_player.source = e.file.name
    # TODO: Agregar un listener a _audio_player para sincronizar el procesamiento
    _audio_player.play()
    threading.Thread(target=wui.process_audio_fft).start()
    threading.Thread(target=wui.play_file_thread, args=(e.file.name,)).start()


def create_audio_manager_div():
    global _audio_player

    with ui.element().classes("w-1/3 p-8"):
        c = "flex flex-col justify-between space-y-4 p-4 w-full h-full rounded-xl bg-white dark:bg-[#1E1E1E] shadow-lg"
        with ui.element().classes(c):
            with ui.element().classes("flex flex-row"):
                ui.icon("fiber_manual_record").classes("text-6xl self-center")
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


enabled = False


@ui.page("/")
def main(client: Client):
    c = "flex flex-row w-full h-dvh bg-[#F9F9F9] dark:bg-[#000]"
    client.content.classes(c, remove="nicegui-content q-pa-md")
    dark = ui.dark_mode()
    ui.colors(primary="#1E1E1E", dark="#F9F9F9")

    toggle_button = None

    def toggle_mode():
        global enabled
        if enabled:
            toggle_button.icon = "dark_mode"
            dark.disable()
        else:
            toggle_button.icon = "light_mode"
            dark.enable()

        enabled = not enabled

    with client.content:
        create_audio_manager_div()

        with ui.element().classes("w-2/3 p-8"):
            with ui.element().classes("flex justify-between"):
                ui.label("Análisis de muestra en vivo").classes("text-4xl font-bold tracking-tight")
                toggle_button = ui.button(icon="dark_mode", on_click=toggle_mode).classes("rounded-lg")

            wui.label_note = ui.label("--").classes("text-4xl font-bold")
            wui.label_freq = ui.label("0.0 Hz").classes("text-2xl")
            wui.label_status = ui.label("En espera").classes("text-2xl font-bold")


# --- EJECUCIÓN ---
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Afinador")
