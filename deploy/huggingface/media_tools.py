"""Real CPU media tools. No commercial API, arbitrary command, or voice clone."""

import base64
import hashlib
import html
import io
from pathlib import Path
import subprocess
import tempfile
import textwrap
import threading

VOICE_REPO = "onnx-community/Kokoro-82M-v1.0-ONNX"
VOICE_REVISION = "1939ad2a8e416c0acfeecc08a694d14ef25f2231"
MAX_FILE_BYTES = 6_000_000
MIMES = {
    "document.md": "text/markdown",
    "narration.wav": "audio/wav",
    "presentation.mp4": "video/mp4",
}
_engine = None
_voice_lock = threading.RLock()


class _TypedSession:
    """Match the exported graph's scalar types, not the wrapper's assumptions."""

    def __init__(self, session):
        self.session = session
        self._model_path = session._model_path

    def get_inputs(self):
        return self.session.get_inputs()

    def run(self, outputs, inputs):
        import numpy as np

        inputs = dict(inputs)
        types = {item.name: item.type for item in self.get_inputs()}
        if "speed" in inputs:
            dtype = np.float32 if types.get("speed") == "tensor(float)" else np.int32
            inputs["speed"] = np.asarray(inputs["speed"], dtype=dtype)
        result = self.session.run(outputs, inputs)
        # Community ONNX export has shape [1, samples]; the wrapper needs mono
        # [samples] before its silence trimming and chunk concatenation.
        return [np.asarray(result[0]).reshape(-1), *result[1:]]


def voice_engine():
    global _engine
    with _voice_lock:
        if _engine is not None:
            return _engine
        import numpy as np
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from kokoro_onnx import Kokoro

        model = hf_hub_download(
            VOICE_REPO, "onnx/model_quantized.onnx", revision=VOICE_REVISION
        )
        voice = hf_hub_download(
            VOICE_REPO, "voices/ff_siwis.bin", revision=VOICE_REVISION
        )
        # Package the publisher's voice tensor without executing pickle.
        voices = Path(tempfile.gettempdir()) / "gairus-kokoro-french-v1.npz"
        np.savez(voices, ff_siwis=np.fromfile(voice, dtype=np.float32).reshape(-1, 1, 256))
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(
            model, sess_options=options, providers=["CPUExecutionProvider"]
        )
        _engine = Kokoro.from_session(_TypedSession(session), str(voices))
        return _engine


def speech(content):
    if not isinstance(content, str) or not 1 <= len(content.strip()) <= 1200:
        raise ValueError("La narration doit contenir entre 1 et 1200 caractères.")
    import numpy as np
    import soundfile as sf

    with _voice_lock:
        samples, rate = voice_engine().create(
            content.strip(), voice="ff_siwis", lang="fr-fr", speed=1.0
        )
    if rate != 24000 or len(samples) < rate // 4 or not np.isfinite(samples).all():
        raise RuntimeError("Le moteur vocal n'a pas produit un audio valide.")
    if float(np.max(np.abs(samples))) < 0.0001:
        raise RuntimeError("Le moteur vocal a produit du silence.")
    output = io.BytesIO()
    sf.write(output, samples, rate, format="WAV", subtype="PCM_16")
    return checked_file("narration.wav", output.getvalue())


def checked_file(name, payload):
    if name not in MIMES or not isinstance(payload, bytes):
        raise ValueError("Type de fichier non autorisé.")
    if not 1 <= len(payload) <= MAX_FILE_BYTES:
        raise ValueError("Le fichier est vide ou dépasse la limite de 6 Mo.")
    if name.endswith(".wav") and not (payload[:4] == b"RIFF" and payload[8:12] == b"WAVE"):
        raise ValueError("Le fichier audio n'est pas un WAV.")
    if name.endswith(".mp4") and payload[4:8] != b"ftyp":
        raise ValueError("Le fichier vidéo n'est pas un MP4.")
    if name.endswith(".md"):
        payload.decode("utf-8")
    return {"name": name, "mime": MIMES[name], "bytes": payload,
            "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}


def presentation(title, slides, wav):
    """A clearly labelled narrated slide video, NOT neural text-to-video."""
    checked_file("narration.wav", wav)
    if not 1 <= len(slides) <= 3 or not all(isinstance(s, str) and len(s) <= 240 for s in slides):
        raise ValueError("La vidéo accepte de une à trois diapositives courtes.")
    from PIL import Image, ImageDraw, ImageFont
    import soundfile as sf

    samples, rate = sf.read(io.BytesIO(wav))
    duration = len(samples) / rate
    if duration > 100:
        raise ValueError("La narration vidéo dépasse 100 secondes.")
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    title_font = ImageFont.truetype(font_path, 32)
    body_font = ImageFont.truetype(font_path, 28)
    small_font = ImageFont.truetype(font_path, 17)
    with tempfile.TemporaryDirectory(prefix="gairus-video-") as directory:
        folder = Path(directory)
        segments = []
        for index, slide in enumerate(slides):
            image = Image.new("RGB", (960, 540), "#f4f6f9")
            draw = ImageDraw.Draw(image)
            draw.text((56, 42), "GAÏRUS / VIDÉO DE PRÉSENTATION", font=small_font, fill="#455467")
            draw.rectangle((56, 94, 904, 98), fill="#215bac")
            draw.text((56, 124), textwrap.shorten(title, width=43), font=title_font, fill="#17212e")
            for line_number, line in enumerate(textwrap.wrap(slide, width=48)[:6]):
                draw.text((56, 206 + 40 * line_number), line, font=body_font, fill="#17212e")
            draw.text((56, 492), f"Voix de synthèse • {index + 1}/{len(slides)}", font=small_font, fill="#455467")
            image.save(folder / f"slide-{index}.png")
            segments.extend([
                f"file 'slide-{index}.png'",
                f"duration {max(duration / len(slides), 0.5):.4f}",
            ])
        segments.append(f"file 'slide-{len(slides)-1}.png'")
        (folder / "slides.txt").write_text("\n".join(segments), encoding="utf-8")
        (folder / "narration.wav").write_bytes(wav)
        # Only fixed arguments and our own generated files; no shell or user path.
        subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "concat", "-safe", "1", "-i", "slides.txt", "-i", "narration.wav",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-threads", "2",
             "-vf", "fps=12,format=yuv420p", "-c:a", "aac", "-b:a", "96k",
             "-shortest", "-movflags", "+faststart", "presentation.mp4"],
            cwd=folder, timeout=150, check=True, capture_output=True,
        )
        return checked_file("presentation.mp4", (folder / "presentation.mp4").read_bytes())


def private_preview(files):
    """Only inline owner-authenticated data. Nothing goes to public file cache."""
    parts = []
    for artifact in files:
        artifact = checked_file(artifact["name"], artifact["bytes"])
        name = html.escape(artifact["name"], quote=True)
        uri = f'data:{artifact["mime"]};base64,' + base64.b64encode(artifact["bytes"]).decode("ascii")
        if artifact["mime"] == "audio/wav":
            parts.append(f'<audio controls preload="metadata" src="{uri}" style="width:100%"></audio>')
        elif artifact["mime"] == "video/mp4":
            parts.append(f'<video controls preload="metadata" src="{uri}" style="width:100%;max-height:540px"></video>')
        parts.append(f'<p><a href="{uri}" download="{name}">Télécharger {name}</a></p>')
    return "\n".join(parts)
