from database.connection import get_engine, get_session
from database.models import Base, Portfolio
from config import DEFAULT_PORTFOLIO_NAME


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    _seed_default_portfolio()


def _seed_default_portfolio():
    session = get_session()
    try:
        existing = session.query(Portfolio).filter_by(name=DEFAULT_PORTFOLIO_NAME).first()
        if not existing:
            portfolio = Portfolio(
                name=DEFAULT_PORTFOLIO_NAME,
                description="Default portfolio"
            )
            session.add(portfolio)
            session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
