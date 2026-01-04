# Afinador de Señales de Audio 

Este proyecto es un **afinador de audio** desarrollado en Python que permite analizar señales de sonido y detectar la frecuencia fundamental, mostrando la nota musical correspondiente mediante una interfaz gráfica.

El afinador utiliza la Transformada Rápida de Fourier (FFT) para convertir la señal del dominio del tiempo al dominio de la frecuencia y así identificar la frecuencia dominante.

## Características
- Análisis de audio usando FFT
- Detección de frecuencia fundamental
- Identificación de notas musicales (escala estándar A4 = 440 Hz)
- Interfaz gráfica con NiceGUI
- Soporte para archivos `.wav`
- Procesamiento en tiempo real mediante hilos

## Requisitos

- Python 3.8 o superior
- Librerías:
  - numpy
  - soundfile
  - sounddevice
  - [NiceGUI](https://nicegui.io)

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/tu-usuario/afinador-seniales.git
cd afinador-seniales
```

2. Instala las dependencias:

```bash
pip3 install -r requirements.txt
```

## Ejecución

Ejecuta el programa con:

```bash
python3 main.py
```

## Uso

- Selecciona un archivo de audio .wav 
- El sistema analiza la señal 
- Se muestra la frecuencia detectada y la nota musical correspondiente
