# Deploying Auto-Pentest

| Part | Where it runs | Cost |
|---|---|---|
| Dashboard (Next.js), the link for your CV | **Vercel** (Hobby) | free, no card |
| Scanner API (FastAPI + nmap, nuclei, ...) | **AWS EC2** `t3.micro` + automatic HTTPS (Caddy) | AWS Free plan credits |
| Database | **MongoDB Atlas** M0 | free |
| Cache | **Upstash Redis** | free |

The API gets a free HTTPS address like `https://3-120-45-67.sslip.io` (your server's
IP with dashes). No domain to buy.

---

## 1. Database and cache (once)

- **MongoDB Atlas**: create an M0 cluster and a database user, copy the
  `mongodb+srv://...` connection string (with the real password), and under
  **Network Access** allow `0.0.0.0/0`.
- **Upstash**: create a free Redis database and copy its `rediss://...` URL.

Keep both in Notepad. They are secrets: never commit them.

## 2. Create the server on AWS

1. Sign in to the AWS console. Top right, pick the region **Europe (Frankfurt) eu-central-1**.
2. Open **EC2** → **Launch instance**:
   - **Name:** `auto-pentest-api`
   - **Application and OS Images:** **Ubuntu**, *Ubuntu Server 24.04 LTS* (64-bit **x86**)
   - **Instance type:** `t3.micro` (marked *Free tier eligible*)
   - **Key pair:** *Proceed without a key pair* (you'll connect from the browser)
   - **Network settings:** tick
     - Allow SSH traffic from **Anywhere**
     - Allow **HTTPS** traffic from the internet
     - Allow **HTTP** traffic from the internet
   - **Configure storage:** `20` GiB, gp3
   - **Advanced details** → **Credit specification** → **Standard** (avoids extra CPU charges)
3. Click **Launch instance**.

### Give it a fixed address (Elastic IP)

So the address (and the HTTPS link) never changes after a reboot:

1. EC2 left menu → **Elastic IPs** → **Allocate Elastic IP address** → **Allocate**.
2. Select it → **Actions** → **Associate Elastic IP address** → choose the instance `auto-pentest-api` → **Associate**.

## 3. Install the API (one command)

1. EC2 → **Instances** → select `auto-pentest-api` → **Connect** → tab **EC2 Instance Connect** → **Connect**.
   A terminal opens in your browser.
2. Paste this and press Enter:
   ```bash
   git clone https://github.com/Salamaaa1/web_vuln_scanner_with_chat_bot.git ~/app && bash ~/app/deploy/aws/setup.sh
   ```
3. When asked, paste `MONGODB_URL`, `REDIS_URL` and `NVIDIA_API_KEY`
   (paste in that terminal with **Ctrl+Shift+V** or right-click → Paste; the text stays
   hidden, which is normal).
4. Wait 5–10 minutes. It ends with:
   ```
   API is online:  https://X-X-X-X.sslip.io
   ```
   Open that address in your browser: it should show `{"status":"online", ...}`.
   **This is your API URL.**

## 4. Dashboard on Vercel

1. <https://vercel.com> → sign up with GitHub → **Add New** → **Project** → import the repo.
2. **Root Directory** → **Edit** → `frontend`.
3. **Environment Variables:** `NEXT_PUBLIC_API_URL` = your API URL from step 3 (no `/` at the end).
4. **Deploy**. You get `https://<something>.vercel.app`: **the link for your CV.**

> `NEXT_PUBLIC_API_URL` is built into the site. If you change it later:
> Vercel → *Deployments* → **Redeploy**.

## 5. Lock the API to your dashboard

In the server terminal (EC2 → Connect again if you closed it):
```bash
bash ~/app/deploy/aws/set-frontend.sh https://<something>.vercel.app
```

## 6. Test

Open your Vercel link and scan a legal test target:
- `scanme.nmap.org`: the Nmap project allows anyone to scan it
- `http://testphp.vulnweb.com`: a deliberately vulnerable demo site

---

## Updating after you push new code

```bash
bash ~/app/deploy/aws/setup.sh
```
It pulls the latest code, rebuilds and restarts the API, and keeps your settings.
(Frontend changes deploy on Vercel automatically on every push.)

## Costs and the 6-month limit

- `t3.micro` + 20 GB disk + the public IP cost about **$13–15/month** in Frankfurt, paid from
  your AWS Free plan credits. Check the balance in **Billing → Credits**.
- The AWS Free plan ends after **6 months** (or when credits run out). AWS then closes the
  account unless you upgrade. Before then, move the API elsewhere or upgrade.
- Don't leave extra instances or Elastic IPs lying around: an Elastic IP that isn't
  attached to a running instance still costs credits.

## Troubleshooting

| Problem | Fix |
|---|---|
| Setup ends with "The API isn't answering yet" | `cd ~/app/deploy/aws && sudo docker compose logs --tail 50` |
| Logs: Mongo `ServerSelectionTimeoutError` | Atlas **Network Access** must include `0.0.0.0/0`; check user/password in `MONGODB_URL`. |
| Wrong value pasted during setup | `rm ~/app/deploy/aws/.env` then run `setup.sh` again. |
| Browser console: CORS error | Run `set-frontend.sh` with the exact Vercel URL (https, no trailing `/`). |
| Dashboard calls `localhost:8000` | `NEXT_PUBLIC_API_URL` missing on Vercel → add it and **Redeploy**. |
| HTTPS address doesn't load | Security group must allow ports 80 and 443 (step 2). |
| AI tab says "not configured" | `rm ~/app/deploy/aws/.env`, run `setup.sh` again and paste the NVIDIA key. |
