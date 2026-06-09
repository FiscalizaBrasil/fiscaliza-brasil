from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from api.camara.router import router as camara_router
from api.senado.router import router as senado_router
from api.portal.router import router as portal_router
from scripts.scraper import start_background_scraper, start_background_fotos, scraping_status

app = FastAPI()

# Configuração CORS
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Servir fotos baixadas localmente
fotos_dir = os.path.join(os.path.dirname(__file__), "data", "fotos")
os.makedirs(fotos_dir, exist_ok=True)
app.mount("/api/fotos", StaticFiles(directory=fotos_dir), name="fotos")

# Rotas
app.include_router(camara_router, prefix="/api")
app.include_router(senado_router, prefix="/api")
app.include_router(portal_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Inicia os scrapers em background quando a aplicação sobe."""
    logger.info("Iniciando downloads em background...")
    start_background_fotos()
    start_background_scraper()


@app.get("/")
def read_root():
    return {"message": "API de Deputados em funcionamento"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/scraping-status")
def get_scraping_status():
    """Retorna o status atual do scraping em background."""
    return scraping_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
