# Uniform Phone Screenshot Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all nine step visuals use one 9:16 phone-screen frame while preserving every screenshot's full content, native aspect ratio, annotations, privacy masks, and current public URL.

**Architecture:** Keep each optimized image as a single downloaded asset. Add a fixed-ratio outer `.uniform-shot` frame with the same asset as a blurred CSS background, then place the original image and its annotation elements inside an aspect-ratio-preserving `.image-stage`. Update the optimizer so every rebuild produces the same structure.

**Tech Stack:** Static HTML/CSS, Python 3, Pillow, `unittest`, Playwright CLI, GitHub Pages.

## Global Constraints

- The original public URL must continue serving the latest page; no product-link change is required.
- The top QR code remains square and is not wrapped in a 9:16 frame.
- Nine step visuals use 9:16 outer frames.
- Foreground screenshots are fully visible, never cropped or stretched.
- Existing red markers remain positioned relative to the foreground screenshot.
- Existing “胡一” mosaics and the complete product name remain visible as designed.
- HTML stays below 100KB and image assets stay below 900KB.

---

### Task 1: Add Uniform-Frame Regression Tests

**Files:**
- Modify: `test_performance.py`

**Interfaces:**
- Consumes: generated `index.html` and the existing ten-image asset contract.
- Produces: `test_step_visuals_use_uniform_phone_frames()` and `test_uniform_frames_reuse_existing_assets_as_backgrounds()`.

- [ ] **Step 1: Write the failing tests**

Add assertions equivalent to:

```python
def test_step_visuals_use_uniform_phone_frames(self) -> None:
    self.assertEqual(self.html.count('class="frame uniform-shot"'), 8)
    self.assertEqual(self.html.count('class="frame uniform-shot icon-shot"'), 1)
    self.assertEqual(self.html.count('class="image-stage '), 8)
    self.assertIn("aspect-ratio: 9 / 16", self.html)

def test_uniform_frames_reuse_existing_assets_as_backgrounds(self) -> None:
    for number in range(2, 11):
        if number == 8:
            continue
        source = re.search(
            rf'src="(assets/{number:02d}-[^"]+)"', self.html
        ).group(1)
        self.assertIn(f"--shot-bg: url('{source}')", self.html)
    self.assertEqual(len(self.img_tags), 10)
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
& 'C:\Users\28350\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' '.\test_performance.py'
```

Expected: the two new tests fail because `uniform-shot` and `image-stage` do not exist.

- [ ] **Step 3: Commit the test only after the implementation task turns it green**

The test and implementation belong in one fix commit because the public page must never be left with a deliberately failing build.

---

### Task 2: Generate 9:16 Frames Without Breaking Annotations

**Files:**
- Modify: `optimize_site.py`
- Regenerate: `index.html`

**Interfaces:**
- Consumes: the embedded source H5 and optimized asset metadata `(asset_name, width, height)`.
- Produces: `find_matching_div(html: str, opening_start: int) -> tuple[int, int]` and `wrap_step_frame(html: str, asset_name: str, width: int, height: int, icon: bool = False) -> str`.

- [ ] **Step 1: Add a matching-div helper**

Implement a depth counter over `<div` and `</div>` tokens so nested `.app-icon-card` markup is handled safely:

```python
def find_matching_div(html: str, opening_start: int) -> tuple[int, int]:
    opening_end = html.index(">", opening_start) + 1
    depth = 1
    for match in re.finditer(r"<div\b|</div>", html[opening_end:]):
        token_start = opening_end + match.start()
        if match.group() == "<div":
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return token_start, token_start + len("</div>")
    raise ValueError("Unclosed frame div")
```

- [ ] **Step 2: Wrap each step frame**

Locate the image by `assets/{asset_name}`, find its nearest preceding `<div class="frame">`, and replace that block with:

