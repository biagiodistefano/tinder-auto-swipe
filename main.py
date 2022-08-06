import typer
from autoswipe import HornyFucker


def main(
    token: str = typer.Option(..., help="Tinder X-Auth token"),
    save: bool = typer.Option(False, help="Save activity locally"),
    surge: bool = typer.Option(False, help="Swipe like a maniac"),
    data_dir: str = typer.Option(None, help="Directory where to save data. Defaults to 'data'"),
):
    hf = HornyFucker(token=token, save_activity=save, data_dir=data_dir)
    hf.swipe_loop(surge=surge)


if __name__ == '__main__':
    typer.run(main)
