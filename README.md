# 18 Video Effects

Igu Shub's 18 short-form video effects, made with Claude. They're built as live, scrubbable 9:16 compositions in a single HTML file, with no build step and no assets.

Open `index.html` in a browser. Click any effect to view it full size, play or pause it, scrub the timeline, step frame by frame (←/→), or change the speed.

| # | Effect | What it does |
|---|--------|--------------|
| 01 | Orbit | Labels orbit the subject on a tilted 3D ring and pass behind the head |
| 02 | Chat Takeover | Chat bubbles stack up until they swallow the shot |
| 03 | Frame Escape | The subject rises out of a framed photo, past its edge |
| 04 | Snap Zoom | Beat-synced punch-ins with blur, flash, shake and word pops |
| 05 | Checklist Pop | Checklist card with bouncy check-offs and strike-throughs |
| 06 | Headline Storm | Newspaper headlines slam in from all sides and shake the frame |
| 07 | Zoom Portal | A glowing portal opens and the camera dives through it |
| 08 | Growth Curve | Self-drawing chart with a counter that tracks the line |
| 09 | B-roll Overlay | PiP B-roll cards slide in and one expands to full frame |
| 10 | Paper Cutout | 8 fps stop-motion collage with a sticker-outlined subject |
| 11 | Magazine Cover | Flash-freeze into a cover with the masthead behind the head |
| 12 | Liquid Glass | Refractive glass shapes bend the footage behind them |
| 13 | Zoom Through Cut | Type filled with the next shot; the camera flies through the letters |
| 14 | Green Screen | Real per-pixel chroma key with spill suppression and a raw/keyed wipe |
| 15 | Frame Break | The shot cracks and shatters toward camera, revealing the next scene |
| 16 | Digital Zoom | Pixelating "enhance" zoom with a camera HUD |
| 17 | Phone Mockup | The clip plays in a 3D phone feed, then pops out to full frame |
| 18 | Checklist Tally | Running score ring, hand-drawn tally marks and a completion stamp |

## Using your own clip

Click **Use your own clip** to swap the procedural footage for any local video. The video never leaves your browser.

Limits:
- **Green Screen** keys your clip for real, if it was shot on green.
- **Orbit, Frame Escape, Paper Cutout and Magazine Cover** rely on a cut-out subject layer. Person segmentation isn't included, so with your own clip these effects fall back to the full frame.
- There's no video export. To capture an effect, screen-record the full-size view.

## Ready-made videos

`videos/` has all 18 effects as MP4 files: 1080×1920 (9:16), 30 fps, one seamless loop each. Import them into any free editor, such as CapCut, InShot or VN.
