# Deploying Auto-Pentest for free

Every piece runs on a free plan:

| Part | Free host | What it is |
|---|---|---|
| Dashboard (Next.js) | **Vercel** (Hobby) | the link you put on your CV |
| Scanner API (FastAPI + tools) | **Render** (free web service, Docker) | runs the scans |
| Database | **MongoDB Atlas** (M0, 512 MB) | targets, results, AI chats |
| Cache | **Upstash Redis** (free, 256 MB) | scan + AI answer cache |

**Limits of the free plans**
- Render's free plan has **512 MB RAM and 0.1 CPU**. Scans are much slower than on your PC, and big targets may get cut off. The settings in `render.yaml` keep the tools light.
- Render **sleeps after 15 minutes without visitors**. The first visit wakes it up in about a minute, and the dashboard shows a "Démarrage du serveur…" banner while that happens.
- Render asks for a card to verify your account, but the free plan doesn't charge it.

Do the steps in this order: each one gives you a value the next one needs.

---

## 1. Push to GitHub

```bash
git add .
git commit -m "Free deployment config (Render + Vercel)"
git push
```

Check that `.env` is **not** pushed (`git ls-files | grep .env` → only `.env.example`).

## 2. MongoDB Atlas (database)

1. Go to <https://cloud.mongodb.com> and sign up → **Create** a cluster → choose **M0 Free**, any region close to Render's (e.g. Frankfurt/AWS eu-central-1).
2. **Database Access** → add a user (username + password). Avoid special characters like `@ : / ?` in the password, or URL-encode them.
3. **Network Access** → **Add IP Address** → `0.0.0.0/0` (allow from anywhere: Render's IPs change).
4. **Connect** → **Drivers** → copy the string:
   `mongodb+srv://USER:PASSWORD@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority`
   This is your **`MONGODB_URL`**.

## 3. Upstash (Redis cache)

1. Go to <https://upstash.com> and sign up → **Create Database** (Redis), any region.
2. On the database page, copy the **Redis URL** (the one that starts with `rediss://default:...@...upstash.io:6379`).
   This is your **`REDIS_URL`**.

## 4. Render (scanner API)

1. Go to <https://render.com> and sign up with GitHub.
2. **New** → **Blueprint** → pick your repo. Render reads `render.yaml` and creates the `auto-pentest-scanner` service on the free plan.
3. It asks for the secret values:
   - `MONGODB_URL`: from step 2
   - `REDIS_URL`: from step 3
   - `NVIDIA_API_KEY`: your key
   - `ALLOWED_ORIGINS`: leave **empty for now** (you'll set it in step 6)
4. Click **Apply**. The first build takes 5–15 minutes (it installs nmap, nuclei and its templates, etc.).
5. When it's live, open `https://auto-pentest-scanner-xxxx.onrender.com/`. It should show
   `{"status":"online", ...}`. Copy this URL: it's your **API URL**.

## 5. Vercel (dashboard)

1. Go to <https://vercel.com> and sign up with GitHub → **Add New** → **Project** → import your repo.
2. **Root Directory:** click *Edit* → choose `frontend`. Vercel detects Next.js automatically.
3. **Environment Variables:** add
   `NEXT_PUBLIC_API_URL` = your Render API URL from step 4 (no `/` at the end).
4. **Deploy**. You get a URL like `https://auto-pentest.vercel.app`: **that's the link for your CV.**

> `NEXT_PUBLIC_API_URL` is built into the site at build time. If you change it later,
> go to *Deployments* → **Redeploy**.

## 6. Lock the API to your dashboard

Back in Render → your service → **Environment** → set
`ALLOWED_ORIGINS` = your Vercel URL (e.g. `https://auto-pentest.vercel.app`, no `/` at the end)
→ **Save, rebuild and deploy**.

## 7. Test

Open your Vercel URL. If the banner shows, wait for it to disappear, then scan a legal test target:
- `scanme.nmap.org`: the Nmap project allows anyone to scan it
- `http://testphp.vulnweb.com`: a deliberately vulnerable demo site

Tip: before sending your CV, open the link once, so the server is already awake when a recruiter clicks.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Banner never goes away | Open the Render URL directly. If it doesn't answer, check the Render **Logs** tab. |
| Render log: Mongo `ServerSelectionTimeoutError` | Atlas **Network Access** must include `0.0.0.0/0`; check user/password in `MONGODB_URL`. |
| Browser console: CORS error | `ALLOWED_ORIGINS` on Render must exactly equal the Vercel URL (https, no trailing `/`). |
| Dashboard calls `localhost:8000` | `NEXT_PUBLIC_API_URL` missing on Vercel → add it and **Redeploy**. |
| Scan stops / Render log says "out of memory" | Free plan limit. Scan smaller targets, or lower `NMAP_TOP_PORTS` / set `NUCLEI_SEVERITY=critical,high`. |
| AI tab says "not configured" | Set `NVIDIA_API_KEY` on Render. |
