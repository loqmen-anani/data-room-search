"""API HTTP : les tools (pour un orchestrateur externe) et l'agent complet (`/ask`).

Lancement : uvicorn dataroom.api:app --port 8001 --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from dataroom.agent import AgentAnswer, run_agent
from dataroom.config import DEFAULT_MODEL
from dataroom.models import SearchRequest, SearchResponse
from dataroom.search import search
from dataroom.tools import ContractText, GetContract, get_contract, get_index, tool_definitions

app = FastAPI(title="Data room tools")


@app.post("/tools/search_data_room", response_model=SearchResponse, response_model_exclude_none=True)
def search_data_room_endpoint(req: SearchRequest) -> SearchResponse:
    try:
        return search(get_index(), req)
    except ValueError as e:  # valeur de filtre absente de la data room
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/tools/get_contract", response_model=ContractText)
def get_contract_endpoint(params: GetContract) -> ContractText:
    try:
        return get_contract(params)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=e.args[0])


@app.get("/tools")
def list_tools() -> list[dict]:
    """Définitions à passer telles quelles dans le paramètre `tools` de l'API Claude."""
    return tool_definitions()


class AskRequest(BaseModel):
    question: str
    model: str = DEFAULT_MODEL
    think: bool = False


@app.post("/ask", response_model=AgentAnswer)
def ask(req: AskRequest) -> AgentAnswer:
    """Question en langage naturel -> réponse de l'agent (LLM Ollama + tools), avec la trace des appels."""
    return run_agent(req.question, model=req.model, think=req.think)
