

import uuid
from sqlalchemy import create_engine, text,Column, Integer, String, Date, DateTime, Boolean, Numeric, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker,declarative_base


  # ← Add this import





Base = declarative_base()


class Player(Base):
    __tablename__ = "players"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    username = Column(String(50), unique=True)
    country = Column(String(50))
    date_of_birth = Column(Date)
    elo_rating = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))


class Team(Base):
    __tablename__ = "teams"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    name = Column(String(100), unique=True)
    region = Column(String(50))
    founded_at = Column(Date)
    prize_pool = Column(Numeric(15, 2))
    is_active = Column(Boolean, default=True)


class TeamRoster(Base):
    __tablename__ = "team_rosters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    role = Column(String(40))
    joined_at = Column(Date)
    left_at = Column(Date)


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    name = Column(String(50))
    game = Column(String(50))
    prize_pool = Column(Numeric(15, 2))
    starts_at = Column(DateTime(timezone=True))
    status = Column(String(20))


class Match(Base):
    __tablename__ = "matches"

    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,                    # ← Fixed
        server_default=text("gen_random_uuid()")
    )
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"))
    team_a_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    team_b_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    winner_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    played_at = Column(DateTime(timezone=True))


class PlayerStat(Base):
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    kills = Column(Integer)
    deaths = Column(Integer)
    assists = Column(Integer)
    damage_dealt = Column(Numeric(12, 2))
    headshot_pct = Column(Numeric(5, 2))


class EloHistory(Base):
    __tablename__ = "elo_history"

    id = Column(Integer, primary_key=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"))
    elo_before = Column(Integer)
    elo_after = Column(Integer)
    changed_at = Column(DateTime(timezone=True), server_default=text("NOW()"))


class PrizePayout(Base):
    __tablename__ = "prize_payouts"

    id = Column(Integer, primary_key=True)                    # ← Changed
    tournament_id = Column(UUID(as_uuid=True), ForeignKey("tournaments.id"))
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    amount = Column(Numeric(12, 2))
    paid_at = Column(DateTime(timezone=True))


class PlayerBan(Base):
    __tablename__ = "player_bans"

    id = Column(Integer, primary_key=True)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    reason = Column(String)
    banned_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    expires_at = Column(DateTime(timezone=True))
    is_permanent = Column(Boolean, default=False)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(20))
    operation = Column(String(50))
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    changed_at = Column(DateTime(timezone=True), server_default=text("NOW()"))