# 🎮 TeamKahoot - Configuración Backend/Frontend

## Estructura del Proyecto

```
- Frontend: Vercel (https://kahootgenerico.vercel.app)
- Backend: Railway (https://kahootgenerico-production.up.railway.app)
```

## Configuración en Railway (Backend)

El backend está en la rama `main` o desplegado en Railway.

**Variables de entorno necesarias en Railway:**

```
DATABASE_URL=mysql://user:password@host:port/database
SECRET_KEY=tu-clave-secreta-aqui
FRONTEND_URL=https://kahootgenerico.vercel.app
```

**El backend automáticamente:**
- ✅ Acepta conexiones desde Vercel
- ✅ Configura CORS para `https://kahootgenerico.vercel.app`
- ✅ Soporta desarrollo local en `http://localhost:3000`

## Configuración en Vercel (Frontend)

**Variables de entorno en Vercel (si necesitas personalizar):**

```
BACKEND_URL=https://kahootgenerico-production.up.railway.app
```

**El frontend automáticamente:**
- ✅ Detecta si está en desarrollo local (`localhost`) o producción
- ✅ Usa la URL correcta de Railway por defecto
- ✅ Se conecta via Socket.IO al backend

## URLs de los Servicios

| Servicio | URL |
|----------|-----|
| Frontend | https://kahootgenerico.vercel.app |
| Backend | https://kahootgenerico-production.up.railway.app |
| Socket.IO | wss://kahootgenerico-production.up.railway.app (WebSocket) |

## Desarrollo Local

Para desarrollar localmente:

```bash
# Backend (en otra terminal)
cd src
export DATABASE_URL=mysql://...
export SECRET_KEY=dev-secret
python -m flask run

# Frontend (en otra terminal)
npm start  # Si tienes un servidor local en puerto 3000
```

El frontend detectará automáticamente `localhost` y se conectará a `http://localhost:5000` para desarrollo.

## Posibles errores y soluciones

### ❌ "No se pudo conectar al servidor"

**Solución:**
1. Verifica que Railway esté corriendo: `https://kahootgenerico-production.up.railway.app`
2. Revisa la consola del navegador (F12) para ver el error exacto
3. Confirma que DATABASE_URL está en Railway
4. Verifica que CORS está configurado correctamente

### ❌ "CORS error"

**Solución:**
- El backend ya está configurado para aceptar Vercel
- Si añades un nuevo dominio, actualiza `FRONTEND_URLS` en `src/app.py`

### ❌ "Socket.IO connection failed"

**Solución:**
- El transporte está configurado para WebSocket + Polling
- Si sigue fallando, verifica que no haya firewall bloqueando WebSocket

## Deployment

### Railway (Backend)
El deploy es automático desde Git cuando haces push a la rama principal.

### Vercel (Frontend)
El deploy es automático desde Git cuando haces push a la rama principal.

---

**Última actualización:** 2024
