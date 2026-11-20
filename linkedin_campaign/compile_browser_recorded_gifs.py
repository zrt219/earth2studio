import os
import shutil
from pathlib import Path
from PIL import Image

shots_dir = Path(r'C:\Users\Zhane\.gemini\antigravity\brain\9bb6996a-c327-4149-beb9-c86629736761\browser_sandbox\screenshots')

out_dirs = [
    Path('linkedin_ad_campaign_assets/05_Video_and_Animated_GIFs'),
    Path('viewer_app/public/linkedin_ad_campaign_assets/05_Video_and_Animated_GIFs'),
    Path('linkedin_campaign/assets')
]

for d in out_dirs:
    d.mkdir(parents=True, exist_ok=True)

# Clean out old synthetic GIFs in these folders
for d in out_dirs:
    for old_gif in d.glob('gif_*.gif'):
        old_gif.unlink(missing_ok=True)

workflows = [
    {
        'filename': 'gif_01_globe_orbit_swath_flyto.gif',
        'files': [
            'step_79_shot_1.png', 'step_79_shot_2.png', 'step_79_shot_3.png',
            'step_79_shot_4.png', 'step_79_shot_5.png', 'step_79_shot_6.png',
            'step_79_shot_7.png', 'step_79_shot_8.png', 'step_79_shot_9.png'
        ],
        'durations': [1200, 750, 750, 950, 750, 750, 750, 950, 1800],
        'title': '3D Globe Rotation & Swath Fly-To'
    },
    {
        'filename': 'gif_02_insar_split_slider_wipe.gif',
        'files': [
            'step_100_shot_1.png', 'step_100_shot_2.png', 'step_100_shot_3.png',
            'step_100_shot_4.png', 'step_100_shot_5.png', 'step_100_shot_6.png',
            'step_100_shot_7.png', 'step_100_shot_8.png', 'step_102_shot_1.png'
        ],
        'durations': [1100, 700, 700, 700, 700, 700, 1300, 950, 1100],
        'title': 'InSAR Split Comparison Slider'
    },
    {
        'filename': 'gif_03_run_gallery_filter_browse.gif',
        'files': [
            'step_104_shot_1.png', 'step_104_shot_2.png', 'step_104_shot_3.png',
            'step_104_shot_4.png', 'step_104_shot_5.png', 'step_104_shot_6.png',
            'step_104_shot_7.png', 'step_104_shot_8.png', 'step_104_shot_9.png'
        ],
        'durations': [1200, 800, 800, 800, 1000, 1000, 1400, 850, 950],
        'title': 'Run Gallery Browsing & Filter Search'
    },
    {
        'filename': 'gif_04_stac_tasking_modal_inspect.gif',
        'files': [
            'step_114_shot_1.png', 'step_116_shot_1.png', 'step_116_shot_2.png',
            'step_116_shot_3.png', 'step_116_shot_4.png', 'step_116_shot_5.png',
            'step_116_shot_6.png'
        ],
        'durations': [1300, 900, 900, 900, 1200, 750, 1600],
        'title': 'OGC STAC Tasking Modal Inspection'
    },
    {
        'filename': 'gif_05_multitheater_quickjump_tour.gif',
        'files': [
            'step_120_shot_1.png', 'step_120_shot_2.png', 'step_120_shot_3.png',
            'step_120_shot_4.png', 'step_122_shot_1.png', 'step_122_shot_2.png',
            'step_122_shot_3.png', 'step_122_shot_4.png', 'step_122_shot_5.png',
            'step_122_shot_6.png'
        ],
        'durations': [750, 1200, 750, 1200, 750, 1200, 750, 1200, 750, 1500],
        'title': 'Multi-Theater Global Quick-Jumps'
    },
    {
        'filename': 'gif_06_hud_telemetry_orbit_scrub.gif',
        'files': [
            'step_124_shot_1.png', 'step_124_shot_2.png', 'step_124_shot_3.png',
            'step_124_shot_4.png', 'step_126_shot_1.png', 'step_126_shot_2.png',
            'step_126_shot_3.png', 'step_126_shot_4.png'
        ],
        'durations': [1100, 1000, 1200, 1100, 850, 850, 850, 1500],
        'title': 'HUD Telemetry & Mode Toggles'
    }
]

# Scale to crisp 960x600 for sharp telemetry text and smooth playback
target_size = (960, 600)

for wf in workflows:
    frames = []
    for f in wf['files']:
        im = Image.open(shots_dir / f).convert('RGB')
        im_resized = im.resize(target_size, Image.Resampling.LANCZOS)
        p_im = im_resized.quantize(colors=224, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
        frames.append(p_im)
    
    first_frame = frames[0]
    out_path = out_dirs[0] / wf['filename']
    first_frame.save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=wf['durations'],
        loop=0,
        optimize=True
    )
    size_kb = out_path.stat().st_size / 1024
    print(f"Compiled {wf['filename']}: {size_kb:.1f} KB, {len(frames)} frames")
    
    for d in out_dirs[1:]:
        shutil.copy2(out_path, d / wf['filename'])

print("All 6 pure browser screen-recorded GIFs compiled and mirrored successfully.")
