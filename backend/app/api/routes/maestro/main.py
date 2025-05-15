
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import asyncio
from dotenv import load_dotenv
import json
import os


app = FastAPI()
load_dotenv()




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
SLAVE_HOSTS = json.loads(os.getenv("SLAVE_HOSTS_JSON", "{}"))

SLAVES = {tipo: f"http://{host}" for tipo, host in SLAVE_HOSTS.items()}




class Documento(BaseModel):
    id: int
    titulo: str
    autores: List[str]
    fecha_publicacion: str
    descripcion: str
    palabras_clave: List[str]
    idioma: str
    rango_etario: str
    disponible: bool
    tipo: str
    score: Optional[float] = None

async def calcular_score(titulo: str, palabras_clave: List[str], 
                         descripcion: str, query_terms: List[str], 
                         rango_usuario: str, rango_doc: str) -> float:
    
    titulo_lower = titulo.lower()
    descripcion_lower = descripcion.lower()
    palabras_clave_lower = [kw.lower() for kw in palabras_clave]
    
    score = sum(term.lower() in titulo_lower for term in query_terms) * 3.0
    
    score += sum(any(term.lower() in kw for kw in palabras_clave_lower) 
                 for term in query_terms) * 2.0
    
    score += sum(term.lower() in descripcion_lower for term in query_terms) * 1.0
    
    if rango_doc == rango_usuario:
        score += 2.0

    return score




@app.get("/query/tipo")
async def buscar_por_tipo_doc(
    tipo_doc: str,
) -> List[Documento]:
    tipos_solicitados = [t.strip() for t in tipo_doc.split(",") if t.strip() in SLAVES]
    if not tipos_solicitados:
        raise HTTPException(status_code=400, detail="tipo_doc inválido o no disponible.")

    resultados = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        async def consultar(tipo):
            try:
                url = f"{SLAVES[tipo]}/buscar"
                response = await client.get(url, params={"titulo": ""})
                return tipo, response
            except Exception:
                return tipo, None

        tasks = [consultar(tipo) for tipo in tipos_solicitados]
        responses = await asyncio.gather(*tasks)

        for tipo, response in responses:
            if response is None or response.status_code != 200:
                continue

            for doc in response.json():
                resultados.append(Documento(**doc, tipo=tipo))

    return resultados

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)