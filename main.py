from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from model.engine import PNPEngine
from model.objects.setup import Setup


def main() -> None:
    start_ts = datetime.now(tz=ZoneInfo("Europe/London")).strftime("%Y-%m-%dT%H_%M_%S")
    output_dir = Path(f"output/results_{start_ts}")
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_path = Path("input/test_2/setup.xlsx")
    setup = Setup(setup_path)
    setup.load_data()

    engine = PNPEngine(setup, save_figs=True)
    results = engine.run()

    for job_id, fig in engine.fig_by_job.items():
        fig.savefig(output_dir / f"{job_id}.png")
    results.to_csv(output_dir / "full_sequence.csv", index=False)

if __name__ == "__main__":
    main()
