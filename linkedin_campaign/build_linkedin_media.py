#!/usr/bin/env python3
"""
build_linkedin_media.py
=======================
Automated compilation of high-impact visual media assets for the Earth-2
X-Band SAR & InSAR Digital Twin LinkedIn Ad Campaign.

Generates:
1. Landscape Sponsored Content (1200 x 627, 1.91:1)
2. Square Sponsored Content (1080 x 1080, 1:1)
3. 10-Card Carousel Deck (1080 x 1080)
4. 4 Animated GIFs (< 5MB, smooth loop)
5. Interactive Asset Previewer (linkedin_campaign/assets_preview.html)

Strict compliance with Rule e2s-014 (Scientific Integrity).
"""

import os
import sys
import json
import math
import time
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

# Directories
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(WORKSPACE_ROOT, "linkedin_campaign", "assets")
SCREENSHOTS_DIR = os.path.join(WORKSPACE_ROOT, "linkedin_campaign", "screenshots")
RUNS_DIR = os.path.join(WORKSPACE_ROOT, "viewer_app", "public", "runs")
HTML_PREVIEW_PATH = os.path.join(WORKSPACE_ROOT, "linkedin_campaign", "assets_preview.html")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Color Palette & Styling Constants
# -----------------------------------------------------------------------------
BG_COLOR = (11, 15, 25)           # Deep space slate #0b0f19
BG_CARD = (15, 23, 42, 220)       # Glass card fill #0f172a
BG_CARD_SOLID = (15, 23, 42)
CYAN = (0, 240, 255)              # Radiant cyan #00f0ff
CYAN_DIM = (0, 180, 200)
CYAN_GLOW = (0, 240, 255, 60)
EMERALD = (16, 185, 129)          # Electric emerald #10b981
EMERALD_DIM = (5, 150, 105)
AMBER = (245, 158, 11)            # Warning amber #f59e0b
PURPLE = (168, 85, 247)           # Radiant violet #a855f7
WHITE = (248, 250, 252)           # #f8fafc
MUTED = (148, 163, 184)           # #94a3b8
DARK_BORDER = (30, 41, 59)        # #1e293b
BORDER_GLOW = (0, 240, 255, 120)

# -----------------------------------------------------------------------------
# Typography Loader
# -----------------------------------------------------------------------------
def get_font(name="segoe", size=20, bold=False):
    windir = os.environ.get("WINDIR", "C:\\Windows")
    font_map = {
        ("segoe", True): os.path.join(windir, "Fonts", "segoeuib.ttf"),
        ("segoe", False): os.path.join(windir, "Fonts", "segoeui.ttf"),
        ("mono", True): os.path.join(windir, "Fonts", "consolab.ttf"),
        ("mono", False): os.path.join(windir, "Fonts", "consola.ttf"),
        ("arial", True): os.path.join(windir, "Fonts", "arialbd.ttf"),
        ("arial", False): os.path.join(windir, "Fonts", "arial.ttf"),
    }
    path = font_map.get((name, bold))
    if path and os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    # Fallback
    for fb in ["arialbd.ttf" if bold else "arial.ttf", "arial.ttf"]:
        fb_path = os.path.join(windir, "Fonts", fb)
        if os.path.exists(fb_path):
            try:
                return ImageFont.truetype(fb_path, size)
            except Exception:
                pass
    return ImageFont.load_default()

# -----------------------------------------------------------------------------
# Graphics Primitives & Layout Helpers
# -----------------------------------------------------------------------------
def draw_rounded_rect(draw, bbox, fill=None, outline=None, width=1, radius=8):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def draw_glass_panel(draw, bbox, fill=BG_CARD, outline=BORDER_GLOW, radius=10, width=1):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline, width=width)

def draw_hud_corners(draw, bbox, color=CYAN, length=12, width=2):
    x0, y0, x1, y1 = bbox
    # Top-Left
    draw.line([(x0, y0), (x0 + length, y0)], fill=color, width=width)
    draw.line([(x0, y0), (x0, y0 + length)], fill=color, width=width)
    # Top-Right
    draw.line([(x1, y0), (x1 - length, y0)], fill=color, width=width)
    draw.line([(x1, y0), (x1, y0 + length)], fill=color, width=width)
    # Bottom-Left
    draw.line([(x0, y1), (x0 + length, y1)], fill=color, width=width)
    draw.line([(x0, y1), (x0, y1 - length)], fill=color, width=width)
    # Bottom-Right
    draw.line([(x1, y1), (x1 - length, y1)], fill=color, width=width)
    draw.line([(x1, y1), (x1, y1 - length)], fill=color, width=width)

def draw_badge(draw, text, xy, bg=(0, 240, 255, 35), border=CYAN, text_color=CYAN, font=None, padding=(10, 5), radius=5):
    if font is None:
        font = get_font("mono", 14, bold=True)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    px, py = padding
    x, y = xy
    box = [x, y, x + tw + px * 2, y + th + py * 2]
    draw.rounded_rectangle(box, radius=radius, fill=bg, outline=border, width=1)
    draw.text((x + px, y + py - bbox[1]), text, fill=text_color, font=font)
    return box[2]  # returns right edge x coordinate

def draw_scanlines_and_grid(draw, width, height, step=50, alpha=15):
    grid_color = (0, 240, 255, alpha)
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)

def load_and_cover(path, target_size, filter_mode=Image.Resampling.LANCZOS):
    if not os.path.exists(path):
        return Image.new("RGBA", target_size, BG_COLOR)
    try:
        im = Image.open(path).convert("RGBA")
        return ImageOps.fit(im, target_size, method=filter_mode)
    except Exception as e:
        print(f"Warning: could not load {path}: {e}")
        return Image.new("RGBA", target_size, BG_COLOR)

def draw_branding_header(draw, width, run_title="EARTH-2 // DIGITAL TWIN", tag="RULE e2s-014 VERIFIED"):
    # Header bar background
    header_h = 56
    draw.rectangle([0, 0, width, header_h], fill=(10, 15, 26, 230))
    draw.line([(0, header_h), (width, header_h)], fill=(0, 240, 255, 70), width=1)
    
    # Pulse dot
    dot_x, dot_y = 28, 28
    draw.ellipse([dot_x - 5, dot_y - 5, dot_x + 5, dot_y + 5], fill=EMERALD)
    draw.ellipse([dot_x - 8, dot_y - 8, dot_x + 8, dot_y + 8], outline=(16, 185, 129, 120), width=1)
    
    # Title
    font_title = get_font("segoe", 15, bold=True)
    draw.text((45, 18), "EARTH-2 MISSION TWIN", fill=WHITE, font=font_title)
    
    font_sub = get_font("mono", 12, bold=False)
    draw.text((250, 20), "|  X-BAND SAR & InSAR MISSION CONTROL", fill=MUTED, font=font_sub)
    
    # Right badge
    if tag:
        font_tag = get_font("mono", 12, bold=True)
        draw_badge(draw, tag, (width - 240, 14), bg=(16, 185, 129, 30), border=EMERALD, text_color=EMERALD, font=font_tag, padding=(8, 4))

def draw_branding_footer(draw, width, height, cta="EXPLORE 3D MISSION TWIN ➔", metrics="NOAA GFS 0.25°  |  OGC STAC v1.0.0  |  ZERO HALLUCINATIONS"):
    footer_h = 52
    y0 = height - footer_h
    draw.rectangle([0, y0, width, height], fill=(10, 15, 26, 235))
    draw.line([(0, y0), (width, y0)], fill=(0, 240, 255, 60), width=1)
    
    font_m = get_font("mono", 12, bold=False)
    draw.text((28, y0 + 17), metrics, fill=MUTED, font=font_m)
    
    font_cta = get_font("segoe", 14, bold=True)
    cta_w = font_cta.getbbox(cta)[2] - font_cta.getbbox(cta)[0]
    cta_box = [width - cta_w - 48, y0 + 9, width - 20, height - 9]
    draw.rounded_rectangle(cta_box, radius=6, fill=(0, 240, 255, 40), outline=CYAN, width=1)
    draw.text((width - cta_w - 34, y0 + 15), cta, fill=CYAN, font=font_cta)


