import numpy as np
import sounddevice as sd
import soundfile as sf  # <--- Necesario para leer .wav
import tkinter as tk
from tkinter import Label, Button, filedialog, messagebox
import queue
import sys
import threading
import time

# --- CONFIGURACIÓN ---
BUFFER_SIZE = 4096 
SAMPLE_RATE = 44100
A4_FREQUENCY = 440.0
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Variables globales
RUNNING = True
audio_queue = queue.Queue()
mode = None # 'mic' o 'file'

# --- LÓGICA MATEMÁTICA (FFT) ---
def hz_to_note(frequency):
    """Convierte Frecuencia a Nota Musical"""
    if frequency == 0: return None, 0
    midi_number = 69 + 12 * np.log2(frequency / A4_FREQUENCY)
    midi_number_rounded = int(round(midi_number))
    idx = midi_number_rounded % 12
    octave = (midi_number_rounded // 12) - 1
    note_name = f"{NOTE_NAMES[idx]}{octave}"
    cents_off = (midi_number - midi_number_rounded) * 100
    return note_name, cents_off

def process_audio_fft():
    """Procesa los datos que llegan a la cola (ya sea del mic o del archivo)"""
    try:
        data = None
        # Vaciamos la cola para obtener el último fragmento
        while not audio_queue.empty():
            data = audio_queue.get_nowait()
            
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
            
            if volumen > 0.1 and freq_detected > 40:
                update_interface(freq_detected)
            else:
                label_status.config(text="Escuchando...", fg="gray")
                
    except Exception as e:
        print(f"Error: {e}")

    if RUNNING:
        root.after(50, process_audio_fft)

# --- MANEJO DE AUDIO (MICRÓFONO) ---
def audio_callback(indata, frames, time, status):
    if RUNNING:
        audio_queue.put(indata[:, 0].copy())

def start_mic():
    global stream
    try:
        stream = sd.InputStream(channels=1, samplerate=SAMPLE_RATE, 
                                blocksize=BUFFER_SIZE, callback=audio_callback)
        stream.start()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo abrir el micrófono: {e}")

# --- MANEJO DE AUDIO (ARCHIVO .WAV) ---
def play_file_thread(filename):
    """Lee el archivo y lo mete en la cola poco a poco para simular tiempo real"""
    global RUNNING
    try:
        # Leer archivo
        data, fs = sf.read(filename)
        
        # Convertir a mono si es estéreo
        if len(data.shape) > 1:
            data = data.mean(axis=1)
            
        # Asegurarnos de usar el Sample Rate correcto en la FFT
        global SAMPLE_RATE
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
            
        label_status.config(text="Fin del archivo", fg="yellow")
        
    except Exception as e:
        print(f"Error leyendo archivo: {e}")

def start_file_mode():
    filename = filedialog.askopenfilename(filetypes=[("Archivos de audio", "*.wav *.mp3")])
    if filename:
        # Iniciar hilo que lee el archivo
        t = threading.Thread(target=play_file_thread, args=(filename,), daemon=True)
        t.start()
    else:
        sys.exit() # Si cancela, salir

# --- INTERFAZ GRÁFICA ---
def update_interface(freq):
    note, cents = hz_to_note(freq)
    if note:
        if abs(cents) < 15:
            color = "#2ecc71" # Verde
            status = "¡AFINADO!"
        elif cents > 0:
            color = "#e74c3c" # Rojo
            status = "Alto (Baja tensión) ▼"
        else:
            color = "#e74c3c" # Rojo
            status = "Bajo (Sube tensión) ▲"
            
        label_note.config(text=note, fg=color)
        label_freq.config(text=f"{freq:.1f} Hz")
        label_status.config(text=f"{status} ({int(cents)} cents)", fg=color)

def on_closing():
    global RUNNING
    RUNNING = False
    try:
        if 'stream' in globals() and stream.active:
            stream.stop()
            stream.close()
    except: pass
    root.destroy()
    sys.exit()

def select_mode(selection):
    global mode
    mode = selection
    menu_window.destroy() # Cierra el menú
    
    # Inicia la ventana principal
    create_main_window()
    
    if mode == 'mic':
        start_mic()
    elif mode == 'file':
        start_file_mode()
        
    # Iniciar el ciclo de análisis FFT
    root.after(100, process_audio_fft)

# --- VENTANAS ---
def create_menu():
    global menu_window
    menu_window = tk.Tk()
    menu_window.title("Selección")
    menu_window.geometry("300x150")
    menu_window.config(bg="#2c3e50")
    
    Label(menu_window, text="¿Qué deseas analizar?", font=("Arial", 12), bg="#2c3e50", fg="white").pack(pady=20)
    
    frame = tk.Frame(menu_window, bg="#2c3e50")
    frame.pack()
    
    btn_mic = Button(frame, text="🎤 Micrófono", font=("Arial", 10), command=lambda: select_mode('mic'))
    btn_mic.pack(side="left", padx=10)
    
    btn_file = Button(frame, text="📂 Archivo .WAV", font=("Arial", 10), command=lambda: select_mode('file'))
    btn_file.pack(side="right", padx=10)
    
    menu_window.mainloop()

def create_main_window():
    global root, label_note, label_freq, label_status
    root = tk.Tk()
    root.title(f"Afinador ESCOM - Modo {mode.upper()}")
    root.geometry("400x350")
    root.config(bg="#222")

    Label(root, text=f"Modo: {mode.upper()}", font=("Arial", 10), bg="#222", fg="#777").pack(pady=5)
    
    label_note = Label(root, text="--", font=("Arial", 80, "bold"), bg="#222", fg="#555")
    label_note.pack()
    
    label_freq = Label(root, text="0.0 Hz", font=("Arial", 14), bg="#222", fg="#aaa")
    label_freq.pack()
    
    label_status = Label(root, text="Esperando...", font=("Arial", 12, "bold"), bg="#222", fg="#555")
    label_status.pack(pady=20)

    root.protocol("WM_DELETE_WINDOW", on_closing)

# --- EJECUCIÓN ---
if __name__ == "__main__":
    create_menu()
    if 'root' in globals():
        root.mainloop()