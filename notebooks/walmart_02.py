from playwright.sync_api import sync_playwright


PROFILE_DIR = "./walmart_profile"


with sync_playwright() as p:

    context = p.chromium.launch_persistent_context(

        PROFILE_DIR,

        channel="chrome",

        headless=False,

        viewport={
            "width": 1366,
            "height": 768
        }
    )

    page = context.new_page()

    page.goto(
        "https://www.walmart.com.mx",
        wait_until="domcontentloaded"
    )

    print("\nRESUELVE EL CAPTCHA MANUALMENTE")
    print("Luego navega un poco por Walmart.")
    print("Cuando termines, presiona ENTER.")

    input()

    context.close()