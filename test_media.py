"""
Скрипт для тестирования классов и проверки выброса исключений.
"""

import os
import wave
import numpy as np
import cv2

from media_processor import MixedMediaProcessor
from media_exceptions import (
    MediaError,
    FileLoadError,
    FormatMismatchError,
    InvalidDataError,
    MediaSyncError,
)


def create_dummy_video(filename: str, duration_sec: float = 2.0, fps: int = 24):
    """Создает тестовый видеофайл с черными кадрами."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (320, 240))
    total_frames = int(duration_sec * fps)
    for _ in range(total_frames):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        out.write(frame)
    out.release()


def create_dummy_audio(filename: str, duration_sec: float = 2.0, sample_rate: int = 44100):
    """Создает тестовый WAV-файл с тишиной."""
    num_samples = int(duration_sec * sample_rate)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b'\x00' * (num_samples * 2))


def run_tests():
    processor = MixedMediaProcessor(sync_tolerance=0.3)

    # Подготовка файлов
    video_good = "temp_good_video.mp4"
    audio_good = "temp_good_audio.wav"
    audio_desync = "temp_desync_audio.wav"
    invalid_format_file = "temp_file.txt"

    create_dummy_video(video_good, duration_sec=2.0)
    create_dummy_audio(audio_good, duration_sec=2.0)
    create_dummy_audio(audio_desync, duration_sec=5.0)

    with open(invalid_format_file, "w") as f:
        f.write("test content")

    print("=== ТЕСТ 1: Успешная синхронизация потоков ===")
    try:
        res = processor.process((video_good, audio_good))
        print(f"[OK] Успех: {res}\n")
    except MediaError as e:
        print(f"[FAIL] Неожиданное исключение: {e}\n")

    print("=== ТЕСТ 2: Ошибка загрузки (FileLoadError) ===")
    try:
        processor.process(("non_existent_video.mp4", audio_good))
    except FileLoadError as e:
        print(f"[OK] Перехвачен FileLoadError: {e}\n")
    except Exception as e:
        print(f"[FAIL] Неверный тип ошибки: {type(e).__name__}\n")

    print("=== ТЕСТ 3: Ошибка формата (FormatMismatchError) ===")
    try:
        processor.process((video_good, invalid_format_file))
    except (FormatMismatchError, InvalidDataError) as e:
        print(f"[OK] Перехвачено исключение формата/данных: {e}\n")
    except Exception as e:
        print(f"[FAIL] Неверный тип ошибки: {type(e).__name__}\n")

    print("=== ТЕСТ 4: Ошибка рассинхронизации (MediaSyncError) ===")
    try:
        processor.process((video_good, audio_desync))
    except MediaSyncError as e:
        print(f"[OK] Перехвачен MediaSyncError: {e}\n")
    except Exception as e:
        print(f"[FAIL] Неверный тип ошибки: {type(e).__name__}\n")

    # Удаление временных файлов
    for path in (video_good, audio_good, audio_desync, invalid_format_file):
        if os.path.exists(path):
            os.remove(path)


if __name__ == '__main__':
    run_tests()