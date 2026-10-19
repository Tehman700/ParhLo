"""PDF in the morning email: signed links, the attachment, and the email text (offline)."""

import time
from datetime import date

from app.parhlo import digest, mailer

USER = {"id": "1b4e28ba-2fa1-11d2-883f-0016d3cca427", "name": "Hina", "email": "hina@example.com"}
PAPER = {"number": 7, "reader": {"name": "Hina", "city": "Lahore"}, "lead_id": 1, "editor_note": "Note.",
         "stories": [{"id": 1, "headline": "Pakistan beat Australia", "summary": "Won by six wickets.",
                      "source": "Dawn", "topics": ["cricket"]}]}


def test_signed_pdf_link_verifies_and_expires():
    exp = int(time.time()) + 60
    token = digest.pdf_token(USER["id"], "2026-10-19", exp)
    assert digest.verify_pdf(USER["id"], "2026-10-19", exp, token)
    assert not digest.verify_pdf(USER["id"], "2026-10-18", exp, token)          # another day
    assert not digest.verify_pdf("someone-else", "2026-10-19", exp, token)      # another reader
    assert not digest.verify_pdf(USER["id"], "2026-10-19", exp + 1, token)      # tampered expiry
    old = int(time.time()) - 1
    assert not digest.verify_pdf(USER["id"], "2026-10-19", old, digest.pdf_token(USER["id"], "2026-10-19", old))


def test_shared_route_rejects_bad_links(client):
    r = client.get("/api/editions/2026-10-19/shared", params={"u": USER["id"], "e": int(time.time()) + 60, "t": "nope"})
    assert r.status_code == 401
    r = client.get("/api/editions/2026-10-19/shared", params={"u": "not-a-uuid", "e": 1, "t": "x"})
    assert r.status_code == 401


def test_email_says_attached_and_links_signed_pdf():
    _, html, text = digest.render(USER, PAPER, date(2026, 10, 19), attached=True)
    assert "Your newspaper PDF is attached" in html and "Your newspaper PDF is attached" in text
    assert f"/pdf/2026-10-19?u={USER['id']}&amp;e=" in html or f"/pdf/2026-10-19?u={USER['id']}&e=" in html
    _, html2, _ = digest.render(USER, PAPER, date(2026, 10, 19))
    assert "Download the PDF" in html2 and "attached" not in html2


def test_message_carries_the_pdf_attachment():
    msg = mailer._message("hina@example.com", "Your paper", "<p>hi</p>", "hi",
                          headers={"List-Unsubscribe": "<https://x/u>"},
                          attachments=[("ParhLo-2026-10-19.pdf", b"%PDF-1.7 test", "application/pdf")])
    parts = [p for p in msg.iter_attachments()]
    assert len(parts) == 1 and parts[0].get_filename() == "ParhLo-2026-10-19.pdf"
    assert parts[0].get_content_type() == "application/pdf" and parts[0].get_content() == b"%PDF-1.7 test"
    assert msg["List-Unsubscribe"] == "<https://x/u>"
    assert not list(mailer._message("a@b.c", "s", "<p>h</p>", "h").iter_attachments())   # no attachment by default
