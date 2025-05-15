from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncpg
import os
from datetime import datetime
import json
from dotenv import load_dotenv


app = FastAPI()
load_dotenv()




# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PORT_BD = int(os.environ.get("PORT_BD")) 
DATABASE_TYPE = os.environ.get("DATABASE_TYPE")
DETALLES_CAMPOS = os.environ.get("DETALLES_CAMPOS")

DB_CONFIG = {

    "db_url": f"postgresql://postgres:postgres@{os.getenv('DATABASE_HOST')}:{os.getenv('PORT_BD')}/{os.getenv('DATABASE_TYPE')}",

    "detalles_campos": DETALLES_CAMPOS.split(",") if DETALLES_CAMPOS else [],
}




async def get_db_connection():
    return await asyncpg.connect(DB_CONFIG["db_url"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "port": os.getenv("PORT")}


@app.get("/buscar")
async def buscar(titulo: Optional[str] = None):
    conn = await get_db_connection()
    try:
        query = f"""
            SELECT *
            FROM documentos d
            JOIN detalles_{DATABASE_TYPE} dl ON d.id = dl.documento_id
        """
        params = []
        
        if titulo:
            palabras = titulo.strip().split()
            condiciones = [f"d.titulo ILIKE ${i+1}" for i in range(len(palabras))]
            query += " WHERE " + " OR ".join(condiciones)
            params.extend([f"%{p}%" for p in palabras])
        
        records = await conn.fetch(query, *params)
        
        documentos = []
        for record in records:
            doc = {
                "id": record["id"],
                "titulo": record["titulo"],
                "autores": record["autores"],
                "fecha_publicacion": str(record["fecha_publicacion"]),
                "descripcion": record["descripcion"],
                "palabras_clave": record["palabras_clave"],
                "idioma": record["idioma"],
                "rango_etario": record["rango_etario"],
                "disponible": record["disponible"]

            }
            for campo in DB_CONFIG["detalles_campos"]:
                if campo in record:
                    doc[campo] = record[campo]



            documentos.append(doc)
        
        return documentos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await conn.close()







@app.middleware("http")
async def log_requests(request: Request, call_next):
    if request.url.path == "/buscar":
        start_time = datetime.now()
        
        
        response = await call_next(request)
        
        if response.status_code == 200:
            try:
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                results = json.loads(response_body.decode()) if response_body else []
                
                response = Response(
                    content=response_body,
                    status_code=200,
                    media_type=response.media_type,
                    headers=dict(response.headers)
                )
                
                end_time = datetime.now()
                doc_ids = [doc['id'] for doc in results] if results else None
                
                conn = await get_db_connection()
                await conn.execute(
                    "SELECT registrar_consulta_log($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)",
                    start_time,
                    end_time,
                    doc_ids if doc_ids else None,
                    str(request.url),
                    json.dumps(dict(request.query_params)),
                    request.client.host if request.client else None,
                    (end_time - start_time).total_seconds() * 1000,
                    len(results) if results else 0,
                    None,
                    request.query_params.get("rango_etario"),
                    json.dumps([doc['titulo'] for doc in results][:3]) if results else None
                )
                await conn.close()
                
            except Exception as e:
                print(f"Error registrando log: {e}")
        
        return response
    
    return await call_next(request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)