from typing import Optional
from nicegui.ui import label
from back import fft
import time

label_note: Optional[label] = None
label_freq: Optional[label] = None
label_status: Optional[label] = None


def set_state(text: str, color: str):
    label_status.text = text
    label_status.style["color"] = color


def update_interface(freq: float):
    note, cents = fft.hz_to_note(freq)
    if note:
        if abs(cents) < 15:
            color = "#2ecc71"  # Verde
            status = "¡AFINADO!"
        elif cents > 0:
            color = "#e74c3c"  # Rojo
            status = "Alto (Baja tensión) ▼"
        else:
            color = "#e74c3c"  # Rojo
            status = "Bajo (Sube tensión) ▲"

        label_note.text = note
        label_note.style["color"] = color
        label_freq.text = f"{freq:.1f} Hz"
        label_status.text = f"{status} ({int(cents)} cents)"
        label_status.style["color"] = color


def create_audio_data(filename: str) -> fft.AudioData:
    d = fft.AudioData(filename)
    d.prepare()
    return d


def update_based_on_chunk_info(volume: float, freq_detected: float, do_not_modify_state_if_invalid: bool = False):
    if volume is None:
        if do_not_modify_state_if_invalid:
            return

        set_state("Escuchando...", "gray")
        return

    if volume == -1:
        set_state("Fin del archivo", "yellow")
        return

    if volume > 0.1 and freq_detected > 40:
        update_interface(freq_detected)
    elif not do_not_modify_state_if_invalid:
        set_state("Escuchando...", "gray")


def process_file_at_t(d: fft.AudioData, t: float):
    d.seek(t)
    volume, freq_detected = d.read()
    update_based_on_chunk_info(volume, freq_detected)


def play_file_thread(filename: str):
    """
    Crea un objeto AudioData para leer el archivo y procesarlo de inmediato,
    simula el comportamiento original de leer, procesar y esperar

    Nota: Esta función debe ejecutarse en un hilo
    """
    d = create_audio_data(filename)

    # TODO: Use proper logging
    print(f"{d.filename=}")
    print(f"{d.total_samples=}")
    print(f"{d.sample_rate=}")
    print(f"{d.duration=}")

    volume, freq_detected = d.read()
    if volume is None:
        return

    while volume != -1:
        time.sleep(fft.BUFFER_SIZE / d.sample_rate)
        if volume > 0.1 and freq_detected > 40:
            update_interface(freq_detected)
        else:
            set_state("Escuchando...", "gray")

        volume, freq_detected = d.read()

    set_state("Fin del archivo", "yellow")
