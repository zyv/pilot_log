from playwright.async_api import async_playwright

from vereinsflieger.models import Flight


class VereinsfliegerScraperSession:
    BASE_URL = "https://www.vereinsflieger.de"

    def __init__(self, username: str, password: str, debug: bool = False):
        self.username = username
        self.password = password
        self.debug = debug
        self._counter = 0

        assert self.username is not None and self.password is not None, "invalid credentials"

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.firefox.launch(headless=self.debug)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
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