# =============================================================================
# 1. LANDSCAPE SPONSORED CONTENT CARDS (1200 x 627)
# =============================================================================
def generate_landscape_cards():
    print("Generating Landscape Sponsored Content Cards (1200x627)...")
    W, H = 1200, 627

    cards = [
        {
            "id": "ad_landscape_01_aps_reduction",
            "filename": "ad_landscape_01_aps_reduction.png",
            "badge": "RULE e2s-014 CERTIFIED",
            "metric_highlight": "-98.7%",
            "metric_label": "APS PHASE VARIANCE REDUCTION",
            "title": "Breaking InSAR Tropospheric APS Noise",
            "subtitle": "CATALYST Physics Model unmasks sub-centimeter displacement using authentic NOAA GFS 0.25° tensors with zero random synthetic noise.",
            "chips": ["12.2 Fringes Removed", "σ²: 14.78 ➔ 0.18 rad²", "ICEYE Spotlight 0.5m"],
            "image_source": os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "06_geoint_sar_aps_trifecta.png"),
            "screenshot_overlay": os.path.join(SCREENSHOTS_DIR, "06_insar_split_slider_comparison.png")
        },
        {
            "id": "ad_landscape_02_global_mission_twin",
            "filename": "ad_landscape_02_global_mission_twin.png",
            "badge": "MISSION CONTROL TWIN",
            "metric_highlight": "SUB-HOURLY",
            "metric_label": "CONSTELLATION REVISIT ARCHITECTURE",
            "title": "Real-Time 3D Radar Mission Twin",
            "subtitle": "Interactive digital twin orchestrating ICEYE & Synspective X-band swaths, look-cones, and orbital mechanics in WebGL.",
            "chips": ["570 km SSO Orbit", "Look-Cone Footprints", "Dynamic Swath Dispatch"],
            "image_source": os.path.join(SCREENSHOTS_DIR, "01_mission_control_overview.png"),
            "screenshot_overlay": os.path.join(SCREENSHOTS_DIR, "04_swath_orbit_activation_mexico.png")
        },
        {
            "id": "ad_landscape_03_deep_hazards_infrastructure",
            "filename": "ad_landscape_03_deep_hazards_infrastructure.png",
            "badge": "GEOPHYSICAL HAZARDS",
            "metric_highlight": "40 cm/yr",
            "metric_label": "DEFORMATION DETECTED AT SCALE",
            "title": "Deep Geophysical Hazard Quantification",
            "subtitle": "Sub-centimeter monitoring across 11 global research theaters: volcanic inflation, permafrost thaw, and coastal delta subsidence.",
            "chips": ["Campi Flegrei Bradyseism", "Norilsk Permafrost", "Cascadia Subduction"],
            "image_source": os.path.join(RUNS_DIR, "run_06_deep_geophysical_hazards", "09_deep_geophysical_hazards.png"),
            "screenshot_overlay": os.path.join(RUNS_DIR, "run_11_vancouver_cascadia_delta", "14_vancouver_terrain.png")
        },
        {
            "id": "ad_landscape_04_ogc_stac_tasking",
            "filename": "ad_landscape_04_ogc_stac_tasking.png",
            "badge": "OGC STAC v1.0.0 COMPLIANT",
            "metric_highlight": "< 50 ms",
            "metric_label": "RADAR TASKING DISPATCH LATENCY",
            "title": "Programmatic SAR Satellite Tasking",
            "subtitle": "Cloud-native tasking engine generating validated OGC STAC GeoJSON orders for automated tip-and-cue defense and commercial ops.",
            "chips": ["GeoJSON Swaths", "Full Radar Metadata", "1-Click Order Copy"],
            "image_source": os.path.join(SCREENSHOTS_DIR, "05_stac_tasking_inspector.png"),
            "screenshot_overlay": None
        },
        {
            "id": "ad_landscape_05_scientific_integrity",
            "filename": "ad_landscape_05_scientific_integrity.png",
            "badge": "ZERO SYNTHETIC HALLUCINATIONS",
            "metric_highlight": "100%",
            "metric_label": "PHYSICALLY GROUNDED VERIFICATION",
            "title": "Scientific Rigor Over Generative Noise",
            "subtitle": "Why aerospace & defense mission twins demand deterministic atmospheric tensors over unverified diffusion models.",
            "chips": ["Rule e2s-014 Enforced", "TAC vs ACC Audited", "Authentic GFS & ERA5"],
            "image_source": os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "03_prognostic_model_benchmark.png"),
            "screenshot_overlay": os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "01_probabilistic_ensemble_spread.png")
        }
    ]

    for card in cards:
        base = Image.new("RGBA", (W, H), BG_COLOR)
        
        # Background composite
        if card["image_source"] and os.path.exists(card["image_source"]):
            bg_im = load_and_cover(card["image_source"], (W, H))
            # Darken and blend background
            bg_im = ImageEnhance.Brightness(bg_im).enhance(0.35)
            base.paste(bg_im, (0, 0))
        
        # Grid overlay
        draw_ov = ImageDraw.Draw(base)
        draw_scanlines_and_grid(draw_ov, W, H, step=60, alpha=14)
        
        # Header & Footer
        draw_branding_header(draw_ov, W, tag=card["badge"])
        draw_branding_footer(draw_ov, W, H)
        
        # Left Content Glass Card
        content_box = [40, 80, 680, H - 75]
        draw_glass_panel(draw_ov, content_box, fill=(12, 18, 32, 235), outline=(0, 240, 255, 100), radius=12)
        draw_hud_corners(draw_ov, content_box, color=CYAN, length=16, width=2)
        
        # Card inner typography
        draw_text = ImageDraw.Draw(base)
        tx = 65
        ty = 105
        
        # Badge
        draw_badge(draw_text, card["badge"], (tx, ty), bg=(0, 240, 255, 30), border=CYAN, text_color=CYAN, font=get_font("mono", 12, bold=True))
        ty += 38
        
        # Big Metric Callout
        font_big = get_font("segoe", 46, bold=True)
        draw_text.text((tx, ty), card["metric_highlight"], fill=CYAN, font=font_big)
        
        font_lbl = get_font("mono", 12, bold=True)
        ty += 56
        draw_text.text((tx, ty), card["metric_label"], fill=EMERALD, font=font_lbl)
        ty += 24
        
        # Divider line
        draw_text.line([(tx, ty), (655, ty)], fill=(0, 240, 255, 50), width=1)
        ty += 16
        
        # Title
        font_h = get_font("segoe", 26, bold=True)
        draw_text.text((tx, ty), card["title"], fill=WHITE, font=font_h)
        ty += 38
        
        # Subtitle paragraph (wrap)
        font_p = get_font("segoe", 15, bold=False)
        words = card["subtitle"].split(" ")
        line = ""
        for w in words:
            test_line = line + w + " "
            if font_p.getbbox(test_line)[2] > 580:
                draw_text.text((tx, ty), line, fill=MUTED, font=font_p)
                ty += 24
                line = w + " "
            else:
                line = test_line
        if line:
            draw_text.text((tx, ty), line, fill=MUTED, font=font_p)
            ty += 32
        
        # Feature chips
        chip_x = tx
        for chip in card["chips"]:
            chip_x = draw_badge(draw_text, chip, (chip_x, ty), bg=(30, 41, 59, 180), border=(71, 85, 105), text_color=WHITE, font=get_font("mono", 11, bold=False), padding=(8, 4)) + 10
        
        # Right Visual Feature Frame
        right_box = [710, 80, W - 40, H - 75]
        draw_glass_panel(draw_ov, right_box, fill=(15, 23, 42, 240), outline=(0, 240, 255, 120), radius=12)
        draw_hud_corners(draw_ov, right_box, color=CYAN, length=16, width=2)
        
        # Crop & place right visual
        rw = right_box[2] - right_box[0] - 16
        rh = right_box[3] - right_box[1] - 16
        if card["screenshot_overlay"] and os.path.exists(card["screenshot_overlay"]):
            feat_im = load_and_cover(card["screenshot_overlay"], (rw, rh))
            base.paste(feat_im, (right_box[0] + 8, right_box[1] + 8))
        elif card["image_source"] and os.path.exists(card["image_source"]):
            feat_im = load_and_cover(card["image_source"], (rw, rh))
            base.paste(feat_im, (right_box[0] + 8, right_box[1] + 8))
            
        # Subtle vignette border on right image
        draw_text.rounded_rectangle([right_box[0] + 8, right_box[1] + 8, right_box[2] - 8, right_box[3] - 8], radius=8, outline=(0, 240, 255, 140), width=1)
        
        out_path = os.path.join(OUTPUT_DIR, card["filename"])
        base.save(out_path, "PNG", optimize=True)
        print(f"  ✓ {card['filename']} saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 2. SQUARE SPONSORED CONTENT CARDS (1080 x 1080)
# =============================================================================
def generate_square_cards():
    print("Generating Square Sponsored Content Cards (1080x1080)...")
    W, H = 1080, 1080

    cards = [
        {
            "id": "ad_square_01_aps_hero",
            "filename": "ad_square_01_aps_hero.png",
            "tag": "RULE e2s-014 VERIFIED",
            "stat": "-98.7%",
            "stat_label": "ATMOSPHERIC PHASE SCREEN (APS) ERROR REDUCTION",
            "title": "Clean InSAR Phase Fringes",
            "sub": "Raw X-band interferograms suffer heavy tropospheric water vapor distortion. Earth-2 assimilates NOAA GFS 0.25° tensors to remove 12.2 turbulent fringes without hallucinated noise.",
            "points": ["ICEYE Spotlight & Synspective StriX", "Authentic Zenith Total Delay Modeling", "Sub-centimeter Surface Displacement"],
            "feat_img": os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "06_geoint_sar_aps_trifecta.png"),
            "cta": "EXPLORE InSAR MISSION TWIN ➔"
        },
        {
            "id": "ad_square_02_global_constellation",
            "filename": "ad_square_02_global_constellation.png",
            "tag": "GLOBAL MISSION CONTROL",
            "stat": "11 RUNS",
            "stat_label": "SCIENTIFIC RESEARCH SUITES & SATELLITE TWIN",
            "title": "Commercial SAR Digital Twin",
            "sub": "Simulate and task commercial X-band radar constellations in real-time. Full WebGL 3D mission control globe with orbital tracks, look-cones, and instant swath activation.",
            "points": ["WebGL Orbit Mechanics Engine", "570 km SSO Polar Orbits", "1-Click Swath Fly-To Navigation"],
            "feat_img": os.path.join(SCREENSHOTS_DIR, "01_mission_control_overview.png"),
            "cta": "LAUNCH 3D MISSION TWIN ➔"
        },
        {
            "id": "ad_square_03_cascadia_subsidence",
            "filename": "ad_square_03_cascadia_subsidence.png",
            "tag": "CRITICAL INFRASTRUCTURE",
            "stat": "40 cm/yr",
            "stat_label": "RAPID COASTAL & DELTA SUBSIDENCE TRACKED",
            "title": "Cascadia Subduction & Fraser Delta",
            "sub": "Quantifying liquefaction risk zones, sea-level vulnerability, and sediment compaction with high-resolution persistent scatterer InSAR and physical hazard models.",
            "points": ["Vancouver Fraser River Delta", "Seismic Liquefaction Vulnerability", "Rule e2s-014 Strict Verification"],
            "feat_img": os.path.join(RUNS_DIR, "run_11_vancouver_cascadia_delta", "14_vancouver_terrain.png"),
            "cta": "INSPECT HAZARD STUDY ➔"
        },
        {
            "id": "ad_square_04_stac_api_dispatch",
            "filename": "ad_square_04_stac_api_dispatch.png",
            "tag": "OGC STAC v1.0.0 COMPLIANT",
            "stat": "< 50 ms",
            "stat_label": "INSTANT SATELLITE TASKING DISPATCH",
            "title": "Automated Radar Tasking API",
            "sub": "Generate production-ready OGC STAC GeoJSON tasking orders directly from atmospheric correction outputs. Ready for commercial constellation dispatch.",
            "points": ["Spotlight & Stripmap Geometry", "Incidence & Azimuth Metadata", "1-Click Clipboard Order Copy"],
            "feat_img": os.path.join(SCREENSHOTS_DIR, "05_stac_tasking_inspector.png"),
            "cta": "VIEW STAC SPECIFICATION ➔"
        },
        {
            "id": "ad_square_05_multiband_sar_physics",
            "filename": "ad_square_05_multiband_sar_physics.png",
            "tag": "MULTI-BAND RADAR PHYSICS",
            "stat": "X / C / L",
            "stat_label": "MULTI-WAVELENGTH COHERENCE MODELING",
            "title": "Multi-Band InSAR Decoupling",
            "sub": "Compare wavelength penetration depths (3.1cm vs 5.6cm vs 23.6cm) and temporal decorrelation across dense Amazon canopy and built environments.",
            "points": ["Volume Scattering Decoupling", "Phase Coherence γ Profiling", "Cross-Constellation Fusion"],
            "feat_img": os.path.join(RUNS_DIR, "run_05_multiband_insar_physics", "08_multiband_insar_comparison.png"),
            "cta": "READ MULTI-BAND PAPER ➔"
        }
    ]

    for card in cards:
        base = Image.new("RGBA", (W, H), BG_COLOR)
        
        # Background preview
        if os.path.exists(card["feat_img"]):
            bg_im = load_and_cover(card["feat_img"], (W, H))
            bg_im = ImageEnhance.Brightness(bg_im).enhance(0.28)
            base.paste(bg_im, (0, 0))
            
        draw_ov = ImageDraw.Draw(base)
        draw_scanlines_and_grid(draw_ov, W, H, step=50, alpha=15)
        
        # Branding Header & Footer
        draw_branding_header(draw_ov, W, tag=card["tag"])
        draw_branding_footer(draw_ov, W, H, cta=card["cta"])
        
        # Top Stat Glass Card
        stat_box = [50, 75, W - 50, 230]
        draw_glass_panel(draw_ov, stat_box, fill=(15, 23, 42, 235), outline=(0, 240, 255, 120), radius=12)
        draw_hud_corners(draw_ov, stat_box, color=CYAN, length=16, width=2)
        
        draw_t = ImageDraw.Draw(base)
        # Tag
        draw_badge(draw_t, card["tag"], (75, 95), bg=(0, 240, 255, 30), border=CYAN, text_color=CYAN, font=get_font("mono", 12, bold=True))
        
        # Stat Number
        font_stat = get_font("segoe", 52, bold=True)
        draw_t.text((75, 125), card["stat"], fill=CYAN, font=font_stat)
        
        # Stat Label
        font_sl = get_font("mono", 13, bold=True)
        draw_t.text((75, 192), card["stat_label"], fill=EMERALD, font=font_sl)
        
        # Middle Visual Window
        vis_box = [50, 250, W - 50, 700]
        draw_glass_panel(draw_ov, vis_box, fill=(10, 15, 26, 240), outline=(0, 240, 255, 90), radius=12)
        draw_hud_corners(draw_ov, vis_box, color=CYAN, length=16, width=2)
        
        vw = vis_box[2] - vis_box[0] - 16
        vh = vis_box[3] - vis_box[1] - 16
        if os.path.exists(card["feat_img"]):
            img_c = load_and_cover(card["feat_img"], (vw, vh))
            base.paste(img_c, (vis_box[0] + 8, vis_box[1] + 8))
            draw_t.rounded_rectangle([vis_box[0] + 8, vis_box[1] + 8, vis_box[2] - 8, vis_box[3] - 8], radius=8, outline=(0, 240, 255, 100), width=1)
            
        # Bottom Text Content Panel
        bot_box = [50, 720, W - 50, H - 75]
        draw_glass_panel(draw_ov, bot_box, fill=(15, 23, 42, 240), outline=(0, 240, 255, 110), radius=12)
        draw_hud_corners(draw_ov, bot_box, color=CYAN, length=16, width=2)
        
        bx = 75
        by = 740
        font_bt = get_font("segoe", 24, bold=True)
        draw_t.text((bx, by), card["title"], fill=WHITE, font=font_bt)
        by += 34
        
        font_bp = get_font("segoe", 15, bold=False)
        words = card["sub"].split(" ")
        line = ""
        for w in words:
            if font_bp.getbbox(line + w + " ")[2] > (W - 160):
                draw_t.text((bx, by), line, fill=MUTED, font=font_bp)
                by += 22
                line = w + " "
            else:
                line += w + " "
        if line:
            draw_t.text((bx, by), line, fill=MUTED, font=font_bp)
            by += 28
            
        # Feature chips
        cx = bx
        for p in card["points"]:
            cx = draw_badge(draw_t, p, (cx, by), bg=(30, 41, 59, 180), border=(71, 85, 105), text_color=WHITE, font=get_font("mono", 11, bold=False), padding=(8, 4)) + 12

        out_path = os.path.join(OUTPUT_DIR, card["filename"])
        base.save(out_path, "PNG", optimize=True)
        print(f"  ✓ {card['filename']} saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 3. 10-CARD CAROUSEL DECK (1080 x 1080)
# =============================================================================
def generate_carousel_cards():
    print("Generating 10-Card Carousel Deck (1080x1080)...")
    W, H = 1080, 1080

    deck = [
        {
            "card_idx": "01 / 10",
            "filename": "carousel_card_01_mission_overview.png",
            "tag": "PORTFOLIO OVERVIEW",
            "run_num": "SYSTEM ARCHITECTURE",
            "title": "Earth-2 X-Band SAR & InSAR Twin",
            "highlight": "11 SCIENTIFIC RUNS",
            "sub": "End-to-end digital twin uniting physical hazard modeling, commercial SAR satellite tasking, and atmospheric correction.",
            "bullets": ["Authentic NOAA GFS 0.25° Tensors", "Rule e2s-014 Scientific Integrity", "ICEYE & Synspective Constellations"],
            "img": os.path.join(SCREENSHOTS_DIR, "01_mission_control_overview.png"),
            "swipe": "Swipe to explore Run 01: APS Correction ➔"
        },
        {
            "card_idx": "02 / 10",
            "filename": "carousel_card_02_run01_tropospheric_aps.png",
            "tag": "RUN 01 // GLOBAL BASELINE",
            "run_num": "BASELINE PILLAR 01",
            "title": "Tropospheric APS Noise Removal",
            "highlight": "-98.7% ERROR REDUCTION",
            "sub": "Po Valley Alps InSAR validation removing 12.2 turbulent atmospheric fringes using CATALYST Zenith Total Delay raytracing.",
            "bullets": ["Uncorrected Phase RMSE: 14.78 rad", "Corrected Phase RMSE: 0.18 rad", "Zero Stochastic Hallucinations"],
            "img": os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "06_geoint_sar_aps_trifecta.png"),
            "swipe": "Swipe to Run 02: Mexico City Subsidence ➔"
        },
        {
            "card_idx": "03 / 10",
            "filename": "carousel_card_03_run02_mexico_city.png",
            "tag": "RUN 02 // HIDDEN TERRAIN",
            "run_num": "LATIN AMERICA THEATER",
            "title": "Mexico City Aquifer Depletion",
            "highlight": "40 CM / YEAR COMPACTION",
            "sub": "Rapid lacustrine clay consolidation and differential settlement threatening critical municipal rail and water lines.",
            "bullets": ["Lacustrine Aquifer Compaction", "Differential Settlement Fault Scarps", "ICEYE Ascending Spotlight VV"],
            "img": os.path.join(RUNS_DIR, "run_02_mexico_hidden_terrain", "07_mexico_hidden_terrain_geoint.png"),
            "swipe": "Swipe to Run 03: Arctic Permafrost Thaw ➔"
        },
        {
            "card_idx": "04 / 10",
            "filename": "carousel_card_04_run03_norilsk_permafrost.png",
            "tag": "RUN 03 // HIDDEN TERRAIN",
            "run_num": "ARCTIC SIBERIA THEATER",
            "title": "Norilsk Permafrost Degradation",
            "highlight": "THERMOKARST SUBSIDENCE",
            "sub": "Active-layer deepening and thermophysical loss of bearing capacity across massive Arctic industrial and metallurgical hubs.",
            "bullets": ["Thermokarst Cavity Collapse", "Talik Formation & Thaw Slumps", "High-Latitude Orbit Tracking"],
            "img": os.path.join(RUNS_DIR, "run_03_northern_russia_terrain", "06_russia_hidden_terrain_geoint.png"),
            "swipe": "Swipe to Run 04: Karst Dolines ➔"
        },
        {
            "card_idx": "05 / 10",
            "filename": "carousel_card_05_run04_south_africa_karst.png",
            "tag": "RUN 04 // HIDDEN TERRAIN",
            "run_num": "SOUTHERN AFRICA THEATER",
            "title": "Gauteng Karst Dolines & Mines",
            "highlight": "SINKHOLE COLLAPSE WARNING",
            "sub": "Sub-surface cavern dewatering and catastrophic sinkhole precursors across deep gold reef mining shafts.",
            "bullets": ["Dolomitic Karst Cavities", "Mine Dewatering Ground Instability", "Coherence Phase Drop Alert"],
            "img": os.path.join(RUNS_DIR, "run_04_south_africa_terrain", "07_geoint_south_africa_hidden_terrain.png"),
            "swipe": "Swipe to Run 05: Multi-Band Physics ➔"
        },
        {
            "card_idx": "06 / 10",
            "filename": "carousel_card_06_run05_multiband_physics.png",
            "tag": "RUN 05 // MULTI-BAND SAR",
            "run_num": "RADAR PHYSICS ENGINE",
            "title": "X vs C vs L-Band Comparison",
            "highlight": "3.1 CM vs 5.6 CM vs 23.6 CM",
            "sub": "Physical trade-offs between high spatial resolution and volumetric canopy decorrelation across diverse vegetation biomes.",
            "bullets": ["X-Band 3.1cm Precision Focus", "C-Band 5.6cm Operational Baseline", "L-Band 23.6cm Deep Canopy Penetration"],
            "img": os.path.join(RUNS_DIR, "run_05_multiband_insar_physics", "08_multiband_insar_comparison.png"),
            "swipe": "Swipe to Run 06 & 07: Volcanotectonics ➔"
        },
        {
            "card_idx": "07 / 10",
            "filename": "carousel_card_07_run06_07_volcanotectonics.png",
            "tag": "RUN 06 & 07 // DEEP HAZARDS",
            "run_num": "MEDITERRANEAN THEATER",
            "title": "Campi Flegrei Bradyseism",
            "highlight": "MAGMA CHAMBER INFLATION",
            "sub": "Caldera uplift and micro-seismic swarm monitoring across Pozzuoli and the Gulf of Pozzuoli with millimeter precision.",
            "bullets": ["Hydrothermal System Overpressure", "Volcanotectonic Faulting", "Synspective StriX Asc/Desc Fusion"],
            "img": os.path.join(RUNS_DIR, "run_06_deep_geophysical_hazards", "09_deep_geophysical_hazards.png"),
            "swipe": "Swipe to Run 08 & 09: Boreal Wetlands ➔"
        },
        {
            "card_idx": "08 / 10",
            "filename": "carousel_card_08_run08_09_wetlands_farmland.png",
            "tag": "RUN 08 & 09 // ECOSYSTEMS",
            "run_num": "NORDIC & JAPAN THEATERS",
            "title": "Boreal Peatlands & Farmland Decay",
            "highlight": "GLACIAL REBOUND & HYDROLOGY",
            "sub": "Post-glacial isostatic uplift in Finland peatlands paired with terraced paddy vegetation succession in rural Honshu.",
            "bullets": ["Fennoscandian Uplift: 8 mm/yr", "Methane Bog Hydrological Flux", "Terraced Paddy Abandonment"],
            "img": os.path.join(RUNS_DIR, "run_08_finland_glacial_rebound_peatlands", "11_finland_terrain.png"),
            "swipe": "Swipe to Run 10 & 11: Amazon & Cascadia ➔"
        },
        {
            "card_idx": "09 / 10",
            "filename": "carousel_card_09_run10_11_tropical_cascadia.png",
            "tag": "RUN 10 & 11 // DYNAMICS",
            "run_num": "AMAZON & CASCADIA THEATERS",
            "title": "Tropical Canopy & Coastal Delta",
            "highlight": "SUBDUCTION & CANOPY PENETRATION",
            "sub": "X-band microwave canopy scattering in the Amazon basin paired with Fraser River delta tidal liquefaction subsidence.",
            "bullets": ["Amazon Heavy Foliage Backscatter", "Cascadia Megathrust Locked Zone", "Fraser Delta Subsidence Risk"],
            "img": os.path.join(RUNS_DIR, "run_11_vancouver_cascadia_delta", "14_vancouver_terrain.png"),
            "swipe": "Swipe to OGC STAC Sensor Tasking ➔"
        },
        {
            "card_idx": "10 / 10",
            "filename": "carousel_card_10_stac_constellation_dispatch.png",
            "tag": "MISSION DISPATCH ENGINE",
            "run_num": "OGC STAC v1.0.0 SPEC",
            "title": "Automated Constellation Tasking",
            "highlight": "INSTANT MISSION ORCHESTRATION",
            "sub": "From atmospheric correction to commercial constellation tasking order in <50ms. Fully compliant with modern defense and GEOINT APIs.",
            "bullets": ["ICEYE & Synspective GeoJSON Specs", "Automated Tasking Order Validation", "Rule e2s-014 Certified Workflow"],
            "img": os.path.join(SCREENSHOTS_DIR, "05_stac_tasking_inspector.png"),
            "swipe": "Explore Live 3D Twin Now 🚀"
        }
    ]

    for card in deck:
        base = Image.new("RGBA", (W, H), BG_COLOR)
        
        # Background
        if os.path.exists(card["img"]):
            bg_im = load_and_cover(card["img"], (W, H))
            bg_im = ImageEnhance.Brightness(bg_im).enhance(0.24)
            base.paste(bg_im, (0, 0))
            
        draw_ov = ImageDraw.Draw(base)
        draw_scanlines_and_grid(draw_ov, W, H, step=50, alpha=15)
        
        # Carousel Header
        draw_branding_header(draw_ov, W, run_title="EARTH-2 // CAROUSEL DECK", tag=f"CARD {card['card_idx']}")
        draw_branding_footer(draw_ov, W, H, cta=card["swipe"], metrics=f"RUN PORTFOLIO  |  {card['run_num']}")
        
        # Top Meta Card
        top_box = [50, 75, W - 50, 205]
        draw_glass_panel(draw_ov, top_box, fill=(15, 23, 42, 235), outline=(0, 240, 255, 120), radius=12)
        draw_hud_corners(draw_ov, top_box, color=CYAN, length=16, width=2)
        
        draw_t = ImageDraw.Draw(base)
        # Card Index Badge
        draw_badge(draw_t, card["tag"], (75, 92), bg=(0, 240, 255, 30), border=CYAN, text_color=CYAN, font=get_font("mono", 12, bold=True))
        draw_badge(draw_t, card["card_idx"], (W - 165, 92), bg=(16, 185, 129, 30), border=EMERALD, text_color=EMERALD, font=get_font("mono", 12, bold=True))
        
        # Highlight Metric
        font_hl = get_font("segoe", 38, bold=True)
        draw_t.text((75, 126), card["highlight"], fill=CYAN, font=font_hl)
        
        font_rn = get_font("mono", 12, bold=True)
        draw_t.text((75, 172), card["run_num"], fill=MUTED, font=font_rn)
        
        # Main Visual Center Window
        vis_box = [50, 225, W - 50, 720]
        draw_glass_panel(draw_ov, vis_box, fill=(10, 15, 26, 240), outline=(0, 240, 255, 90), radius=12)
        draw_hud_corners(draw_ov, vis_box, color=CYAN, length=16, width=2)
        
        vw = vis_box[2] - vis_box[0] - 16
        vh = vis_box[3] - vis_box[1] - 16
        if os.path.exists(card["img"]):
            img_c = load_and_cover(card["img"], (vw, vh))
            base.paste(img_c, (vis_box[0] + 8, vis_box[1] + 8))
            draw_t.rounded_rectangle([vis_box[0] + 8, vis_box[1] + 8, vis_box[2] - 8, vis_box[3] - 8], radius=8, outline=(0, 240, 255, 90), width=1)
            
        # Bottom Information Box
        bot_box = [50, 740, W - 50, H - 75]
        draw_glass_panel(draw_ov, bot_box, fill=(15, 23, 42, 240), outline=(0, 240, 255, 110), radius=12)
        draw_hud_corners(draw_ov, bot_box, color=CYAN, length=16, width=2)
        
        bx = 75
        by = 758
        font_bt = get_font("segoe", 24, bold=True)
        draw_t.text((bx, by), card["title"], fill=WHITE, font=font_bt)
        by += 32
        
        font_bp = get_font("segoe", 15, bold=False)
        words = card["sub"].split(" ")
        line = ""
        for w in words:
            if font_bp.getbbox(line + w + " ")[2] > (W - 160):
                draw_t.text((bx, by), line, fill=MUTED, font=font_bp)
                by += 22
                line = w + " "
            else:
                line += w + " "
        if line:
            draw_t.text((bx, by), line, fill=MUTED, font=font_bp)
            by += 28
            
        # Bullets
        cx = bx
        for b in card["bullets"]:
            cx = draw_badge(draw_t, b, (cx, by), bg=(30, 41, 59, 180), border=(71, 85, 105), text_color=WHITE, font=get_font("mono", 11, bold=False), padding=(8, 4)) + 10

        out_path = os.path.join(OUTPUT_DIR, card["filename"])
        base.save(out_path, "PNG", optimize=True)
        print(f"  ✓ {card['filename']} saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 4. ANIMATED GIF 01: GLOBAL MISSION TWIN (640 x 360)
# =============================================================================
def generate_gif_01_global_mission_twin():
    print("Generating gif_01_global_mission_twin.gif (3D Mission Control Overview)...")
    W, H = 640, 360
    n_frames = 36
    frames = []

    # Source base screenshot
    bg_source = os.path.join(SCREENSHOTS_DIR, "01_mission_control_overview.png")
    bg_base = load_and_cover(bg_source, (W, H))

    for i in range(n_frames):
        # Progress 0.0 to 1.0
        p = i / n_frames
        angle = p * 2 * math.pi
        
        # Frame canvas
        im = bg_base.copy()
        draw = ImageDraw.Draw(im)
        
        # Scanning grid overlay
        draw_scanlines_and_grid(draw, W, H, step=40, alpha=10)
        
        # Rotating Radar Arc / Sweeping Cone from center
        cx, cy = 320, 180
        cone_radius = 160
        cone_angle = angle
        
        # Draw sweeping radar line
        sweep_x = cx + cone_radius * math.cos(cone_angle)
        sweep_y = cy + cone_radius * math.sin(cone_angle)
        draw.line([(cx, cy), (sweep_x, sweep_y)], fill=(0, 240, 255, 180), width=2)
        
        # Radar scan trail arcs
        for t in range(5):
            ta = cone_angle - (t + 1) * 0.08
            tx = cx + cone_radius * math.cos(ta)
            ty = cy + cone_radius * math.sin(ta)
            alpha_val = max(10, 140 - t * 28)
            draw.line([(cx, cy), (tx, ty)], fill=(0, 240, 255, alpha_val), width=1)
            
        # Satellites in orbit
        # Orbit 1: ICEYE-X38 (Polar SSO inclination)
        sat1_x = cx + 210 * math.cos(angle)
        sat1_y = cy + 110 * math.sin(angle)
        draw.ellipse([sat1_x - 4, sat1_y - 4, sat1_x + 4, sat1_y + 4], fill=CYAN)
        draw.ellipse([sat1_x - 8, sat1_y - 8, sat1_x + 8, sat1_y + 8], outline=(0, 240, 255, 140), width=1)
        # Look-cone from sat to earth
        draw.line([(sat1_x, sat1_y), (cx + 30 * math.cos(angle), cy + 20 * math.sin(angle))], fill=(0, 240, 255, 70), width=1)
        
        # Orbit 2: StriX-3 (Mid inclination)
        sat2_x = cx + 180 * math.cos(-angle * 1.2 + 1.0)
        sat2_y = cy + 130 * math.sin(-angle * 1.2 + 1.0)
        draw.ellipse([sat2_x - 4, sat2_y - 4, sat2_x + 4, sat2_y + 4], fill=EMERALD)
        draw.ellipse([sat2_x - 7, sat2_y - 7, sat2_x + 7, sat2_y + 7], outline=(16, 185, 129, 140), width=1)
        draw.line([(sat2_x, sat2_y), (cx - 20, cy + 10)], fill=(16, 185, 129, 60), width=1)
        
        # Top HUD Bar
        draw.rectangle([0, 0, W, 36], fill=(10, 15, 26, 230))
        draw.line([(0, 36), (W, 36)], fill=(0, 240, 255, 80), width=1)
        
        font_h = get_font("segoe", 12, bold=True)
        draw.text((15, 9), "EARTH-2 MISSION CONTROL // 3D DIGITAL TWIN", fill=WHITE, font=font_h)
        
        # Live Timecode & Telemetry
        font_mono = get_font("mono", 11, bold=True)
        sec = int(i * (60 / n_frames))
        timecode = f"UTC 14:24:{sec:02d}Z  |  ORBIT: ICEYE-X38 (570 KM)"
        draw.text((W - 305, 10), timecode, fill=CYAN, font=font_mono)
        
        # Bottom Telemetry Bar
        draw.rectangle([0, H - 32, W, H], fill=(10, 15, 26, 230))
        draw.line([(0, H - 32), (W, H - 32)], fill=(0, 240, 255, 80), width=1)
        
        lat = 19.43 + 2.0 * math.sin(angle)
        lon = -99.13 + 3.0 * math.cos(angle)
        hud_coords = f"BORESIGHT LAT: {lat:+.3f}° | LON: {lon:+.3f}° | APS DELAY: -98.7% GFS"
        draw.text((15, H - 23), hud_coords, fill=EMERALD, font=font_mono)
        
        badge_text = "STAC v1.0.0 ACTIVE"
        draw.text((W - 135, H - 23), badge_text, fill=CYAN, font=font_mono)
        
        # Corner HUD marks
        draw_hud_corners(draw, [10, 46, W - 10, H - 42], color=(0, 240, 255, 120), length=12, width=1)
        
        # Adaptive Palette quantization
        im_p = im.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        frames.append(im_p)

    out_path = os.path.join(OUTPUT_DIR, "gif_01_global_mission_twin.gif")
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
    print(f"  ✓ gif_01_global_mission_twin.gif saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 5. ANIMATED GIF 02: InSAR PHASE SPLIT SLIDER (640 x 400)
# =============================================================================
def generate_gif_02_insar_phase_split_slider():
    print("Generating gif_02_insar_phase_split_slider.gif (Interactive Split Slider)...")
    W, H = 640, 400
    n_frames = 36
    frames = []

    # Authentic background crops
    # Left: Heavy atmospheric fringes from Run 01 trifecta
    trifecta_path = os.path.join(RUNS_DIR, "run_01_baseline_advanced_pillars", "06_geoint_sar_aps_trifecta.png")
    slider_ui_path = os.path.join(SCREENSHOTS_DIR, "06_insar_split_slider_comparison.png")
    
    if os.path.exists(trifecta_path):
        trifecta_im = Image.open(trifecta_path).convert("RGBA")
        # In 3000x2200 trifecta, panel 1 is raw uncorrected (left), panel 3 is corrected (right)
        raw_crop = trifecta_im.crop((0, 200, 1500, 2000))
        raw_bg = ImageOps.fit(raw_crop, (W, H), method=Image.Resampling.LANCZOS)
        
        corr_crop = trifecta_im.crop((1500, 200, 3000, 2000))
        corr_bg = ImageOps.fit(corr_crop, (W, H), method=Image.Resampling.LANCZOS)
    elif os.path.exists(slider_ui_path):
        raw_bg = load_and_cover(slider_ui_path, (W, H))
        corr_bg = raw_bg.copy()
    else:
        raw_bg = Image.new("RGBA", (W, H), (20, 25, 40))
        corr_bg = Image.new("RGBA", (W, H), (10, 35, 30))

    for i in range(n_frames):
        # Ping-pong sine wave slider position: 15% to 85%
        p = i / n_frames
        slider_pct = 0.50 + 0.35 * math.sin(p * 2 * math.pi)
        split_x = int(W * slider_pct)
        
        # Composite frame: Left has raw_bg, Right has corr_bg
        frame = Image.new("RGBA", (W, H))
        frame.paste(raw_bg, (0, 0))
        
        # Paste right corrected section
        right_crop = corr_bg.crop((split_x, 0, W, H))
        frame.paste(right_crop, (split_x, 0))
        
        draw = ImageDraw.Draw(frame)
        
        # Divider Line (Glowing Cyan)
        draw.line([(split_x, 0), (split_x, H)], fill=(0, 240, 255, 255), width=3)
        draw.line([(split_x - 1, 0), (split_x - 1, H)], fill=(0, 240, 255, 120), width=1)
        draw.line([(split_x + 1, 0), (split_x + 1, H)], fill=(0, 240, 255, 120), width=1)
        
        # Slider Handle Button
        hy = H // 2
        btn_w, btn_h = 44, 26
        btn_box = [split_x - btn_w // 2, hy - btn_h // 2, split_x + btn_w // 2, hy + btn_h // 2]
        draw.rounded_rectangle(btn_box, radius=6, fill=(15, 23, 42, 245), outline=CYAN, width=2)
        font_arrows = get_font("segoe", 12, bold=True)
        draw.text((split_x - 14, hy - 9), "◀ ❚ ▶", fill=CYAN, font=font_arrows)
        
        # Top Comparison Badges
        font_tag = get_font("mono", 11, bold=True)
        # Left Badge: Raw
        draw_badge(draw, "RAW InSAR (σ² = 14.78 rad²)", (18, 14), bg=(239, 68, 68, 40), border=(239, 68, 68), text_color=(254, 202, 202), font=font_tag, padding=(8, 4))
        # Right Badge: Corrected
        draw_badge(draw, "CATALYST GFS CORRECTED (-98.7% σ²)", (W - 275, 14), bg=(16, 185, 129, 40), border=EMERALD, text_color=EMERALD, font=font_tag, padding=(8, 4))
        
        # Bottom Telemetry Bar
        draw.rectangle([0, H - 34, W, H], fill=(10, 15, 26, 230))
        draw.line([(0, H - 34), (W, H - 34)], fill=(0, 240, 255, 70), width=1)
        
        font_bar = get_font("mono", 11, bold=False)
        draw.text((18, H - 24), "X-BAND λ = 3.106 cm  |  PO VALLEY ALPS INTERFEROGRAM  |  RULE e2s-014 VERIFIED", fill=WHITE, font=font_bar)
        
        # Quantize
        im_p = frame.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        frames.append(im_p)

    out_path = os.path.join(OUTPUT_DIR, "gif_02_insar_phase_split_slider.gif")
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
    print(f"  ✓ gif_02_insar_phase_split_slider.gif saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 6. ANIMATED GIF 03: SWATH ACTIVATION THEATER HOP (640 x 400)
# =============================================================================
def generate_gif_03_swath_activation_theater_hop():
    print("Generating gif_03_swath_activation_theater_hop.gif (1-Click Swath Activation)...")
    W, H = 640, 400
    
    theaters = [
        {
            "name": "MEXICO CITY",
            "country": "MEXICO",
            "hazard": "Aquifer Compaction & Rapid Subsidence",
            "rate": "40.2 cm / year",
            "coords": "19.432° N, -99.133° W",
            "sat": "ICEYE-X38 (Ascending)",
            "img_path": os.path.join(RUNS_DIR, "run_02_mexico_hidden_terrain", "07_mexico_hidden_terrain_geoint.png")
        },
        {
            "name": "CAMPI FLEGREI",
            "country": "ITALY",
            "hazard": "Caldera Bradyseismic Inflation",
            "rate": "12.4 cm / year",
            "coords": "40.827° N, +14.139° E",
            "sat": "StriX-3 (Descending)",
            "img_path": os.path.join(RUNS_DIR, "run_07_southern_italy_volcanotectonics", "10_southern_italy_terrain.png")
        },
        {
            "name": "NORILSK TUNDRA",
            "country": "RUSSIA",
            "hazard": "Permafrost Active-Layer Thaw",
            "rate": "8.7 cm / year",
            "coords": "69.353° N, +88.202° E",
            "sat": "ICEYE-X22 (Polar SSO)",
            "img_path": os.path.join(RUNS_DIR, "run_03_northern_russia_terrain", "06_russia_hidden_terrain_geoint.png")
        },
        {
            "name": "AMAZON BASIN",
            "country": "BRAZIL",
            "hazard": "Tropical Canopy Moisture Dynamics",
            "rate": "Multi-Temporal Decoupling",
            "coords": "-3.119° S, -60.021° W",
            "sat": "StriX-1 (StripMap VV/VH)",
            "img_path": os.path.join(RUNS_DIR, "run_10_brazil_tropical_dynamics", "13_brazil_terrain.png")
        },
        {
            "name": "FRASER RIVER DELTA",
            "country": "VANCOUVER",
            "hazard": "Cascadia Coastal Subsidence Risk",
            "rate": "14.8 mm / year",
            "coords": "49.282° N, -123.120° W",
            "sat": "ICEYE-X38 (Spotlight)",
            "img_path": os.path.join(RUNS_DIR, "run_11_vancouver_cascadia_delta", "14_vancouver_terrain.png")
        }
    ]

    frames_per_theater = 8
    frames = []

    for th_idx, th in enumerate(theaters):
        bg = load_and_cover(th["img_path"], (W, H))
        bg = ImageEnhance.Brightness(bg).enhance(0.45)
        
        for f in range(frames_per_theater):
            im = bg.copy()
            draw = ImageDraw.Draw(im)
            
            # Subtle grid
            draw_scanlines_and_grid(draw, W, H, step=40, alpha=12)
            
            # Animating Reticle & Swath Footprint
            # Progress inside theater: 0.0 to 1.0
            tp = f / frames_per_theater
            
            # Central Target Lock Box
            cx, cy = W // 2, H // 2
            # Size shrinks as it "locks on"
            box_sz = int(80 - tp * 25)
            swath_box = [cx - box_sz, cy - box_sz, cx + box_sz, cy + box_sz]
            
            # Draw targeting crosshair
            line_len = 18
            draw.line([(cx - box_sz - line_len, cy), (cx + box_sz + line_len, cy)], fill=(0, 240, 255, 120), width=1)
            draw.line([(cx, cy - box_sz - line_len), (cx, cy + box_sz + line_len)], fill=(0, 240, 255, 120), width=1)
            
            # Draw radar footprint polygon
            draw_hud_corners(draw, swath_box, color=EMERALD if tp > 0.4 else CYAN, length=14, width=2)
            
            if tp > 0.3:
                # Fill activated footprint
                swath_fill = (16, 185, 129, 45) if tp > 0.5 else (0, 240, 255, 30)
                draw.rectangle(swath_box, fill=swath_fill)
                font_status = get_font("mono", 11, bold=True)
                draw.text((cx - 55, cy - 6), "● SWATH ACTIVE", fill=EMERALD, font=font_status)
            
            # Top Theater Info HUD
            hud_top = [20, 16, W - 20, 80]
            draw_glass_panel(draw, hud_top, fill=(15, 23, 42, 235), outline=(0, 240, 255, 120), radius=8)
            draw_hud_corners(draw, hud_top, color=CYAN, length=10, width=1)
            
            font_title = get_font("segoe", 18, bold=True)
            draw.text((35, 24), f"{th['name']}  ({th['country']})", fill=WHITE, font=font_title)
            
            font_hz = get_font("mono", 11, bold=True)
            draw.text((35, 52), f"HAZARD: {th['hazard']}  |  RATE: {th['rate']}", fill=EMERALD, font=font_hz)
            
            draw_badge(draw, f"THEATER 0{th_idx+1}/05", (W - 145, 24), bg=(0, 240, 255, 30), border=CYAN, text_color=CYAN, font=get_font("mono", 10, bold=True), padding=(6, 3))
            
            # Bottom Coordinates & Sat Info
            hud_bot = [20, H - 46, W - 20, H - 14]
            draw_glass_panel(draw, hud_bot, fill=(15, 23, 42, 230), outline=(0, 240, 255, 80), radius=6)
            
            font_sub = get_font("mono", 11, bold=False)
            draw.text((32, H - 38), f"COORDS: {th['coords']}   |   PLATFORM: {th['sat']}   |   1-CLICK FLY-TO VERIFIED", fill=WHITE, font=font_sub)
            
            # Quantize
            im_p = im.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
            frames.append(im_p)

    out_path = os.path.join(OUTPUT_DIR, "gif_03_swath_activation_theater_hop.gif")
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=150, loop=0, optimize=True)
    print(f"  ✓ gif_03_swath_activation_theater_hop.gif saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 7. ANIMATED GIF 04: OGC STAC TASKING ORDER (640 x 400)
# =============================================================================
def generate_gif_04_stac_tasking_order():
    print("Generating gif_04_stac_tasking_order.gif (OGC STAC Inspector & Copy)...")
    W, H = 640, 400
    n_frames = 36
    frames = []

    # Background screenshot
    stac_bg_path = os.path.join(SCREENSHOTS_DIR, "05_stac_tasking_inspector.png")
    bg = load_and_cover(stac_bg_path, (W, H))
    bg = ImageEnhance.Brightness(bg).enhance(0.35)

    code_lines = [
        ('{', (148, 163, 184)),
        ('  "type": "Feature",', (0, 240, 255)),
        ('  "stac_version": "1.0.0",', (0, 240, 255)),
        ('  "id": "earth2-task-iceye-0042",', (245, 158, 11)),
        ('  "properties": {', (148, 163, 184)),
        ('    "constellation": "ICEYE",', (16, 185, 129)),
        ('    "sar:frequency_ghz": 9.65,', (168, 85, 247)),
        ('    "sar:polarization": "VV",', (168, 85, 247)),
        ('    "aps:correction": "NOAA_GFS_0.25",', (0, 240, 255)),
        ('    "variance_reduction_pct": 98.73', (16, 185, 129)),
        ('  }', (148, 163, 184)),
        ('}', (148, 163, 184))
    ]

    for i in range(n_frames):
        im = bg.copy()
        draw = ImageDraw.Draw(im)
        draw_scanlines_and_grid(draw, W, H, step=40, alpha=10)
        
        # Central Inspector Modal
        modal_box = [30, 25, W - 30, H - 25]
        draw_glass_panel(draw, modal_box, fill=(15, 23, 42, 245), outline=(0, 240, 255, 140), radius=10)
        draw_hud_corners(draw, modal_box, color=CYAN, length=14, width=2)
        
        # Modal Titlebar
        draw.rectangle([30, 25, W - 30, 60], fill=(10, 15, 26, 255))
        draw.line([(30, 60), (W - 30, 60)], fill=(0, 240, 255, 80), width=1)
        
        # Traffic light dots
        draw.ellipse([45, 39, 53, 47], fill=(239, 68, 68))
        draw.ellipse([58, 39, 66, 47], fill=(245, 158, 11))
        draw.ellipse([71, 39, 79, 47], fill=(16, 185, 129))
        
        font_mt = get_font("mono", 12, bold=True)
        draw.text((95, 35), "OGC STAC v1.0.0 // RADAR TASKING ORDER DISPATCH", fill=WHITE, font=font_mt)
        
        # Parameters Summary Row
        p_box = [45, 72, W - 45, 112]
        draw_rounded_rect(draw, p_box, fill=(20, 29, 48), outline=(51, 65, 85), radius=6)
        
        font_p = get_font("mono", 11, bold=False)
        draw.text((58, 84), "PLATFORM: ICEYE-X38   MODE: SPOTLIGHT 0.5m   INC: 28.4°   RULE: e2s-014", fill=CYAN, font=font_p)
        
        # Code Editor Box
        c_box = [45, 122, W - 45, H - 80]
        draw_rounded_rect(draw, c_box, fill=(10, 14, 23), outline=(30, 41, 59), radius=6)
        
        # Render code lines
        font_code = get_font("mono", 11, bold=False)
        cy = 132
        for line_txt, line_col in code_lines:
            draw.text((60, cy), line_txt, fill=line_col, font=font_code)
            cy += 16
            
        # Copy Button Animation
        # Frame 0 to 18: moving cursor towards button
        # Frame 18 to 36: button clicked, emerald green with checkmark!
        btn_box = [W - 225, H - 70, W - 45, H - 38]
        is_clicked = (i >= 18)
        
        if not is_clicked:
            draw.rounded_rectangle(btn_box, radius=6, fill=(0, 240, 255, 40), outline=CYAN, width=1)
            font_btn = get_font("segoe", 12, bold=True)
            draw.text((W - 200, H - 62), "📋 Copy STAC JSON", fill=CYAN, font=font_btn)
        else:
            draw.rounded_rectangle(btn_box, radius=6, fill=(16, 185, 129, 50), outline=EMERALD, width=2)
            font_btn = get_font("segoe", 12, bold=True)
            draw.text((W - 215, H - 62), "✓ COPIED TO CLIPBOARD!", fill=EMERALD, font=font_btn)
            
            # Checkmark flash particles
            for p_off in [-15, 0, 15]:
                draw.ellipse([W - 130 + p_off, H - 80, W - 124 + p_off, H - 74], fill=EMERALD)
                
        # Cursor arrow moving towards button
        if i < 18:
            cp = i / 18.0
            cur_x = int(320 + cp * (W - 140 - 320))
            cur_y = int(280 + cp * (H - 55 - 280))
        else:
            cur_x = W - 140
            cur_y = H - 55
            
        # Draw high-tech pointer cursor
        draw.polygon([(cur_x, cur_y), (cur_x + 12, cur_y + 12), (cur_x + 5, cur_y + 13), (cur_x + 8, cur_y + 20), (cur_x + 4, cur_y + 21), (cur_x + 1, cur_y + 14), (cur_x - 3, cur_y + 17)], fill=WHITE, outline=(0, 0, 0))

        # Quantize
        im_p = im.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        frames.append(im_p)

    out_path = os.path.join(OUTPUT_DIR, "gif_04_stac_tasking_order.gif")
    frames[0].save(out_path, save_all=True, append_images=frames[1:], duration=70, loop=0, optimize=True)
    print(f"  ✓ gif_04_stac_tasking_order.gif saved ({os.path.getsize(out_path)} bytes)")


# =============================================================================
# 8. HTML ASSET CATALOG / PREVIEWER
# =============================================================================
def generate_html_previewer():
    print("Generating Interactive HTML Asset Previewer (linkedin_campaign/assets_preview.html)...")
    
    # Collect all generated files with metadata
    all_files = sorted(os.listdir(OUTPUT_DIR))
    assets = []
    
    for f in all_files:
        fpath = os.path.join(OUTPUT_DIR, f)
        if not os.path.isfile(fpath):
            continue
        size_bytes = os.path.getsize(fpath)
        size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024*1024 else f"{size_bytes / (1024*1024):.2f} MB"
        
        # Determine category & dimensions
        category = "Unknown"
        dims = "Unknown"
        aspect = "Unknown"
        placement = "LinkedIn Sponsored Content"
        desc = ""
        
        try:
            with Image.open(fpath) as img:
                w, h = img.size
                dims = f"{w} x {h}"
                if w == 1200 and h == 627:
                    aspect = "1.91 : 1 (Landscape)"
                    category = "Landscape Cards"
                    desc = "Single-Image Sponsored Content with bold metric chips and Rule e2s-014 compliance seals."
                elif w == 1080 and h == 1080:
                    aspect = "1 : 1 (Square)"
                    if f.startswith("carousel"):
                        category = "Carousel Deck"
                        desc = "Part of 10-card carousel story sequence covering the 11 scientific research runs."
                    else:
                        category = "Square Cards"
                        desc = "Mobile feed-optimized 1:1 single image ad with high-contrast metric callouts."
                elif f.endswith(".gif"):
                    aspect = f"{w}:{h}"
                    category = "Animated GIFs"
                    desc = f"Smooth looping animation (< 5MB) for dynamic motion sponsored posts and video placements."
        except Exception:
            pass
            
        assets.append({
            "filename": f,
            "rel_path": f"assets/{f}",
            "size_str": size_str,
            "size_bytes": size_bytes,
            "category": category,
            "dimensions": dims,
            "aspect": aspect,
            "placement": placement,
            "desc": desc
        })

    # Render HTML template
    assets_json = json.dumps(assets, indent=2)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Earth-2 X-Band SAR & InSAR | LinkedIn Campaign Asset Catalog</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0b0f19;
      --card-bg: rgba(15, 23, 42, 0.75);
      --card-border: rgba(0, 240, 255, 0.2);
      --cyan: #00f0ff;
      --cyan-glow: rgba(0, 240, 255, 0.35);
      --emerald: #10b981;
      --amber: #f59e0b;
      --purple: #a855f7;
      --text: #f8fafc;
      --muted: #94a3b8;
      --mono: 'JetBrains Mono', monospace;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      min-height: 100vh;
      padding-bottom: 60px;
      line-height: 1.5;
    }}
    /* Cyber Grid */
    body::before {{
      content: "";
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at 50% 15%, rgba(0, 240, 255, 0.08), transparent 60%),
                  linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px),
                  linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px);
      background-size: 100% 100%, 40px 40px, 40px 40px;
      pointer-events: none;
      z-index: 0;
    }}
    .container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 28px;
      position: relative;
      z-index: 1;
    }}
    header {{
      padding: 36px 0 28px;
      border-bottom: 1px solid rgba(0, 240, 255, 0.15);
      margin-bottom: 32px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      flex-wrap: wrap;
      gap: 20px;
    }}
    .brand-title {{
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.5px;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .pulse-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 12px var(--emerald);
    }}
    .brand-sub {{
      font-size: 14px;
      color: var(--muted);
      margin-top: 6px;
      font-family: var(--mono);
    }}
    .stats-bar {{
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
    }}
    .stat-pill {{
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      border-radius: 8px;
      font-family: var(--mono);
      font-size: 13px;
    }}
    .stat-pill strong {{
      color: var(--cyan);
    }}
    /* Tabs */
    .filter-tabs {{
      display: flex;
      gap: 10px;
      margin-bottom: 28px;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: var(--muted);
      padding: 10px 20px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      font-size: 14px;
      transition: all 0.2s ease;
    }}
    .tab-btn:hover {{
      border-color: var(--cyan);
      color: #fff;
    }}
    .tab-btn.active {{
      background: rgba(0, 240, 255, 0.15);
      border-color: var(--cyan);
      color: var(--cyan);
      box-shadow: 0 0 15px rgba(0, 240, 255, 0.2);
    }}
    /* Grid */
    .media-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 28px;
    }}
    .media-card {{
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .media-card:hover {{
      transform: translateY(-4px);
      border-color: var(--cyan);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.6), 0 0 20px rgba(0, 240, 255, 0.15);
    }}
    .preview-box {{
      width: 100%;
      height: 260px;
      background: #070a12;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      overflow: hidden;
      cursor: pointer;
    }}
    .preview-box img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      transition: transform 0.3s ease;
    }}
    .preview-box:hover img {{
      transform: scale(1.03);
    }}
    .badge-float {{
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(11, 15, 25, 0.85);
      border: 1px solid var(--cyan);
      color: var(--cyan);
      font-family: var(--mono);
      font-size: 11px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 4px;
    }}
    .card-body {{
      padding: 20px;
      display: flex;
      flex-direction: column;
      flex: 1;
    }}
    .card-title {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
      word-break: break-all;
    }}
    .card-desc {{
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 16px;
      flex: 1;
    }}
    .specs-list {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      font-family: var(--mono);
      font-size: 11px;
      background: rgba(11, 15, 25, 0.6);
      padding: 10px 12px;
      border-radius: 6px;
      margin-bottom: 16px;
      border: 1px solid rgba(255, 255, 255, 0.05);
    }}
    .spec-item {{
      color: var(--muted);
    }}
    .spec-item span {{
      color: #fff;
      font-weight: 600;
    }}
    .card-actions {{
      display: flex;
      gap: 10px;
    }}
    .btn {{
      flex: 1;
      padding: 10px 14px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      text-align: center;
      text-decoration: none;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .btn-primary {{
      background: rgba(0, 240, 255, 0.15);
      border: 1px solid var(--cyan);
      color: var(--cyan);
    }}
    .btn-primary:hover {{
      background: var(--cyan);
      color: #0b0f19;
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.4);
    }}
    .btn-secondary {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #fff;
    }}
    .btn-secondary:hover {{
      background: rgba(255, 255, 255, 0.12);
    }}
    /* Lightbox Modal */
    #lightbox {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(5, 8, 15, 0.92);
      backdrop-filter: blur(16px);
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 40px;
    }}
    #lightbox.active {{
      display: flex;
    }}
    .lightbox-content {{
      max-width: 90vw;
      max-height: 85vh;
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .lightbox-content img {{
      max-width: 100%;
      max-height: 75vh;
      object-fit: contain;
      border-radius: 8px;
      border: 1px solid var(--cyan);
      box-shadow: 0 0 40px rgba(0, 240, 255, 0.25);
    }}
    .lightbox-meta {{
      margin-top: 16px;
      color: #fff;
      font-family: var(--mono);
      font-size: 14px;
      text-align: center;
    }}
    .close-btn {{
      position: absolute;
      top: -38px;
      right: 0;
      background: none;
      border: none;
      color: var(--muted);
      font-size: 28px;
      cursor: pointer;
    }}
    .close-btn:hover {{
      color: var(--cyan);
    }}
  </style>
</head>
<body>

<div class="container">
  <header>
    <div>
      <div class="brand-title">
        <div class="pulse-dot"></div>
        EARTH-2 // LINKEDIN CAMPAIGN ASSET SUITE
      </div>
      <div class="brand-sub">
        X-BAND SAR & InSAR MISSION TWIN &bull; RULE e2s-014 VERIFIED &bull; OGC STAC v1.0.0
      </div>
    </div>
    <div class="stats-bar">
      <div class="stat-pill">Total Assets: <strong id="total-count">{len(assets)}</strong></div>
      <div class="stat-pill">Landscape: <strong>5</strong></div>
      <div class="stat-pill">Square: <strong>5</strong></div>
      <div class="stat-pill">Carousel Cards: <strong>10</strong></div>
      <div class="stat-pill">Animated GIFs: <strong>4</strong></div>
    </div>
  </header>

  <div class="filter-tabs">
    <button class="tab-btn active" data-filter="all">All Assets ({len(assets)})</button>
    <button class="tab-btn" data-filter="Landscape Cards">Landscape (1200x627)</button>
    <button class="tab-btn" data-filter="Square Cards">Square (1080x1080)</button>
    <button class="tab-btn" data-filter="Carousel Deck">Carousel Deck (10 Cards)</button>
    <button class="tab-btn" data-filter="Animated GIFs">Animated GIFs</button>
  </div>

  <div class="media-grid" id="grid">
    <!-- Populated by JavaScript -->
  </div>
</div>

<div id="lightbox" onclick="closeLightbox(event)">
  <div class="lightbox-content" onclick="event.stopPropagation()">
    <button class="close-btn" onclick="closeLightbox()">&times;</button>
    <img id="lightbox-img" src="" alt="Enlarged preview">
    <div class="lightbox-meta" id="lightbox-meta"></div>
  </div>
</div>

<script>
  const ASSETS = {assets_json};

  function renderGrid(filter = "all") {{
    const grid = document.getElementById("grid");
    grid.innerHTML = "";

    const filtered = filter === "all" ? ASSETS : ASSETS.filter(a => a.category === filter);

    filtered.forEach(item => {{
      const card = document.createElement("div");
      card.className = "media-card";

      card.innerHTML = `
        <div class="preview-box" onclick="openLightbox('${{item.rel_path}}', '${{item.filename}}', '${{item.dimensions}}', '${{item.size_str}}')">
          <img src="${{item.rel_path}}" alt="${{item.filename}}" loading="lazy">
          <div class="badge-float">${{item.category}}</div>
        </div>
        <div class="card-body">
          <div class="card-title">${{item.filename}}</div>
          <div class="card-desc">${{item.desc}}</div>
          <div class="specs-list">
            <div class="spec-item">Dimensions: <span>${{item.dimensions}}</span></div>
            <div class="spec-item">Size: <span>${{item.size_str}}</span></div>
            <div class="spec-item">Ratio: <span>${{item.aspect}}</span></div>
            <div class="spec-item">Placement: <span>Sponsored</span></div>
          </div>
          <div class="card-actions">
            <a href="${{item.rel_path}}" download="${{item.filename}}" class="btn btn-primary">
              ⬇ Download
            </a>
            <button onclick="openLightbox('${{item.rel_path}}', '${{item.filename}}', '${{item.dimensions}}', '${{item.size_str}}')" class="btn btn-secondary">
              🔍 Inspect
            </button>
          </div>
        </div>
      `;
      grid.appendChild(card);
    }});
  }}

  // Filter Buttons
  document.querySelectorAll(".tab-btn").forEach(btn => {{
    btn.addEventListener("click", () => {{
      document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      renderGrid(btn.getAttribute("data-filter"));
    }});
  }});

  // Lightbox
  function openLightbox(src, name, dims, size) {{
    document.getElementById("lightbox-img").src = src;
    document.getElementById("lightbox-meta").innerHTML = `<strong>${{name}}</strong> &bull; ${{dims}} &bull; ${{size}}`;
    document.getElementById("lightbox").classList.add("active");
  }}

  function closeLightbox(e) {{
    document.getElementById("lightbox").classList.remove("active");
  }}

  document.addEventListener("keydown", (e) => {{
    if (e.key === "Escape") closeLightbox();
  }});

  // Initial render
  renderGrid("all");
</script>

</body>
</html>
"""

    with open(HTML_PREVIEW_PATH, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  ✓ {HTML_PREVIEW_PATH} saved ({os.path.getsize(HTML_PREVIEW_PATH)} bytes)")


# =============================================================================
# MAIN ORCHESTRATION & VALIDATION
# =============================================================================
def main():
    t0 = time.time()
    print("=" * 70)
    print("EARTH-2 // LINKEDIN AD CAMPAIGN MEDIA COMPILER")
    print("Rule e2s-014 Scientific Integrity Enforcement")
    print("=" * 70)

    # 1. Generate Static Landscape Cards
    generate_landscape_cards()

    # 2. Generate Static Square Cards
    generate_square_cards()

    # 3. Generate 10-Card Carousel Deck
    generate_carousel_cards()

    # 4. Generate 4 Animated GIFs
    generate_gif_01_global_mission_twin()
    generate_gif_02_insar_phase_split_slider()
    generate_gif_03_swath_activation_theater_hop()
    generate_gif_04_stac_tasking_order()

    # 5. Generate Asset Previewer HTML
    generate_html_previewer()

    # 6. Audit & Validation
    print("=" * 70)
    print("AUDIT & VERIFICATION MANIFEST:")
    print("=" * 70)
    total_files = 0
    total_bytes = 0

    all_assets = sorted(os.listdir(OUTPUT_DIR))
    for f in all_assets:
        p = os.path.join(OUTPUT_DIR, f)
        if not os.path.isfile(p):
            continue
        sz = os.path.getsize(p)
        total_files += 1
        total_bytes += sz
        
        # Check dimensions & gif limits
        extra = ""
        if f.endswith(".png"):
            with Image.open(p) as img:
                extra = f"{img.size[0]}x{img.size[1]}"
        elif f.endswith(".gif"):
            with Image.open(p) as img:
                mb = sz / (1024 * 1024)
                extra = f"{img.size[0]}x{img.size[1]}, {mb:.2f}MB (<5MB limit)"
                assert sz < 5 * 1024 * 1024, f"ERROR: {f} exceeds 5MB LinkedIn limit!"

        print(f"  • {f:<42} | {sz:>9} bytes | {extra}")

    print("-" * 70)
    print(f"Total Assets Generated: {total_files} files ({total_bytes / (1024*1024):.2f} MB)")
    print(f"HTML Previewer: {HTML_PREVIEW_PATH} ({os.path.getsize(HTML_PREVIEW_PATH)} bytes)")
    print(f"Execution Completed in {time.time() - t0:.2f} seconds.")
    print("=" * 70)


if __name__ == "__main__":
    main()
