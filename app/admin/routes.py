from fastapi import APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.vendor import Vendor
from app.models.offer import Offer
from app.models.category import Category
from app.models.slider import Slider
from app.models.user import User
from app.models.subscription import SubscriptionPlan
from app.models.transaction import OfferTransaction
from app.models.notification import Notification, UserNotification
from app.models.user import MobileDevice
from app.services.fcm import send_push_multicast
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])

def page(title: str, content: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Snatchit Admin — {title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f5; }}
    nav {{ background: #1a1a2e; color: white; padding: 16px 32px; display: flex; align-items: center; gap: 32px; }}
    nav a {{ color: #ccc; text-decoration: none; font-size: 14px; }}
    nav a:hover {{ color: white; }}
    nav .logo {{ font-size: 20px; font-weight: 700; color: white; margin-right: 16px; }}
    .container {{ max-width: 1100px; margin: 32px auto; padding: 0 24px; }}
    h1 {{ font-size: 24px; margin-bottom: 24px; color: #1a1a2e; }}
    h2 {{ font-size: 18px; margin-bottom: 16px; color: #333; }}
    .card {{ background: white; border-radius: 12px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th {{ text-align: left; padding: 10px 12px; background: #f0f0f0; color: #555; font-weight: 600; }}
    td {{ padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }}
    tr:last-child td {{ border-bottom: none; }}
    form {{ display: grid; gap: 14px; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .row3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }}
    label {{ font-size: 13px; color: #555; font-weight: 500; }}
    input, select, textarea {{ width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; margin-top: 4px; }}
    textarea {{ height: 80px; resize: vertical; }}
    .btn {{ background: #1a1a2e; color: white; border: none; padding: 11px 24px; border-radius: 8px; font-size: 14px; cursor: pointer; font-weight: 600; }}
    .btn:hover {{ background: #16213e; }}
    .btn-red {{ background: #e74c3c; }}
    .btn-sm {{ padding: 6px 14px; font-size: 12px; border-radius: 6px; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
    .stat {{ background: white; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }}
    .stat .num {{ font-size: 32px; font-weight: 700; color: #1a1a2e; }}
    .stat .lbl {{ font-size: 13px; color: #888; margin-top: 4px; }}
    .section-title {{ font-size: 13px; font-weight: 700; color: #1a1a2e; text-transform: uppercase; letter-spacing: 1px; padding: 8px 0 4px; border-bottom: 2px solid #f0f0f0; margin-bottom: 4px; }}
  </style>
</head>
<body>
  <nav>
    <span class="logo">Snatchit</span>
    <a href="/admin">Dashboard</a>
    <a href="/admin/vendors">Vendors</a>
    <a href="/admin/categories">Categories</a>
    <a href="/admin/offers">Offers</a>
    <a href="/admin/sliders">Sliders</a>
    <a href="/admin/subscriptions">Subscriptions</a>
    <a href="/admin/users">Users</a>
    <a href="/admin/redemptions">Redemptions</a>
    <a href="/admin/notifications">Notifications</a>
  </nav>
  <div class="container">
    <h1>{title}</h1>
    {content}
  </div>
</body>
</html>
"""

# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
def dashboard(db: Session = Depends(get_db)):
    from datetime import date

    # ── core counts ──────────────────────────────────────────────────────────
    total_users       = db.query(User).count()
    total_vendors     = db.query(Vendor).count()
    total_offers      = db.query(Offer).count()
    total_categories  = db.query(Category).count()
    total_redemptions = db.query(OfferTransaction).count()
    total_points      = db.query(func.sum(User.total_points)).scalar() or 0

    # ── top 5 redeemed offers ─────────────────────────────────────────────────
    top_offer_rows = (
        db.query(OfferTransaction.offer_id, func.count(OfferTransaction.id).label("cnt"))
        .group_by(OfferTransaction.offer_id)
        .order_by(func.count(OfferTransaction.id).desc())
        .limit(5).all()
    )
    max_offer_cnt = top_offer_rows[0].cnt if top_offer_rows else 1
    top_offers_html = ""
    for rank, row in enumerate(top_offer_rows, 1):
        offer = db.query(Offer).filter(Offer.id == row.offer_id).first()
        name  = offer.name if offer else f"Offer #{row.offer_id}"
        vendor_name = ""
        if offer:
            v = db.query(Vendor).filter(Vendor.id == offer.vendor_id).first()
            vendor_name = v.name if v else ""
        pct = int(row.cnt / max_offer_cnt * 100)
        medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][rank-1]
        top_offers_html += f"""
        <tr>
          <td style="width:28px;font-size:18px">{medal}</td>
          <td>
            <div style="font-weight:600;color:#1a1a2e">{name}</div>
            <div style="font-size:12px;color:#888">{vendor_name}</div>
            <div style="margin-top:5px;background:#f0f0f0;border-radius:99px;height:6px">
              <div style="width:{pct}%;background:linear-gradient(90deg,#f0932b,#e74c3c);border-radius:99px;height:6px"></div>
            </div>
          </td>
          <td style="text-align:right;font-weight:700;color:#f0932b;white-space:nowrap">{row.cnt} redemption{"s" if row.cnt!=1 else ""}</td>
        </tr>"""
    if not top_offers_html:
        top_offers_html = '<tr><td colspan="3" style="color:#aaa;text-align:center;padding:20px">No redemptions yet</td></tr>'

    # ── top 5 customers ───────────────────────────────────────────────────────
    top_user_rows = (
        db.query(OfferTransaction.user_id, func.count(OfferTransaction.id).label("cnt"))
        .group_by(OfferTransaction.user_id)
        .order_by(func.count(OfferTransaction.id).desc())
        .limit(5).all()
    )
    max_user_cnt = top_user_rows[0].cnt if top_user_rows else 1
    top_users_html = ""
    for rank, row in enumerate(top_user_rows, 1):
        u = db.query(User).filter(User.id == row.user_id).first()
        name  = f"{u.first_name or ''} {u.last_name or ''}".strip() if u else row.user_id
        email = u.email or u.phone_number or "" if u else ""
        pts   = u.total_points or 0 if u else 0
        pct   = int(row.cnt / max_user_cnt * 100)
        medal = ["🥇","🥈","🥉","4️⃣","5️⃣"][rank-1]
        top_users_html += f"""
        <tr>
          <td style="width:28px;font-size:18px">{medal}</td>
          <td>
            <div style="font-weight:600;color:#1a1a2e">{name}</div>
            <div style="font-size:12px;color:#888">{email}</div>
            <div style="margin-top:5px;background:#f0f0f0;border-radius:99px;height:6px">
              <div style="width:{pct}%;background:linear-gradient(90deg,#6c5ce7,#a29bfe);border-radius:99px;height:6px"></div>
            </div>
          </td>
          <td style="text-align:right;white-space:nowrap">
            <span style="font-weight:700;color:#6c5ce7">{row.cnt} uses</span><br>
            <span style="font-size:12px;color:#f0932b">⭐ {pts} pts</span>
          </td>
        </tr>"""
    if not top_users_html:
        top_users_html = '<tr><td colspan="3" style="color:#aaa;text-align:center;padding:20px">No activity yet</td></tr>'

    # ── birthdays today ───────────────────────────────────────────────────────
    today = date.today()
    all_users = db.query(User).all()
    bday_users = [
        u for u in all_users
        if u.birth_date and (
            (hasattr(u.birth_date, 'month') and u.birth_date.month == today.month and u.birth_date.day == today.day)
        )
    ]
    if bday_users:
        bday_html = "".join([f"""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #f5f5f5">
          <div style="font-size:28px">🎂</div>
          <div>
            <div style="font-weight:600;color:#1a1a2e">{(u.first_name or '')+' '+(u.last_name or '')}</div>
            <div style="font-size:12px;color:#888">{u.email or u.phone_number or ''}</div>
          </div>
          <div style="margin-left:auto;background:#fff0f8;color:#e84393;padding:4px 12px;border-radius:99px;font-size:12px;font-weight:600">🎉 Birthday!</div>
        </div>""" for u in bday_users])
    else:
        bday_html = '<div style="text-align:center;color:#aaa;padding:24px 0;font-size:14px">🎈 No birthdays today</div>'

    # ── top vendors by redemptions ────────────────────────────────────────────
    vendor_stats = (
        db.query(Vendor.id, Vendor.name, func.count(OfferTransaction.id).label("cnt"))
        .join(Offer, Offer.vendor_id == Vendor.id)
        .join(OfferTransaction, OfferTransaction.offer_id == Offer.id)
        .group_by(Vendor.id, Vendor.name)
        .order_by(func.count(OfferTransaction.id).desc())
        .limit(5).all()
    )
    max_v_cnt = vendor_stats[0].cnt if vendor_stats else 1
    vendor_html = ""
    colors = ["#00b894","#0984e3","#fdcb6e","#e17055","#a29bfe"]
    for rank, row in enumerate(vendor_stats, 1):
        pct = int(row.cnt / max_v_cnt * 100)
        offer_count = db.query(Offer).filter(Offer.vendor_id == row.id).count()
        vendor_html += f"""
        <tr>
          <td style="width:28px">
            <div style="width:28px;height:28px;border-radius:50%;background:{colors[(rank-1)%5]};color:white;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px">{rank}</div>
          </td>
          <td>
            <div style="font-weight:600;color:#1a1a2e">{row.name}</div>
            <div style="font-size:12px;color:#888">{offer_count} offer{"s" if offer_count!=1 else ""}</div>
            <div style="margin-top:5px;background:#f0f0f0;border-radius:99px;height:6px">
              <div style="width:{pct}%;background:{colors[(rank-1)%5]};border-radius:99px;height:6px"></div>
            </div>
          </td>
          <td style="text-align:right;font-weight:700;color:{colors[(rank-1)%5]};white-space:nowrap">{row.cnt} redemption{"s" if row.cnt!=1 else ""}</td>
        </tr>"""
    if not vendor_html:
        vendor_html = '<tr><td colspan="3" style="color:#aaa;text-align:center;padding:20px">No data yet</td></tr>'

    today_str = today.strftime("%A, %B %d %Y")

    content = f"""
    <div style="font-size:13px;color:#888;margin-bottom:20px;margin-top:-8px">📅 {today_str}</div>

    <!-- ── KPI bar ── -->
    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-bottom:28px">
      <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(26,26,46,.25)">
        <div style="font-size:30px;font-weight:800">{total_users}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Users</div>
      </div>
      <div style="background:linear-gradient(135deg,#0984e3,#74b9ff);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(9,132,227,.25)">
        <div style="font-size:30px;font-weight:800">{total_vendors}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Vendors</div>
      </div>
      <div style="background:linear-gradient(135deg,#6c5ce7,#a29bfe);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(108,92,231,.25)">
        <div style="font-size:30px;font-weight:800">{total_offers}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Offers</div>
      </div>
      <div style="background:linear-gradient(135deg,#00b894,#55efc4);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(0,184,148,.25)">
        <div style="font-size:30px;font-weight:800">{total_categories}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Categories</div>
      </div>
      <div style="background:linear-gradient(135deg,#f0932b,#fdcb6e);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(240,147,43,.25)">
        <div style="font-size:30px;font-weight:800">{total_redemptions}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Redemptions</div>
      </div>
      <div style="background:linear-gradient(135deg,#e84393,#fd79a8);color:white;border-radius:14px;padding:20px;text-align:center;box-shadow:0 4px 12px rgba(232,67,147,.25)">
        <div style="font-size:30px;font-weight:800">{total_points:,}</div>
        <div style="font-size:11px;opacity:.7;margin-top:4px;text-transform:uppercase;letter-spacing:1px">Points Issued</div>
      </div>
    </div>

    <!-- ── Quick Actions ── -->
    <div style="background:white;border-radius:14px;padding:20px 24px;margin-bottom:28px;box-shadow:0 1px 4px rgba(0,0,0,.08);display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <span style="font-weight:700;color:#1a1a2e;font-size:14px;margin-right:8px">Quick Actions:</span>
      <a href="/admin/vendors/new"><button class="btn" style="background:#0984e3">+ Vendor</button></a>
      <a href="/admin/offers/new"><button class="btn" style="background:#6c5ce7">+ Offer</button></a>
      <a href="/admin/categories/new"><button class="btn" style="background:#00b894">+ Category</button></a>
      <a href="/admin/sliders/new"><button class="btn" style="background:#f0932b">+ Slider</button></a>
      <a href="/admin/notifications"><button class="btn" style="background:#e84393">📣 Send Notification</button></a>
    </div>

    <!-- ── Row 1: Top Offers | Top Customers ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px">

      <div style="background:white;border-radius:14px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
          <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#f0932b,#e74c3c);display:flex;align-items:center;justify-content:center;font-size:18px">🔥</div>
          <div>
            <div style="font-weight:700;font-size:15px;color:#1a1a2e">Most Redeemed Offers</div>
            <div style="font-size:12px;color:#aaa">All time top performers</div>
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse">
          {top_offers_html}
        </table>
      </div>

      <div style="background:white;border-radius:14px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
          <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#6c5ce7,#a29bfe);display:flex;align-items:center;justify-content:center;font-size:18px">👑</div>
          <div>
            <div style="font-weight:700;font-size:15px;color:#1a1a2e">Top Customers</div>
            <div style="font-size:12px;color:#aaa">Most active users</div>
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse">
          {top_users_html}
        </table>
      </div>

    </div>

    <!-- ── Row 2: Birthdays Today | Top Vendors ── -->
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">

      <div style="background:white;border-radius:14px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
          <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#e84393,#fd79a8);display:flex;align-items:center;justify-content:center;font-size:18px">🎂</div>
          <div>
            <div style="font-weight:700;font-size:15px;color:#1a1a2e">Birthdays Today</div>
            <div style="font-size:12px;color:#aaa">{today.strftime("%B %d")}</div>
          </div>
          {"<div style='margin-left:auto;background:#fff0f8;color:#e84393;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:700'>"+str(len(bday_users))+" today</div>" if bday_users else ""}
        </div>
        {bday_html}
      </div>

      <div style="background:white;border-radius:14px;padding:24px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px">
          <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#00b894,#55efc4);display:flex;align-items:center;justify-content:center;font-size:18px">🏪</div>
          <div>
            <div style="font-weight:700;font-size:15px;color:#1a1a2e">Top Vendors</div>
            <div style="font-size:12px;color:#aaa">By offer redemptions</div>
          </div>
        </div>
        <table style="width:100%;border-collapse:collapse">
          {vendor_html}
        </table>
      </div>

    </div>
    """
    return HTMLResponse(page("Dashboard", content))

# ─── Categories ───────────────────────────────────────────────────────────────

@router.get("/categories", response_class=HTMLResponse)
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    rows = "".join([f"<tr><td>{c.id}</td><td>{c.name}</td><td>{len(c.vendors)} vendors</td><td><a href='/admin/categories/{c.id}/edit'><button class='btn btn-sm' style='margin-right:4px'>Edit</button></a><a href='/admin/categories/{c.id}/delete'><button class='btn btn-red btn-sm'>Delete</button></a></td></tr>" for c in cats])
    content = f"""
    <a href="/admin/categories/new"><button class="btn" style="margin-bottom:16px">+ Add Category</button></a>
    <div class="card">
      <table><tr><th>ID</th><th>Name</th><th>Vendors</th><th>Action</th></tr>{rows}</table>
    </div>"""
    return HTMLResponse(page("Categories", content))

@router.get("/categories/new", response_class=HTMLResponse)
def new_category_form():
    content = """
    <div class="card">
      <form method="post" action="/admin/categories/new" enctype="multipart/form-data">
        <label>Name<input name="name" required placeholder="e.g. Restaurants"/></label>

        <div class="section-title" style="margin-top:16px">Category Icon</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>200 × 200 px</strong> — Square PNG with transparent background works best.
        </p>
        <div class="row">
          <label>Upload Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_cat')"/></label>
          <label>— OR — Image URL<input name="image_url" placeholder="https://..."/></label>
        </div>
        <img id="preview_cat" style="max-height:100px;margin:8px 0;display:none;border-radius:8px"/>

        <button class="btn" type="submit" style="margin-top:8px">Save Category</button>
      </form>
    </div>
    <script>
    function previewImg(input, previewId) {
      const preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }
    }
    </script>"""
    return HTMLResponse(page("New Category", content))

@router.post("/categories/new")
async def create_category(request: Request, name: str = Form(...), image_url: str = Form(""), db: Session = Depends(get_db)):
    import shutil, uuid
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    c = Category(name=name, image=final_image)
    db.add(c)
    db.commit()
    return RedirectResponse("/admin/categories", status_code=302)

@router.get("/categories/{id}/edit", response_class=HTMLResponse)
def edit_category_form(id: int, db: Session = Depends(get_db)):
    c = db.query(Category).filter(Category.id == id).first()
    if not c:
        return HTMLResponse("Not found", status_code=404)
    content = f"""
    <div class="card">
      <form method="post" action="/admin/categories/{c.id}/edit" enctype="multipart/form-data">
        <label>Name<input name="name" required value="{c.name or ''}"/></label>

        <div class="section-title" style="margin-top:16px">Category Icon</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>200 × 200 px</strong> — Square PNG with transparent background works best.
        </p>
        {"<img src='" + c.image + "' style='max-height:100px;margin:8px 0;border-radius:8px' onerror=\"this.style.display='none'\"/>" if c.image else ""}
        <div class="row">
          <label>Upload New Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_cat')"/></label>
          <label>— OR — Image URL<input name="image_url" value="{c.image or ''}"/></label>
        </div>
        <img id="preview_cat" style="max-height:100px;margin:8px 0;display:none;border-radius:8px"/>

        <button class="btn" type="submit" style="margin-top:8px">Save Changes</button>
      </form>
    </div>
    <script>
    function previewImg(input, previewId) {{
      const preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }}
    }}
    </script>"""
    return HTMLResponse(page(f"Edit Category #{id}", content))

@router.post("/categories/{id}/edit")
async def update_category(id: int, request: Request, name: str = Form(...), image_url: str = Form(""), db: Session = Depends(get_db)):
    import shutil, uuid
    c = db.query(Category).filter(Category.id == id).first()
    if not c:
        return HTMLResponse("Not found", status_code=404)
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    c.name = name
    c.image = final_image
    db.commit()
    return RedirectResponse("/admin/categories", status_code=302)

@router.get("/categories/{id}/delete")
def delete_category(id: int, db: Session = Depends(get_db)):
    c = db.query(Category).filter(Category.id == id).first()
    if c:
        db.delete(c)
        db.commit()
    return RedirectResponse("/admin/categories", status_code=302)

# ─── Vendors ──────────────────────────────────────────────────────────────────

@router.get("/vendors", response_class=HTMLResponse)
def list_vendors(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).all()
    rows = "".join([f"<tr><td>{v.id}</td><td>{v.name}</td><td>{len(v.offers)} offers</td><td>{v.phone or ''}</td><td>{'Yes' if v.is_active else 'No'}</td><td>{'Top' if v.is_top else ''}</td><td><a href='/admin/vendors/{v.id}/edit'><button class='btn btn-sm' style='margin-right:4px'>Edit</button></a><a href='/admin/vendors/{v.id}/delete'><button class='btn btn-red btn-sm'>Delete</button></a></td></tr>" for v in vendors])
    content = f"""
    <a href="/admin/vendors/new"><button class="btn" style="margin-bottom:16px">+ Add Vendor</button></a>
    <div class="card">
      <table><tr><th>ID</th><th>Name</th><th>Offers</th><th>Phone</th><th>Status</th><th>Top</th><th>Action</th></tr>{rows}</table>
    </div>"""
    return HTMLResponse(page("Vendors", content))

@router.get("/vendors/new", response_class=HTMLResponse)
def new_vendor_form(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    cat_options = "".join([f"<option value='{c.id}'>{c.name}</option>" for c in cats])
    content = f"""
    <div class="card">
      <form method="post" action="/admin/vendors/new" enctype="multipart/form-data">
        <div class="section-title">Basic Info</div>
        <div class="row">
          <label>Vendor Name *<input name="name" required/></label>
          <label>Phone<input name="phone" placeholder="+61..."/></label>
        </div>
        <label>Description<textarea name="description"></textarea></label>

        <div class="section-title" style="margin-top:8px">Logo / Profile Image</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>400 × 400 px</strong> — Square PNG or JPG. Displayed as a round icon in the app.
        </p>
        <div class="row">
          <label>Upload Logo<input name="profile_image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_profile')"/></label>
          <label>— OR — Logo URL<input name="profile_image_url" placeholder="https://..."/></label>
        </div>
        <img id="preview_profile" style="max-height:100px;margin:8px 0;display:none;border-radius:50%"/>

        <div class="section-title" style="margin-top:8px">Banner Image</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>1170 × 390 px</strong> — Wide landscape JPG (3:1 ratio). Shown as a full-width header in the vendor page.
        </p>
        <div class="row">
          <label>Upload Banner<input name="banner_image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_banner')"/></label>
          <label>— OR — Banner URL<input name="banner_image_url" placeholder="https://..."/></label>
        </div>
        <img id="preview_banner" style="max-height:120px;margin:8px 0;display:none;border-radius:8px;width:100%;object-fit:cover"/>

        <div class="section-title" style="margin-top:8px">Location</div>
        <div class="row">
          <label>Latitude<input name="lat" placeholder="e.g. -33.8688"/></label>
          <label>Longitude<input name="lon" placeholder="e.g. 151.2093"/></label>
        </div>

        <div class="section-title" style="margin-top:8px">Settings</div>
        <div class="row3">
          <label>QR Code<input name="qr_code" placeholder="Unique code for scanning"/></label>
          <label>Category<select name="category_id"><option value="">None</option>{cat_options}</select></label>
          <label>Is Top Vendor?<select name="is_top"><option value="0">No</option><option value="1">Yes</option></select></label>
        </div>
        <div class="row">
          <label>Is POS Vendor? (for points redemption)<select name="is_pos"><option value="0">No</option><option value="1">Yes</option></select></label>
          <label>Is Active?<select name="is_active"><option value="1">Yes</option><option value="0">No</option></select></label>
        </div>
        <button class="btn" type="submit">Save Vendor</button>
      </form>
    </div>
    <script>
    function previewImg(input, previewId) {{
      const preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }}
    }}
    </script>"""
    return HTMLResponse(page("New Vendor", content))

@router.post("/vendors/new")
async def create_vendor(
    request: Request,
    name: str = Form(...), phone: str = Form(""), description: str = Form(""),
    profile_image_url: str = Form(""), banner_image_url: str = Form(""),
    lat: str = Form(""), lon: str = Form(""), qr_code: str = Form(""),
    category_id: str = Form(""), is_top: str = Form("0"), is_pos: str = Form("0"),
    is_active: str = Form("1"), db: Session = Depends(get_db)
):
    import shutil, uuid
    form = await request.form()

    def save_upload(field_name, fallback_url):
        f = form.get(field_name)
        if f and hasattr(f, "filename") and f.filename:
            ext = f.filename.rsplit(".", 1)[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = f"static/uploads/{filename}"
            with open(filepath, "wb") as out:
                shutil.copyfileobj(f.file, out)
            return f"/static/uploads/{filename}"
        return fallback_url

    profile_image = save_upload("profile_image_file", profile_image_url)
    banner_image = save_upload("banner_image_file", banner_image_url)

    v = Vendor(
        name=name, phone=phone, description=description,
        profile_image=profile_image, banner_image=banner_image,
        lat=lat, lon=lon, qr_code=qr_code or None,
        category_id=int(category_id) if category_id else None,
        is_top=is_top == "1", is_pos=is_pos == "1",
        is_active=is_active == "1"
    )
    db.add(v)
    db.commit()
    return RedirectResponse("/admin/vendors", status_code=302)

@router.get("/vendors/{id}/edit", response_class=HTMLResponse)
def edit_vendor_form(id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        return HTMLResponse("Not found", status_code=404)
    cats = db.query(Category).all()
    cat_options = "".join([f"<option value='{c.id}' {'selected' if c.id == v.category_id else ''}>{c.name}</option>" for c in cats])
    content = f"""
    <div class="card">
      <form method="post" action="/admin/vendors/{v.id}/edit" enctype="multipart/form-data">
        <div class="section-title">Basic Info</div>
        <div class="row">
          <label>Vendor Name *<input name="name" required value="{v.name or ''}"/></label>
          <label>Phone<input name="phone" value="{v.phone or ''}"/></label>
        </div>
        <label>Description<textarea name="description">{v.description or ''}</textarea></label>

        <div class="section-title" style="margin-top:8px">Logo / Profile Image</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>400 × 400 px</strong> — Square PNG or JPG. Displayed as a round icon in the app.
        </p>
        {"<img src='" + v.profile_image + "' style='max-height:100px;margin:8px 0;border-radius:50%' onerror=\"this.style.display='none'\"/>" if v.profile_image else ""}
        <div class="row">
          <label>Upload New Logo<input name="profile_image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_profile')"/></label>
          <label>— OR — Logo URL<input name="profile_image_url" value="{v.profile_image or ''}"/></label>
        </div>
        <img id="preview_profile" style="max-height:100px;margin:8px 0;display:none;border-radius:50%"/>

        <div class="section-title" style="margin-top:8px">Banner Image</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>1170 × 390 px</strong> — Wide landscape JPG (3:1 ratio). Shown as a full-width header in the vendor page.
        </p>
        {"<img src='" + v.banner_image + "' style='max-height:120px;margin:8px 0;border-radius:8px;width:100%;object-fit:cover' onerror=\"this.style.display='none'\"/>" if v.banner_image else ""}
        <div class="row">
          <label>Upload New Banner<input name="banner_image_file" type="file" accept="image/*" onchange="previewImg(this,'preview_banner')"/></label>
          <label>— OR — Banner URL<input name="banner_image_url" value="{v.banner_image or ''}"/></label>
        </div>
        <img id="preview_banner" style="max-height:120px;margin:8px 0;display:none;border-radius:8px;width:100%;object-fit:cover"/>

        <div class="section-title" style="margin-top:8px">Location</div>
        <div class="row">
          <label>Latitude<input name="lat" value="{v.lat or ''}"/></label>
          <label>Longitude<input name="lon" value="{v.lon or ''}"/></label>
        </div>

        <div class="section-title" style="margin-top:8px">Settings</div>
        <div class="row3">
          <label>QR Code<input name="qr_code" value="{v.qr_code or ''}"/></label>
          <label>Category<select name="category_id"><option value="">None</option>{cat_options}</select></label>
          <label>Is Top Vendor?<select name="is_top">
            <option value="0" {"selected" if not v.is_top else ""}>No</option>
            <option value="1" {"selected" if v.is_top else ""}>Yes</option>
          </select></label>
        </div>
        <div class="row">
          <label>Is POS Vendor?<select name="is_pos">
            <option value="0" {"selected" if not v.is_pos else ""}>No</option>
            <option value="1" {"selected" if v.is_pos else ""}>Yes</option>
          </select></label>
          <label>Is Active?<select name="is_active">
            <option value="1" {"selected" if v.is_active else ""}>Yes</option>
            <option value="0" {"selected" if not v.is_active else ""}>No</option>
          </select></label>
        </div>
        <button class="btn" type="submit">Save Changes</button>
      </form>
    </div>
    <script>
    function previewImg(input, previewId) {{
      const preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }}
    }}
    </script>"""
    return HTMLResponse(page(f"Edit Vendor #{id}", content))

@router.post("/vendors/{id}/edit")
async def update_vendor(
    id: int, request: Request,
    name: str = Form(...), phone: str = Form(""), description: str = Form(""),
    profile_image_url: str = Form(""), banner_image_url: str = Form(""),
    lat: str = Form(""), lon: str = Form(""), qr_code: str = Form(""),
    category_id: str = Form(""), is_top: str = Form("0"), is_pos: str = Form("0"),
    is_active: str = Form("1"), db: Session = Depends(get_db)
):
    import shutil, uuid
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if not v:
        return HTMLResponse("Not found", status_code=404)
    form = await request.form()

    def save_upload(field_name, fallback_url):
        f = form.get(field_name)
        if f and hasattr(f, "filename") and f.filename:
            ext = f.filename.rsplit(".", 1)[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = f"static/uploads/{filename}"
            with open(filepath, "wb") as out:
                shutil.copyfileobj(f.file, out)
            return f"/static/uploads/{filename}"
        return fallback_url

    v.name = name
    v.phone = phone
    v.description = description
    v.profile_image = save_upload("profile_image_file", profile_image_url)
    v.banner_image = save_upload("banner_image_file", banner_image_url)
    v.lat = lat
    v.lon = lon
    v.qr_code = qr_code or None
    v.category_id = int(category_id) if category_id else None
    v.is_top = is_top == "1"
    v.is_pos = is_pos == "1"
    v.is_active = is_active == "1"
    db.commit()
    return RedirectResponse("/admin/vendors", status_code=302)

@router.get("/vendors/{id}/delete")
def delete_vendor(id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == id).first()
    if v:
        db.delete(v)
        db.commit()
    return RedirectResponse("/admin/vendors", status_code=302)

# ─── Offers ───────────────────────────────────────────────────────────────────

@router.get("/offers", response_class=HTMLResponse)
def list_offers(db: Session = Depends(get_db)):
    offers = db.query(Offer).all()
    rows = "".join([f"<tr><td>{o.id}</td><td>{o.name}</td><td>{o.vendor_id}</td><td>{o.discount}%</td><td>{o.promo_code or '-'}</td><td>{'Flash' if o.is_flash else 'Promo' if o.is_promo else 'General'}</td><td style='text-align:center'>{o.orders or 0}</td><td>{'Top' if o.is_top else ''}</td><td><a href='/admin/offers/{o.id}/edit'><button class='btn btn-sm' style='margin-right:4px'>Edit</button></a><a href='/admin/offers/{o.id}/delete'><button class='btn btn-red btn-sm'>Delete</button></a></td></tr>" for o in offers])
    content = f"""
    <a href="/admin/offers/new"><button class="btn" style="margin-bottom:16px">+ Add Offer</button></a>
    <div class="card">
      <table><tr><th>ID</th><th>Name</th><th>Vendor</th><th>Discount</th><th>Promo Code</th><th>Type</th><th>Order</th><th>Top</th><th>Action</th></tr>{rows}</table>
    </div>"""
    return HTMLResponse(page("Offers", content))

@router.get("/offers/new", response_class=HTMLResponse)
def new_offer_form(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    vendor_options = "".join([f"<option value='{v.id}'>{v.name}</option>" for v in vendors])
    content = f"""
    <div class="card">
      <form method="post" action="/admin/offers/new" enctype="multipart/form-data">
        <div class="section-title">Offer Type</div>
        <label>Select Type *
          <select name="offer_kind" id="offer_kind" onchange="showSection(this.value)" required>
            <option value="">-- Select --</option>
            <option value="general">General</option>
            <option value="flash">Flash</option>
            <option value="promo">Promo Code</option>
          </select>
        </label>

        <div id="shared_fields" style="display:none">
          <div class="section-title" style="margin-top:20px">Basic Info</div>
          <div class="row">
            <label>Name *<input name="name" required/></label>
            <label>Vendor *<select name="vendor_id">{vendor_options}</select></label>
          </div>
          <label>Description<textarea name="description"></textarea></label>
          <div class="section-title" style="margin-top:12px">Offer Image <span style="font-size:11px;color:#888;font-weight:400">(shown beside the offer in listings)</span></div>
          <div class="row">
            <label>Upload Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this,'prev_img')"/></label>
            <label>— or — Image URL<input name="image" placeholder="https://..."/></label>
          </div>
          <img id="prev_img" style="max-height:80px;margin:4px 0;display:none;border-radius:8px"/>
          <div class="section-title" style="margin-top:12px">Top Offer Banner <span style="font-size:11px;color:#888;font-weight:400">(used when offer is marked as Top Offer)</span></div>
          <div class="row">
            <label>Upload Top Banner<input name="top_image_file" type="file" accept="image/*" onchange="previewImg(this,'prev_top')"/></label>
            <label>— or — Top Banner URL<input name="top_image" placeholder="https://..."/></label>
          </div>
          <img id="prev_top" style="max-height:80px;margin:4px 0;display:none;border-radius:8px"/>
          <div class="row3">
            <label>Discount %<input name="discount" type="number" value="0"/></label>
            <label>Save Up To<input name="save_up_to" type="number" step="0.01" value="0"/></label>
            <label>Currency<input name="save_up_to_currency" value="AUD"/></label>
          </div>
          <div class="row3">
            <label>Points Earned<input name="points" type="number" value="0"/></label>
            <label>Display Order<input name="orders" type="number" value="0" title="Lower number = shown first"/></label>
            <label>Required Tier<select name="required_tier">
              <option value="free">Free</option>
              <option value="premium">Premium</option>
            </select></label>
          </div>
          <div class="row">
            <label>Top Offer?<select name="is_top"><option value="0">No</option><option value="1">Yes</option></select></label>
            <label>Status<select name="status"><option value="approved">Approved</option><option value="pending">Pending</option></select></label>
          </div>
        </div>

        <div id="section_general" style="display:none">
          <div class="section-title" style="margin-top:20px">General Settings</div>
          <label>Renew Duration (days)<input name="renew_duration" type="number" value="7"/></label>
          <div class="section-title" style="margin-top:16px">Availability (Australian Sydney Time)</div>
          <div style="display:flex;gap:12px;margin:8px 0 16px">
            <button type="button" id="btn_allday" onclick="setAvailability('allday')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid #f08220;background:#f08220;color:white;font-weight:700;cursor:pointer">
              All Day
            </button>
            <button type="button" id="btn_partial" onclick="setAvailability('partial')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid #ddd;background:white;color:#555;font-weight:700;cursor:pointer">
              Partial Hours
            </button>
          </div>
          <input type="hidden" name="availability_type" id="availability_type" value="allday"/>
          <div id="time_window_fields" style="display:none">
            <div class="row">
              <label>Active From<input name="active_from" type="time" id="active_from_input"/></label>
              <label>Active Until<input name="active_until" type="time" id="active_until_input"/></label>
            </div>
            <div style="font-size:12px;color:#888;margin-top:-8px;margin-bottom:12px">Crosses midnight is supported — e.g. 18:00 to 02:00 = 6 PM until 2 AM</div>
          </div>
        </div>

        <div id="section_flash" style="display:none">
          <div class="section-title" style="margin-top:20px">Flash Settings</div>
          <div class="row">
            <label>Flash Start<input name="flash_start" type="datetime-local"/></label>
            <label>Flash End<input name="flash_end" type="datetime-local"/></label>
          </div>
          <div class="section-title" style="margin-top:16px">Availability (Australian Sydney Time)</div>
          <div style="display:flex;gap:12px;margin:8px 0 16px">
            <button type="button" id="btn_allday_f" onclick="setAvailability('allday','f')" style="flex:1;padding:10px;border-radius:8px;border:2px solid #f08220;background:#f08220;color:white;font-weight:700;cursor:pointer">All Day</button>
            <button type="button" id="btn_partial_f" onclick="setAvailability('partial','f')" style="flex:1;padding:10px;border-radius:8px;border:2px solid #ddd;background:white;color:#555;font-weight:700;cursor:pointer">Partial Hours</button>
          </div>
          <div id="time_window_fields_f" style="display:none">
            <div class="row">
              <label>Active From<input name="active_from_f" type="time" id="active_from_input_f"/></label>
              <label>Active Until<input name="active_until_f" type="time" id="active_until_input_f"/></label>
            </div>
            <div style="font-size:12px;color:#888;margin-top:-8px;margin-bottom:12px">e.g. 18:00 to 02:00 = 6 PM until 2 AM</div>
          </div>
        </div>

        <div id="section_promo" style="display:none">
          <div class="section-title" style="margin-top:20px">Promo Settings</div>
          <div class="row">
            <label>Promo Code *<input name="promo_code" placeholder="e.g. SAVE20"/></label>
            <label>Promo Expiry<input name="promo_expiry_date" type="date"/></label>
          </div>
          <div class="section-title" style="margin-top:16px">Availability (Australian Sydney Time)</div>
          <div style="display:flex;gap:12px;margin:8px 0 16px">
            <button type="button" id="btn_allday_p" onclick="setAvailability('allday','p')" style="flex:1;padding:10px;border-radius:8px;border:2px solid #f08220;background:#f08220;color:white;font-weight:700;cursor:pointer">All Day</button>
            <button type="button" id="btn_partial_p" onclick="setAvailability('partial','p')" style="flex:1;padding:10px;border-radius:8px;border:2px solid #ddd;background:white;color:#555;font-weight:700;cursor:pointer">Partial Hours</button>
          </div>
          <div id="time_window_fields_p" style="display:none">
            <div class="row">
              <label>Active From<input name="active_from_p" type="time" id="active_from_input_p"/></label>
              <label>Active Until<input name="active_until_p" type="time" id="active_until_input_p"/></label>
            </div>
            <div style="font-size:12px;color:#888;margin-top:-8px;margin-bottom:12px">e.g. 18:00 to 02:00 = 6 PM until 2 AM</div>
          </div>
        </div>

        <input type="hidden" name="is_flash" id="is_flash" value="0"/>
        <input type="hidden" name="is_promo" id="is_promo" value="0"/>
        <button class="btn" type="submit" id="submit_btn" style="margin-top:20px;display:none">Save Offer</button>
      </form>
    </div>
    <script>
    function showSection(type) {{
      document.getElementById("shared_fields").style.display = type ? "block" : "none";
      document.getElementById("section_general").style.display = type === "general" ? "block" : "none";
      document.getElementById("section_flash").style.display = type === "flash" ? "block" : "none";
      document.getElementById("section_promo").style.display = type === "promo" ? "block" : "none";
      document.getElementById("submit_btn").style.display = type ? "block" : "none";
      document.getElementById("is_flash").value = type === "flash" ? "1" : "0";
      document.getElementById("is_promo").value = type === "promo" ? "1" : "0";
    }}
    function previewImg(input, previewId) {{
      var preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        var reader = new FileReader();
        reader.onload = function(e) {{ preview.src = e.target.result; preview.style.display = 'block'; }};
        reader.readAsDataURL(input.files[0]);
      }} else {{ preview.style.display = 'none'; }}
    }}
    function setAvailability(type, suffix) {{
      suffix = suffix || "";
      const sfx = suffix ? "_" + suffix : "";
      const isPartial = type === "partial";
      document.getElementById("time_window_fields" + sfx).style.display = isPartial ? "block" : "none";
      if (document.getElementById("availability_type" + sfx))
        document.getElementById("availability_type" + sfx).value = type;
      document.getElementById("btn_allday" + sfx).style.background = isPartial ? "white" : "#f08220";
      document.getElementById("btn_allday" + sfx).style.color = isPartial ? "#555" : "white";
      document.getElementById("btn_allday" + sfx).style.borderColor = isPartial ? "#ddd" : "#f08220";
      document.getElementById("btn_partial" + sfx).style.background = isPartial ? "#f08220" : "white";
      document.getElementById("btn_partial" + sfx).style.color = isPartial ? "white" : "#555";
      document.getElementById("btn_partial" + sfx).style.borderColor = isPartial ? "#f08220" : "#ddd";
      if (!isPartial) {{
        document.getElementById("active_from_input" + sfx).value = "";
        document.getElementById("active_until_input" + sfx).value = "";
      }}
    }}
    </script>"""
    return HTMLResponse(page("New Offer", content))

@router.post("/offers/new")
async def create_offer(request: Request, db: Session = Depends(get_db)):
    import shutil, uuid as _uuid
    from app.core.config import settings
    form = await request.form()

    def _save_upload(field_name):
        f = form.get(field_name)
        if f and hasattr(f, "filename") and f.filename:
            ext = f.filename.rsplit(".", 1)[-1]
            fname = f"{_uuid.uuid4()}.{ext}"
            with open(f"static/uploads/{fname}", "wb") as out:
                shutil.copyfileobj(f.file, out)
            return f"{settings.BASE_URL}/static/uploads/{fname}"
        return None

    name               = form.get("name", "")
    vendor_id          = int(form.get("vendor_id", 0))
    description        = form.get("description", "")
    image              = _save_upload("image_file") or form.get("image", "") or None
    top_image          = _save_upload("top_image_file") or form.get("top_image", "") or None
    discount           = int(form.get("discount", 0))
    save_up_to         = float(form.get("save_up_to", 0))
    save_up_to_currency= form.get("save_up_to_currency", "AUD")
    promo_code         = form.get("promo_code", "") or None
    points             = int(form.get("points", 0))
    orders             = int(form.get("orders", 0))
    flash_start        = form.get("flash_start", "")
    flash_end          = form.get("flash_end", "")
    promo_expiry_date  = form.get("promo_expiry_date", "")
    is_flash           = form.get("is_flash", "0")
    is_promo           = form.get("is_promo", "0")
    required_tier      = form.get("required_tier", "free")
    is_top             = form.get("is_top", "0")
    status             = form.get("status", "approved")
    renew_duration     = int(form.get("renew_duration", 0))
    active_from        = form.get("active_from", "")
    active_until       = form.get("active_until", "")
    active_from_f      = form.get("active_from_f", "")
    active_until_f     = form.get("active_until_f", "")
    active_from_p      = form.get("active_from_p", "")
    active_until_p     = form.get("active_until_p", "")
    offer_kind         = form.get("offer_kind", "general")

    def parse_dt(s):
        try: return datetime.strptime(s, "%Y-%m-%dT%H:%M") if s else None
        except: return None
    def parse_date(s):
        try: return datetime.strptime(s, "%Y-%m-%d") if s else None
        except: return None

    if is_flash == "1":
        final_active_from, final_active_until = active_from_f or None, active_until_f or None
    elif is_promo == "1":
        final_active_from, final_active_until = active_from_p or None, active_until_p or None
    else:
        final_active_from, final_active_until = active_from or None, active_until or None

    o = Offer(
        name=name, vendor_id=vendor_id, description=description,
        image=image, top_image=top_image, discount=discount,
        save_up_to=save_up_to, save_up_to_currency=save_up_to_currency,
        promo_code=promo_code, points=points, orders=orders,
        is_flash=is_flash=="1", is_promo=is_promo=="1",
        flash_start=parse_dt(flash_start), flash_end=parse_dt(flash_end),
        promo_expiry=parse_date(promo_expiry_date),
        required_tier=required_tier,
        level_priority=1 if required_tier == "premium" else 0,
        is_top=is_top=="1",
        status=status, renew_duration=renew_duration if offer_kind=="general" else None,
        active_from=final_active_from, active_until=final_active_until
    )
    db.add(o)
    db.commit()
    return RedirectResponse("/admin/offers", status_code=302)


@router.get("/offers/{id}/edit", response_class=HTMLResponse)
def edit_offer_form(id: int, db: Session = Depends(get_db)):
    o = db.query(Offer).filter(Offer.id == id).first()
    if not o:
        return HTMLResponse("Not found", status_code=404)
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    vendor_options = "".join([f"<option value='{v.id}' {'selected' if v.id == o.vendor_id else ''}>{v.name}</option>" for v in vendors])
    offer_kind = "flash" if o.is_flash else "promo" if o.is_promo else "general"
    flash_start = o.flash_start.strftime("%Y-%m-%dT%H:%M") if o.flash_start else ""
    flash_end = o.flash_end.strftime("%Y-%m-%dT%H:%M") if o.flash_end else ""
    promo_expiry = o.promo_expiry.strftime("%Y-%m-%d") if o.promo_expiry else ""
    content = f"""
    <div class="card">
      <form method="post" action="/admin/offers/{o.id}/edit" enctype="multipart/form-data">
        <div class="section-title">Offer Type</div>
        <label>Type *
          <select name="offer_kind" id="offer_kind" onchange="showSection(this.value)" required>
            <option value="general" {"selected" if offer_kind=="general" else ""}>General</option>
            <option value="flash" {"selected" if offer_kind=="flash" else ""}>Flash</option>
            <option value="promo" {"selected" if offer_kind=="promo" else ""}>Promo Code</option>
          </select>
        </label>

        <div id="shared_fields">
          <div class="section-title" style="margin-top:20px">Basic Info</div>
          <div class="row">
            <label>Name *<input name="name" required value="{o.name or ""}"/></label>
            <label>Vendor *<select name="vendor_id">{vendor_options}</select></label>
          </div>
          <label>Description<textarea name="description">{o.description or ""}</textarea></label>
          <div class="section-title" style="margin-top:12px">Offer Image <span style="font-size:11px;color:#888;font-weight:400">(shown beside the offer in listings)</span></div>
          {"<img src='" + o.image + "' style='max-height:60px;border-radius:6px;margin:4px 0'/>" if o.image else ""}
          <div class="row">
            <label>Upload New Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this,'prev_img_e')"/></label>
            <label>— or — Image URL<input name="image" value="{o.image or ""}" placeholder="https://..."/></label>
          </div>
          <img id="prev_img_e" style="max-height:80px;margin:4px 0;display:none;border-radius:8px"/>
          <div class="section-title" style="margin-top:12px">Top Offer Banner <span style="font-size:11px;color:#888;font-weight:400">(used when offer is marked as Top Offer)</span></div>
          {"<img src='" + o.top_image + "' style='max-height:60px;border-radius:6px;margin:4px 0'/>" if o.top_image else ""}
          <div class="row">
            <label>Upload New Top Banner<input name="top_image_file" type="file" accept="image/*" onchange="previewImg(this,'prev_top_e')"/></label>
            <label>— or — Top Banner URL<input name="top_image" value="{o.top_image or ""}" placeholder="https://..."/></label>
          </div>
          <img id="prev_top_e" style="max-height:80px;margin:4px 0;display:none;border-radius:8px"/>
          <div class="row3">
            <label>Discount %<input name="discount" type="number" value="{o.discount or 0}"/></label>
            <label>Save Up To<input name="save_up_to" type="number" step="0.01" value="{o.save_up_to or 0}"/></label>
            <label>Currency<input name="save_up_to_currency" value="{o.save_up_to_currency or "AUD"}"/></label>
          </div>
          <div class="row3">
            <label>Points<input name="points" type="number" value="{o.points or 0}"/></label>
            <label>Display Order<input name="orders" type="number" value="{o.orders or 0}" title="Lower number = shown first"/></label>
            <label>Required Tier<select name="required_tier">
              <option value="free" {"selected" if o.required_tier != "premium" else ""}>Free</option>
              <option value="premium" {"selected" if o.required_tier == "premium" else ""}>Premium</option>
            </select></label>
          </div>
          <div class="row">
            <label>Top Offer?<select name="is_top">
              <option value="0" {"selected" if not o.is_top else ""}>No</option>
              <option value="1" {"selected" if o.is_top else ""}>Yes</option>
            </select></label>
            <label>Status<select name="status">
              <option value="approved" {"selected" if o.status=="approved" else ""}>Approved</option>
              <option value="pending" {"selected" if o.status=="pending" else ""}>Pending</option>
            </select></label>
          </div>
        </div>

        <div id="section_general" style="display:{"block" if offer_kind=="general" else "none"}">
          <div class="section-title" style="margin-top:20px">General Settings</div>
          <label>Renew Duration (days)<input name="renew_duration" type="number" value="{o.renew_duration or 0}"/></label>
          <div class="section-title" style="margin-top:16px">Availability (Australian Sydney Time)</div>
          <div style="display:flex;gap:12px;margin:8px 0 16px">
            <button type="button" id="btn_allday" onclick="setAvailability('allday')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#ddd" if o.active_from else "#f08220"};background:{"white" if o.active_from else "#f08220"};color:{"#555" if o.active_from else "white"};font-weight:700;cursor:pointer">
              All Day
            </button>
            <button type="button" id="btn_partial" onclick="setAvailability('partial')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#f08220" if o.active_from else "#ddd"};background:{"#f08220" if o.active_from else "white"};color:{"white" if o.active_from else "#555"};font-weight:700;cursor:pointer">
              Partial Hours
            </button>
          </div>
          <input type="hidden" name="availability_type" id="availability_type" value="{"partial" if o.active_from else "allday"}"/>
          <div id="time_window_fields" style="display:{"block" if o.active_from else "none"}">
            <div class="row">
              <label>Active From<input name="active_from" type="time" id="active_from_input" value="{o.active_from or ""}"/></label>
              <label>Active Until<input name="active_until" type="time" id="active_until_input" value="{o.active_until or ""}"/></label>
            </div>
            <div style="font-size:12px;color:#888;margin-top:-8px;margin-bottom:12px">Crosses midnight is supported — e.g. 18:00 to 02:00 = 6 PM until 2 AM</div>
          </div>
        </div>

        <div id="section_flash" style="display:{"block" if offer_kind=="flash" else "none"}">
          <div class="section-title" style="margin-top:20px">Flash Settings</div>
          <div class="row">
            <label>Flash Start<input name="flash_start" type="datetime-local" value="{flash_start}"/></label>
            <label>Flash End<input name="flash_end" type="datetime-local" value="{flash_end}"/></label>
          </div>
          <div class="section-title" style="margin-top:16px">Availability Hours</div>
          <div style="display:flex;gap:8px;margin-bottom:8px">
            <button type="button" id="btn_allday_f" onclick="setAvailability('allday','f')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#ddd" if (offer_kind=="flash" and o.active_from) else "#f08220"};background:{"white" if (offer_kind=="flash" and o.active_from) else "#f08220"};color:{"#555" if (offer_kind=="flash" and o.active_from) else "white"};font-weight:700;cursor:pointer">All Day</button>
            <button type="button" id="btn_partial_f" onclick="setAvailability('partial','f')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#f08220" if (offer_kind=="flash" and o.active_from) else "#ddd"};background:{"#f08220" if (offer_kind=="flash" and o.active_from) else "white"};color:{"white" if (offer_kind=="flash" and o.active_from) else "#555"};font-weight:700;cursor:pointer">Partial Hours</button>
          </div>
          <input type="hidden" name="availability_type_f" id="availability_type_f" value="{"partial" if (offer_kind=="flash" and o.active_from) else "allday"}"/>
          <div id="time_window_fields_f" style="display:{"block" if (offer_kind=="flash" and o.active_from) else "none"}">
            <div class="row">
              <label>Active From<input name="active_from_f" type="time" id="active_from_input_f" value="{"" if offer_kind!="flash" else (o.active_from or "")}"/></label>
              <label>Active Until<input name="active_until_f" type="time" id="active_until_input_f" value="{"" if offer_kind!="flash" else (o.active_until or "")}"/></label>
            </div>
          </div>
        </div>

        <div id="section_promo" style="display:{"block" if offer_kind=="promo" else "none"}">
          <div class="section-title" style="margin-top:20px">Promo Settings</div>
          <div class="row">
            <label>Promo Code<input name="promo_code" value="{o.promo_code or ""}"/></label>
            <label>Promo Expiry<input name="promo_expiry_date" type="date" value="{promo_expiry}"/></label>
          </div>
          <div class="section-title" style="margin-top:16px">Availability Hours</div>
          <div style="display:flex;gap:8px;margin-bottom:8px">
            <button type="button" id="btn_allday_p" onclick="setAvailability('allday','p')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#ddd" if (offer_kind=="promo" and o.active_from) else "#f08220"};background:{"white" if (offer_kind=="promo" and o.active_from) else "#f08220"};color:{"#555" if (offer_kind=="promo" and o.active_from) else "white"};font-weight:700;cursor:pointer">All Day</button>
            <button type="button" id="btn_partial_p" onclick="setAvailability('partial','p')"
              style="flex:1;padding:10px;border-radius:8px;border:2px solid {"#f08220" if (offer_kind=="promo" and o.active_from) else "#ddd"};background:{"#f08220" if (offer_kind=="promo" and o.active_from) else "white"};color:{"white" if (offer_kind=="promo" and o.active_from) else "#555"};font-weight:700;cursor:pointer">Partial Hours</button>
          </div>
          <input type="hidden" name="availability_type_p" id="availability_type_p" value="{"partial" if (offer_kind=="promo" and o.active_from) else "allday"}"/>
          <div id="time_window_fields_p" style="display:{"block" if (offer_kind=="promo" and o.active_from) else "none"}">
            <div class="row">
              <label>Active From<input name="active_from_p" type="time" id="active_from_input_p" value="{"" if offer_kind!="promo" else (o.active_from or "")}"/></label>
              <label>Active Until<input name="active_until_p" type="time" id="active_until_input_p" value="{"" if offer_kind!="promo" else (o.active_until or "")}"/></label>
            </div>
          </div>
        </div>

        <input type="hidden" name="is_flash" id="is_flash" value="{"1" if o.is_flash else "0"}"/>
        <input type="hidden" name="is_promo" id="is_promo" value="{"1" if o.is_promo else "0"}"/>
        <button class="btn" type="submit" style="margin-top:20px">Save Changes</button>
      </form>
    </div>
    <script>
    function showSection(type) {{
      document.getElementById("section_general").style.display = type === "general" ? "block" : "none";
      document.getElementById("section_flash").style.display = type === "flash" ? "block" : "none";
      document.getElementById("section_promo").style.display = type === "promo" ? "block" : "none";
      document.getElementById("is_flash").value = type === "flash" ? "1" : "0";
      document.getElementById("is_promo").value = type === "promo" ? "1" : "0";
    }}
    function previewImg(input, previewId) {{
      var preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        var reader = new FileReader();
        reader.onload = function(e) {{ preview.src = e.target.result; preview.style.display = 'block'; }};
        reader.readAsDataURL(input.files[0]);
      }} else {{ preview.style.display = 'none'; }}
    }}
    function setAvailability(type, suffix) {{
      suffix = suffix || "";
      const sfx = suffix ? "_" + suffix : "";
      const isPartial = type === "partial";
      document.getElementById("time_window_fields" + sfx).style.display = isPartial ? "block" : "none";
      document.getElementById("availability_type" + sfx).value = type;
      document.getElementById("btn_allday" + sfx).style.background = isPartial ? "white" : "#f08220";
      document.getElementById("btn_allday" + sfx).style.color = isPartial ? "#555" : "white";
      document.getElementById("btn_allday" + sfx).style.borderColor = isPartial ? "#ddd" : "#f08220";
      document.getElementById("btn_partial" + sfx).style.background = isPartial ? "#f08220" : "white";
      document.getElementById("btn_partial" + sfx).style.color = isPartial ? "white" : "#555";
      document.getElementById("btn_partial" + sfx).style.borderColor = isPartial ? "#f08220" : "#ddd";
      if (!isPartial) {{
        document.getElementById("active_from_input" + sfx).value = "";
        document.getElementById("active_until_input" + sfx).value = "";
      }}
    }}
    </script>"""
    return HTMLResponse(page(f"Edit Offer #{id}", content))

@router.post("/offers/{id}/edit")
async def update_offer(id: int, request: Request, db: Session = Depends(get_db)):
    import shutil, uuid as _uuid
    from app.core.config import settings
    form = await request.form()

    def _save_upload(field_name):
        f = form.get(field_name)
        if f and hasattr(f, "filename") and f.filename:
            ext = f.filename.rsplit(".", 1)[-1]
            fname = f"{_uuid.uuid4()}.{ext}"
            with open(f"static/uploads/{fname}", "wb") as out:
                shutil.copyfileobj(f.file, out)
            return f"{settings.BASE_URL}/static/uploads/{fname}"
        return None

    o = db.query(Offer).filter(Offer.id == id).first()
    if not o:
        return HTMLResponse("Not found", status_code=404)

    def parse_dt(s):
        try: return datetime.strptime(s, "%Y-%m-%dT%H:%M") if s else None
        except: return None
    def parse_date(s):
        try: return datetime.strptime(s, "%Y-%m-%d") if s else None
        except: return None

    is_flash  = form.get("is_flash", "0")
    is_promo  = form.get("is_promo", "0")
    offer_kind= form.get("offer_kind", "general")

    o.name               = form.get("name", o.name)
    o.vendor_id          = int(form.get("vendor_id", o.vendor_id))
    o.description        = form.get("description", "")
    o.image              = _save_upload("image_file") or form.get("image", "") or o.image
    o.top_image          = _save_upload("top_image_file") or form.get("top_image", "") or o.top_image
    o.discount           = int(form.get("discount", 0))
    o.save_up_to         = float(form.get("save_up_to", 0))
    o.save_up_to_currency= form.get("save_up_to_currency", "AUD")
    o.promo_code         = form.get("promo_code", "") or None
    o.points             = int(form.get("points", 0))
    o.orders             = int(form.get("orders", 0))
    o.is_flash           = is_flash == "1"
    o.is_promo           = is_promo == "1"
    o.flash_start        = parse_dt(form.get("flash_start", ""))
    o.flash_end          = parse_dt(form.get("flash_end", ""))
    o.promo_expiry       = parse_date(form.get("promo_expiry_date", ""))
    o.required_tier      = form.get("required_tier", "free")
    o.level_priority     = 1 if o.required_tier == "premium" else 0
    o.is_top             = form.get("is_top", "0") == "1"
    o.status             = form.get("status", "approved")
    o.renew_duration     = int(form.get("renew_duration", 0)) if offer_kind == "general" else None

    if is_flash == "1":
        o.active_from = form.get("active_from_f", "") or None
        o.active_until = form.get("active_until_f", "") or None
    elif is_promo == "1":
        o.active_from = form.get("active_from_p", "") or None
        o.active_until = form.get("active_until_p", "") or None
    else:
        o.active_from = form.get("active_from", "") or None
        o.active_until = form.get("active_until", "") or None

    db.commit()
    return RedirectResponse("/admin/offers", status_code=302)

@router.get("/offers/{id}/delete")
def delete_offer(id: int, db: Session = Depends(get_db)):
    o = db.query(Offer).filter(Offer.id == id).first()
    if o:
        db.query(OfferTransaction).filter(OfferTransaction.offer_id == id).delete()
        db.delete(o)
        db.commit()
    return RedirectResponse("/admin/offers", status_code=302)

# ─── Sliders ──────────────────────────────────────────────────────────────────

@router.get("/sliders", response_class=HTMLResponse)
def list_sliders(db: Session = Depends(get_db)):
    sliders = db.query(Slider).all()
    def link_label(s):
        if s.link_type == "vendor": return f"Vendor #{s.target_id}"
        if s.link_type == "subscription": return "Subscription Page"
        return s.url or "—"
    def slider_img(s):
        return f"<img src='{s.image}' style='height:40px'>" if s.image else "—"
    rows = "".join([f"<tr><td>{s.id}</td><td>{s.name or ''}</td><td>{slider_img(s)}</td><td>{s.link_type or 'web'}</td><td>{link_label(s)}</td><td>{'Yes' if s.is_active else 'No'}</td><td><a href='/admin/sliders/{s.id}/edit'><button class='btn btn-sm' style='margin-right:4px'>Edit</button></a><a href='/admin/sliders/{s.id}/delete'><button class='btn btn-red btn-sm'>Delete</button></a></td></tr>" for s in sliders])
    content = f"""
    <a href="/admin/sliders/new"><button class="btn" style="margin-bottom:16px">+ Add Slider</button></a>
    <div class="card">
      <table><tr><th>ID</th><th>Name</th><th>Image</th><th>Link Type</th><th>Destination</th><th>Active</th><th>Action</th></tr>{rows}</table>
    </div>"""
    return HTMLResponse(page("Sliders", content))

@router.get("/sliders/new", response_class=HTMLResponse)
def new_slider_form(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    vendor_options = "".join([f"<option value='{v.id}'>{v.name}</option>" for v in vendors])
    content = f"""
    <div class="card">
      <form method="post" action="/admin/sliders/new" enctype="multipart/form-data">
        <label>Slider Name<input name="name" placeholder="e.g. Summer Sale"/></label>

        <div class="section-title" style="margin-top:16px">Image</div>
        <p style="font-size:12px;color:#888;margin-bottom:8px">
          Recommended size: <strong>1170 × 540 px</strong> — Wide landscape JPG (roughly 2:1 ratio). Fills the full-width slider at the top of the Explore screen.
        </p>
        <div class="row">
          <label>Upload Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this)"/></label>
          <label>— OR — Image URL<input name="image_url" placeholder="https://..."/></label>
        </div>
        <img id="preview" style="max-height:120px;margin:8px 0;display:none;border-radius:8px"/>

        <div class="section-title" style="margin-top:16px">Link Type</div>
        <label>When tapped, go to:
          <select name="link_type" id="link_type" onchange="showLinkSection(this.value)">
            <option value="web">External Website</option>
            <option value="vendor">Vendor Page</option>
            <option value="subscription">Subscription Page</option>
          </select>
        </label>

        <div id="section_web" style="margin-top:8px">
          <label>Website URL<input name="url" placeholder="https://..."/></label>
        </div>
        <div id="section_vendor" style="display:none;margin-top:8px">
          <label>Select Vendor<select name="target_id">{vendor_options}</select></label>
        </div>

        <div class="row" style="margin-top:16px">
          <label>Display Order (0 = first)<input name="display_order" type="number" value="0" min="0"/></label>
          <label>Seconds to display<input name="display_seconds" type="number" value="5" min="1" max="30"/></label>
        </div>
        <div class="row" style="margin-top:16px">
          <label>Active?<select name="is_active">
            <option value="1">Yes</option>
            <option value="0">No</option>
          </select></label>
        </div>

        <button class="btn" type="submit" style="margin-top:16px">Save Slider</button>
      </form>
    </div>
    <script>
    function showLinkSection(type) {{
      document.getElementById("section_web").style.display = type === "web" ? "block" : "none";
      document.getElementById("section_vendor").style.display = type === "vendor" ? "block" : "none";
    }}
    function previewImg(input) {{
      const preview = document.getElementById("preview");
      if (input.files && input.files[0]) {{
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }}
    }}
    </script>"""
    return HTMLResponse(page("New Slider", content))

@router.post("/sliders/new")
async def create_slider(
    request: Request,
    name: str = Form(""), image_url: str = Form(""),
    url: str = Form(""), link_type: str = Form("web"),
    target_id: str = Form(""), display_order: int = Form(0),
    display_seconds: int = Form(5), is_active: str = Form("1"),
    db: Session = Depends(get_db)
):
    from fastapi import UploadFile
    import shutil, uuid
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    s = Slider(
        name=name, image=final_image, url=url or None,
        link_type=link_type,
        target_id=int(target_id) if target_id and link_type == "vendor" else None,
        vendor_id=int(target_id) if target_id and link_type == "vendor" else None,
        is_active=is_active == "1"
    )
    db.add(s)
    db.commit()
    return RedirectResponse("/admin/sliders", status_code=302)

@router.get("/sliders/{id}/edit", response_class=HTMLResponse)
def edit_slider_form(id: int, db: Session = Depends(get_db)):
    s = db.query(Slider).filter(Slider.id == id).first()
    if not s:
        return HTMLResponse("Not found", status_code=404)
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    vendor_options = "".join([f"<option value='{v.id}' {'selected' if v.id == s.target_id else ''}>{v.name}</option>" for v in vendors])
    link_type = s.link_type or "web"
    content = f"""
    <div class="card">
      <form method="post" action="/admin/sliders/{s.id}/edit" enctype="multipart/form-data">
        <label>Slider Name<input name="name" value="{s.name or ''}"/></label>

        <div class="section-title" style="margin-top:16px">Image</div>
        {"<img src='" + s.image + "' style='max-height:120px;margin:8px 0;border-radius:8px' onerror=\"this.style.display='none'\"/>" if s.image else ""}
        <div class="row">
          <label>Upload New Image<input name="image_file" type="file" accept="image/*" onchange="previewImg(this)"/></label>
          <label>— OR — Image URL<input name="image_url" value="{s.image or ''}"/></label>
        </div>
        <img id="preview" style="max-height:120px;margin:8px 0;display:none;border-radius:8px"/>

        <div class="section-title" style="margin-top:16px">Link Type</div>
        <label>When tapped, go to:
          <select name="link_type" id="link_type" onchange="showLinkSection(this.value)">
            <option value="web" {"selected" if link_type=="web" else ""}>External Website</option>
            <option value="vendor" {"selected" if link_type=="vendor" else ""}>Vendor Page</option>
            <option value="subscription" {"selected" if link_type=="subscription" else ""}>Subscription Page</option>
          </select>
        </label>
        <div id="section_web" style="display:{"block" if link_type=="web" else "none"};margin-top:8px">
          <label>Website URL<input name="url" value="{s.url or ''}"/></label>
        </div>
        <div id="section_vendor" style="display:{"block" if link_type=="vendor" else "none"};margin-top:8px">
          <label>Select Vendor<select name="target_id">{vendor_options}</select></label>
        </div>

        <div class="row" style="margin-top:16px">
        </div>
        <div class="row" style="margin-top:16px">
          <label>Display Order (0 = first)<input name="display_order" type="number" value="{s.display_order or 0}" min="0"/></label>
          <label>Seconds to display<input name="display_seconds" type="number" value="{s.display_seconds or 5}" min="1" max="30"/></label>
        </div>
        <div class="row" style="margin-top:16px">
          <label>Active?<select name="is_active">
            <option value="1" {"selected" if s.is_active else ""}>Yes</option>
            <option value="0" {"selected" if not s.is_active else ""}>No</option>
          </select></label>
        </div>

        <button class="btn" type="submit" style="margin-top:16px">Save Changes</button>
      </form>
    </div>
    <script>
    function showLinkSection(type) {{
      document.getElementById("section_web").style.display = type === "web" ? "block" : "none";
      document.getElementById("section_vendor").style.display = type === "vendor" ? "block" : "none";
    }}
    function previewImg(input) {{
      const preview = document.getElementById("preview");
      if (input.files && input.files[0]) {{
        preview.src = URL.createObjectURL(input.files[0]);
        preview.style.display = "block";
      }}
    }}
    </script>"""
    return HTMLResponse(page(f"Edit Slider #{id}", content))

@router.post("/sliders/{id}/edit")
async def update_slider(
    id: int, request: Request,
    name: str = Form(""), image_url: str = Form(""),
    url: str = Form(""), link_type: str = Form("web"),
    target_id: str = Form(""), display_order: int = Form(0),
    display_seconds: int = Form(5), is_active: str = Form("1"),
    db: Session = Depends(get_db)
):
    import shutil, uuid
    s = db.query(Slider).filter(Slider.id == id).first()
    if not s:
        return HTMLResponse("Not found", status_code=404)
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    s.name = name
    s.image = final_image
    s.url = url or None
    s.link_type = link_type
    s.target_id = int(target_id) if target_id and link_type == "vendor" else None
    s.vendor_id = int(target_id) if target_id and link_type == "vendor" else None
    s.display_order = display_order
    s.display_seconds = display_seconds
    s.is_active = is_active == "1"
    db.commit()
    return RedirectResponse("/admin/sliders", status_code=302)

@router.get("/sliders/{id}/delete")
def delete_slider(id: int, db: Session = Depends(get_db)):
    s = db.query(Slider).filter(Slider.id == id).first()
    if s:
        db.delete(s)
        db.commit()
    return RedirectResponse("/admin/sliders", status_code=302)


# ─── Subscription Plans ───────────────────────────────────────────────────────

@router.get("/subscriptions", response_class=HTMLResponse)
def list_subscription_plans(db: Session = Depends(get_db)):
    plans = db.query(SubscriptionPlan).order_by(SubscriptionPlan.duration_months).all()
    rows = "".join([f"""<tr>
        <td>{p.id}</td><td>{p.name}</td><td>{p.duration_months or '-'} months</td>
        <td>${p.price}</td><td>{p.apple_product_id or '-'}</td>
        <td>{'<img src="' + p.image + '" style="height:50px;border-radius:6px" onerror="this.style.display=\'none\'">' if p.image else '-'}</td>
        <td>{'Yes' if p.is_active else 'No'}</td>
        <td><a href="/admin/subscriptions/{p.id}/edit">Edit</a> | <a href="/admin/subscriptions/{p.id}/delete" onclick="return confirm('Delete?')">Delete</a></td>
    </tr>""" for p in plans])
    content = f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h2>Subscription Plans</h2>
        <a class="btn" href="/admin/subscriptions/new">+ New Plan</a>
      </div>
      <table><tr><th>ID</th><th>Name</th><th>Duration</th><th>Price</th><th>Apple Product ID</th><th>Image</th><th>Active</th><th>Action</th></tr>{rows}</table>
    </div>"""
    return HTMLResponse(page("Subscription Plans", content))

@router.get("/subscriptions/new", response_class=HTMLResponse)
def new_subscription_plan_form():
    content = """
    <div class="card" style="max-width:600px">
      <h2 style="margin-bottom:20px">New Subscription Plan</h2>
      <form method="post" enctype="multipart/form-data">
        <label>Name (e.g. "3 Months")</label>
        <input name="name" required style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Duration (months)</label>
        <input name="duration_months" type="number" required style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Price (AUD)</label>
        <input name="price" type="number" step="0.01" required style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Apple Product ID (from App Store Connect)</label>
        <input name="apple_product_id" placeholder="com.snatchit.subscription.3months" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Plan Image (recommended: 700x200px, PNG/JPG)</label>
        <input type="file" name="image_file" accept="image/*" style="margin:6px 0 4px">
        <div style="font-size:12px;color:#888;margin-bottom:14px">Or enter image URL: <input name="image_url" style="width:60%;padding:6px;border:1px solid #ddd;border-radius:6px"></div>
        <label>Active</label>
        <select name="is_active" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
          <option value="1">Yes</option><option value="0">No</option>
        </select>
        <button type="submit" class="btn">Create Plan</button>
      </form>
    </div>"""
    return HTMLResponse(page("New Subscription Plan", content))

@router.post("/subscriptions/new")
async def create_subscription_plan(
    request: Request,
    name: str = Form(""), duration_months: int = Form(0),
    price: float = Form(0.0), apple_product_id: str = Form(""),
    image_url: str = Form(""), is_active: str = Form("1"),
    db: Session = Depends(get_db)
):
    import shutil, uuid
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    plan = SubscriptionPlan(
        name=name, duration_months=duration_months, price=price,
        apple_product_id=apple_product_id or None,
        image=final_image or None,
        billing_cycle="monthly", is_active=is_active == "1"
    )
    db.add(plan)
    db.commit()
    return RedirectResponse("/admin/subscriptions", status_code=302)

@router.get("/subscriptions/{id}/edit", response_class=HTMLResponse)
def edit_subscription_plan_form(id: int, db: Session = Depends(get_db)):
    p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == id).first()
    if not p:
        return HTMLResponse("Not found", status_code=404)
    img_preview = f'<img src="{p.image}" style="height:80px;border-radius:8px;margin:8px 0" onerror="this.style.display=\'none\'">' if p.image else ""
    content = f"""
    <div class="card" style="max-width:600px">
      <h2 style="margin-bottom:20px">Edit Plan: {p.name}</h2>
      <form method="post" enctype="multipart/form-data">
        <label>Name</label>
        <input name="name" value="{p.name}" required style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Duration (months)</label>
        <input name="duration_months" type="number" value="{p.duration_months or ''}" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Price (AUD)</label>
        <input name="price" type="number" step="0.01" value="{p.price}" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Apple Product ID</label>
        <input name="apple_product_id" value="{p.apple_product_id or ''}" placeholder="com.snatchit.subscription.3months" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
        <label>Plan Image (recommended: 700x200px)</label>
        {img_preview}
        <input type="file" name="image_file" accept="image/*" style="margin:6px 0 4px">
        <div style="font-size:12px;color:#888;margin-bottom:14px">Or enter image URL: <input name="image_url" value="{p.image or ''}" style="width:60%;padding:6px;border:1px solid #ddd;border-radius:6px"></div>
        <label>Active</label>
        <select name="is_active" style="width:100%;padding:8px;margin:6px 0 14px;border:1px solid #ddd;border-radius:6px">
          <option value="1" {'selected' if p.is_active else ''}>Yes</option>
          <option value="0" {'' if p.is_active else 'selected'}>No</option>
        </select>
        <button type="submit" class="btn">Save Changes</button>
      </form>
    </div>"""
    return HTMLResponse(page(f"Edit Plan: {p.name}", content))

@router.post("/subscriptions/{id}/edit")
async def update_subscription_plan(
    id: int, request: Request,
    name: str = Form(""), duration_months: int = Form(0),
    price: float = Form(0.0), apple_product_id: str = Form(""),
    image_url: str = Form(""), is_active: str = Form("1"),
    db: Session = Depends(get_db)
):
    import shutil, uuid
    p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == id).first()
    if not p:
        return HTMLResponse("Not found", status_code=404)
    form = await request.form()
    image_file = form.get("image_file")
    final_image = image_url
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        final_image = f"/static/uploads/{filename}"
    p.name = name
    p.duration_months = duration_months
    p.price = price
    p.apple_product_id = apple_product_id or None
    if final_image:
        p.image = final_image
    p.is_active = is_active == "1"
    db.commit()
    return RedirectResponse("/admin/subscriptions", status_code=302)

@router.get("/subscriptions/{id}/delete")
def delete_subscription_plan(id: int, db: Session = Depends(get_db)):
    p = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == id).first()
    if p:
        db.delete(p)
        db.commit()
    return RedirectResponse("/admin/subscriptions", status_code=302)


# ─── Users ────────────────────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.role == "client").order_by(User.created_at.desc()).all()
    rows = ""
    for u in users:
        status = "<span style='color:green;font-weight:600'>Active</span>" if u.is_active else "<span style='color:#aaa'>Inactive</span>"
        rows += f"""<tr>
          <td>{u.first_name} {u.last_name}</td>
          <td>{u.email}</td>
          <td>{u.phone_number}</td>
          <td><strong>{u.total_points or 0}</strong></td>
          <td>{status}</td>
          <td><a href='/admin/users/{u.id}/edit'><button class='btn btn-sm'>Edit</button></a></td>
        </tr>"""
    content = f"""
    <div class="card">
      <table>
        <tr><th>Name</th><th>Email</th><th>Phone</th><th>Points</th><th>Active</th><th>Action</th></tr>
        {rows if rows else "<tr><td colspan='6' style='text-align:center;color:#aaa;padding:24px'>No users yet</td></tr>"}
      </table>
    </div>"""
    return HTMLResponse(page("Users", content))


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
def edit_user_form(user_id: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return HTMLResponse("User not found", status_code=404)
    birth = u.birth_date.strftime("%Y-%m-%d") if u.birth_date else ""
    gender = u.gender_id or ""
    content = f"""
    <div class="card">
      <h2 style="margin-bottom:20px">{u.first_name} {u.last_name}</h2>
      <form method="post" action="/admin/users/{u.id}/edit">

        <div class="section-title">Account Info</div>
        <div class="row">
          <label>First Name<input name="first_name" value="{u.first_name or ""}"/></label>
          <label>Last Name<input name="last_name" value="{u.last_name or ""}"/></label>
        </div>
        <div class="row">
          <label>Email<input name="email" type="email" value="{u.email or ""}"/></label>
          <label>Phone<input name="phone" value="{u.phone_number or ""}"/></label>
        </div>
        <div class="row">
          <label>Date of Birth<input name="birth_date" type="date" value="{birth}"/></label>
          <label>Gender
            <select name="gender_id">
              <option value="">— Not set —</option>
              <option value="1" {"selected" if u.gender_id == 1 else ""}>Male</option>
              <option value="2" {"selected" if u.gender_id == 2 else ""}>Female</option>
            </select>
          </label>
        </div>
        <div class="row">
          <label>Active
            <select name="is_active">
              <option value="1" {"selected" if u.is_active else ""}>Yes</option>
              <option value="0" {"selected" if not u.is_active else ""}>No</option>
            </select>
          </label>
          <label>Role
            <select name="role">
              <option value="client" {"selected" if u.role == "client" else ""}>Client</option>
              <option value="admin" {"selected" if u.role == "admin" else ""}>Admin</option>
            </select>
          </label>
        </div>

        <div class="section-title" style="margin-top:20px">Points</div>
        <div class="row">
          <label>Current Points<input value="{u.total_points or 0}" disabled style="background:#f5f5f5;color:#888"/></label>
          <label>Add / Remove Points
            <input name="points_delta" type="number" value="0"
              placeholder="e.g. 100 to add, -50 to remove"/>
          </label>
        </div>
        <p style="font-size:12px;color:#888;margin-top:-8px">Enter a positive number to add points, negative to deduct. 0 = no change.</p>

        <button class="btn" type="submit" style="margin-top:20px">Save Changes</button>
        <a href="/admin/users" style="margin-left:12px;font-size:14px;color:#888">Cancel</a>
      </form>
    </div>"""
    return HTMLResponse(page(f"Edit User — {u.first_name} {u.last_name}", content))


@router.post("/users/{user_id}/edit")
def update_user(
    user_id: str,
    first_name: str = Form(""), last_name: str = Form(""),
    email: str = Form(""), phone: str = Form(""),
    birth_date: str = Form(""), gender_id: str = Form(""),
    is_active: str = Form("1"), role: str = Form("client"),
    points_delta: int = Form(0),
    db: Session = Depends(get_db)
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    u.first_name = first_name or u.first_name
    u.last_name  = last_name  or u.last_name
    u.is_active  = is_active == "1"
    u.role       = role

    # Only update email/phone if they changed (they're unique)
    if email and email != u.email:
        existing = db.query(User).filter(User.email == email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use by another user")
        u.email = email

    if phone and phone != u.phone_number:
        existing = db.query(User).filter(User.phone_number == phone, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Phone already in use by another user")
        u.phone_number = phone

    if birth_date:
        try:
            from datetime import datetime as _dt
            u.birth_date = _dt.strptime(birth_date, "%Y-%m-%d")
        except Exception:
            pass

    u.gender_id = int(gender_id) if gender_id else None

    if points_delta != 0:
        u.total_points = max(0, (u.total_points or 0) + points_delta)

    db.commit()
    return RedirectResponse("/admin/users", status_code=302)


# ─── Redemptions ──────────────────────────────────────────────────────────────

@router.get("/redemptions", response_class=HTMLResponse)
def list_redemptions(db: Session = Depends(get_db)):
    txns = db.query(OfferTransaction).order_by(OfferTransaction.created_at.desc()).all()

    def offer_type(o):
        if o.is_flash:  return "<span style='background:#e67e22;color:white;padding:2px 8px;border-radius:4px;font-size:12px'>Flash</span>"
        if o.is_promo:  return "<span style='background:#8e44ad;color:white;padding:2px 8px;border-radius:4px;font-size:12px'>Promo</span>"
        return "<span style='background:#27ae60;color:white;padding:2px 8px;border-radius:4px;font-size:12px'>General</span>"

    rows = ""
    for t in txns:
        o = t.offer
        u = t.user
        v = o.vendor if o else None
        offer_name  = o.name if o else "—"
        vendor_name = v.name if v else "—"
        user_name   = f"{u.first_name} {u.last_name}" if u else "—"
        user_phone  = u.phone_number if u else "—"
        redeemed_at = t.created_at.strftime("%Y-%m-%d %H:%M:%S") if t.created_at else "—"
        otype       = offer_type(o) if o else "—"
        rows += f"""<tr>
            <td>{t.id}</td>
            <td>{offer_name}<br><small style='color:#888'>ID {o.id if o else '—'}</small></td>
            <td>{otype}</td>
            <td>{vendor_name}</td>
            <td>{user_name}<br><small style='color:#888'>{user_phone}</small></td>
            <td>{redeemed_at}</td>
            <td><a href='/admin/redemptions/{t.id}/unlock'><button class='btn btn-sm' style='background:#e67e22'>Unlock</button></a></td>
        </tr>"""

    content = f"""
    <div class="card">
      <p style="font-size:13px;color:#888;margin-bottom:12px">Total: <strong>{len(txns)}</strong> redemptions — Click <strong>Unlock</strong> to remove a redemption and make the offer available again for that user.</p>
      <table>
        <tr>
          <th>#</th><th>Offer</th><th>Type</th><th>Vendor</th><th>User</th><th>Redeemed At</th><th>Action</th>
        </tr>
        {rows}
      </table>
    </div>"""
    return HTMLResponse(page("Redemptions", content))


@router.get("/redemptions/{id}/unlock")
def unlock_redemption(id: int, db: Session = Depends(get_db)):
    txn = db.query(OfferTransaction).filter(OfferTransaction.id == id).first()
    if txn:
        db.delete(txn)
        db.commit()
    return RedirectResponse("/admin/redemptions", status_code=302)


# ─── Notifications ────────────────────────────────────────────────────────────

def _get_target_users(notif, db):
    """Return list of User objects based on notification targeting rules."""
    from datetime import date
    base = db.query(User).filter(User.role == "client")
    ft = notif.filter_type or "all"
    fv = notif.filter_value or ""

    if ft == "user" and fv:
        return base.filter(User.id == fv).all()
    elif ft == "gender" and fv in ("male", "female"):
        gender_id = 1 if fv == "male" else 2
        return base.filter(User.gender_id == gender_id).all()
    elif ft == "birthday":
        today = date.today()
        return [u for u in base.all()
                if u.birth_date and u.birth_date.month == today.month and u.birth_date.day == today.day]
    elif ft == "age_above" and fv.isdigit():
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=int(fv) * 365)
        return base.filter(User.birth_date != None, User.birth_date <= cutoff).all()
    else:
        return base.all()


@router.get("/notifications", response_class=HTMLResponse)
def list_notifications(db: Session = Depends(get_db)):
    notifs = db.query(Notification).order_by(Notification.created_at.desc()).all()
    rows = ""
    for n in notifs:
        if n.sent:
            status = "<span style='color:green;font-weight:600'>Sent</span>"
        elif n.scheduled_at:
            from zoneinfo import ZoneInfo
            syd_time = n.scheduled_at.replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Australia/Sydney"))
            status = f"<span style='color:#e67e22;font-weight:600'>Scheduled<br><small>{syd_time.strftime('%Y-%m-%d %H:%M')} Sydney</small></span>"
        else:
            status = "<span style='color:#aaa'>Draft</span>"

        target_map = {"all": "All Users", "gender": f"Gender: {n.filter_value}",
                      "birthday": "Birthday Today", "age_above": f"Age ≥ {n.filter_value}",
                      "user": "Specific User"}
        target = target_map.get(n.filter_type or "all", "All Users")
        link = f"Vendor #{n.deep_link_id}" if n.deep_link_type == "vendor" else \
               f"Offer #{n.deep_link_id}" if n.deep_link_type == "offer" else \
               (n.deep_link_id or "—") if n.deep_link_type == "url" else "—"

        rows += f"""<tr>
          <td>{n.id}</td>
          <td><strong>{n.title}</strong></td>
          <td style='max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{n.message}</td>
          <td>{target}</td>
          <td>{link}</td>
          <td>{status}</td>
          <td>
            <a href='/admin/notifications/{n.id}/send'><button class='btn btn-sm' style='margin-right:4px;margin-bottom:4px'>Send</button></a>
            <a href='/admin/notifications/{n.id}/delete'><button class='btn btn-red btn-sm'>Delete</button></a>
          </td>
        </tr>"""

    content = f"""
    <a href="/admin/notifications/new"><button class="btn" style="margin-bottom:16px">+ New Notification</button></a>
    <div class="card">
      <table>
        <tr><th>ID</th><th>Title</th><th>Message</th><th>Target</th><th>Deep Link</th><th>Status</th><th>Action</th></tr>
        {rows if rows else "<tr><td colspan='7' style='text-align:center;color:#aaa;padding:24px'>No notifications yet</td></tr>"}
      </table>
    </div>"""
    return HTMLResponse(page("Notifications", content))


@router.get("/notifications/new", response_class=HTMLResponse)
def new_notification_form(db: Session = Depends(get_db)):
    from app.models.vendor import Vendor
    from app.models.offer import Offer
    users = db.query(User).filter(User.role == "client").all()
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    offers = db.query(Offer).filter(Offer.status == "approved").all()

    user_opts = "".join([f"<option value='{u.id}'>{u.first_name} {u.last_name} ({u.phone_number})</option>" for u in users])
    vendor_opts = "".join([f"<option value='{v.id}'>{v.name}</option>" for v in vendors])
    offer_opts = "".join([f"<option value='{o.id}'>{o.name}</option>" for o in offers])

    content = f"""
    <div class="card">
      <form method="post" action="/admin/notifications/new" enctype="multipart/form-data">

        <div class="section-title">Content</div>
        <label>Title<input name="title" required placeholder="e.g. New Flash Offer!"/></label>
        <label>Message<textarea name="message" required placeholder="Notification body text..."></textarea></label>
        <div class="row">
          <label>Upload Image (optional)<input name="image_file" type="file" accept="image/*" onchange="previewImg(this,'prev_notif')"/></label>
          <label>— OR — Image URL<input name="image_url" placeholder="https://..."/></label>
        </div>
        <img id="prev_notif" style="max-height:80px;margin:4px 0;display:none;border-radius:8px"/>

        <div class="section-title" style="margin-top:16px">Deep Link — Where does it open?</div>
        <div class="row">
          <label>Opens
            <select name="deep_link_type" onchange="toggleDeepLink(this.value)">
              <option value="none">No deep link (just open app)</option>
              <option value="vendor">Specific Vendor page</option>
              <option value="offer">Specific Offer</option>
              <option value="url">External URL</option>
            </select>
          </label>
          <div id="dl_vendor" style="display:none">
            <label>Vendor<select name="deep_link_vendor">{vendor_opts}</select></label>
          </div>
          <div id="dl_offer" style="display:none">
            <label>Offer<select name="deep_link_offer">{offer_opts}</select></label>
          </div>
          <div id="dl_url" style="display:none">
            <label>URL<input name="deep_link_url" placeholder="https://..."/></label>
          </div>
        </div>

        <div class="section-title" style="margin-top:16px">Target Audience</div>
        <div class="row">
          <label>Send To
            <select name="target" onchange="toggleTarget(this.value)">
              <option value="all">All Users</option>
              <option value="user">Specific User</option>
              <option value="gender">By Gender</option>
              <option value="birthday">Birthday Today</option>
              <option value="age_above">Age Above</option>
            </select>
          </label>
          <div id="target_user" style="display:none">
            <label>User<select name="user_id"><option value="">— Select —</option>{user_opts}</select></label>
          </div>
          <div id="target_gender" style="display:none">
            <label>Gender
              <select name="gender_value">
                <option value="male">Male</option>
                <option value="female">Female</option>
              </select>
            </label>
          </div>
          <div id="target_age" style="display:none">
            <label>Minimum Age<input name="age_value" type="number" min="1" max="120" placeholder="e.g. 60"/></label>
          </div>
        </div>

        <div class="section-title" style="margin-top:16px">Schedule</div>
        <div class="row">
          <label>Send
            <select name="send_when" onchange="toggleSchedule(this.value)">
              <option value="now">Send Immediately</option>
              <option value="scheduled">Schedule for later</option>
            </select>
          </label>
          <div id="schedule_picker" style="display:none">
            <label>Date &amp; Time <span style="color:#e67e22;font-size:12px">(Sydney time — AEDT/AEST)</span><input name="scheduled_at" type="datetime-local"/></label>
          </div>
        </div>

        <div style="display:flex;gap:12px;margin-top:20px">
          <button class="btn" type="submit" name="action" value="save">Save Draft</button>
          <button class="btn" type="submit" name="action" value="send" style="background:#27ae60">Save &amp; Send Now</button>
        </div>
      </form>
    </div>
    <script>
    function toggleDeepLink(v) {{
      ['vendor','offer','url'].forEach(t => document.getElementById('dl_'+t).style.display = v===t?'block':'none');
    }}
    function toggleTarget(v) {{
      ['user','gender','age'].forEach(t => document.getElementById('target_'+t).style.display = v==='age_above'&&t==='age'||v===t?'block':'none');
    }}
    function toggleSchedule(v) {{
      document.getElementById('schedule_picker').style.display = v==='scheduled'?'block':'none';
    }}
    function previewImg(input, previewId) {{
      var preview = document.getElementById(previewId);
      if (input.files && input.files[0]) {{
        var reader = new FileReader();
        reader.onload = function(e) {{ preview.src = e.target.result; preview.style.display = 'block'; }};
        reader.readAsDataURL(input.files[0]);
      }} else {{ preview.style.display = 'none'; }}
    }}
    </script>"""
    return HTMLResponse(page("New Notification", content))


@router.post("/notifications/new")
async def create_notification(request: Request, db: Session = Depends(get_db)):
    import shutil, uuid as _uuid
    form = await request.form()
    title         = form.get("title", "")
    message       = form.get("message", "")
    image_url     = form.get("image_url", "")
    deep_link_type= form.get("deep_link_type", "none")
    deep_link_vendor = form.get("deep_link_vendor", "")
    deep_link_offer  = form.get("deep_link_offer", "")
    deep_link_url_val= form.get("deep_link_url", "")
    target        = form.get("target", "all")
    user_id       = form.get("user_id", "")
    gender_value  = form.get("gender_value", "")
    age_value     = form.get("age_value", "")
    send_when     = form.get("send_when", "now")
    scheduled_at  = form.get("scheduled_at", "")
    action        = form.get("action", "save")

    # Handle image upload or URL
    final_image = image_url or None
    image_file = form.get("image_file")
    if image_file and hasattr(image_file, "filename") and image_file.filename:
        ext = image_file.filename.rsplit(".", 1)[-1]
        filename = f"{_uuid.uuid4()}.{ext}"
        filepath = f"static/uploads/{filename}"
        with open(filepath, "wb") as f:
            shutil.copyfileobj(image_file.file, f)
        from app.core.config import settings
        final_image = f"{settings.BASE_URL}/static/uploads/{filename}"

    # Resolve deep link
    dl_id = {"vendor": deep_link_vendor, "offer": deep_link_offer, "url": deep_link_url_val}.get(deep_link_type, "")

    # Resolve targeting
    filter_type  = target
    filter_value = {"user": user_id, "gender": gender_value, "age_above": age_value}.get(target, "")

    # Resolve schedule — Sydney local time → UTC
    sched = None
    if send_when == "scheduled" and scheduled_at:
        try:
            from zoneinfo import ZoneInfo
            local_dt  = datetime.fromisoformat(scheduled_at)
            sydney_dt = local_dt.replace(tzinfo=ZoneInfo("Australia/Sydney"))
            sched     = sydney_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        except Exception:
            pass

    notif = Notification(
        title=title, message=message, image=final_image,
        filter_type=filter_type, filter_value=filter_value or None,
        deep_link_type=deep_link_type, deep_link_id=dl_id or None,
        scheduled_at=sched, sent=False, created_at=datetime.utcnow()
    )
    db.add(notif)
    db.flush()

    users = _get_target_users(notif, db)
    for u in users:
        db.add(UserNotification(
            user_id=u.id, notification_id=notif.id,
            title=title, message=message, image=final_image,
            is_read=False, created_at=datetime.utcnow()
        ))

    if action == "send" and not sched:
        user_ids = [u.id for u in users]
        devices = db.query(MobileDevice).filter(MobileDevice.user_id.in_(user_ids)).all()
        tokens = list({d.token for d in devices if d.token})
        send_push_multicast(tokens, title, message, final_image, deep_link_type, dl_id)
        notif.sent = True

    db.commit()
    return RedirectResponse("/admin/notifications", status_code=302)


@router.get("/notifications/{id}/send")
def send_notification_now(id: int, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Not found")
    users = _get_target_users(notif, db)
    user_ids = [u.id for u in users]
    devices = db.query(MobileDevice).filter(MobileDevice.user_id.in_(user_ids)).all()
    tokens = list({d.token for d in devices if d.token})
    send_push_multicast(tokens, notif.title, notif.message, notif.image,
                        notif.deep_link_type or "none", notif.deep_link_id or "")
    notif.sent = True
    db.commit()
    return RedirectResponse("/admin/notifications", status_code=302)


@router.get("/notifications/{id}/delete")
def delete_notification_record(id: int, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == id).first()
    if notif:
        db.query(UserNotification).filter(UserNotification.notification_id == id).delete()
        db.delete(notif)
        db.commit()
    return RedirectResponse("/admin/notifications", status_code=302)
