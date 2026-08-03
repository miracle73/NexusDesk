from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import Document, Tenant, User
from app.services.knowledge import chunks, knowledge

FAQS = """# CiphezNexus FAQs
NexusDesk is an AI customer-support workspace for company knowledge, customer conversations, and human escalations.
Support hours are Monday to Friday, 9:00 to 17:00 UK time.
Customers can request a password reset from the account Security page. A reset link expires after 30 minutes.
Billing questions and refund requests are reviewed by a human support specialist.
Uploaded company documents are isolated by tenant and are never shared with other companies.
"""


def seed_demo(db: Session) -> None:
    if db.scalar(select(User).where(User.email == settings.demo_email)):
        return
    tenant = Tenant(name="CiphezNexus Demo", slug="cipheznexus-demo")
    user = User(tenant=tenant, email=settings.demo_email, password_hash=hash_password(settings.demo_password))
    db.add(user)
    db.flush()
    text_chunks = chunks(FAQS)
    document = Document(tenant_id=tenant.id, filename="demo-faqs.md", content_type="text/markdown", chunk_count=len(text_chunks))
    db.add(document)
    db.commit()
    knowledge.add(tenant.id, document.id, document.filename, text_chunks)
