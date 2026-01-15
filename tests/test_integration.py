import pytest
import subprocess
import time
import os
import json
import signal
from src.init_db import init_db
from src.sync import sync_and_match
from src.models import db, BankTransaction
from src.app import create_app

# Global process handle
mock_api_process = None

@pytest.fixture(scope="module", autouse=True)
def setup_teardown():
    global mock_api_process

    # 1. Setup Mock Data
    invoices = [
        {"id": "code:FAK1", "kod": "FAK1", "varSym": "1001", "sumCelkem": "1000.0", "buc": "123/0100", "nazev": "Client A"},
        {"id": "code:FAK2", "kod": "FAK2", "varSym": "1002", "sumCelkem": "2000.0", "buc": "456/0100", "nazev": "Client B"}
    ]
    bank = [
        {"id": "code:BAN1", "cisloDokl": "BAN1", "varSym": "1001", "sumCelkem": "1000.0", "buc": "123/0100", "nazev": "Client A", "datVyst": "2024-01-01"}, # Exact match
        {"id": "code:BAN2", "cisloDokl": "BAN2", "varSym": "1002", "sumCelkem": "2500.0", "buc": "456/0100", "nazev": "Client B", "datVyst": "2024-01-02"}, # Overpayment
        {"id": "code:BAN3", "cisloDokl": "BAN3", "varSym": "9999", "sumCelkem": "500.0", "buc": "789/0100", "nazev": "Unknown", "datVyst": "2024-01-03"}  # No match
    ]

    with open("mock_invoices.json", "w") as f:
        json.dump(invoices, f)
    with open("mock_bank.json", "w") as f:
        json.dump(bank, f)

    # 2. Start Mock API
    # Assuming we are in root
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    mock_api_process = subprocess.Popen(
        ["python", "mock_api/server.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2) # Give it time to start

    # 3. Init DB
    db_path = os.path.join("instance", "app.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # We need to run init_db logic but specifically for the test context if possible
    # Or just rely on sync.py creating app context which uses `sqlite:///app.db`
    # Ideally we use a test db, but for this integration test `app.db` is fine as long as we clean up.
    # Let's call init_db programmatically
    init_db()

    yield

    # Teardown
    if mock_api_process:
        mock_api_process.terminate()
        try:
            mock_api_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            mock_api_process.kill()

    db_path = os.path.join("instance", "app.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    # Clean up json files
    # os.remove("mock_invoices.json")
    # os.remove("mock_bank.json")


def test_integration_sync():
    # Run the sync logic
    # Ensure env vars point to localhost:5000 (default in code, but explicit is good)
    os.environ["FLEXI_URL"] = "http://localhost:5000"

    sync_and_match()

    # Verify results in DB
    app = create_app()
    with app.app_context():
        # BAN1 should be MATCHED
        ban1 = BankTransaction.query.filter_by(flexi_id="code:BAN1").first()
        assert ban1 is not None
        assert ban1.status == 'MATCHED'

        # BAN2 should be CREDIT (Overpayment > 10%)
        # Invoice 2000, Pay 2500. Diff 500. 10% of 2000 is 200. 500 > 200.
        ban2 = BankTransaction.query.filter_by(flexi_id="code:BAN2").first()
        assert ban2 is not None
        assert ban2.status == 'CREDIT'

        # BAN3 should be PENDING (if no logic handled it) or stayed PENDING because no match found
        # In sync.py: "No match found for..." -> status remains PENDING (or whatever it was initialized as)
        # initialized as PENDING.
        ban3 = BankTransaction.query.filter_by(flexi_id="code:BAN3").first()
        assert ban3 is not None
        assert ban3.status == 'PENDING'
