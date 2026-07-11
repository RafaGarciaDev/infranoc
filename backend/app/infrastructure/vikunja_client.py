"""
app/infrastructure/vikunja_client.py

Cliente HTTP para o Vikunja (kanban self-hosted).
Auth: token de API estatico (gerado na UI do Vikunja, sem expiracao).
API: REST em /api/v1  (Swagger disponivel em /api/v1/docs)
"""
import httpx

from app.core.config import settings

# Mapa de labels ja existentes no Vikunja -> id numerico.
# Populado na primeira chamada e cacheado em memoria.
# Se uma label nao existir, sera criada automaticamente.
_label_cache: dict[str, int] = {}


class VikunjaClient:

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {settings.vikunja_token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Labels (criacao lazy + cache)
    # ------------------------------------------------------------------
    async def _ensure_label(self, client: httpx.AsyncClient, name: str) -> int:
        """Devolve o id de uma label existente ou cria uma nova."""
        if name in _label_cache:
            return _label_cache[name]

        # Busca labels existentes
        r = await client.get("/api/v1/labels", headers=self._headers())
        r.raise_for_status()
        for lbl in r.json():
            _label_cache[lbl["title"]] = lbl["id"]

        if name in _label_cache:
            return _label_cache[name]

        # Cria nova label
        r = await client.put(
            "/api/v1/labels",
            headers=self._headers(),
            json={"title": name},
        )
        r.raise_for_status()
        lbl = r.json()
        _label_cache[lbl["title"]] = lbl["id"]
        return lbl["id"]

    # ------------------------------------------------------------------
    # Operacoes
    # ------------------------------------------------------------------
    async def create_task(
        self,
        title: str,
        description: str,
        labels: list[str],
        priority: int = 3,
    ) -> int:
        """
        Cria uma task no projeto configurado e devolve o task id (int).
        priority: 0 (nenhuma) a 5 (urgente) — padrao Vikunja.
        """
        if not settings.vikunja_project_id:
            raise RuntimeError("vikunja_project_id nao configurado (INFRANOC_VIKUNJA_PROJECT_ID)")

        async with httpx.AsyncClient(base_url=settings.vikunja_url, timeout=15) as client:
            # Resolve ids das labels
            label_ids = []
            for name in labels:
                try:
                    lid = await self._ensure_label(client, name)
                    label_ids.append({"id": lid})
                except Exception:
                    pass  # label opcional, nao derruba a criacao da task

            r = await client.put(
                f"/api/v1/projects/{settings.vikunja_project_id}/tasks",
                headers=self._headers(),
                json={
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "labels": label_ids,
                },
            )
            r.raise_for_status()
            data = r.json()
            if "id" not in data:
                raise RuntimeError(f"Vikunja create_task resposta inesperada: {data}")
            return int(data["id"])

    async def mark_done(self, task_id: int) -> None:
        """Marca a task como concluida (done = True)."""
        async with httpx.AsyncClient(base_url=settings.vikunja_url, timeout=15) as client:
            r = await client.post(
                f"/api/v1/tasks/{task_id}",
                headers=self._headers(),
                json={"done": True},
            )
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(f"Vikunja mark_done error: {data}")
