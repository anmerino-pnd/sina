from playwright.sync_api import sync_playwright
import json
from pathlib import Path


CONFIG_PATH = Path(
    "src/sina/config/walmart_config.json"
)

PROFILE_DIR = "./walmart_profile"


def extraer_arbol_walmart():

    print("🛒 Explorador Walmart iniciado")

    categorias = {}

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

        try:

            print("🌐 Entrando a Walmart")

            page.goto(
                "https://www.walmart.com.mx/all-departments",
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            # Verificar bloqueo
            contenido = page.content().lower()

            if "verifica tu identidad" in contenido:

                print(
                    "\n⚠️ Walmart activó challenge."
                )

                print(
                    "Resuélvelo manualmente."
                )

                input(
                    "\nPresiona ENTER cuando termines..."
                )

            print("🔍 Extrayendo categorías")

            # Esperar contenedor principal
            page.wait_for_selector(
                "div.ld.Dc.ld_Dd",
                timeout=30000
            )

            tarjetas = page.locator(
                "div.ld.Dc.ld_Dd > div"
            ).all()

            print(
                f"📦 Tarjetas detectadas: "
                f"{len(tarjetas)}"
            )

            for tarjeta in tarjetas:

                try:

                    titulo = (
                        tarjeta.locator("h2")
                        .inner_text()
                        .strip()
                    )

                    links = tarjeta.locator("a").all()

                    categorias[titulo] = {}

                    for link in links:

                        try:

                            texto = (
                                link.inner_text()
                                .strip()
                            )

                            href = link.get_attribute(
                                "href"
                            )

                            if not texto or not href:
                                continue

                            if not href.startswith("/"):
                                continue

                            categorias[titulo][
                                texto
                            ] = {
                                "url_path": href
                            }

                        except Exception:
                            continue

                except Exception:
                    continue

        except Exception as e:

            print(f"❌ Error: {e}")

        finally:

            context.close()

    CONFIG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        CONFIG_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            categorias,
            f,
            ensure_ascii=False,
            indent=4
        )

    total = sum(
        len(v)
        for v in categorias.values()
    )

    print("\n✅ FINALIZADO")
    print(f"Departamentos: {len(categorias)}")
    print(f"Categorías: {total}")


if __name__ == "__main__":

    extraer_arbol_walmart()