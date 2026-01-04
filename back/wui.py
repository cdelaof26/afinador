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


def process_audio_fft():
    """
    Procesa los datos que llegan a la cola (ya sea del mic o del archivo)
    Nota: Esta función debe ejecutarse en un hilo
    """
    while fft.RUNNING:
        volume, freq_detected = fft.process_chunk()
        if volume > 0.1 and freq_detected > 40:
            update_interface(freq_detected)
        else:
            set_state("Escuchando...", "gray")

        time.sleep(0.05)


# --- MANEJO DE AUDIO (ARCHIVO .WAV) ---
def play_file_thread(filename: str):
    """
    Lee el archivo y lo mete en la cola poco a poco para simular tiempo real
    Nota: Esta función debe ejecutarse en un hilo
    """
    fft.process_file(filename)
    set_state("Fin del archivo", "yellow")
