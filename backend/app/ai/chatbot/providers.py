from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings

EMBEDDING_DIM = 768


class ProviderConfigError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    async def embed(self, text: str, task_type: str = "retrieval_query") -> list[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    name = "hash"

    async def embed(self, text: str, task_type: str = "retrieval_query") -> list[float]:
        vector = [0.0] * EMBEDDING_DIM
        tokens = re.findall(r"[\wÀ-ỹ]+", text.lower())
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    async def embed(self, text: str, task_type: str = "retrieval_query") -> list[float]:
        if not settings.GEMINI_API_KEY:
            raise ProviderConfigError("Thiếu GEMINI_API_KEY")

        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=settings.GEMINI_API_KEY)
        response = genai.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type=task_type,
        )
        embedding = response.get("embedding")
        if not embedding:
            raise ProviderConfigError("Gemini không trả về embedding")
        return list(embedding)


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    name = "huggingface"

    async def embed(self, text: str, task_type: str = "retrieval_query") -> list[float]:
        if not settings.HUGGINGFACE_API_TOKEN:
            raise ProviderConfigError("Thiếu HUGGINGFACE_API_TOKEN")

        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{settings.HF_EMBEDDING_MODEL}"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers=headers, json={"inputs": text})
            response.raise_for_status()
            payload = response.json()

        if payload and isinstance(payload[0], list) and payload[0] and isinstance(payload[0][0], list):
            values = [sum(column) / len(column) for column in zip(*payload[0])]
        elif payload and isinstance(payload[0], list):
            values = payload[0]
        else:
            raise ProviderConfigError("Hugging Face không trả về embedding hợp lệ")

        return _fit_embedding(values)


class ChatProvider(ABC):
    name: str

    @abstractmethod
    async def answer(
        self,
        question: str,
        retrieved_context: str,
        student_context: str,
        history: list[dict[str, str]],
    ) -> str:
        raise NotImplementedError


class ExtractiveChatProvider(ChatProvider):
    name = "extractive"

    async def answer(
        self,
        question: str,
        retrieved_context: str,
        student_context: str,
        history: list[dict[str, str]],
    ) -> str:
        if student_context and not retrieved_context:
            return _answer_from_student_context(question, student_context)

        if retrieved_context:
            return _answer_with_retrieved_context(question, retrieved_context, student_context)

        return (
            "Mình chưa có đủ dữ liệu để trả lời chắc chắn câu này. "
            "Nếu bạn hỏi về quy chế, admin cần nạp tài liệu liên quan trước để mình trích dẫn đúng nguồn."
        )


class GeminiChatProvider(ChatProvider):
    name = "gemini"
    fallback_models = (
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-flash-latest",
    )

    async def answer(
        self,
        question: str,
        retrieved_context: str,
        student_context: str,
        history: list[dict[str, str]],
    ) -> str:
        if not settings.GEMINI_API_KEY:
            raise ProviderConfigError("Thiếu GEMINI_API_KEY")

        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=settings.GEMINI_API_KEY)
        prompt = _build_prompt(question, retrieved_context, student_context, history)
        last_error: Exception | None = None
        for model_name in _candidate_gemini_models(settings.GEMINI_CHAT_MODEL, self.fallback_models):
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.35},
                )
                return getattr(response, "text", "") or "Mình chưa tạo được câu trả lời."
            except Exception as exc:  # pragma: no cover - depends on upstream API availability.
                last_error = exc

        detail = _compact_provider_error(last_error)
        raise ProviderConfigError(f"Gemini chưa gọi được model chat ({detail})")


class HuggingFaceChatProvider(ChatProvider):
    name = "huggingface"

    async def answer(
        self,
        question: str,
        retrieved_context: str,
        student_context: str,
        history: list[dict[str, str]],
    ) -> str:
        if not settings.HUGGINGFACE_API_TOKEN:
            raise ProviderConfigError("Thiếu HUGGINGFACE_API_TOKEN")

        url = f"https://api-inference.huggingface.co/models/{settings.HF_CHAT_MODEL}"
        headers = {"Authorization": f"Bearer {settings.HUGGINGFACE_API_TOKEN}"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                url,
                headers=headers,
                json={"inputs": _build_prompt(question, retrieved_context, student_context, history)},
            )
            response.raise_for_status()
            payload = response.json()

        if isinstance(payload, list) and payload:
            return payload[0].get("generated_text", "").strip() or "Mình chưa tạo được câu trả lời."
        if isinstance(payload, dict):
            return payload.get("generated_text", "").strip() or str(payload)
        return "Mình chưa tạo được câu trả lời."


