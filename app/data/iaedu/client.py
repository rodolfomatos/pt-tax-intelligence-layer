import logging
import json
from typing import Optional, AsyncGenerator
from uuid import uuid4
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class IAEDUClient:
    """Client for IAEDU API (iaedu.pt) - free for Portuguese universities."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        channel_id: Optional[str] = None,
    ):
        self.api_key = api_key or settings.iaedu_api_key
        self.endpoint = endpoint or settings.iaedu_endpoint
        self.channel_id = channel_id or settings.iaedu_channel_id
        self.model_name = settings.iaedu_model_name or "iaedu-gpt4o"
    
    async def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a chat message and yield response tokens.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            
        Yields:
            Response tokens (chunks)
        """
        thread_id = f"tax-{uuid4().hex[:16]}"
        
        form_data = {
            "channel_id": self.channel_id,
            "thread_id": thread_id,
            "user_info": json.dumps({"system_prompt": system_prompt}) if system_prompt else "{}",
            "message": message,
        }
        
        logger.info(f"IAEDU request: thread={thread_id}, message={message[:50]}...")
        
        try:
            async with httpx.AsyncClient(
                timeout=120.0,
                follow_redirects=True,
            ) as client:
                response = await client.post(
                    self.endpoint,
                    files={k: (None, v) for k, v in form_data.items()},
                    headers={"x-api-key": self.api_key},
                )
                
                if not response.ok:
                    error_text = await response.text()
                    logger.error(f"IAEDU error: {response.status} - {error_text}")
                    yield f"[Erro: {response.status}] {error_text}"
                    return
                
                # Stream NDJSON response
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        
                        if not line:
                            continue
                        
                        try:
                            parsed = json.loads(line)
                            if parsed.get("type") == "token" and parsed.get("content"):
                                yield parsed["content"]
                            elif parsed.get("type") == "error":
                                yield f"[Erro: {parsed.get('message')}]"
                        except json.JSONDecodeError:
                            pass
                            
        except httpx.TimeoutException:
            logger.error("IAEDU timeout")
            yield "[Erro: Timeout exceeded]"
        except httpx.HTTPError as e:
            logger.error(f"IAEDU HTTP error: {e}")
            yield f"[Erro: {str(e)}]"
    
    async def chat_complete(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a chat message and return complete response.
        
        Args:
            message: User message
            system_prompt: Optional system prompt
            
        Returns:
            Complete response string
        """
        chunks = []
        async for chunk in self.chat(message, system_prompt):
            chunks.append(chunk)
        return "".join(chunks)
    
    async def health_check(self) -> bool:
        """Check if IAEDU API is available."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.endpoint,
                    files={
                        "channel_id": (None, self.channel_id),
                        "thread_id": (None, "health-check"),
                        "user_info": (None, "{}"),
                        "message": (None, "ping"),
                    },
                    headers={"x-api-key": self.api_key},
                )
                return response.status_code < 500
        except httpx.HTTPError:
            return False


_iaedu_client: Optional[IAEDUClient] = None


def get_iaedu_client() -> IAEDUClient:
    global _iaedu_client
    if _iaedu_client is None:
        _iaedu_client = IAEDUClient()
    return _iaedu_client
