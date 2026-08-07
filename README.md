# Crumble Tracker — Butter & Crumble

Two HTML files. No frameworks, no build step, no dependencies. Just open them in a browser.

## Files

- `index.html` — Customer-facing tracker (public URL)
- `staff.html` — Staff admin dashboard (password-protect this!)

---

## How to get this live in 30 minutes (free)

### Option A: Netlify Drop (easiest, no account needed)
1. Go to https://app.netlify.com/drop
2. Drag and drop the entire `crumble-tracker` folder onto the page
3. You get a live URL instantly — e.g. `https://random-name.netlify.app`
4. Share `index.html` URL with customers, keep `staff.html` for internal use

### Option B: GitHub Pages (free, permanent)
1. Create a free account at https://github.com
2. New repository → name it `crumble-tracker` → public
3. Upload both HTML files
4. Settings → Pages → Source: main branch → Save
5. Live at `https://yourusername.github.io/crumble-tracker`

### Option C: Vercel (free, fast)
1. https://vercel.com → sign up with GitHub
2. Import your crumble-tracker repo
3. Deploy → done. Custom domain support built in.

---

## Custom domain (optional, ~$12/year)
Buy `butterandcrumble.app` or similar at Namecheap/Google Domains, then point it to your Netlify/Vercel URL via their DNS settings.

---

## What's currently hardcoded (you'll need to update manually until backend is built)

In `index.html`:
- Line count, wait time, pastry stock levels — update the JS `pastries` array
- Sell-out timeline items — edit the `.tl-item` HTML blocks
- Nearby viewer count — edit the stat card value

In `staff.html`:
- KPI numbers (line count, revenue, served)
- `invData` array — the inventory starting values

---

## Phase 2: Making it truly live (backend integration)

To make data update automatically, you'll need a small backend. Recommended stack:

### POS Integration (Square or Toast)
Both have webhooks that fire when items are sold:
- Square: https://developer.squareup.com/docs/webhooks
- Toast: https://doc.toasttab.com/doc/devguide/apiWebhooks.html

When a webhook fires, update a simple database with new stock counts.

### Recommended backend: Supabase (free tier)
- https://supabase.com — free Postgres database + realtime subscriptions
- Create a `pastries` table: id, name, stock, max_stock, updated_at
- Create a `queue` table: position_count, updated_at
- Frontend polls every 30s OR uses Supabase realtime for instant updates

### Queue tracking
- Staff tap a button when someone joins the line (or scans QR)
- QR scan endpoint increments the queue count in Supabase
- Front page reads the count and calculates wait time

### GPS verification (for digital queue)
Use the browser Geolocation API:
```javascript
navigator.geolocation.getCurrentPosition(pos => {
  const dist = haversine(pos.coords, { lat: 37.7749, lng: -122.4194 }); // bakery coords
  if (dist < 200) enableQueueJoin();
});
```

### Push notifications
Use OneSignal (free tier): https://onesignal.com
- Users subscribe when they tap "Notify me if sold out"
- When stock hits 0 via webhook, trigger a OneSignal push to subscribers

---

## Presenting to Butter & Crumble

Lead with the customer problem: *"People arrive at 5am because they're scared. This eliminates the fear."*

Show the three-tab flow on your phone — Queue → Pastries → Simulator.
Then show the staff dashboard and the Insights tab.

Key numbers to cite:
- 8% attrition rate (customers who leave lines empty-handed never return)
- $56/day in lost kouign-amann revenue = $1,120/month recoverable
- 30–60 seconds saved per transaction by pre-informed customers

---

Built with pure HTML/CSS/JS. No frameworks needed to ship v1.