class LocalChatProvider(ChatProvider):
    name = "local"

    async def answer(
        self,
        question: str,
        retrieved_context: str,
        student_context: str,
        history: list[dict[str, str]],
    ) -> str:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _system_prompt()},
            *history[-8:],
            {
                "role": "user",
                "content": _build_user_prompt(question, retrieved_context, student_context),
            },
        ]
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.LOCAL_LLM_BASE_URL.rstrip('/')}/chat/completions",
                json={"model": settings.LOCAL_LLM_MODEL, "messages": messages, "temperature": 0.2},
            )
            response.raise_for_status()
            payload = response.json()
        return payload["choices"][0]["message"]["content"]


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.EMBEDDING_PROVIDER.lower()
    if provider == "gemini":
        return GeminiEmbeddingProvider()
    if provider in {"huggingface", "hf"}:
        return HuggingFaceEmbeddingProvider()
    return HashEmbeddingProvider()


def get_chat_provider() -> ChatProvider:
    provider = settings.CHAT_PROVIDER.lower()
    if provider == "gemini":
        return GeminiChatProvider()
    if provider in {"huggingface", "hf"}:
        return HuggingFaceChatProvider()
    if provider == "local":
        return LocalChatProvider()
    return ExtractiveChatProvider()


def _fit_embedding(values: list[float]) -> list[float]:
    fitted = [float(value) for value in values[:EMBEDDING_DIM]]
    if len(fitted) < EMBEDDING_DIM:
        fitted.extend([0.0] * (EMBEDDING_DIM - len(fitted)))
    norm = math.sqrt(sum(value * value for value in fitted))
    if norm:
        fitted = [value / norm for value in fitted]
    return fitted


def _candidate_gemini_models(configured_model: str, fallback_models: tuple[str, ...]) -> list[str]:
    models: list[str] = []
    for model in (configured_model, *fallback_models):
        normalized = model.strip()
        if normalized and normalized not in models:
            models.append(normalized)
    return models


def _compact_provider_error(error: Exception | None) -> str:
    if error is None:
        return "không rõ lỗi"
    message = str(error).strip().splitlines()[0]
    if not message:
        return error.__class__.__name__
    return message[:180]


def _system_prompt() -> str:
    return (
        "Bạn là trợ lý tư vấn học vụ cho sinh viên HCMUT. "
        "Trả lời như một cố vấn học tập thân thiện, tự nhiên, đi thẳng vào câu hỏi của sinh viên. "
        "Câu hỏi hiện tại là nhiệm vụ chính; lịch sử chỉ là bối cảnh phụ để hiểu các tham chiếu như 'môn đó'. "
        "Không trả lời theo ý của câu hỏi cũ nếu câu hỏi hiện tại đang hỏi chuyện khác. "
        "Không chép lại toàn bộ dữ liệu đầu vào, không liệt kê context thô nếu người dùng không hỏi. "
        "Dựa trên dữ liệu sinh viên và tài liệu quy chế được cung cấp; nếu thiếu nguồn thì nói rõ là chưa đủ nguồn, không bịa quy chế. "
        "Dữ liệu sinh viên có thể bao gồm bảng điểm đã parse từ page Điểm số; khi có dữ liệu này, hãy dùng nó để tư vấn và đừng nói rằng bạn không xem được bảng điểm đã upload. "
        "Không khẳng định cách trường thay thế điểm, xóa điểm F, điều kiện cảnh báo hay tốt nghiệp nếu không có đoạn quy chế liên quan trong tài liệu truy xuất. "
        "Với câu hỏi follow-up, hãy dùng lịch sử hội thoại để hiểu 'môn đó', 'cái này', 'vậy thì' đang nhắc tới gì. "
        "Nếu người dùng sửa hoặc phản biện, hãy công nhận phần đúng và điều chỉnh câu trả lời."
    )


