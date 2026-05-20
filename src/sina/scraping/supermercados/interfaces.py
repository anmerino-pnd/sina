from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class BrowserConfig:
    """Configuración base para spiders de supermercados (Playwright/Selenium)."""
    headless: bool = True
    viewport: Dict[str, int] = field(default_factory=lambda: {'width': 1366, 'height': 768})
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    timeout_ms: int = 60000

    def to_playwright_context(self) -> Dict[str, Any]:
        """Devuelve los kwargs para el context de Playwright."""
        return {
            "viewport": self.viewport,
            "user_agent": self.user_agent
        }
