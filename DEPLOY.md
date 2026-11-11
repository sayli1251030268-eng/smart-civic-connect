# Deploying Smart Civic Connect

Two routes. Pick one.

## Before you start
- **Use HTTPS.** Browsers only allow the Geolocation API (used for "Use my location") on HTTPS or localhost. Without HTTPS, GPS reporting will fail on your live link.
- Create a free **Cloudinary** account and copy the cloud name, API key and API secret. Most hosts wipe local files on redeploy, so uploaded photos would disappear without it.
- Choose a strong `SECRET_KEY` and `ADMIN_PASSWORD`. With `APP_ENV=production` the backend refuses to start on the defaults.

## Route A: one server with Docker Compose
Works on any VPS or cloud VM with Docker installed (about 1 GB RAM without AI, about 3 GB with it).

    cp .env.example .env      # fill in every empty value
    docker compose up -d --build
    docker compose logs -f backend

The app is on port 8080 (`WEB_PORT`). The frontend's nginx forwards `/api` to the backend, so there is one origin and no CORS setup. MySQL, uploads and the AI model cache live in Docker volumes.

For HTTPS, put a reverse proxy in front, for example Caddy (`yourdomain.com { reverse_proxy localhost:8080 }`), and set `CORS_ORIGINS=https://yourdomain.com`.

To include AI: set `WITH_AI=true` in `.env` and rebuild. The first start downloads about 600 MB of model weights.

## Route B: hosted services (split)
1. **Database:** any hosted MySQL (for example Railway, Aiven or TiDB Cloud). Copy its connection URL. `mysql://...` URLs are accepted.
2. **Backend:** deploy the `backend/` folder as a Docker service (Railway, Render, Fly.io and similar). Set:
   `APP_ENV=production`, `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
   `CORS_ORIGINS=https://<your-frontend-domain>`, the three `CLOUDINARY_*` values.
   The service must listen on `$PORT` (the Dockerfile already does). Check `/health`.
3. **Frontend:** deploy the `frontend/` folder to Vercel or Netlify (SPA redirects are included).
   Set the build variable `VITE_API_URL=https://<your-backend-domain>` before building.
4. Open the frontend URL and log in as the admin.

Free tiers change often, so check each provider's current limits. A free tier with under 2 GB RAM cannot run the CLIP model: set `AI_ENABLED=off` and the app uses the hash-based duplicate check.

## Smoke test your live link
1. Register a citizen and report an issue with a photo (check the photo loads from Cloudinary).
2. Report the same spot again: the duplicate prompt should appear.
3. Log in as admin, assign the complaint, then resolve it with an after photo.
4. As the citizen, verify the fix.
5. Register a representative, verify them as admin, post a development update.

## Good to know
- The rate limiter is in memory and per process (20 auth attempts a minute, 30 reports an hour, 30 comments a minute per IP). If you run several backend replicas, move it to Redis.
- Tables are created automatically on startup. There are no migrations yet, so schema changes need `ALTER TABLE` or a fresh database.
- Back up the `db_data` volume (or your hosted database) before demos.
- This has not been load tested.