def _build_user_prompt(question: str, retrieved_context: str, student_context: str) -> str:
    return (
        f"Dữ liệu sinh viên:\n{student_context or 'Không có dữ liệu cá nhân.'}\n\n"
        f"Tài liệu quy chế truy xuất được:\n{retrieved_context or 'Không có tài liệu liên quan.'}\n\n"
        f"CÂU HỎI HIỆN TẠI CẦN TRẢ LỜI: {question}\n\n"
        "Hãy trả lời bằng tiếng Việt tự nhiên, ngắn gọn nhưng đủ ý. "
        "Mở đầu bằng câu trả lời trực tiếp cho câu hỏi hiện tại, rồi mới bổ sung lời khuyên nếu thật sự hữu ích. "
        "Nếu câu hỏi hỏi về một môn học, hãy nêu mã môn, tên môn, số tín chỉ, trạng thái/điểm nếu có trong dữ liệu. "
        "Nếu câu hỏi xin kế hoạch cải thiện, hãy ưu tiên môn F còn hiệu lực, sau đó dùng danh sách môn điểm thấp/có thể cải thiện trong bảng điểm đã parse. "
        "Khi khuyên học lại/cải thiện điểm, hãy nói là để xử lý môn F và cải thiện tiến độ/GPA, nhưng không hứa điểm cũ sẽ bị xóa nếu chưa có nguồn quy chế. "
        "Chỉ nhắc đến trích dẫn/tài liệu quy chế khi câu hỏi thật sự cần quy định."
    )


def _build_prompt(
    question: str,
    retrieved_context: str,
    student_context: str,
    history: list[dict[str, str]],
) -> str:
    history_text = _format_history_for_prompt(history[-6:]) if _needs_history_resolution(question) else ""
    history_label = (
        "Lịch sử gần đây, chỉ dùng để giải nghĩa tham chiếu và không được lấn át câu hỏi hiện tại:"
        if history_text
        else "Câu hỏi hiện tại tự đủ nghĩa; không dùng lịch sử cũ để thêm mục tiêu hoặc giả định mới:"
    )
    return (
        f"{_system_prompt()}\n\n"
        f"{history_label}\n"
        f"{history_text or 'Không có lịch sử.'}\n\n"
        f"{_build_user_prompt(question, retrieved_context, student_context)}"
    )


def _needs_history_resolution(question: str) -> bool:
    if re.search(r"\b[A-Z]{2}\d{4}\b", question.upper()):
        return False
    q = question.lower()
    reference_terms = [
        "môn đó",
        "môn này",
        "cái đó",
        "cái này",
        "ý đó",
        "vậy",
        "như trên",
        "ở trên",
        "nó",
    ]
    return any(term in q for term in reference_terms)


def _format_history_for_prompt(history: list[dict[str, str]]) -> str:
    lines = []
    for item in history:
        role = item.get("role", "unknown")
        content = " ".join(item.get("content", "").split())
        if not content:
            continue
        lines.append(f"{role}: {content[:500]}")
    return "\n".join(lines)


def _answer_from_student_context(question: str, student_context: str) -> str:
    profile = _parse_student_context(student_context)
    intent = _personal_intent(question)

    if intent == "failed_courses":
        return _answer_failed_courses(profile)

    if intent == "retake_priority":
        return _answer_retake_priority(profile)

    gpa = profile.get("gpa")
    credits = profile.get("credits")
    warning = profile.get("warning")
    failed_count = profile.get("unresolved_failed_count")
    failed_courses = profile.get("unresolved_failed_courses")
    risk_score = profile.get("risk_score")
    risk_level = profile.get("risk_level")

    if gpa is None:
        return (
            "Mình đã xem dữ liệu học vụ của bạn, nhưng chưa thấy đủ thông tin GPA để đánh giá rõ. "
            "Bạn thử import/cập nhật bảng điểm rồi hỏi lại nhé."
        )

    gpa_value = float(gpa)
    if gpa_value >= 3.2:
        tone = "khá tốt"
        advice = "Bạn đang có nền điểm ổn; mục tiêu hợp lý là giữ nhịp học đều và ưu tiên các môn nhiều tín chỉ."
    elif gpa_value >= 2.5:
        tone = "tạm ổn"
        advice = "Bạn chưa ở vùng quá căng, nhưng vẫn nên kéo dần lên bằng các môn có khả năng cải thiện điểm."
    elif gpa_value >= 2.0:
        tone = "hơi mong manh"
        advice = "Bạn nên ưu tiên xử lý các môn F/học lại trước, vì chỉ cần thêm vài học kỳ điểm thấp là rủi ro cảnh báo sẽ tăng khá nhanh."
    else:
        tone = "đáng lo"
        advice = "Bạn nên lập kế hoạch phục hồi ngay: giảm tải môn khó, học lại môn F và trao đổi cố vấn học tập nếu có thể."

    lines = [
        f"Nhìn nhanh thì GPA tích lũy {gpa_value:.2f} của bạn đang ở mức {tone}.",
    ]
    if warning is not None:
        warning_text = "chưa bị cảnh báo" if warning == "0" else f"đang ở cảnh báo mức {warning}"
        lines.append(f"Điểm tích cực là trạng thái hiện tại của bạn {warning_text}.")
    if credits is not None:
        lines.append(f"Bạn đã tích lũy {credits} tín chỉ, tức là dữ liệu học tập đã khá dày; việc kéo GPA lên sẽ cần chiến lược hơn là chỉ một học kỳ điểm cao.")
    if failed_count and failed_count != "0":
        course_text = f" ({failed_courses})" if failed_courses else ""
        lines.append(f"Mình để ý bạn còn {failed_count} môn chưa đạt còn hiệu lực{course_text}. Đây là phần nên ưu tiên nhất vì nó vừa ảnh hưởng GPA vừa ảnh hưởng tiến độ.")
    elif profile.get("historical_failed_count") and profile.get("historical_failed_count") != "0":
        resolved = profile.get("resolved_failed_courses")
        if resolved:
            lines.append(f"Các điểm F lịch sử có vẻ đã có môn được học lại/được thay bằng lần đạt hơn: {resolved}.")
    if risk_score:
        risk_label = f", mức {risk_level}" if risk_level else ""
        lines.append(f"Dự báo AI hiện cho risk score khoảng {risk_score}{risk_label}, nên mình sẽ xem đây là tình trạng cần theo dõi chứ chưa phải an toàn tuyệt đối.")

    lines.append(advice)
    lines.append("Nếu muốn, bạn có thể hỏi tiếp kiểu: “môn nào nên học lại trước?” hoặc “kỳ tới nên đăng ký bao nhiêu tín chỉ?”.")
    return "\n\n".join(lines)


