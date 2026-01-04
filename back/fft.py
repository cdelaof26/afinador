from typing import Optional
import sounddevice as sd
import soundfile as sf
import numpy as np
import queue
import math

BUFFER_SIZE = 4096
SAMPLE_RATE = 44100
A4_FREQUENCY = 440.0
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

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


def process_chunk(chunk: Optional[np.array] = None, sr: int = SAMPLE_RATE) -> tuple:
    if chunk is None:  # Solo mic
        if audio_queue.empty():
            return None, None

        chunk = audio_queue.get()

    try:
        # Ventana Hanning para suavizar
        windowed_data = chunk * np.hanning(len(chunk))

        # FFT
        fft_result = np.fft.rfft(windowed_data)
        fft_magnitude = np.abs(fft_result)

        # Limpiar ruido grave
        fft_magnitude[:int(40 * len(chunk) / sr)] = 0

        # Buscar pico
        peak_index = np.argmax(fft_magnitude)
        freq_detected = peak_index * sr / len(chunk)

        # Filtro de silencio
        volume = np.linalg.norm(chunk) / 10

        return volume, freq_detected
    except (IndexError or ValueError) as e:
        print(f"Error: {e}")

    return None, None


def start_mic():
    global stream
    if stream is not None:
        return

    try:
        stream = sd.InputStream(
            channels=1, samplerate=SAMPLE_RATE,
            blocksize=BUFFER_SIZE, callback=lambda indata, _, _1, _2: audio_queue.put(indata[:, 0])
        )
        stream.start()
    except Exception as e:
        print(e)


def stop_mic():
    global stream
    if stream.active:
        stream.stop()
        stream.close()
        stream = None


class AudioData:
    def __init__(self, filename: str):
        self._filename: str = filename
        self._sample_rate: Optional[int] = None
        self._total_samples: Optional[int] = None
        self._data: Optional[list] = None
        self._cursor: int = 0

    @property
    def filename(self):
        return self._filename

    @property
    def sample_rate(self):
        return self._sample_rate

    @property
    def total_samples(self):
        return self._total_samples

    @property
    def duration(self):
        if self._total_samples is None:
            return 0

        return self._total_samples / self._sample_rate

    def prepare(self):
        if self._data is not None:
            raise ValueError("AudioData has already been prepared")

        self._data, self._sample_rate = sf.read(self._filename)

        # Convertir a mono si es estéreo
        if len(self._data.shape) > 1:
            self._data = self._data.mean(axis=1)

        self._total_samples = len(self._data)

    def read(self) -> tuple:
        if self._total_samples is None:
            raise ValueError("AudioData hasn't been prepared yet")

        if self._cursor >= self._total_samples:
            return -1, -1

        # Tomar un "chunk" (fragmento) de audio
        end = min(self._cursor + BUFFER_SIZE, self._total_samples)
        chunk = self._data[self._cursor:end]

        # Rellenar con ceros si el último pedazo es pequeño
        if len(chunk) < BUFFER_SIZE:
            chunk = np.pad(chunk, (0, BUFFER_SIZE - len(chunk)))

        self._cursor += BUFFER_SIZE
        return process_chunk(chunk, self._sample_rate)

    def tell(self) -> float:
        return self._cursor / self._sample_rate

    def seek(self, t: float):
        position = math.ceil(t * self._sample_rate)
        if position >= self._total_samples:
            self._cursor = self._total_samples
            return

        cursor = 0
        while cursor < position:
            cursor += BUFFER_SIZE

        self._cursor = cursor
