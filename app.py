from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional
import uvicorn
import socket
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from email_service import send_contact_email

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# Inizializza il rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="CIP Network",
    description="Crowdfunding Immobiliare a Dubai",
    version="1.0.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Secret key per sicurezza (usata per firmare token, crittografia, ecc.)
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production-' + os.urandom(32).hex())

# Monta i file statici (deve essere dopo l'inizializzazione di app)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
# Mount aggiuntivo per /img come fallback
app.mount("/img", StaticFiles(directory="assets/img"), name="img")
# Mount per i video
app.mount("/video", StaticFiles(directory="assets/video"), name="video")

# Modello per il form di contatto
class ContactForm(BaseModel):
    nome: str
    email: EmailStr
    telefono: Optional[str] = None
    messaggio: str


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve la pagina principale"""
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.post("/api/contatti")
@limiter.limit("5/minute")  # Massimo 5 richieste al minuto per IP
async def submit_contact(request: Request, form_data: ContactForm):
    """
    Endpoint per gestire l'invio del form di contatto.
    Invia un'email di notifica quando arriva un nuovo messaggio.
    Protetto con rate limiting per prevenire spam.
    """
    try:
        # Invia l'email di notifica
        email_sent = send_contact_email(
            name=form_data.nome,
            email=form_data.email,
            phone=form_data.telefono or "",
            message=form_data.messaggio
        )
        
        if email_sent:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Grazie per la tua richiesta! Ti contatteremo presto.",
                    "data": {
                        "nome": form_data.nome,
                        "email": form_data.email,
                        "telefono": form_data.telefono
                    }
                }
            )
        else:
            # Se l'invio dell'email fallisce, restituisci comunque successo
            # per non esporre errori interni all'utente
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Grazie per la tua richiesta! Ti contatteremo presto.",
                    "data": {
                        "nome": form_data.nome,
                        "email": form_data.email,
                        "telefono": form_data.telefono
                    }
                }
            )
    except Exception as e:
        # In caso di errore, restituisci comunque successo per non esporre errori
        print(f"❌ Errore durante l'elaborazione del form: {str(e)}")
        return JSONResponse(
            content={
                "success": True,
                "message": "Grazie per la tua richiesta! Ti contatteremo presto.",
            },
            status_code=200
        )


@app.get("/health")
async def health_check():
    """Endpoint per verificare lo stato dell'applicazione"""
    return {"status": "ok", "message": "CIP Network API is running"}


if __name__ == "__main__":
    host = "0.0.0.0"
    port = 8002
    
    # Ottieni l'IP locale della macchina
    try:
        # Connessione a un server DNS per ottenere l'IP locale
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        host_ip = s.getsockname()[0]
        s.close()
    except Exception:
        host_ip = "127.0.0.1"
    
    # Stampa gli indirizzi
    print("\n" + "="*50)
    print("🚀 CIP Network - Server avviato!")
    print("="*50)
    print(f"📍 Localhost: http://localhost:{port}")
    print(f"🌐 Host IP:    http://{host_ip}:{port}")
    print("="*50 + "\n")
    
    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True  # Auto-reload durante lo sviluppo
    )