def _answer_with_retrieved_context(
    question: str,
    retrieved_context: str,
    student_context: str,
) -> str:
    top_sources = _top_source_lines(retrieved_context, limit=3)
    parts = [
        "Mình tìm trong các tài liệu đã nạp và thấy vài đoạn có liên quan. Mình sẽ trả lời thận trọng theo nguồn hiện có, không suy diễn quá phần tài liệu.",
    ]
    if student_context and _looks_personal(question):
        profile = _parse_student_context(student_context)
        gpa = profile.get("gpa")
        warning = profile.get("warning")
        if gpa:
            warning_text = "chưa bị cảnh báo" if warning == "0" else f"cảnh báo mức {warning}"
            parts.append(f"Với dữ liệu của bạn, GPA tích lũy đang là {float(gpa):.2f} và trạng thái hiện tại là {warning_text}.")
    if top_sources:
        parts.append("Các nguồn gần nhất mình dùng:\n" + "\n".join(top_sources))
    parts.append("Bạn nên mở các trích dẫn bên dưới để đối chiếu văn bản gốc, nhất là với các điều kiện học vụ quan trọng.")
    return "\n\n".join(parts)


def _parse_student_context(student_context: str) -> dict[str, str]:
    patterns = {
        "gpa": r"GPA tích lũy hiện lưu:\s*([\d.]+)",
        "credits": r"tín chỉ tích lũy:\s*(\d+)",
        "warning": r"cảnh báo mức:\s*(\d+)",
        "historical_failed_count": r"Lượt F lịch sử trong dữ liệu:\s*(\d+)",
        "unresolved_failed_courses": r"Môn chưa đạt còn hiệu lực:\s*([^.]+)",
        "historical_failed_courses": r"Các lượt F lịch sử:\s*([^.]+)",
        "resolved_failed_courses": r"Môn từng F nhưng đã có lần học sau đạt/tốt hơn:\s*([^.]+)",
        "risk_score": r"risk score\s*([\d.]+%)",
        "risk_level": r"mức\s*([a-zA-Z]+)",
    }
    parsed: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, student_context)
        if match:
            parsed[key] = match.group(1)
    unresolved = parsed.get("unresolved_failed_courses")
    if unresolved:
        parsed["unresolved_failed_count"] = "0" if unresolved == "không có" else str(_count_course_codes(unresolved))
    return parsed


def _top_source_lines(retrieved_context: str, limit: int = 3) -> list[str]:
    lines = []
    for block in retrieved_context.split("\n\n"):
        cleaned = block.strip()
        if cleaned:
            lines.append(cleaned)
        if len(lines) == limit:
            break
    return lines


def _looks_personal(question: str) -> bool:
    q = question.lower()
    return any(token in q for token in ("tôi", "em", "mình", "của tôi", "của em", "của mình"))


