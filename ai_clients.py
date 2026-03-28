import json
from urllib import error, request


def provider_runtime_note(provider: str) -> str:
    notes = {
        "none": "AI disabled.",
        "ollama": "Local runtime. Usually not available on Streamlit Cloud unless you host Ollama yourself.",
        "openai": "Cloud/API-key runtime. Works on Streamlit Cloud with a valid API key.",
        "anthropic": "Cloud/API-key runtime. Works on Streamlit Cloud with a valid API key.",
        "gemini": "Cloud/API-key runtime. Works on Streamlit Cloud with a valid API key.",
    }
    return notes.get(provider, "Unknown provider.")


def _post_json(url: str, headers: dict[str, str], payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def run_ai_analysis(
    provider: str,
    model: str,
    prompt: str,
    api_key: str = "",
) -> str:
    provider = (provider or "none").strip().lower()
    if provider == "none":
        return "AI analysis is disabled."

    if provider == "ollama":
        try:
            import ollama  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "Ollama package not installed. Install with `pip install ollama` for local AI."
            ) from exc

        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert SEO analyst."},
                {"role": "user", "content": prompt},
            ],
        )
        return response["message"]["content"]

    if not api_key.strip():
        raise RuntimeError(f"{provider} API key is required.")

    if provider == "openai":
        data = _post_json(
            url="https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are an expert SEO analyst."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
            },
        )
        return data["choices"][0]["message"]["content"]

    if provider == "anthropic":
        data = _post_json(
            url="https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload={
                "model": model,
                "max_tokens": 1200,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        content = data.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text", "")
        return str(data)

    if provider == "gemini":
        safe_model = model or "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{safe_model}:generateContent?key={api_key}"
        data = _post_json(
            url=url,
            headers={"Content-Type": "application/json"},
            payload={"contents": [{"parts": [{"text": prompt}]}]},
        )
        return data["candidates"][0]["content"]["parts"][0]["text"]

    raise RuntimeError(f"Unsupported provider: {provider}")
