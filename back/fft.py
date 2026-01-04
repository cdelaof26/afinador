from typing import Optional
import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import time

BUFFER_SIZE = 4096
SAMPLE_RATE = 44100
A4_FREQUENCY = 440.0
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

RUNNING = True
audio_queue = queue.Queue()
mode: Optional[str] = None  # 'mic' o 'file'

stream: Optional[sd.InputStream] = None


def hz_to_note(frequency: float) -> tuple:
    """Convierte frecuencia a nota musical"""
    if frequency == 0:
        return None, 0

    midi_number = 69 + 12 * np.log2(frequency / A4_FREQUENCY)
    midi_number_rounded = int(round(midi_number))
    idx = midi_number_rounded % 12
    octave = midi_number_rounded // 12 - 1
    note_name = f"{NOTE_NAMES[idx]}{octave}"
    cents_off = (midi_number - midi_number_rounded) * 100
    return note_name, cents_off


def process_chunk() -> tuple:
    try:
        # data = None
        # Vaciamos la cola para obtener el último fragmento
        # while not audio_queue.empty():
        #     data = audio_queue.get_nowait()
        data = audio_queue.get()

        if data is not None:
            # Ventana Hanning para suavizar
            windowed_data = data * np.hanning(len(data))

            # FFT
            fft_result = np.fft.rfft(windowed_data)
            fft_magnitude = np.abs(fft_result)

            # Limpiar ruido grave
            fft_magnitude[:int(40 * len(data) / SAMPLE_RATE)] = 0

            # Buscar pico
            peak_index = np.argmax(fft_magnitude)
            freq_detected = peak_index * SAMPLE_RATE / len(data)

            # Filtro de silencio
            volumen = np.linalg.norm(data) / 10

            return volumen, freq_detected
    except (IndexError or queue.Empty) as e:
        print(f"Error: {e}")

    return 0, 0


# --- MANEJO DE AUDIO (MICRÓFONO) ---
def audio_callback(indata, _, _1, _2):
    if RUNNING:
        audio_queue.put(indata[:, 0])


def start_mic():
    global stream
    try:
        stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                                blocksize=BUFFER_SIZE, callback=audio_callback)
        stream.start()
    except Exception as e:
        print(e)
        # messagebox.showerror("Error", f"No se pudo abrir el micrófono: {e}")


def process_file(filename: str):
    # TODO: Cambiar la lógica para que procese el archivo conforme a el chunk
    #  que se le indique
    global SAMPLE_RATE

    try:
        # Leer archivo
        data, fs = sf.read(filename)

        # Convertir a mono si es estéreo
        if len(data.shape) > 1:
            data = data.mean(axis=1)

        # Asegurarnos de usar el Sample Rate correcto en la FFT
        SAMPLE_RATE = fs

        cursor = 0
        total_samples = len(data)

        while RUNNING and cursor < total_samples:
            # Tomar un "chunk" (fragmento) de audio
            end = min(cursor + BUFFER_SIZE, total_samples)
            chunk = data[cursor:end]

            # Rellenar con ceros si el último pedazo es pequeño
            if len(chunk) < BUFFER_SIZE:
                chunk = np.pad(chunk, (0, BUFFER_SIZE - len(chunk)))

            # Meter a la cola para análisis
            audio_queue.put(chunk)

            # Esperar el tiempo real que dura ese audio para no ir acelerado
            duration = BUFFER_SIZE / fs
            time.sleep(duration)

            cursor += BUFFER_SIZE

    except Exception as e:
        print(f"Error leyendo archivo: {e}")
