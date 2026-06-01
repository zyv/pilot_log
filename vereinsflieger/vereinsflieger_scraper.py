from typing import Self

from playwright.async_api import ViewportSize, async_playwright

from vereinsflieger.models import Flight


class VereinsfliegerScraperSession:
    BASE_URL = "https://vereinsflieger.de"

    def __init__(self, username: str, password: str, debug: bool = False):
        self.username = username
        self.password = password
        self.debug = debug
        self._counter = 0

        assert self.username is not None
        assert self.password is not None

    async def __aenter__(self) -> Self:
        self.playwright = await async_playwright().start()
        # self.browser = await self.playwright.firefox.launch(headless=self.debug)

        self.browser = await self.playwright.chromium.launch(
            headless=self.debug,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport=ViewportSize(width=1920, height=1080),
            device_scale_factor=1,
            extra_http_headers={
                "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
        )

        self.page = await self.context.new_page()

        await self.page.add_init_script("""
            // Redefine navigator.webdriver to fully hide it
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock languages array which can sometimes drop to empty in headless
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });

            // Mock hardware concurrency to look like a real consumer machine
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
        """)

        await self.sign_in()

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.sign_out()
        await self.page.close()
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def _screenshot(self, stage: str):
        if self.debug:
            await self.page.screenshot(path=f"vf-{str(self._counter).zfill(2)}-{stage}.png")
            self._counter += 1

    async def sign_in(self):
        await self.page.goto(self.BASE_URL)
        await self.page.wait_for_load_state("load")

        await self.page.get_by_placeholder("Benutzer oder E-Mail").fill(self.username)
        await self.page.get_by_placeholder("Passwort").fill(self.password)

        await self._screenshot("before-sign-in")

        await self.page.get_by_role("button", name="Anmelden").click()
        await self.page.wait_for_url(f"{self.BASE_URL}/member/overview/overview")

        await self._screenshot("after-sign-in")

    async def sign_out(self):
        await self._screenshot("before-logout")

        await self.page.locator("#topnavi").get_by_text("Abmelden").click()
        await self.page.wait_for_load_state("load")

        await self._screenshot("after-logout")

    async def get_flight(self, fid: int) -> Flight:
        await self._screenshot(f"before-flight-{fid}")

        await self.page.goto(f"{self.BASE_URL}/member/profile/viewflight.php?flid={fid}")
        await self.page.wait_for_load_state("load")

        await self._screenshot(f"after-flight-{fid}")

        return await Flight.from_vereinsflieger_scraper(self.page)
