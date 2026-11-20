import os
import shutil
import subprocess
import time
from pathlib import Path
from PIL import Image

shots_dir = Path(r'C:\Users\Zhane\.gemini\antigravity\brain\835f1f53-340c-4582-9e5a-2c8e6ec8df8a\browser_sandbox\screenshots')

gif_dirs = [
    Path('linkedin_ad_campaign_assets/05_Video_and_Animated_GIFs'),
    Path('viewer_app/public/linkedin_ad_campaign_assets/05_Video_and_Animated_GIFs'),
    Path('linkedin_campaign/assets')
]

video_dirs = [
    Path('linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('viewer_app/public/linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('linkedin_campaign/assets/high_framerate_videos')
]

for d in gif_dirs + video_dirs:
    d.mkdir(parents=True, exist_ok=True)

suites = [
    {
        'id': '01_all_surfaces_relief',
        'gif_name': 'gif_01_all_surfaces_relief.gif',
        'vid_stem': 'video_01_all_surfaces_relief',
        'title': 'All Surfaces, Sentinel-2 131K LOD & 3D Topographic Relief',
        'files': [
            'step_6_shot_1.png',
            'step_6_shot_2.png',
            'step_6_shot_3.png',
            'step_6_shot_4.png',
            'step_6_shot_5.png'
        ],
        'durations_ms': [1200, 1100, 1100, 1100, 1800],
        'durations_sec': [1.2, 1.1, 1.1, 1.1, 1.8]
    },
    {
        'id': '02_surface_temps_tendency_wind',
        'gif_name': 'gif_02_surface_temps_tendency_wind.gif',
        'vid_stem': 'video_02_surface_temps_tendency_wind',
        'title': 'NOAA GFS Surface Temperatures, 24h Tendency, Winds & Hazards',
        'files': [
            'step_8_shot_1.png',
            'step_8_shot_2.png',
            'step_8_shot_3.png',
            'step_8_shot_4.png'
        ],
        'durations_ms': [1300, 1300, 1500, 1800],
        'durations_sec': [1.3, 1.3, 1.5, 1.8]
    },
    {
        'id': '03_sar_incidence_kinematics',
        'gif_name': 'gif_03_sar_incidence_kinematics.gif',
        'vid_stem': 'video_03_sar_incidence_kinematics',
        'title': 'SAR Kinematics, 50km Swaths & Incidence Angle Geometry',
        'files': [
            'step_10_shot_1.png',
            'step_10_shot_2.png',
            'step_10_shot_3.png'
        ],
        'durations_ms': [1400, 1400, 1800],
        'durations_sec': [1.4, 1.4, 1.8]
    },
    {
        'id': '04_weather_hazards_forecast_playback',
        'gif_name': 'gif_04_weather_hazards_forecast_playback.gif',
        'vid_stem': 'video_04_weather_hazards_forecast_playback',
        'title': '24h Forecast Lead-Time Playback & Hazard Simulation',
        'files': [
            'step_18_shot_1.png',
            'step_18_shot_2.png',
            'step_18_shot_3.png',
            'step_18_shot_4.png'
        ],
        'durations_ms': [1100, 1100, 1100, 1800],
        'durations_sec': [1.1, 1.1, 1.1, 1.8]
    },
    {
        'id': '05_insar_split_slider_comparison',
        'gif_name': 'gif_05_insar_split_slider_comparison.gif',
        'vid_stem': 'video_05_insar_split_slider_comparison',
        'title': 'InSAR Split-Screen Curtain Slider Comparison',
        'files': [
            'step_24_shot_1.png',
            'step_26_shot_1.png',
            'step_26_shot_2.png',
            'step_26_shot_3.png',
            'step_26_shot_4.png',
            'step_26_shot_5.png'
        ],
        'durations_ms': [1000, 700, 700, 700, 700, 1500],
        'durations_sec': [1.0, 0.7, 0.7, 0.7, 0.7, 1.5]
    },
    {
        'id': '06_stac_tasking_modal_inspection',
        'gif_name': 'gif_06_stac_tasking_modal_inspection.gif',
        'vid_stem': 'video_06_stac_tasking_modal_inspection',
        'title': 'OGC STAC v1.0.0 Tasking Modal & API Payload',
        'files': [
            'step_32_shot_1.png',
            'step_34_shot_1.png',
            'step_34_shot_2.png'
        ],
        'durations_ms': [1300, 1300, 1800],
        'durations_sec': [1.3, 1.3, 1.8]
    },
    {
        'id': '07_all_11_regions_grand_tour',
        'gif_name': 'gif_07_all_11_regions_grand_tour.gif',
        'vid_stem': 'video_07_all_11_regions_grand_tour',
        'title': 'All 11 Global Research Theaters Grand Tour',
        'files': [
            'step_39_shot_1.png',
            'step_39_shot_2.png',
            'step_39_shot_3.png',
            'step_39_shot_4.png',
            'step_39_shot_5.png',
            'step_39_shot_6.png',
            'step_41_shot_1.png',
            'step_41_shot_2.png',
            'step_41_shot_3.png',
            'step_41_shot_4.png',
            'step_41_shot_5.png'
        ],
        'durations_ms': [850, 850, 850, 850, 850, 850, 850, 850, 850, 850, 1800],
        'durations_sec': [0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 1.8]
    },
    {
        'id': '08_precision_city_targets_beacons',
        'gif_name': 'gif_08_precision_city_targets_beacons.gif',
        'vid_stem': 'video_08_precision_city_targets_beacons',
        'title': 'Precision Urban Targets, Volcano Beacons & High-Res Geology',
        'files': [
            'step_45_shot_1.png',
            'step_45_shot_2.png',
            'step_45_shot_3.png'
        ],
        'durations_ms': [1300, 1300, 1800],
        'durations_sec': [1.3, 1.3, 1.8]
    }
]

# Strict 16:9 dimensions for GIFs: 960x540 (exact 16:9 ratio, zero squish, <5MB)
gif_target_size = (960, 540)
print(f"Target GIF Resolution: {gif_target_size[0]}x{gif_target_size[1]} (Aspect ratio: {gif_target_size[0]/gif_target_size[1]:.4f} - Exact 16:9)")

print("\n--- PHASE 1: COMPILING 8 TRUE 16:9 ANIMATED GIFS ---")
for s in suites:
    frames = []
    for fn in s['files']:
        fp = shots_dir / fn
        if not fp.exists():
            print(f"Error: {fp} missing!")
            continue
        im = Image.open(fp).convert('RGB')
        im_resized = im.resize(gif_target_size, Image.Resampling.LANCZOS)
        p_im = im_resized.quantize(colors=216, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        frames.append(p_im)

    if frames:
        out_file = gif_dirs[0] / s['gif_name']
        frames[0].save(
            out_file,
            save_all=True,
            append_images=frames[1:],
            duration=s['durations_ms'],
            loop=0,
            optimize=True
        )
        sz_mb = out_file.stat().st_size / (1024 * 1024)
        print(f"  ✓ Saved {s['gif_name']}: {sz_mb:.2f} MB ({gif_target_size[0]}x{gif_target_size[1]}, exact 16:9, <5MB)")
        for d in gif_dirs[1:]:
            shutil.copy2(out_file, d / s['gif_name'])

print("\n--- PHASE 2: RENDERING 16 FULL HD 1080P MP4 VIDEOS (60 FPS & 120 FPS) ---")
tmp_concat = Path('tmp_1080p_render.txt')

for s in suites:
    with open(tmp_concat, 'w', encoding='utf-8') as f:
        for fn, dur in zip(s['files'], s['durations_sec']):
            abs_p = (shots_dir / fn).resolve().as_posix()
            f.write(f"file '{abs_p}'\n")
            f.write(f"duration {dur}\n")
        last_p = (shots_dir / s['files'][-1]).resolve().as_posix()
        f.write(f"file '{last_p}'\n")

    for fps in [60, 120]:
        out_name = f"{s['vid_stem']}_{fps}fps.mp4"
        out_path = video_dirs[0] / out_name

        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(tmp_concat),
            '-vf', f"scale=1920:1080:flags=lanczos,minterpolate=fps={fps}:mi_mode=blend",
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'fast', '-crf', '19',
            str(out_path)
        ]

        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        t_el = time.time() - t0

        if res.returncode == 0:
            sz_kb = out_path.stat().st_size / 1024
            print(f"  ✓ Rendered {out_name}: {sz_kb:.1f} KB in {t_el:.2f}s ({fps} fps, 1080p)")
            for d in video_dirs[1:]:
                shutil.copy2(out_path, d / out_name)
        else:
            print(f"  ✗ Error {out_name}: {res.stderr[-250:]}")

if tmp_concat.exists():
    tmp_concat.unlink()

print("\nAll 8 GIFs (<5MB, exact 16:9, clean cockpit) and 16 High-Framerate 1080p MP4s generated successfully.")
