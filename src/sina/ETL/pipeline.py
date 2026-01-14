import logging
from pathlib import Path
from sina.ETL.extract_gas import extract_gas
from sina.ETL.extract_qqp import extract_qqp
#from jita.ETL.extract_casa_ley import extract_otro

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

OUTPUT_DIR = Path("data_output")
OUTPUT_DIR.mkdir(exist_ok=True)

def main():
    logging.info("🚀 Iniciando pipeline ETL...")

    df_gasolina = extract_gas()
    df_qqp = extract_qqp()

    # Ejemplo: guardar cada dataset por separado
    df_gasolina.to_parquet(OUTPUT_DIR / "gasolina.parquet", index=False)
    df_qqp.to_parquet(OUTPUT_DIR / "qqp.parquet", index=False)

    logging.info("🎉 Pipeline completado exitosamente")

if __name__ == "__main__":
    main()
