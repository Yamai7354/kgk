import os

from cli.main import main


def test_cli_ingest_and_search(tmp_path, capsys):
    db_file = tmp_path / "cli_test.db"
    db_str = str(db_file)

    try:
        # Ingest statement
        ret_ingest = main(
            [
                "--db",
                db_str,
                "ingest",
                "--subject",
                "Mina",
                "--relation",
                "hobby",
                "--object",
                "Guitar",
                "--confidence",
                "0.95",
            ]
        )
        assert ret_ingest == 0
        captured = capsys.readouterr().out
        assert "[OK] Ingested Statement" in captured

        # Search
        ret_search = main(
            [
                "--db",
                db_str,
                "search",
                "--query",
                "Mina",
            ]
        )
        assert ret_search == 0
        search_out = capsys.readouterr().out
        assert "Mina" in search_out

        # Replay
        ret_replay = main(
            [
                "--db",
                db_str,
                "replay",
            ]
        )
        assert ret_replay == 0
        replay_out = capsys.readouterr().out
        assert "[OK] Replay Completed Successfully" in replay_out
    finally:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except Exception:
                pass
