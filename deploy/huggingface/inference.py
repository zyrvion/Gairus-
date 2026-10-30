"""Free ZeroGPU inference. No paid endpoint or arbitrary tool execution."""

import os
import threading

MODEL_ID = "Qwen/Qwen3-4B-Instruct-2507"
MODEL_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
MAX_INPUT_TOKENS = 6144
MAX_NEW_TOKENS = 512
_model = None
_tokenizer = None
_lock = threading.Lock()

if os.getenv("SPACE_ID"):
    # Import Spaces before Torch so ZeroGPU can install CUDA emulation.
    from spaces import GPU
else:
    def GPU(**kwargs):
        return lambda function: function


def initialize():
    global _model, _tokenizer
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID, revision=MODEL_REVISION, trust_remote_code=False
    )
    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        dtype=torch.bfloat16,
        trust_remote_code=False,
        use_safetensors=True,
        low_cpu_mem_usage=True,
        attn_implementation="sdpa",
    ).to("cuda")
    _model.eval()


@GPU(duration=45)
def generate(messages):
    if _model is None or _tokenizer is None:
        raise RuntimeError("Le moteur IA n'est pas initialisé.")
    import torch

    with _lock, torch.inference_mode():
        messages = list(messages)
        while True:
            prompt = _tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = _tokenizer(prompt, return_tensors="pt")
            if inputs.input_ids.shape[1] <= MAX_INPUT_TOKENS:
                break
            if len(messages) <= 2:
                raise ValueError("La demande est trop longue. Réduis sa taille.")
            # Keep the system instructions and latest user message intact.
            del messages[1:3]
        inputs = inputs.to("cuda")
        output = _model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.6,
            top_p=0.9,
            pad_token_id=_tokenizer.eos_token_id,
        )
        result = _tokenizer.decode(
            output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True
        ).strip()
        if not result:
            raise RuntimeError("Le moteur n'a pas produit de réponse.")
        return result
