"""Browser acceptance checks; run against the demo backend and a built frontend.

uv run --with playwright python scripts/check_browser.py --url http://localhost:4173
Install Chromium with `uv run --with playwright playwright install chromium` first,
or pass --browser /path/to/chrome. Playwright is optional QA tooling, not an app dependency.
"""

import argparse
import json
import sys

from playwright.sync_api import expect, sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:4173")
    parser.add_argument("--browser", default=None)
    parser.add_argument("--angle", default=None, help="Use gl for a hardware OpenGL run")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        flags = ["--no-sandbox"] + ([f"--use-angle={args.angle}"] if args.angle else [])
        browser = playwright.chromium.launch(executable_path=args.browser, args=flags)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.add_init_script("""const NativeWorker = Worker;
            window.Worker = class extends NativeWorker {
                constructor(...args) {
                    super(...args);
                    this.addEventListener('message', e => {
                        if (e.data?.type === 'done') window.qaWorkerMs = e.data.ms;
                    });
                }
            };
        """)
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until="domcontentloaded")
        for label, query in [("Origin", "Denver"), ("Destination", "Salt Lake City")]:
            page.get_by_role("combobox", name=label, exact=True).fill(query)
            page.get_by_role("listbox", name=f"{label} suggestions").get_by_role(
                "option"
            ).first.click()
        departure = page.get_by_label("Departure", exact=True)
        departure.fill(departure.input_value()[:14] + "30")
        with page.expect_response(lambda r: "/api/v1/plans" in r.url) as plan_response:
            page.get_by_role("button", name="Plan route", exact=True).click()
        plan = plan_response.value.json()
        assert len(plan["routes"]) == 3, plan
        assert plan["assumptions"]["providers"] == "fake"
        page.get_by_role("radiogroup", name="Route options").wait_for()
        slider = page.get_by_role("slider", name="Forecast time")
        page.wait_for_function("document.querySelector('input[type=range]')?.disabled === false")
        page.wait_for_timeout(1500)
        assert not errors, errors
        assert page.evaluate("document.documentElement.scrollHeight === innerHeight")
        api_requests: list[str] = []
        page.on(
            "request",
            lambda request: api_requests.append(request.url) if "/api/" in request.url else None,
        )
        page.evaluate("""() => {
            window.qaLongTasks = [];
            window.qaFrames = [];
            window.qaTracking = true;
            requestAnimationFrame(function tick(t) {
                window.qaFrames.push(t);
                if (window.qaTracking) requestAnimationFrame(tick);
            });
            new PerformanceObserver(list => window.qaLongTasks.push(
                ...list.getEntries().map(e => e.duration)
            )).observe({type: 'longtask'});
        }""")
        slider.focus()
        slider.press("ArrowRight")
        assert slider.input_value() == "1"
        slider.press("Shift+ArrowRight")
        assert slider.input_value() == "7"
        box = slider.bounding_box()
        assert box
        page.mouse.move(box["x"], box["y"] + box["height"] / 2)
        page.mouse.down()
        for step in range(120):
            page.mouse.move(box["x"] + box["width"] * step / 120, box["y"] + box["height"] / 2)
            page.wait_for_timeout(40)
        page.mouse.up()
        assert not api_requests, api_requests
        long_tasks = page.evaluate("window.qaLongTasks")
        metrics = page.evaluate("""() => {
            window.qaTracking = false;
            const frames = window.qaFrames;
            const canvas = document.querySelector('.maplibregl-canvas');
            const gl = canvas.getContext('webgl2') || canvas.getContext('webgl');
            const info = gl.getExtension('WEBGL_debug_renderer_info');
            return {
                fps: (frames.length - 1) * 1000 / (frames.at(-1) - frames[0]),
                renderer: info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : 'unknown',
                worker_ms: window.qaWorkerMs
            };
        }""")
        page.emulate_media(reduced_motion="reduce")
        expect(page.get_by_role("button", name="Play forecast")).to_be_disabled()
        slider.press("Home")
        slider.press("Space")
        assert slider.input_value() == "0"
        for width, height in [(1200, 700), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(200)
            assert page.evaluate("document.documentElement.scrollHeight === innerHeight")
            assert page.evaluate("document.documentElement.scrollWidth === innerWidth")
        assert not errors, errors
        sys.stdout.write(
            json.dumps(
                {
                    "routes": 3,
                    "departure_minute": 30,
                    "slider_api_requests": len(api_requests),
                    "layout": "desktop and mobile pass",
                    "reduced_motion": "pass",
                    "slider_long_tasks_ms": long_tasks,
                    **metrics,
                },
                indent=2,
            )
            + "\n"
        )
        browser.close()


if __name__ == "__main__":
    main()