```html
<div class="frame uniform-shot" style="--shot-bg: url('assets/example.webp');">
  <div class="image-stage fit-height" style="aspect-ratio: 720 / 1560;">
    <!-- existing image, marker, and tag markup unchanged -->
  </div>
</div>
```

Use `fit-height` when `width / height <= 9 / 16`, otherwise use `fit-width`. For `08-ima-app-icon.webp`, use `class="frame uniform-shot icon-shot"`, keep `.app-icon-card` as the direct child, and do not add a blurred background.

- [ ] **Step 3: Add the uniform-frame CSS**

Insert these rules after the existing frame-image rule:

```css
.uniform-shot {
  position: relative; aspect-ratio: 9 / 16; display: flex;
  align-items: center; justify-content: center; isolation: isolate;
  background: var(--cream-alt); overflow: hidden;
}
.uniform-shot::before {
  content: ""; position: absolute; inset: -24px; z-index: -2;
  background: var(--shot-bg) center / cover no-repeat;
  filter: blur(18px); transform: scale(1.08); opacity: 0.45;
}
.uniform-shot::after {
  content: ""; position: absolute; inset: 0; z-index: -1;
  background: rgba(20, 27, 43, 0.24);
}
.image-stage { position: relative; max-width: 100%; max-height: 100%; }
.image-stage.fit-height { height: 100%; width: auto; }
.image-stage.fit-width { width: 100%; height: auto; }
.image-stage > img { width: 100%; height: 100%; object-fit: contain; }
.uniform-shot .tap-marker, .uniform-shot .tap-tag { z-index: 2; }
.icon-shot::before, .icon-shot::after { display: none; }
.icon-shot .app-icon-card {
  width: 100%; height: 100%; padding: 30px 18px; background: var(--cream-alt);
}
```

- [ ] **Step 4: Regenerate the public HTML**

Run:

```powershell
& 'C:\Users\28350\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' '.\optimize_site.py' 'D:\ObsidianVaults\胡亿刀的工作台\00_虚拟产品\产出\Codex\儿童教育知识库_ima使用指南网页修改_2026-07-16\孩子自驱力培养_领取指南.html'
```

- [ ] **Step 5: Run tests and verify GREEN**

Run the complete `test_performance.py` command. Expected: all tests pass, image count stays 10, link checks pass, and size budgets remain green.

- [ ] **Step 6: Commit**

```powershell
git add optimize_site.py test_performance.py index.html
git commit -m "Standardize screenshot cards"
```

---

### Task 3: Mobile Visual QA and Original-Link Deployment

**Files:**
- Verify: `index.html`
- Deploy: GitHub Pages branch `main`

**Interfaces:**
- Consumes: the generated site from Task 2.
- Produces: a public, cache-independent verification of the original URL.

- [ ] **Step 1: Run local mobile QA**

Serve the repository locally, open it at 360×800 and 390×844, and emulate dark mode. Scroll through all nine frames and assert:

```javascript
({
  uniformFrames: document.querySelectorAll('.uniform-shot').length === 9,
  imageStages: document.querySelectorAll('.image-stage').length === 8,
  noOverflow: document.documentElement.scrollWidth <= innerWidth,
  allImagesLoaded: [...document.images].every(i => i.complete && i.naturalWidth > 0)
})
```

Capture a full-page screenshot and inspect every red marker, both mosaics, and the App icon card.

- [ ] **Step 2: Push the implementation**

```powershell
git push origin main
gh api --method POST repos/hu18310055211-coder/ima-kids-self-drive-guide/pages/builds
```

Wait until the Pages build status is `built` for the new commit.

- [ ] **Step 3: Verify the original public URL without a version query**

Open `https://hu18310055211-coder.github.io/ima-kids-self-drive-guide/` in a fresh browser context with cache disabled. Repeat the structural assertions, verify console errors and warnings are both zero, and confirm the ima join link remains unchanged.

- [ ] **Step 4: Final regression check**

Run the complete Python test suite once more and verify `git status --short` is empty.
