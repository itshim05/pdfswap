# 🚀 Render Deployment Guide - PDFSwap

## Quick Deploy Steps

### Step 1: Sign Up for Render

1. Go to **[render.com](https://render.com)**
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account** (easiest option)
4. Authorize Render to access your GitHub repositories

---

### Step 2: Create New Web Service

1. Once logged in, click **"New +"** (top right)
2. Select **"Web Service"**
3. Click **"Build and deploy from a Git repository"**
4. Click **"Next"**

---

### Step 3: Connect Your Repository

1. Find and select **`itshim05/pdfswap`** from the list
   - If you don't see it, click **"Configure account"** and grant access
2. Click **"Connect"**

---

### Step 4: Configure Your Service

Fill in the following settings:

**Basic Settings:**
- **Name**: `pdfswap` (or any name you prefer - this will be in your URL)
- **Region**: `Singapore` (best for Indian students - lowest latency)
- **Branch**: `main`
- **Root Directory**: Leave blank
- **Runtime**: `Python 3`

**Build & Deploy:**
- **Build Command**: 
  ```
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```
  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```

**Instance Type:**
- Select **"Free"** (perfect for starting out)

**Advanced (Optional):**
- **Auto-Deploy**: `Yes` (recommended - auto-deploys when you push to GitHub)

---

### Step 5: Deploy!

1. Click **"Create Web Service"** at the bottom
2. Render will start building your app (takes 2-3 minutes)
3. Watch the logs - you'll see:
   - Installing dependencies
   - Starting the server
   - **"Your service is live 🎉"**

---

### Step 6: Get Your Live URL

Once deployed, you'll get a URL like:
```
https://pdfswap.onrender.com
```

**Test it:**
1. Click on the URL
2. You should see your PDF processing app!
3. Try uploading a PDF to make sure it works

---

## 🎯 Next Steps After Deployment

### 1. Custom Domain (Optional but Recommended for AdSense)

**Free Option:**
- Use the Render URL: `https://pdfswap.onrender.com`

**Custom Domain ($10/year):**
1. Buy a domain from [Namecheap](https://www.namecheap.com) or [GoDaddy](https://www.godaddy.com)
   - Example: `pdfswap.com` or `pdftools.in`
2. In Render dashboard → **Settings** → **Custom Domains**
3. Add your domain and follow DNS instructions
4. Wait for SSL certificate (automatic, takes ~5 minutes)

### 2. Add Ads (Easy Approval)

Since you are using a free Render domain, **Google AdSense will likely reject you**.
I recommend **PropellerAds** or **A-Ads** as they approve almost everyone.

**Option A: PropellerAds (Pop-ups & Banners)**
1.  Sign up at [PropellerAds](https://propellerads.com/).
2.  Add your site (`https://pdfswap.onrender.com`).
3.  They will give you a **verification tag**. Paste it into `frontend/index.html` inside the `<head>` tag.
4.  Once verified, create a "MultiTag" or "OnClick" ad zone and paste the code they give you.

**Option B: A-Ads (Crypto / Anonymous)**
1.  Go to [A-Ads](https://a-ads.com/).
2.  Click "Create Ad Unit".
3.  Select "Site" and enter your URL.
4.  They give you HTML code immediately. Paste it where you want ads to appear (e.g., top or bottom banner).

### 3. Monitor Your App

**Render Dashboard:**
- View logs
- Monitor usage
- Check uptime
- See deployment history

**Important Note:**
- Free tier spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- Upgrade to **Starter ($7/month)** for always-on service if needed

---

## 🔄 Updating Your App

Whenever you make changes:

```bash
# Make your changes to the code
git add .
git commit -m "Description of changes"
git push origin main

# Render automatically deploys! ✨
```

You'll see the deployment progress in your Render dashboard.

---

## 📊 Free Tier Limits

- **Hours**: 750 hours/month (enough for moderate usage)
- **Bandwidth**: Unlimited
- **Build Time**: Unlimited
- **Spin Down**: After 15 min inactivity (wakes up on first request)

**When to Upgrade:**
- If students complain about slow first load
- If you're getting consistent traffic
- If AdSense revenue covers the $7/month cost

---

## 🆘 Troubleshooting

### App Won't Start?

Check the logs in Render dashboard:
- Look for error messages
- Common issues:
  - Missing dependencies (add to `requirements.txt`)
  - Port binding (we're using `$PORT` variable ✓)
  - Python version mismatch

### Files Not Uploading?

- Check file size limits
- Verify CORS settings (already configured ✓)
- Check browser console for errors

### Static Files Not Loading?

- Ensure `frontend` folder is in GitHub ✓
- Check file paths in `backend/main.py` ✓

---

## 💡 Pro Tips

1. **Share the URL** with students once deployed
2. **Monitor logs** regularly for errors
3. **Set up custom domain** before applying for AdSense
4. **Add analytics** (Google Analytics) to track usage
5. **Create a landing page** explaining how to use the tool

---

## 📞 Need Help?

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Render Community**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

---

## ✅ Deployment Checklist

- [ ] Sign up for Render
- [ ] Connect GitHub repository
- [ ] Configure web service settings
- [ ] Deploy and test
- [ ] Share URL with students
- [ ] (Optional) Set up custom domain
- [ ] (Optional) Apply for Google AdSense
- [ ] (Optional) Add Privacy Policy page

---

**Your app will be live at**: `https://pdfswap.onrender.com` (or your custom name)

Good luck with your deployment! 🎉
