import base64
import logging
from openai import OpenAI
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
client = OpenAI(api_key=OPENAI_API_KEY)

def extract_part_number_from_image(image_bytes: bytes) -> dict:
    b64_img = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are an industrial automation expert scouting parts in a surplus yard. "
        "Look at this equipment nameplate/label photo. "
        "Extract the Brand (e.g. Siemens, Allen-Bradley, Omron) and the primary Part Number (e.g. 6ES7315-2AH14-0AB0). "
        "Reply ONLY in this format: BRAND | PART_NUMBER. If unreadable, reply UNKNOWN."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        },
                    ],
                }
            ],
            max_tokens=60,
        )
        raw_text = response.choices[0].message.content.strip()

        if "UNKNOWN" in raw_text or "|" not in raw_text:
            return {"success": False, "error": "Could not identify clear part number."}

        brand, part_num = [item.strip() for item in raw_text.split("|", 1)]
        return {"success": True, "brand": brand, "part_number": part_num}

    except Exception as e:
        return {"success": False, "error": str(e)}