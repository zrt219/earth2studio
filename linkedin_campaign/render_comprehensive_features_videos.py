import os
import shutil
import subprocess
import time
from pathlib import Path

p_ee4f = Path(r'C:\Users\Zhane\.gemini\antigravity\brain\ee4f0f8c-839f-4fb8-9401-681aee9b97af\browser_sandbox\screenshots')
p_9bb = Path(r'C:\Users\Zhane\.gemini\antigravity\brain\9bb6996a-c327-4149-beb9-c86629736761\browser_sandbox\screenshots')

out_dirs = [
    Path('linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('viewer_app/public/linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('linkedin_campaign/assets/high_framerate_videos')
]

for d in out_dirs:
    d.mkdir(parents=True, exist_ok=True)

video_suites = [
    {
        'id': 'video_01_all_surfaces_relief',
        'title': 'All Surfaces, Sentinel-2 131K LOD & 3D Topographic Relief',
        'files': [
            p_ee4f / 'step_10.png',
            p_ee4f / 'step_12_shot_1.png',
            p_ee4f / 'step_12_shot_2.png',
            p_ee4f / 'step_14_shot_1.png',
            p_ee4f / 'step_14_shot_2.png',
            p_ee4f / 'step_14_shot_3.png',
            p_ee4f / 'step_14_shot_4.png'
        ],
        'durations': [1.2, 1.0, 1.2, 1.0, 1.2, 1.2, 1.8]
    },
    {
        'id': 'video_02_surface_temps_tendency_wind',
        'title': 'NOAA GFS Surface Temperatures (T2m), 24h Tendency, Wind Streamlines & Hazards',
        'files': [
            p_ee4f / 'step_16_shot_1.png',
            p_ee4f / 'step_16_shot_2.png',
            p_ee4f / 'step_16_shot_3.png',
            p_ee4f / 'step_16_shot_4.png',
            p_ee4f / 'step_16.png'
        ],
        'durations': [1.3, 1.3, 1.5, 1.5, 1.8]
    },
    {
        'id': 'video_03_sar_incidence_kinematics',
        'title': 'SAR Kinematics, 50km Swaths & Incidence Angle Geometry',
        'files': [
            p_9bb / 'step_79_shot_1.png',
            p_9bb / 'step_79_shot_2.png',
            p_9bb / 'step_79_shot_3.png',
            p_9bb / 'step_79_shot_4.png',
            p_9bb / 'step_79_shot_5.png',
            p_9bb / 'step_124_shot_1.png',
            p_9bb / 'step_124_shot_2.png',
            p_9bb / 'step_124_shot_3.png',
            p_9bb / 'step_124_shot_4.png'
        ],
        'durations': [1.1, 0.8, 0.8, 0.8, 1.1, 0.9, 0.9, 0.9, 1.5]
    },
    {
        'id': 'video_04_weather_hazards_forecast_playback',
        'title': '24h Forecast Lead-Time Playback & Extreme Weather Hazard Simulation',
        'files': [
            p_9bb / 'step_126_shot_1.png',
            p_9bb / 'step_126_shot_2.png',
            p_9bb / 'step_126_shot_3.png',
            p_9bb / 'step_126_shot_4.png',
            p_9bb / 'step_126.png'
        ],
        'durations': [1.2, 1.0, 1.0, 1.0, 1.8]
    },
    {
        'id': 'video_05_insar_split_slider_comparison',
        'title': 'Interactive InSAR Split Curtain Comparison Slider (Raw vs Displaced)',
        'files': [
            p_9bb / 'step_100_shot_1.png',
            p_9bb / 'step_100_shot_2.png',
            p_9bb / 'step_100_shot_3.png',
            p_9bb / 'step_100_shot_4.png',
            p_9bb / 'step_100_shot_5.png',
            p_9bb / 'step_100_shot_6.png',
            p_9bb / 'step_100_shot_7.png',
            p_9bb / 'step_100_shot_8.png',
            p_9bb / 'step_100.png'
        ],
        'durations': [1.0, 0.7, 0.7, 0.7, 0.7, 0.7, 0.8, 1.0, 1.5]
    },
    {
        'id': 'video_06_stac_tasking_modal_inspection',
        'title': 'OGC STAC v1.0.0 Tasking Order Modal Inspection & API Payload',
        'files': [
            p_9bb / 'step_114_shot_1.png',
            p_9bb / 'step_114.png',
            p_9bb / 'step_116_shot_1.png',
            p_9bb / 'step_116_shot_2.png',
            p_9bb / 'step_116_shot_3.png',
            p_9bb / 'step_116_shot_4.png',
            p_9bb / 'step_116_shot_5.png',
            p_9bb / 'step_116_shot_6.png',
            p_9bb / 'step_116.png'
        ],
        'durations': [1.2, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 1.6]
    },
    {
        'id': 'video_07_all_11_regions_grand_tour',
        'title': 'All 11 Global Research Theaters Orbital Grand Tour',
        'files': [
            p_ee4f / 'step_36_shot_1.png',
            p_ee4f / 'step_36_shot_2.png',
            p_ee4f / 'step_36_shot_3.png',
            p_ee4f / 'step_36_shot_4.png',
            p_ee4f / 'step_36_shot_5.png',
            p_ee4f / 'step_36_shot_6.png',
            p_ee4f / 'step_38_shot_1.png',
            p_ee4f / 'step_38_shot_2.png',
            p_ee4f / 'step_38_shot_3.png',
            p_ee4f / 'step_38_shot_4.png',
            p_ee4f / 'step_38_shot_5.png'
        ],
        'durations': [0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 1.8]
    },
    {
        'id': 'video_08_precision_city_targets_beacons',
        'title': 'Precision Urban Targets, Volcano Beacons & High-Res Geology',
        'files': [
            p_ee4f / 'step_22.png',
            p_ee4f / 'step_26_shot_1.png',
            p_ee4f / 'step_28_shot_1.png',
            p_ee4f / 'step_30_shot_1.png',
            p_ee4f / 'step_30_shot_2.png',
            p_ee4f / 'step_32_shot_1.png'
        ],
        'durations': [1.1, 1.2, 1.2, 1.2, 1.2, 1.8]
    }
]

framerates = [60, 120]
tmp_concat = Path('tmp_render_concat.txt')

print(f"Starting render of {len(video_suites)} video suites at {framerates} fps (1080p)...")

for vs in video_suites:
    print(f"\nProcessing: {vs['title']} ({vs['id']})...")
    with open(tmp_concat, 'w', encoding='utf-8') as f:
        for fp, dur in zip(vs['files'], vs['durations']):
            f.write(f"file '{fp.resolve().as_posix()}'\n")
            f.write(f"duration {dur}\n")
        f.write(f"file '{vs['files'][-1].resolve().as_posix()}'\n")

    for fps in framerates:
        out_name = f"{vs['id']}_{fps}fps.mp4"
        out_path = out_dirs[0] / out_name

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
            size_kb = out_path.stat().st_size / 1024
            print(f"  ✓ Rendered {out_name}: {size_kb:.1f} KB in {t_el:.2f}s ({fps} fps, 1080p)")
            for d in out_dirs[1:]:
                shutil.copy2(out_path, d / out_name)
        else:
            print(f"  ✗ Error rendering {out_name}: {res.stderr[-300:]}")

if tmp_concat.exists():
    tmp_concat.unlink()

print("\nRender completed successfully for all 16 MP4 videos.")
