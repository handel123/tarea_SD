
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SLAVE_PORTS = {
    "libros": 8003,
    "recetas": 8004,
}

SLAVES = {tipo: f"http://localhost:{port}" 
          for tipo, port in SLAVE_PORTS.items()}

class RangoEtario(str, Enum):
    NINOS = "10-15"
    JOVENES = "16-25"
    ADULTOS = "26+"

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
    score: float

async def calcular_score(titulo: str, palabras_clave: List[str], 
                        query_terms: List[str], rango_usuario: str, 
                        tipo_doc: str) -> float:
    titulo_lower = titulo.lower()
    score = sum(term.lower() in titulo_lower for term in query_terms) * 2.0
    
    score += sum(any(term.lower() in kw.lower() for kw in palabras_clave) 
             for term in query_terms) * 1.0
    
    if rango_usuario == RangoEtario.NINOS and tipo_doc == "libro":
        score *= 1.5
    elif rango_usuario == RangoEtario.JOVENES and tipo_doc == "articulo":
        score *= 1.3
    elif rango_usuario == RangoEtario.ADULTOS and tipo_doc == "revista":
        score *= 1.2
    
    return score




@app.get("/query/titulo")
async def buscar_por_titulo(
    titulo: str = "",
    rango_etario: RangoEtario = RangoEtario.ADULTOS
) -> List[Documento]:
    if not titulo.strip():
        raise HTTPException(status_code=400, detail="Debe proporcionar un título válido.")

    query_terms = titulo.strip().split()
    resultados = []

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def consultar_esclavo(tipo: str):
            try:
                url = f"{SLAVES[tipo]}/buscar"
                response = await client.get(url, params={"titulo": titulo})
                return tipo, response
            except Exception as e:
                print(f"Error consultando esclavo {tipo}: {e}")
                return tipo, None

        tasks = [consultar_esclavo(tipo) for tipo in SLAVES.keys()]
        responses = await asyncio.gather(*tasks)

        for tipo, response in responses:
            if response is None or response.status_code != 200:
                continue

            for doc in response.json():
                score = await calcular_score(
                    doc["titulo"],
                    doc["palabras_clave"],
                    query_terms,
                    rango_etario,
                    tipo
                )
                resultados.append(Documento(**doc, tipo=tipo, score=score))

    resultados.sort(key=lambda x: x.score, reverse=True)
    return resultados


@app.get("/query/tipo")
async def buscar_por_tipo_doc(
    tipo_doc: str,
    rango_etario: RangoEtario = RangoEtario.ADULTOS
) -> List[Documento]:
    tipos_solicitados = [t.strip() for t in tipo_doc.split() if t.strip() in SLAVES]
    if not tipos_solicitados:
        raise HTTPException(status_code=400, detail="tipo_doc inválido o no disponible.")

    resultados = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        tasks = []
        for tipo in tipos_solicitados:
            url = f"{SLAVES[tipo]}/buscar"
            tasks.append(client.get(url))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for tipo, response in zip(tipos_solicitados, responses):
            if isinstance(response, Exception):
                print(f"Error consultando esclavo {tipo}: {response}")
                continue

            if response.status_code == 200:
                for doc in response.json():
                    score = await calcular_score(
                        doc["titulo"],
                        doc["palabras_clave"],
                        [],
                        rango_etario,
                        tipo
                    )
                    resultados.append(Documento(**doc, tipo=tipo, score=score))

    resultados.sort(key=lambda x: x.score, reverse=True)
    return resultados

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)