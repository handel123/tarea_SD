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
## VARIABLES DE ENTORNO
#HOST = os.environ.get("HOST")
PORT_BD = int(os.environ.get("PORT_BD")) # 5433 
DATABASE_TYPE = os.environ.get("DATABASE_TYPE") # "libros"
DETALLES_CAMPOS = os.environ.get("DETALLES_CAMPOS") # "isbn, editorial, n_paginas, genero"

# Configuración de la base de datos

DB_CONFIG = {

    "db_url": f"postgresql://postgres:postgres@{os.getenv('DATABASE_HOST')}:{os.getenv('PORT_BD')}/{os.getenv('DATABASE_TYPE')}",

    "detalles_campos": DETALLES_CAMPOS.split(",") if DETALLES_CAMPOS else [],
}

print(DB_CONFIG["db_url"])
print(DB_CONFIG["detalles_campos"])


async def get_db_connection():
    return await asyncpg.connect(DB_CONFIG["db_url"])




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
        
        # Datos básicos para el log
        log_data = {
            "timestamp_ini": start_time,
            "query_busqueda": str(request.url),
            "parametros": dict(request.query_params),
            "ip_cliente": request.client.host if request.client else None
        }
        
        # Procesar la solicitud
        response = await call_next(request)
        
        # Solo registrar logs para respuestas exitosas
        if response.status_code == 200:
            try:
                # Leer el contenido de la respuesta
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk
                
                # Parsear el JSON si es necesario
                results = json.loads(response_body.decode()) if response_body else []
                
                # Restaurar la respuesta original
                response = Response(
                    content=response_body,
                    status_code=200,
                    media_type=response.media_type,
                    headers=dict(response.headers)
                )
                
                # Registrar el log
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