def _personal_intent(question: str) -> str:
    q = question.lower()
    if any(token in q for token in ("học lại môn nào", "môn nào trước", "ưu tiên môn", "học lại trước", "xử lý môn")):
        return "retake_priority"
    if any(token in q for token in ("chưa đạt", "rớt", "rớt môn", "môn f", "đã học lại", "đạt rồi", "3 lượt")):
        return "failed_courses"
    return "general"


def _answer_failed_courses(profile: dict[str, str]) -> str:
    historical_count = profile.get("historical_failed_count", "0")
    unresolved = profile.get("unresolved_failed_courses", "không có")
    resolved = profile.get("resolved_failed_courses")
    historical = profile.get("historical_failed_courses")

    if unresolved == "không có":
        lines = [
            "Bạn bắt đúng điểm yếu trong câu trả lời trước của mình: mình đã nói hơi nhập nhằng giữa “lượt F lịch sử” và “môn còn nợ hiện tại”.",
            f"Trong dữ liệu có {historical_count} lượt F lịch sử, nhưng sau khi xét học lại/cải thiện theo từng môn thì hiện mình không thấy môn F nào còn hiệu lực.",
        ]
        if resolved:
            lines.append(f"Các môn từng F nhưng đã có lần học sau đạt/tốt hơn gồm: {resolved}.")
        lines.append("Vì vậy, nếu dữ liệu import của bạn đầy đủ, mình không nên kết luận là bạn còn nợ 3 môn. Mình sẽ dùng cách đếm “môn chưa đạt còn hiệu lực” cho các tư vấn tiếp theo.")
        return "\n\n".join(lines)

    lines = [
        f"Mình tách rõ lại nhé: dữ liệu có {historical_count} lượt F lịch sử, nhưng môn chưa đạt còn hiệu lực hiện là: {unresolved}.",
    ]
    if resolved:
        lines.append(f"Các môn từng F nhưng đã được học lại/được thay bằng lần đạt hơn: {resolved}.")
    if historical:
        lines.append(f"Còn danh sách lượt F lịch sử là: {historical}.")
    lines.append("Khi tư vấn học lại, mình sẽ ưu tiên danh sách “còn hiệu lực”, không dùng toàn bộ F lịch sử.")
    return "\n\n".join(lines)


def _answer_retake_priority(profile: dict[str, str]) -> str:
    unresolved = profile.get("unresolved_failed_courses", "không có")
    resolved = profile.get("resolved_failed_courses")

    if unresolved == "không có":
        lines = [
            "Nếu dữ liệu hiện tại đầy đủ thì bạn không có môn F nào còn hiệu lực để bắt buộc phải học lại ngay.",
        ]
        if resolved:
            lines.append(f"Một số môn từng F nhưng đã có lần học sau đạt/tốt hơn: {resolved}.")
        lines.append("Vậy ưu tiên của bạn không phải là “học lại môn F trước”, mà là chọn các môn kỳ tới sao cho vừa sức và kéo GPA dần lên. Nếu muốn cải thiện GPA, nên nhắm các môn nhiều tín chỉ mà bạn có khả năng đạt B/B+ trở lên.")
        return "\n\n".join(lines)

    ranked = _rank_failed_courses(unresolved)
    if not ranked:
        return f"Môn nên xử lý trước là các môn còn chưa đạt hiệu lực: {unresolved}."

    first = ranked[0]
    lines = [
        f"Mình sẽ ưu tiên {first['code']} trước.",
        f"Lý do: môn này đang còn chưa đạt hiệu lực, {first['credits']} tín chỉ, nên vừa ảnh hưởng tiến độ vừa kéo GPA tích lũy.",
    ]
    if len(ranked) > 1:
        order = " -> ".join(item["code"] for item in ranked)
        lines.append(f"Thứ tự gợi ý hiện tại: {order}.")
    lines.append("Nếu có môn tiên quyết/môn mở không đều theo học kỳ, bạn nên ưu tiên môn nào sắp mở hoặc đang chặn các môn sau trước.")
    return "\n\n".join(lines)


def _count_course_codes(text: str) -> int:
    return len(set(re.findall(r"\b[A-Z]{2}\d{4}\b", text)))


def _rank_failed_courses(text: str) -> list[dict[str, str]]:
    courses = []
    for match in re.finditer(r"\b(?P<code>[A-Z]{2}\d{4})\b.*?\((?P<credits>\d+)\s*TC", text):
        courses.append({"code": match.group("code"), "credits": match.group("credits")})
    return sorted(courses, key=lambda item: int(item["credits"]), reverse=True)
