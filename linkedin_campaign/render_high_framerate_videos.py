import os
import shutil
import subprocess
import time
from pathlib import Path

shots_dir = Path(r'C:\Users\Zhane\.gemini\antigravity\brain\9bb6996a-c327-4149-beb9-c86629736761\browser_sandbox\screenshots')

out_dirs = [
    Path('linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('viewer_app/public/linkedin_ad_campaign_assets/05_High_Framerate_Videos_60fps_120fps'),
    Path('linkedin_campaign/assets/high_framerate_videos')
]

for d in out_dirs:
    d.mkdir(parents=True, exist_ok=True)

workflows = [
    {
        'id': 'video_01_globe_orbit_swath_flyto',
        'files': [
            'step_79_shot_1.png', 'step_79_shot_2.png', 'step_79_shot_3.png',
            'step_79_shot_4.png', 'step_79_shot_5.png', 'step_79_shot_6.png',
            'step_79_shot_7.png', 'step_79_shot_8.png', 'step_79_shot_9.png'
        ],
        'durations': [1.2, 0.75, 0.75, 0.95, 0.75, 0.75, 0.75, 0.95, 1.8],
        'title': '3D Globe Rotation & Swath Fly-To'
    },
    {
        'id': 'video_02_insar_split_slider_wipe',
        'files': [
            'step_100_shot_1.png', 'step_100_shot_2.png', 'step_100_shot_3.png',
            'step_100_shot_4.png', 'step_100_shot_5.png', 'step_100_shot_6.png',
            'step_100_shot_7.png', 'step_100_shot_8.png', 'step_102_shot_1.png'
        ],
        'durations': [1.1, 0.7, 0.7, 0.7, 0.7, 0.7, 1.3, 0.95, 1.1],
        'title': 'InSAR Split Comparison Slider'
    },
    {
        'id': 'video_03_run_gallery_filter_browse',
        'files': [
            'step_104_shot_1.png', 'step_104_shot_2.png', 'step_104_shot_3.png',
            'step_104_shot_4.png', 'step_104_shot_5.png', 'step_104_shot_6.png',
            'step_104_shot_7.png', 'step_104_shot_8.png', 'step_104_shot_9.png'
        ],
        'durations': [1.2, 0.8, 0.8, 0.8, 1.0, 1.0, 1.4, 0.85, 0.95],
        'title': 'Run Gallery Browsing & Filter Search'
    },
    {
        'id': 'video_04_stac_tasking_modal_inspect',
        'files': [
            'step_114_shot_1.png', 'step_116_shot_1.png', 'step_116_shot_2.png',
            'step_116_shot_3.png', 'step_116_shot_4.png', 'step_116_shot_5.png',
            'step_116_shot_6.png'
        ],
        'durations': [1.3, 0.9, 0.9, 0.9, 1.2, 0.75, 1.6],
        'title': 'OGC STAC Tasking Modal Inspection'
    },
    {
        'id': 'video_05_multitheater_quickjump_tour',
        'files': [
            'step_120_shot_1.png', 'step_120_shot_2.png', 'step_120_shot_3.png',
            'step_120_shot_4.png', 'step_122_shot_1.png', 'step_122_shot_2.png',
            'step_122_shot_3.png', 'step_122_shot_4.png', 'step_122_shot_5.png',
            'step_122_shot_6.png'
        ],
        'durations': [0.75, 1.2, 0.75, 1.2, 0.75, 1.2, 0.75, 1.2, 0.75, 1.5],
        'title': 'Multi-Theater Global Quick-Jumps'
    },
    {
        'id': 'video_06_hud_telemetry_orbit_scrub',
        'files': [
            'step_124_shot_1.png', 'step_124_shot_2.png', 'step_124_shot_3.png',
            'step_124_shot_4.png', 'step_126_shot_1.png', 'step_126_shot_2.png',
            'step_126_shot_3.png', 'step_126_shot_4.png'
        ],
        'durations': [1.1, 1.0, 1.2, 1.1, 0.85, 0.85, 0.85, 1.5],
        'title': 'HUD Telemetry & Mode Toggles'
    }
]

framerates = [60, 120]
tmp_concat = Path('tmp_render_concat.txt')

for wf in workflows:
    # 1. Generate concat file
    with open(tmp_concat, 'w', encoding='utf-8') as f:
        for fn, dur in zip(wf['files'], wf['durations']):
            abs_p = (shots_dir / fn).resolve().as_posix()
            f.write(f"file '{abs_p}'\n")
            f.write(f"duration {dur}\n")
        last_p = (shots_dir / wf['files'][-1]).resolve().as_posix()
        f.write(f"file '{last_p}'\n")

    for fps in framerates:
        out_name = f"{wf['id']}_{fps}fps.mp4"
        out_path = out_dirs[0] / out_name
        
        # 1080p 1920x1080 Lanczos scaling, minterpolate frame blending at target fps, x264 yuv420p
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
            print(f"Rendered {out_name}: {size_kb:.1f} KB in {t_el:.2f}s ({fps} fps, 1080p)")
            for d in out_dirs[1:]:
                shutil.copy2(out_path, d / out_name)
        else:
            print(f"Error rendering {out_name}: {res.stderr[-300:]}")

if tmp_concat.exists():
    tmp_concat.unlink()

print("All 60 fps & 120 fps 1080p MP4 videos rendered and mirrored successfully.")
