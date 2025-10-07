
from pathlib import Path

from model.engine import PNPEngine
from model.objects.setup import Setup


def main() -> None:
    setup_path = Path("input/test_1/setup.xlsx")
    setup = Setup(setup_path)
    setup.load_data()

    engine = PNPEngine(setup)
    results = engine.run()

    results.sequence_df.to_csv("output/final_sequence.csv", index=False)

if __name__ == "__main__":
    main()
